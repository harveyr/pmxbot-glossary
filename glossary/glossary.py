import calendar
import datetime
import json
import random
import string
from collections import namedtuple

from dateutil.parser import parse as parse_date

import pmxbot
from pmxbot import storage
from pmxbot.core import command

DEFINE_COMMAND = 'define'
QUERY_COMMAND = 'whatis'
SEARCH_COMMAND = 'search'
ARCHIVES_LINK_COMMAND = 'tardis'

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
    u'{entry} ({num}/{total}): {definition} '
    u'[defined by {author} {age}{channel_str}]'
)

UNDEFINED_TEMPLATE = u'"{}" is undefined.'


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
       entry_lower VARCHAR NOT NULL,
       definition TEXT NOT NULL,
       author VARCHAR NOT NULL,
       channel VARCHAR,
       timestamp DATE DEFAULT (datetime('now','utc'))
    )
    """

    CREATE_GLOSSARY_INDEX_SQL = """
      CREATE INDEX IF NOT EXISTS ix_glossary_entry ON glossary(entry_lower)
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

    def add_entry(self, entry, definition, author, channel=None):
        sql = """
          INSERT INTO glossary (entry, entry_lower, definition, author, channel)
          VALUES (?, ?, ?, ?, ?)
        """

        self.db.execute(
            sql, (entry, entry.lower(), definition, author, channel)
        )
        self.db.commit()
        self.bust_all_entries_cache()

        return self.get_entry_data(entry)

    def get_all_records(self):
        """
        Returns list of all entries in the glossary.
        """
        cache_key = 'all_entries'
        entries = self.cache.get(cache_key)

        if entries is None:
            sql = """
              SELECT entry,
                entry_lower,
                definition,
                author,
                channel,
                strftime('%s', timestamp),
                COUNT(entry_lower)
              FROM glossary
              GROUP BY entry_lower
              ORDER BY timestamp
            """

            query = self.db.execute(sql).fetchall()
            entries = []

            for row in query:
                count = row[-1]
                record = GlossaryRecord(
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    datetime.datetime.utcfromtimestamp(int(row[5])),
                    count - 1,
                    count
                )

                entries.append(record)

            entries.sort(key=lambda x: x.entry_lower)

            self.cache[cache_key] = entries

        return entries

    def get_random_entry(self):
        """
        Returns a random entry from the glossary.
        """
        entries = self.get_all_records()

        if not entries:
            return None

        return random.choice(entries).entry

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
            SELECT entry,
              entry_lower,
              definition,
              author,
              channel,
              strftime('%s', timestamp)
            FROM glossary
            WHERE entry_lower LIKE ?
            ORDER BY timestamp
        """

        results = self.db.execute(sql, (entry, )).fetchall()

        entry_data = []
        total_count = len(results)

        for i, row in enumerate(results):
            entry_data.append(
                GlossaryRecord(
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    datetime.datetime.utcfromtimestamp(int(row[5])),
                    i,
                    total_count
                )
            )

        return entry_data

    def get_similar_words(self, search_str):
        search_str = search_str.lower()
        all_entries = self.get_all_records()

        matches = [e.entry for e in all_entries if search_str in e.entry_lower]

        return matches

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


GlossaryRecord = namedtuple(
    'GlossaryQueryResult',
    'entry entry_lower definition author channel datetime index total_count'
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
    try:
        query_result = Glossary.store.get_entry_data(entry, num)
    except IndexError:
        return u'"{}" is not a valid glossary entry number for "{}".'.format(
            num, entry
        )

    if query_result:
        if query_result.channel:
            channel_str = ' in ' + query_result.channel
        else:
            channel_str = ''

        return QUERY_RESULT_TEMPLATE.format(
            entry=query_result.entry,
            num=query_result.index + 1,
            total=query_result.total_count,
            definition=query_result.definition,
            author=query_result.author,
            age=datetime_to_age_str(query_result.datetime),
            channel_str=channel_str
        )

    response = UNDEFINED_TEMPLATE.format(entry)

    # Check if there are any similar entries that may be relevant.
    suggestions = list(get_alternative_suggestions(entry))[:10]

    if suggestions:
        response += (
            u' May I interest you in {}?'.format(readable_join(suggestions))
        )

    return response


def handle_search(rest):
    """
    Returns formatted list of entries found with the given search string.
    """
    entry_matches = set(Glossary.store.get_similar_words(rest))
    lower_matches = {e.lower() for e in entry_matches}

    def_matches = set(
        e for e in Glossary.store.search_definitions(rest)
        if e.lower() not in lower_matches
    )

    matches = sorted(list(entry_matches | def_matches))

    if not matches:
        return 'No glossary results found.'
    else:
        result = (
            u'Found glossary entries: {}. To get a definition: !{} <entry>'
        ).format(readable_join(matches, conjunction='and'), QUERY_COMMAND)

        return result


def entry_number_command(func):
    """
    Decorator for commands that care about an entry string and possibly an
    entry number.
    """
    def inner(client, event, channel, nick, rest):
        rest = rest.strip()
        num = None

        if rest.lower() == 'help':
            return DOCS_STR

        if ':' in rest:
            parts = rest.split(':', 1)
            entry, num = parts[0].strip(), parts[1].strip()

            try:
                num = int(num)
            except (ValueError, TypeError):
                return OOPS_STR
        else:
            entry = rest

        return func(entry, num)

    return inner


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

    result = Glossary.store.add_entry(entry, definition, nick, channel)

    return ADD_DEFINITION_RESULT_TEMPLATE.format(
        entry=result.entry,
        definition=result.definition
    )


@command(QUERY_COMMAND, doc=DOCS_STR)
@entry_number_command
def query(entry, num):
    """
    Retrieve a definition of an entry.
    """
    if not entry:
        return handle_random_query()

    return handle_nth_definition(entry, num)


@command(SEARCH_COMMAND, doc=DOCS_STR)
@entry_number_command
def search(entry, num=None):
    """
    Search the entries and defintions.
    """
    # No `num` handled here.
    if not entry or num:
        return OOPS_STR

    return handle_search(entry)


@command(ARCHIVES_LINK_COMMAND, doc=DOCS_STR)
@entry_number_command
def archives_link(rest, num=None):

    slack_url = pmxbot.config.get('slack_url')

    if not slack_url:
        return 'Slack URL is not configured.'

    entry = Glossary.store.get_entry_data(rest, num)

    if not entry:
        return UNDEFINED_TEMPLATE.format(entry)

    timestamp = calendar.timegm(entry.datetime.utctimetuple())

    channel = entry.channel

    if not channel:
        return (
            u"I don't know which channel {} was defined in. "
            u"If it's redefined, I can try again."
        ).format(rest)

    if channel.startswith('#'):
        channel = channel[1:]

    url = '{slack_url}/archives/{channel}/p{timestamp}'.format(
        slack_url=slack_url,
        channel=channel,
        timestamp=timestamp * 1000000
    )

    template = '[Experimental] Attempting to link to Slack archives at {}: {}'

    return template.format(entry.datetime.ctime(), url)
