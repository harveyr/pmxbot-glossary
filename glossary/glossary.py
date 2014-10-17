import datetime
import json
import random
import string
import time
from collections import namedtuple

from dateutil.parser import parse as parse_date

import pmxbot
from pmxbot import storage
from pmxbot.core import command

DEFINE_COMMAND = 'define'
QUERY_COMMAND = 'whatis'
SEARCH_COMMAND = 'search'

HELP_DEFINE_STR = '!{} <entry>: <definition>'.format(DEFINE_COMMAND)
HELP_QUERY_STR = '!{} <entry> [<num>]'.format(QUERY_COMMAND)
HELP_SEARCH_STR = '!{} <search terms>'.format(SEARCH_COMMAND)

DOCS_STR = (
    'To define a glossary entry: `{}`. '
    'To get a definition: `{}`. '
    'To search for entries: `{}`. '
    'Pass in an integer >= 1 to get a definition from the history. '
    'Get a random definition by omitting the entry argument.'
).format(HELP_DEFINE_STR, HELP_QUERY_STR, HELP_SEARCH_STR)

OOPS_STR = "I didn't understand that. " + DOCS_STR

ADD_DEFINITION_RESULT_TEMPLATE = u'Okay! "{entry}" is now "{definition}"'

QUERY_RESULT_TEMPLATE = (
    u'{entry} ({num}/{total}): {definition} [defined by {author} {age}]'
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

        if load_fixtures:
            cls.load_fixtures()

        cls._finalizers.append(cls.finalize)

    @classmethod
    def finalize(cls):
        del cls.store

    @classmethod
    def load_fixtures(cls, path=None):
        config_path_key = 'glossary_fixtures_path'

        if not path:
            path = pmxbot.config.get(config_path_key)

        if not path:
            print('- No fixtures path provided.')

        try:
            with open(path) as f:
                print('- Loading fixtures from ' + path)
                data = json.load(f)
                cls.save_entries(data)
        except IOError:
            print('- No fixtures file found at path {}'.format(path))

    @classmethod
    def save_entries(cls, data):
        """
        Save a dictionary of entries and definitions to the store.

        If the definition already exists in the history for the entry,
        this will not re-add it.
        """
        for entry, definition in data.items():
            existing = cls.store.get_all_records_for_entry(entry)
            existing_defs = [e.definition for e in existing]

            if definition not in existing_defs:
                cls.store.add_entry(entry, definition, 'the defaults')


class SQLiteGlossary(Glossary, storage.SQLiteStorage):
    CREATE_GLOSSARY_SQL = """
      CREATE TABLE IF NOT EXISTS glossary (
       entryid INTEGER PRIMARY KEY AUTOINCREMENT,
       entry VARCHAR NOT NULL,
       definition TEXT NOT NULL,
       author VARCHAR NOT NULL,
       timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    def bust_all_entries_cache(self):
        if self.ALL_ENTRIES_CACHE_KEY in self.cache:
            del self.cache[self.ALL_ENTRIES_CACHE_KEY]

    def add_entry(self, entry, definition, author):
        entry = entry.lower()

        sql = """
          INSERT INTO glossary (entry, definition, author)
          VALUES (?, ?, ?)
        """

        self.db.execute(sql, (entry, definition, author))
        self.db.commit()
        self.bust_all_entries_cache()

        return self.get_entry_data(entry)

    def get_all_entries(self):
        """
        Returns list of all entries in the glossary.
        """
        cache_key = 'all_entries'
        entries = self.cache.get(cache_key)

        if entries is None:
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
        # Entry numbering starts at 1
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
            datetime_ = parse_date(row[-1])

            entry_data.append(
                GlossaryQueryResult(
                    row[0],
                    row[1],
                    row[2],
                    datetime_,
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
    hours = int(seconds / 3600)

    if hours > 1:
        return '{} hours ago'.format(hours)

    if hours == 1:
        return '1 hour ago'

    minutes = int(seconds / 60)

    if minutes > 1:
        return '{} minutes ago'.format(minutes)

    if minutes == 1:
        return '1 minute ago'

    return 'just now'


def readable_join(items, conjunction='or'):
    """
    Returns an oxford-comma-joined string with "or."

    E.g., ['thing1', 'thing2', 'thing3'] becomes "thing1, thing2, or thing3".
    """
    if not items:
        return None

    count = len(items)

    if count == 1:
        s = items[0]
    elif count == 2:
        template = u' {} '.format(conjunction)
        s = template.join(items)
    else:
        s = u'{}, {} {}'.format(u', '.join(items[:-1]), conjunction, items[-1])

    return s


def get_alternative_suggestions(entry):
    """
    Returns a set of entries that may be similar to the provided entry.

    Useful for trying to find near misses. E.g., "run" is not defined but
    "running" is.
    """
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
    entry = entry.strip()

    if num is not None:
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

    # No result found. Check if there are any similar entries that may be
    # relevant.
    suggestions = list(get_alternative_suggestions(entry))[:10]

    if suggestions:
        suggestion_str = (
            u' May I interest you in {}?'.format(readable_join(suggestions))
        )
    else:
        suggestion_str = u''

    return u'"{}" is undefined.{}'.format(entry, suggestion_str)


def handle_search(rest):
    """
    Returns formatted list of entries found with the given search string.
    """
    term = rest.split('search', 1)[-1].strip()

    entry_matches = set(Glossary.store.get_similar_words(term))
    def_matches = set(Glossary.store.search_definitions(term))

    matches = sorted(list(entry_matches | def_matches))

    if not matches:
        return 'No glossary results found.'
    else:
        result = (
            u'Found glossary entries: {}. To get a definition: !{} <entry>'
        ).format(readable_join(matches, conjunction='and'), QUERY_COMMAND)

        return result




@command(DEFINE_COMMAND, doc=DOCS_STR)
def define(client, event, channel, nick, rest):
    """
    Add a definition for a glossary entry.
    """
    rest = rest.strip()

    if rest.lower() == 'help':
        return DOCS_STR

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


@command(QUERY_COMMAND, doc=DOCS_STR)
def query(client, event, channel, nick, rest):
    """
    Retrieve a definition of an entry.
    """
    rest = rest.strip()

    if not rest:
        return handle_random_query()

    if rest.lower() == 'help':
        return DOCS_STR

    if ':' in rest:
        parts = rest.split(':', 1)
        entry, num = parts[0].strip(), parts[1].strip()

        if not num.isdigit():
            return OOPS_STR

        return handle_nth_definition(entry, num)

    return handle_nth_definition(rest)


@command(SEARCH_COMMAND, doc=DOCS_STR)
def search(client, event, channel, nick, rest):
    """
    Search the entries and defintions.
    """
    rest = rest.strip()

    if rest.lower() == 'help':
        return DOCS_STR

    if not rest:
        return OOPS_STR

    return handle_search(rest)
