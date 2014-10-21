import os
import datetime
import random
import unittest

from pmx_glossary import glossary


class GlossaryTestCase(unittest.TestCase):
    DB_FILE = 'pmxbot_test.sqlite'

    TEST_DEFINITIONS = {
        'blargh': 'this one thing I had',
        'building': 'where salmon hold meetings',
        'castle': 'where salmon have tea',
        'fish Oil': 'what salmon sell',
        'Salmon-person': 'a type of things',
        'snargh': 'also a thing',
        'snowman': u'\u2603',
        '__underscores__': 'woah',
    }

    TEST_NICK = 'tester_person'

    def setUp(self):
        self.wipe_and_init_glossary()
        self.store = glossary.Glossary.store

    def wipe_and_init_glossary(self):
        if os.path.exists(self.DB_FILE):
            os.remove(self.DB_FILE)

        glossary.Glossary.initialize(
            'sqlite:' + self.DB_FILE, load_fixtures=False
        )

    def tearDown(self):
        glossary.pmxbot.storage.SelectableStorage.finalize()

    def _load_test_definitions(self, definition_dict=None):
        definition_dict = definition_dict or self.TEST_DEFINITIONS

        for entry, definition in definition_dict.items():
            self._call_define(
                u'{}: {}'.format(entry, definition), nick=self.TEST_NICK
            )

    def _call_command(self, func, rest, nick=None):
        nick = nick or self.TEST_NICK

        return func(
            client='client',
            event='event',
            channel='channel',
            nick=nick,
            rest=rest
        )

    def _call_search(self, rest):
        return glossary.search(
            client='client',
            event='event',
            channel='channel',
            nick=self.TEST_NICK,
            rest=rest
        )

    def _call_define(self, rest, nick=None):
        nick = nick or self.TEST_NICK

        return glossary.define(
            client='client',
            event='event',
            channel='channel',
            nick=nick,
            rest=rest
        )

    def _call_whatis(self, rest, nick=None):
        nick = nick or self.TEST_NICK

        return glossary.query_command(
            client='client',
            event='event',
            channel='channel',
            nick=nick,
            rest=rest
        )

    def _call_redirect(self, rest, nick=None):
        nick = nick or self.TEST_NICK

        return glossary.redirect_command(
            client='client',
            event='event',
            channel='channel',
            nick=nick,
            rest=rest
        )

    def _call_unredirect(self, rest, nick=None):
        return self._call_command(glossary.remove_redirect, rest, nick)

    def _call_whowrote(self, rest, nick=None):
        return self._call_command(glossary.who_wrote, rest, nick)

    def test_dump_and_load(self):
        self._load_test_definitions()

        redirects = 'red1', 'red2', 'red3', 'red4'
        redirect_map = {}

        for redirect_from in redirects:
            redirect_to = random.choice(self.TEST_DEFINITIONS.keys())
            redirect_map[redirect_from] = redirect_to

            self._call_redirect('{}: {}'.format(redirect_from, redirect_to))

        self.assertEqual(len(redirects), len(redirect_map.keys()))

        # Dump the data
        dump_data, filepath = glossary.Glossary.store.dump_to_json()

        dumped_entries = {r['entry'] for r in dump_data['entries']}
        expected_entries = set(self.TEST_DEFINITIONS.keys())

        self.assertEqual(dumped_entries, expected_entries)

        # Reloading what's already in the db should not affect anything.
        loaded_json, inserted = glossary.Glossary.store.load_from_json(
            filepath
        )
        self.assertEqual(len(inserted), 0)
        self.assertEqual(len(loaded_json['entries']), len(expected_entries))

        # Loading into a clean db should insert all the things.
        self.wipe_and_init_glossary()
        glossary.Glossary.store.bust_all_entries_cache()

        loaded_entries, inserted = glossary.Glossary.store.load_from_json(
            filepath
        )
        self.assertEqual(len(inserted), len(expected_entries))

        # Did we get all our entries back?
        for entry in expected_entries:
            records = glossary.Glossary.store.get_all_records_for_entry(entry)

            self.assertEqual(1, len(records))

            self.assertEqual(records[0].entry, entry)

        # Did we get all our redirects back?
        for redirect_from, redirect_to in redirect_map.items():
            record = self.store.get_redirect(redirect_from)
            self.assertEqual(record.entry, redirect_to)

        os.remove(filepath)

    def test_add_and_retrieve_simple_definition(self):
        author = 'bojangles'
        entry = 'fish'
        definition = 'a swimmy thingy'
        rest = '{}: {}'.format(entry, definition)

        add_result = self._call_define(rest, nick=author)

        self.assertEqual(
            add_result,
            glossary.ADD_DEFINITION_RESULT_TEMPLATE.format(
                entry=entry,
                definition=definition,
                nth=glossary.nth_str(1)
            )
        )

        result = self._call_whatis(entry)
        expected = 'fish (1/1): a swimmy thingy [just now]'

        self.assertEqual(result, expected)

    def test_suggestions_on_query_miss(self):
        self._load_test_definitions({
            'shindig': 'a thing',
            'shining': 'shiny thing',
            'flabbergasted': 'wat!',
            'ning-ning-ning': 'no idea',
        })

        expected = (
            '"shin" is undefined. May I interest you in shindig or shining?'
        )
        result = self._call_whatis('shin')

        self.assertEqual(result, expected)

    def test_get_all_records(self):
        """
        All entries gets only the latest entry for a given entry_lower.
        """
        self._load_test_definitions({
            'fish': 'swimmer',
        })
        self._load_test_definitions({
            'FISH': 'big swimmer',
        })
        self._load_test_definitions({
            'fisH': 'awkward swimmer',
        })
        self._load_test_definitions({
            'FisH': 'symmetrical swimmer',
        })
        self._load_test_definitions({
            'onion': 'yumm',
        })
        self._load_test_definitions({
            'oNion': 'a thing',
        })
        self._load_test_definitions({
            'onioN': 'snappy',
        })

        records = glossary.Glossary.store.get_all_records()

        entries = {r.entry for r in records}

        self.assertEqual(entries, {'FisH', 'onioN'})

    def test_add_and_retrieve_entry_with_unicode(self):
        entry = u'\u2603'
        definition = u'a snowman, like \u2603'

        self._call_define(u'{}: {}'.format(entry, definition))

        result = self._call_whatis(entry)

        expected = glossary.QUERY_RESULT_TEMPLATE.format(
            entry=entry,
            num=1,
            total=1,
            definition=definition,
            author=self.TEST_NICK,
            age=glossary.datetime_to_age_str(datetime.datetime.utcnow()),
            channel_str=' in channel'
        )

        self.assertEqual(result, expected)

    def test_add_and_retrieve_entry_with_spaces(self):
        entry = 'a fish called wanda'
        definition = 'a fish named wanda'
        self._call_define('{}:{}'.format(entry, definition))

        result = self._call_whatis(entry)

        expected = glossary.QUERY_RESULT_TEMPLATE.format(
            entry=entry,
            num=1,
            total=1,
            definition=definition,
            author=self.TEST_NICK,
            age=glossary.datetime_to_age_str(datetime.datetime.utcnow()),
            channel_str=' in channel'
        )

        self.assertEqual(result, expected)

    def test_add_and_retrieve_multiple_definitions(self):
        author = 'bojangles'
        entry = 'fish'
        definitions = (
            'a swimmy thingy',
            'a swimmy slimy thingy',
            'dinner'
        )

        for i, definition in enumerate(definitions):
            result = self._call_define(
                '{}: {}'.format(entry, definition), nick=author
            )

            self.assertIn(
                'This is the {} time it has been defined'.format(
                    glossary.nth_str(i + 1)
                ),
                result
            )

        expected_zero = '"fish" has 3 records. Valid record numbers are 1-3.'
        self.assertEqual(self._call_whatis('fish: 0'), expected_zero)

        # Fetch the first definition
        expected_1 = "fish (1/3): a swimmy thingy [just now]"
        result = self._call_whatis('fish: 1')
        self.assertEqual(result, expected_1)

        # Fetch the second definition
        expected_2 = "fish (2/3): a swimmy slimy thingy [just now]"
        result = self._call_whatis('fish: 2')
        self.assertEqual(result, expected_2)

        # Fetch the third definition
        expected_3 = "fish (3/3): dinner [just now]"
        result = self._call_whatis('fish: 3')
        self.assertEqual(result, expected_3)

        # Fetch the default (latest) definition
        result = self._call_whatis('fish')
        self.assertEqual(result, expected_3)

    def test_get_random_definition(self):
        self._load_test_definitions()

        expected_entries = set(self.TEST_DEFINITIONS.keys())

        for i in range(20):
            result = self._call_whatis('')
            entry = result.split('(', 1)[0].strip()
            definition = result.split(':')[-1].strip()

            self.assertIn(entry, expected_entries)

            expected_definition = (
                u'{} [just now]'.format(self.TEST_DEFINITIONS[entry])
            )
            self.assertEqual(definition, expected_definition)

    def test_all_entries(self):
        self._load_test_definitions()

        all_records = set(glossary.Glossary.store.get_all_records())
        all_entries = {r.entry for r in all_records}

        self.assertEqual(all_entries, set(self.TEST_DEFINITIONS.keys()))

        # Make sure cache is invalidated by new addition
        new_entry = 'new_entry'

        glossary.Glossary.store.add_entry(
            entry=new_entry,
            definition='new def',
            author='author'
        )

        all_records_again = glossary.Glossary.store.get_all_records()

        self.assertEqual(
            all_entries | {new_entry, },
            {r.entry for r in all_records_again}
        )

    def test_get_words_like(self):
        entry_dict = {
            'a fish': 'just a fish',
            'fishy': 'fishlike',
            'gone fishing': 'fishin',
            'gofish': 'sweet game',
        }

        self._load_test_definitions(entry_dict)

        result = set(glossary.Glossary.store.get_similar_words('fish'))

        self.assertEqual(result, set(entry_dict.keys()))

    def test_punctuation_error_response(self):
        for punct_char in glossary.INVALID_ENTRY_CHARS:
            entry = 'entry' + punct_char
            definition = 'a super disallowed entry'

            result = self._call_define('{}: {}'.format(entry, definition))

            if punct_char == ':':
                expected = (
                    "I can't handle '::' right now. "
                    "Please try again without it."
                )
                self.assertEqual(expected, result)
            else:
                expected = (
                    '"{}" cannot be used in a glossary entry.'
                ).format(punct_char)

                self.assertEqual(result, expected)

    def test_get_alternative_suggestions(self):
        self._load_test_definitions({
            'dataplasm': 'a plasm full of data',
            'octonerd': 'eight nerds, enmeshed',
            'terse herd': 'a concise form of herd'
        })

        self.assertEqual(
            glossary.get_alternative_suggestions('terse data'),
            {'terse herd', 'dataplasm'}
        )

        self.assertEqual(
            glossary.get_alternative_suggestions('octo-plasm'),
            {'octonerd', 'dataplasm'}
        )

        self.assertEqual(
            glossary.get_alternative_suggestions('plasm_herd'),
            {'terse herd', 'dataplasm'}
        )

        self.assertEqual(
            glossary.get_alternative_suggestions('zamboni'),
            set()
        )

    def test_search(self):
        self._call_define('fish: swimmer')
        self._call_define('fisH: shugga')
        self._call_define('fish head: the top part of a fish')
        self._call_define('fissure: rip')
        self._call_define('zamboni: big thingie')
        self._call_define('FisH: shugga bomb')

        result = self._call_search('fish')

        self.assertIn(': FisH and fish head.', result)

    def test_simple_redirect(self):
        self._call_define('Bad Dude: one bad summagun')
        self._call_define('cool Dude: one cool summagun')

        self._call_redirect('bad Dude: cool DUde')

        redirect = self.store.get_redirect('bad dude')

        self.assertEqual(redirect.entry, 'cool Dude')

        result = self._call_whatis('bad dude')
        expected = glossary.QUERY_RESULT_TEMPLATE.format(
            entry='cool Dude',
            num=1,
            total=1,
            definition='one cool summagun',
            age='just now'
        )

        # Capitalization of bad dude should reflect what user passed in,
        # not what's stored in entry.
        expected = 'bad dude redirects to ' + expected

        self.assertEqual(result, expected)

    def test_redefine_redirect(self):
        self._load_test_definitions({
            'thingy': 'flamma jam',
            'tom tom tom': 'superdrum',
        })

        for _ in range(5):
            self.store.add_redirect('thingy', 'tom tom tom')
            self.assertEqual(
                self.store.get_redirect('thingy').entry, 'tom tom tom'
            )

    def test_redirect_to_undefined(self):
        result = self._call_redirect('ting: thing')
        self.assertEqual(result, '"thing" is not defined')

    def test_circular_redirect(self):
        self._load_test_definitions({
            'thingy': 'flamma jam',
            'tom tom tom': 'superdrum',
        })

        self._call_redirect('thingy: tom tom tom')
        r_record = self.store.get_redirect('thingy')
        self.assertEqual(r_record.entry, 'tom tom tom')

        invalid_attempt = self._call_redirect('tom tom tom: thingy')
        self.assertEqual(
            invalid_attempt,
            '"thingy" is itself being redirected to "tom tom tom."'
        )

    def test_remove_redirect(self):
        self._load_test_definitions({
            'thingy': 'flamma jam',
            'tom tom tom': 'superdrum',
        })

        self._call_redirect('thingy: tom tom tom')
        self.assertEqual(self.store.get_redirect('thingy').entry, 'tom tom tom')

        self._call_unredirect('thingy')
        self.assertIsNone(self.store.get_redirect('thingy'))

        self.assertEqual(
            self._call_whatis('thingy'),
            glossary.QUERY_RESULT_TEMPLATE.format(
                entry='thingy',
                num=1,
                total=1,
                definition='flamma jam',
                author=self.TEST_NICK,
                age='just now'
            )
        )

    def test_who_wrote(self):
        nick1 = 'happyfeller'
        nick2 = 'happyfeller_blues'
        self._call_define('thing: a thing, you know?', nick=nick1)
        self._call_define('thing: thing thing thing', nick=nick2)

        expected = nick2 + ' authored the 2nd definition of thing.'
        result = self._call_whowrote('thing')
        self.assertEqual(result, expected)

        expected_1 = nick1 + ' authored the 1st definition of thing.'
        result_1 = self._call_whowrote('thing: 1')
        self.assertEqual(result_1, expected_1)

    def test_who_wrote_with_redirect(self):
        nick = 'happyfeller'
        self._call_define('thing: a thing, you know?', nick=nick)
        self._call_redirect('ting: thing', nick=nick)

        expected = (
            'ting redirects to thing. {} authored the 1st definition of thing.'
        ).format(nick)
        result = self._call_whowrote('ting')

        self.assertEqual(result, expected)


