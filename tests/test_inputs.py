import unittest

from source_fixture import load


class ExchangeInputs(unittest.TestCase):
    def test_related_source_records(self):
        exchange = load()
        initial = exchange["initial"]
        changes = exchange["changes"]
        old = initial["/school/submissions"]["body"]["records"][0]
        new = changes[0]["routes"]["/school/submissions"]["body"]["records"][1]
        self.assertEqual(old["attempt"], new["retest_of"])
        self.assertNotEqual(old["disk"], new["disk"])
        rows = changes[1]["routes"]["/vendor/artifacts"]["body"]["records"]
        self.assertEqual(rows[0]["missing"], [2])
        self.assertNotEqual(initial["/vendor/current"]["body"]["claims"][1]["disk"], changes[1]["routes"]["/vendor/current"]["body"]["claims"][1]["disk"])
