import os
import unittest
import datetime

from glossary import pmxbot
import glossary


class GlossaryTestCase(unittest.TestCase):
    DB_FILE = 'pmxbot_test.sqlite'

    TEST_DEFINITIONS = {
        'blargh': 'this one thing I had',
        'snargh': 'also a thing',
        'salmon': 'a type of things',
        'fish_oil': 'what salmon sell',
        'building': 'where salmon hold meetings',
        'castle': 'where salmon have tea',
    }

    TEST_NICK = 'nick_at_now'

    def setUp(self):
        if os.path.exists(self.DB_FILE):
            os.remove(self.DB_FILE)

        glossary.Glossary.initialize(
            'sqlite:' + self.DB_FILE, load_fixtures=False
        )

    def tearDown(self):
        pmxbot.storage.SelectableStorage.finalize()

    def _load_test_definitions(self):
        for entry, definition in self.TEST_DEFINITIONS.items():
            self._call_quote(
                'define {}: {}'.format(entry, definition), nick=self.TEST_NICK
            )

    def _call_quote(self, rest, nick=None):
        nick = nick or self.TEST_NICK

        return glossary.quote(
            client='client',
            event='event',
            channel='channel',
            nick=nick,
            rest=rest
        )

    def test_add_and_retrieve_simple_definition(self):
        author = 'bojangles'
        entry = 'fish'
        definition = 'a swimmy thingy'
        rest = 'define {}: {}'.format(entry, definition)

        add_result = self._call_quote(rest, nick=author)

        self.assertEqual(
            add_result,
            glossary.ADD_DEFINITION_RESULT_TEMPLATE.format(
                entry=entry,
                definition=definition
            )
        )

        expected = glossary.QUERY_RESULT_TEMPLATE.format(
            entry=entry,
            num=1,
            total=1,
            definition=definition,
            author=author,
            age=glossary.datetime_to_age_str(datetime.datetime.utcnow())
        )

        result = self._call_quote(entry)

        self.assertEqual(result, expected)

    def test_add_and_retrieve_multiple_definitions(self):
        author = 'bojangles'
        entry = 'fish'
        definitions = (
            'a swimmy thingy',
            'a swimmy slimy thingy',
            'dinner'
        )

        self._call_quote(
            'define {}: {}'.format(entry, definitions[0]), nick=author
        )
        self._call_quote(
            'define {}: {}'.format(entry, definitions[1]), nick=author
        )
        self._call_quote(
            'define {}: {}'.format(entry, definitions[2]), nick=author
        )

        expected_total = len(definitions)
        expected_age = glossary.datetime_to_age_str(datetime.datetime.utcnow())

        # Fetch the first definition
        expected_1 = glossary.QUERY_RESULT_TEMPLATE.format(
            entry=entry,
            num=1,
            total=expected_total,
            definition=definitions[0],
            author=author,
            age=expected_age
        )
        result = self._call_quote('fish 1')
        self.assertEqual(result, expected_1)

        # Fetch the second definition
        expected_2 = glossary.QUERY_RESULT_TEMPLATE.format(
            entry=entry,
            num=2,
            total=expected_total,
            definition=definitions[1],
            author=author,
            age=expected_age
        )
        result = self._call_quote('fish 2')
        self.assertEqual(result, expected_2)

        # Fetch the third definition
        expected_3 = glossary.QUERY_RESULT_TEMPLATE.format(
            entry=entry,
            num=expected_total,
            total=expected_total,
            definition=definitions[2],
            author=author,
            age=expected_age
        )
        result = self._call_quote('fish 3')
        self.assertEqual(result, expected_3)

        # Fetch the default (latest) definition
        result = self._call_quote('fish')
        self.assertEqual(result, expected_3)

    def test_get_random_definition(self):
        self._load_test_definitions()

        expected_entries = set(self.TEST_DEFINITIONS.keys())

        for i in range(20):
            result = self._call_quote('')
            parts = result.split()
            entry, definition = parts[0], ' '.join(parts[2:])

            self.assertIn(entry, expected_entries)

            expected_definition = (
                '{} [by {}, today]'.format(
                    self.TEST_DEFINITIONS[entry],
                    self.TEST_NICK
                )
            )
            self.assertEqual(definition, expected_definition)

    def test_all_entries(self):
        self._load_test_definitions()

        all_entries = set(glossary.Glossary.store.get_all_entries())

        self.assertEqual(all_entries, set(self.TEST_DEFINITIONS.keys()))

        # Make sure cache is invalidated by new addition
        new_entry = 'new_entry'

        glossary.Glossary.store.add_entry(
            entry=new_entry,
            definition='new def',
            author='author'
        )

        self.assertEqual(
            all_entries | {new_entry, },
            set(glossary.Glossary.store.get_all_entries())
        )


class AgeStringTestCase(unittest.TestCase):
    def test_just_now_str(self):
        dt = datetime.datetime.now()
        self.assertEqual('today', glossary.datetime_to_age_str(dt))

    def test_yesterday_str(self):
        dt = datetime.datetime.now() - datetime.timedelta(days=1)
        self.assertEqual('yesterday', glossary.datetime_to_age_str(dt))

    def test_two_days_ago(self):
        dt = datetime.datetime.now() - datetime.timedelta(days=2)
        self.assertEqual('2 days ago', glossary.datetime_to_age_str(dt))

    def test_30_days_ago(self):
        dt = datetime.datetime.now() - datetime.timedelta(days=30)
        self.assertEqual('30 days ago', glossary.datetime_to_age_str(dt))

    def test_31_days_ago(self):
        dt = datetime.datetime.now() - datetime.timedelta(days=31)
        self.assertEqual('1.0 months ago', glossary.datetime_to_age_str(dt))

    def test_40_days_ago(self):
        dt = datetime.datetime.now() - datetime.timedelta(days=40)
        self.assertEqual('1.3 months ago', glossary.datetime_to_age_str(dt))

    def test_100_days_ago(self):
        dt = datetime.datetime.now() - datetime.timedelta(days=100)
        self.assertEqual('3.3 months ago', glossary.datetime_to_age_str(dt))

    def test_365_days_ago(self):
        dt = datetime.datetime.now() - datetime.timedelta(days=365)
        self.assertEqual('1.0 years ago', glossary.datetime_to_age_str(dt))

    def test_450_days_ago(self):
        dt = datetime.datetime.now() - datetime.timedelta(days=450)
        self.assertEqual('1.2 years ago', glossary.datetime_to_age_str(dt))
