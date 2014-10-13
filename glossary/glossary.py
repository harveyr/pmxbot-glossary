import datetime
import json
import random
import time
from collections import namedtuple

import pmxbot
from pmxbot import storage
from pmxbot.core import command

ALIASES = ('gl', )
HELP_DEFINE_STR = '!{} define <entry>: <definition>'.format(ALIASES[0])
HELP_QUERY_STR = '!{} <entry> [<num>]'.format(ALIASES[0])

DOCS_STR = (
    'To define an entry: `{}`. '
    'To get a definition: `{}`. '
    'Pass in an integer >= 1 to get a definition from the history. '
    'Get a random definition by omitting the entry argument.'
).format(HELP_DEFINE_STR, HELP_QUERY_STR)

OOPS_STR = 'One of us screwed this up. Hopefully you. ' + DOCS_STR

ADD_DEFINITION_RESULT_TEMPLATE = u'Okay! "{entry}" is now "{definition}"'

QUERY_RESULT_TEMPLATE =(
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

        timestamp = int(time.mktime(datetime.datetime.now().utctimetuple()))

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
              SELECT DISTINCT entry FROM glossary
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


GlossaryQueryResult = namedtuple(
    'GlossaryQueryResult', 'entry definition author datetime index total_count'
)


def datetime_to_age_str(dt):
    """
    Returns a human-readable age given a datetime object.
    """
    days = (datetime.datetime.utcnow() - dt).days

    if days >= 365:
        age_str = '{0:.1f} years ago'.format(days / 365.0)
    elif days > 30:
        age_str = '{0:.1f} months ago'.format(days / 30.5)
    elif days > 1:
        age_str = '{} days ago'.format(days)
    elif days == 1:
        age_str = 'yesterday'
    elif days == 0:
        age_str = 'today'
    else:
        age_str = '{} days ago'.format(days)

    return age_str


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

        if not num > 0:
            return OOPS_STR

    try:
        query_result = Glossary.store.get_entry_data(entry, num)
    except IndexError:
        return OOPS_STR

    if query_result:
        return QUERY_RESULT_TEMPLATE.format(
            entry=query_result.entry,
            num=query_result.index + 1,
            total=query_result.total_count,
            definition=query_result.definition,
            author=query_result.author,
            age=datetime_to_age_str(query_result.datetime)
        )

    return u'"{}" is undefined. {}'.format(entry, DOCS_STR)


def handle_definition_add(nick, rest):
    """
    Attempt to save a new definition.
    """
    if not ':' in rest:
        return OOPS_STR

    parts = rest.split(':', 1)

    if len(parts) != 2:
        return OOPS_STR

    entry = parts[0].split()[-1].strip()

    definition = parts[1].strip()

    existing = Glossary.store.get_entry_data(entry)

    if existing and existing.definition == definition:
        return "That's already the current definition."

    result = Glossary.store.add_entry(entry, definition, author=nick)

    return ADD_DEFINITION_RESULT_TEMPLATE.format(
        entry=result.entry,
        definition=result.definition
    )


@command('glossary', aliases=ALIASES, doc=DOCS_STR)
def quote(client, event, channel, nick, rest):
    """
    Glossary command. Handles all command versions.

    Assumes `rest` is a unicode object.
    """
    rest = rest.strip()

    if rest.startswith('define'):
        return handle_definition_add(nick, rest)

    parts = rest.strip().split()

    if not parts:
        return handle_random_query()

    entry = parts[0]

    if len(parts) == 2:
        return handle_nth_definition(entry, parts[1])
    elif len(parts) > 2:
        return OOPS_STR
    else:
        return handle_nth_definition(entry)
