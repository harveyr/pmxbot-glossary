import os
import unittest
import datetime

from glossary import pmxbot
import glossary

DB_FILE = 'pmxbot_test.sqlite'
DB_URI = 'sqlite:' + DB_FILE


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)

        glossary.Glossary.initialize(DB_URI)

    def tearDown(self):
        pmxbot.storage.SelectableStorage.finalize()

    def _call_quote(self, nick, rest):
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
        rest = u'define {}: {}'.format(entry, definition)

        add_result = self._call_quote(author, rest)

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

        result = self._call_quote(author, entry)

        self.assertEqual(result, expected)

    def test_add_and_retrieve_multiple_definitions(self):
        author = 'bojangles'
        entry = 'fish'
        definitions = ('a swimmy thingy', 'a swimmy slimy thingy')

        self._call_quote(author, u'define {}: {}'.format(entry, definitions[0]))
        self._call_quote(author, u'define {}: {}'.format(entry, definitions[1]))

        # Fetch the first definition
        expected = glossary.QUERY_RESULT_TEMPLATE.format(
            entry=entry,
            num=1,
            total=2,
            definition=definitions[0],
            author=author,
            age=glossary.datetime_to_age_str(datetime.datetime.utcnow())
        )
        result = self._call_quote(author, 'fish 1')
        self.assertEqual(result, expected)

        # Fetch the default (latest) definition
        expected = glossary.QUERY_RESULT_TEMPLATE.format(
            entry=entry,
            num=2,
            total=2,
            definition=definitions[1],
            author=author,
            age=glossary.datetime_to_age_str(datetime.datetime.utcnow())
        )
        result = self._call_quote(author, 'fish')
        self.assertEqual(result, expected)