class ReadableJoinTestCase(unittest.TestCase):
    def test_no_items(self):
        self.assertEqual(None, glossary.readable_join([]))

    def test_one_item(self):
        self.assertEqual('thing', glossary.readable_join(['thing']))

    def test_two_items(self):
        self.assertEqual(
            'thing1 or thing2', glossary.readable_join(['thing1', 'thing2'])
        )

    def test_three_items(self):
        self.assertEqual(
            'thing1, thing2, or thing3',
            glossary.readable_join(['thing1', 'thing2', 'thing3'])
        )

    def test_four_items(self):
        self.assertEqual(
            'thing1, thing2, thing3, or thing4',
            glossary.readable_join(['thing1', 'thing2', 'thing3', 'thing4'])
        )


class AgeStringTestCase(unittest.TestCase):
    @property
    def now(self):
        return datetime.datetime.utcnow()

    def test_just_now_str(self):
        self.assertEqual('just now', glossary.datetime_to_age_str(self.now))

    def test_just_now_str_under_minute(self):
        dt = self.now - datetime.timedelta(seconds=55)
        self.assertEqual('just now', glossary.datetime_to_age_str(dt))

    def test_minute_ago(self):
        dt = self.now - datetime.timedelta(seconds=60)
        self.assertEqual('1 minute ago', glossary.datetime_to_age_str(dt))

    def test_minutes_ago(self):
        dt = self.now - datetime.timedelta(seconds=60 * 55)
        self.assertEqual('55 minutes ago', glossary.datetime_to_age_str(dt))

    def test_hour_ago(self):
        dt = self.now - datetime.timedelta(seconds=60 * 60)
        self.assertEqual('1 hour ago', glossary.datetime_to_age_str(dt))

    def test_hours_ago_str(self):
        dt = self.now - datetime.timedelta(hours=13)
        self.assertEqual('13 hours ago', glossary.datetime_to_age_str(dt))

    def test_yesterday_str(self):
        dt = self.now - datetime.timedelta(days=1)
        self.assertEqual('yesterday', glossary.datetime_to_age_str(dt))

    def test_two_days_ago(self):
        dt = self.now - datetime.timedelta(days=2)
        self.assertEqual('2 days ago', glossary.datetime_to_age_str(dt))

    def test_30_days_ago(self):
        dt = self.now - datetime.timedelta(days=30)
        self.assertEqual('30 days ago', glossary.datetime_to_age_str(dt))

    def test_31_days_ago(self):
        dt = self.now - datetime.timedelta(days=31)
        self.assertEqual('1.0 months ago', glossary.datetime_to_age_str(dt))

    def test_40_days_ago(self):
        dt = self.now - datetime.timedelta(days=40)
        self.assertEqual('1.3 months ago', glossary.datetime_to_age_str(dt))

    def test_100_days_ago(self):
        dt = self.now - datetime.timedelta(days=100)
        self.assertEqual('3.3 months ago', glossary.datetime_to_age_str(dt))

    def test_365_days_ago(self):
        dt = self.now - datetime.timedelta(days=365)
        self.assertEqual('1.0 years ago', glossary.datetime_to_age_str(dt))

    def test_450_days_ago(self):
        dt = self.now - datetime.timedelta(days=450)
        self.assertEqual('1.2 years ago', glossary.datetime_to_age_str(dt))


class NthStringTestCase(unittest.TestCase):
    def test_nth_string(self):
        self.assertEqual(glossary.nth_str(1), '1st')
        self.assertEqual(glossary.nth_str(2), '2nd')
        self.assertEqual(glossary.nth_str(3), '3rd')
        self.assertEqual(glossary.nth_str(4), '4th')
        self.assertEqual(glossary.nth_str(5), '5th')
        self.assertEqual(glossary.nth_str(1000), '1000th')
