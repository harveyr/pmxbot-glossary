import datetime
import json
import random
import string
import time
from collections import namedtuple

import pmxbot
from pmxbot import storage
from pmxbot.core import command

DEFINE_COMMAND = 'define'
GET_COMMAND = 'whatis'

HELP_DEFINE_STR = '!{} <entry>: <definition>'.format(DEFINE_COMMAND)
HELP_QUERY_STR = '!{} <entry> [<num>]'.format(GET_COMMAND)

DOCS_STR = (
    'To define a glossary entry: `{}`. '
    'To get a definition: `{}`. '
    'Pass in an integer >= 1 to get a definition from the history. '
    'Get a random definition by omitting the entry argument.'
).format(HELP_DEFINE_STR, HELP_QUERY_STR)

OOPS_STR = "I didn't understand that. " + DOCS_STR

ADD_DEFINITION_RESULT_TEMPLATE = u'Okay! "{entry}" is now "{definition}"'

QUERY_RESULT_TEMPLATE = (
    u'{entry} ({num}/{total}): {definition} [by {author}, {age}]'
)


class Glossary(storage.SelectableStorage):
    """
    Glossary class.

    The usage of SelectableStorage, SQLiteStorage, and cls.store are cribbed
    from the pmxbot quotes module.
    """
    @classmethod
    def initialize(cls, db_uri=None, load_fixtures=True):
        db_uri = db_uri or pmxbot.config.database
        cls.store = cls.from_URI(db_uri)

        # for item in Handler._registry:
        #     print(item)

        if load_fixtures:
            cls.load_fixtures()

        cls._finalizers.append(cls.finalize)

    @classmethod
    def finalize(cls):
        del cls.store

    @classmethod
    def load_fixtures(cls, path='glossary_fixtures.json'):
        try:
            with open(path) as f:
                print('- Loading fixture data from ' + path)
                data = json.load(f)
                cls.save_entries(data)
        except IOError:
            print('- No fixture data found.')

    @classmethod
    def save_entries(cls, data):
        """
        Save a dictionary of entries and definitions to the store.
        """
        for entry, definition in data.items():
            existing = cls.store.get_all_records_for_entry(entry)
            existing_defs = [e.definition for e in existing]

            if definition not in existing_defs:
                cls.store.add_entry(entry, definition, '<default>')


class SQLiteGlossary(Glossary, storage.SQLiteStorage):
    CREATE_GLOSSARY_SQL = """
      CREATE TABLE IF NOT EXISTS glossary (
       entryid INTEGER NOT NULL,
       entry VARCHAR NOT NULL,
       definition TEXT NOT NULL,
       author VARCHAR NOT NULL,
       timestamp INTEGER NOT NULL,
       PRIMARY KEY (entryid)
    )
    """

    CREATE_GLOSSARY_INDEX_SQL = """
      CREATE INDEX IF NOT EXISTS ix_glossary_entry ON glossary(entry)
    """

    ALL_ENTRIES_CACHE_KEY = 'all_entries'

    cache = {}

    def init_tables(self):
        self.db.execute(self.CREATE_GLOSSARY_SQL)
        self.db.execute(self.CREATE_GLOSSARY_INDEX_SQL)
        self.db.commit()

    def add_entry(self, entry, definition, author):
        entry = entry.lower()

        sql = """
          INSERT INTO glossary (entry, definition, author, timestamp)
          VALUES (?, ?, ?, ?)
        """

        timestamp = int(time.mktime(datetime.datetime.utcnow().utctimetuple()))

        self.db.execute(sql, (entry, definition, author, timestamp))
        self.db.commit()

        if self.ALL_ENTRIES_CACHE_KEY in self.cache:
            del self.cache[self.ALL_ENTRIES_CACHE_KEY]

        return self.get_entry_data(entry)

    def get_all_entries(self):
        """
        Returns list of all entries in the glossary.
        """
        cache_key = 'all_entries'
        entries = self.cache.get(cache_key)

        if not entries:
            sql = """
              SELECT DISTINCT entry
              FROM glossary
            """
            query = self.db.execute(sql).fetchall()
            entries = [r[0] for r in query]
            self.cache[cache_key] = entries

        return entries

    def get_random_entry(self):
        """
        Returns a random entry from the glossary.
        """
        entries = self.get_all_entries()

        if not entries:
            return None

        return random.choice(entries)

    def get_entry_data(self, entry, num=None):
        """
        Returns GlossaryQueryResult for an entry in the glossary.

        If ``num`` is provided, returns the object for that version of the
        definition in history.
        """
        if num is not None and num < 1:
            raise IndexError

        stored = self.get_all_records_for_entry(entry)

        if not stored:
            return None

        if num:
            return stored[num - 1]

        return stored[-1]

    def get_all_records_for_entry(self, entry):
        """
        Returns a list of objects for all definitions of an entry.
        """
        entry = entry.lower()

        sql = """
            SELECT entry, definition, author, timestamp
            FROM glossary
            WHERE entry LIKE ?
            ORDER BY timestamp
        """

        results = self.db.execute(sql, (entry, )).fetchall()

        entry_data = []
        total_count = len(results)

        for i, row in enumerate(results):
            entry_data.append(
                GlossaryQueryResult(
                    row[0],
                    row[1],
                    row[2],
                    datetime.datetime.fromtimestamp(float(row[-1])),
                    i,
                    total_count
                )
            )

        return entry_data

    def get_similar_words(self, search_str, limit=10):
        search_str = '%{}%'.format(search_str)

        sql = """
            SELECT DISTINCT entry
            FROM glossary
            WHERE entry LIKE ?
            ORDER BY entry
            LIMIT ?
        """

        results = self.db.execute(sql, (search_str, limit))

        return [r[0] for r in results]

    def search_definitions(self, search_str):
        """
        Returns entries whose definitions contain the search string.
        """
        search_str = '%{}%'.format(search_str)

        sql = """
            SELECT DISTINCT entry
            FROM glossary
            WHERE definition LIKE ?
            ORDER BY entry
        """

        results = self.db.execute(sql, (search_str, ))

        return [r[0] for r in results]


GlossaryQueryResult = namedtuple(
    'GlossaryQueryResult', 'entry definition author datetime index total_count'
)


def datetime_to_age_str(dt):
    """
    Returns a human-readable age given a datetime object.
    """
    age = (datetime.datetime.utcnow() - dt)
    days = age.days

    if days >= 365:
        return '{0:.1f} years ago'.format(days / 365.0)

    if days > 30:
        return '{0:.1f} months ago'.format(days / 30.5)

    if days > 1:
        return '{} days ago'.format(days)

    if days == 1:
        return 'yesterday'

    seconds = age.total_seconds()
    minutes = int(seconds / 60)
    hours = int(seconds / 3600)

    if hours > 1:
        return '{} hours ago'.format(hours)

    if hours == 1:
        return '1 hour ago'

    if minutes > 1:
        return '{} minutes ago'.format(minutes)

    if minutes == 1:
        return '1 minute ago'

    return 'just now'


def readable_join(items):
    """
    Returns an oxford-comma-joined string with "or".

    E.g., ['thing1', 'thing2', 'thing3'] becomes "thing1, thing2, or thing3".
    """
    if not items:
        return None

    count = len(items)

    if count == 1:
        s = items[0]
    elif count == 2:
        s = u' or '.join(items)
    else:
        s = u'{}, or {}'.format(u', '.join(items[:-1]), items[-1])

    return s


def get_alternative_suggestions(entry):
    query_words = set()

    for delim in (' ', '-', '_'):
        for part in entry.split(delim):
            query_words.add(part.strip().lower())

    results = set()

    for word in query_words:
        similar = Glossary.store.get_similar_words(word)

        if similar:
            results |= set(similar)

    return results


def handle_random_query():
    """
    Returns a formatted result string for a random entry.

    Uses the latest definition of the entry.
    """
    entry = Glossary.store.get_random_entry()

    if not entry:
        return "I can't find a single definition. " + DOCS_STR

    return handle_nth_definition(entry)


def handle_nth_definition(entry, num=None):
    """
    Returns a formatted result string for an entry.

    If ``num`` is passed, it will return the corresponding numbered, historical
    definition for the entry.
    """
    if num:
        try:
            num = int(num)
        except (ValueError, TypeError):
            return OOPS_STR

    try:
        query_result = Glossary.store.get_entry_data(entry, num)
    except IndexError:
        return u'"{}" is not a valid glossary entry number for "{}".'.format(
            num, entry
        )

    if query_result:
        return QUERY_RESULT_TEMPLATE.format(
            entry=query_result.entry,
            num=query_result.index + 1,
            total=query_result.total_count,
            definition=query_result.definition,
            author=query_result.author,
            age=datetime_to_age_str(query_result.datetime)
        )

    suggestions = list(get_alternative_suggestions(entry))[:10]

    if suggestions:
        suggestion_str = (
            u' May I interest you in {}?'.format(readable_join(suggestions))
        )
    else:
        suggestion_str = u''

    return u'"{}" is undefined.{}'.format(entry, suggestion_str)


def handle_search(rest):
    term = rest.split('search', 1)[-1].strip()

    entry_matches = set(Glossary.store.get_similar_words(term))
    def_matches = set(Glossary.store.search_definitions(term))

    matches = entry_matches | def_matches

    if not matches:
        return 'No glossary results found.'
    else:
        return u'Relevant entries: {}'.format(u', '.join(matches))


@command(DEFINE_COMMAND, doc=DOCS_STR)
def define(client, event, channel, nick, rest):
    """
    Add a definition for a glossary entry.
    """
    rest = rest.strip()

    if not ':' in rest:
        return OOPS_STR

    if '::' in rest:
        return "I can't handle '::' right now. Please try again without it."

    parts = rest.split(':', 1)

    if len(parts) != 2:
        return OOPS_STR

    entry = parts[0].strip()

    invalid_char = next((c for c in entry if c in string.punctuation), None)

    if invalid_char:
        return 'Punctation ("{}") cannot be used in a glossary entry.'.format(
            invalid_char
        )

    definition = parts[1].strip()

    existing = Glossary.store.get_entry_data(entry)

    if existing and existing.definition == definition:
        return "That's already the current definition."

    result = Glossary.store.add_entry(entry, definition, author=nick)

    return ADD_DEFINITION_RESULT_TEMPLATE.format(
        entry=result.entry,
        definition=result.definition
    )


@command(GET_COMMAND, doc=DOCS_STR)
def get(client, event, channel, nick, rest):
    if not rest:
        return handle_random_query()

    parts = rest.strip().split()

    if parts[-1].isdigit():
        entry = ' '.join(parts[:-1])
        num = int(parts[-1])

        return handle_nth_definition(entry, num)

    return handle_nth_definition(rest)
