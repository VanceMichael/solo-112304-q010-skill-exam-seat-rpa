import unittest

from source_fixture import load


class ExchangeInputs(unittest.TestCase):
    def test_related_source_records(self):
        exchange = load()
        initial = exchange["initial"]
        changes = exchange["changes"]
        catalog = initial["/vendor/catalog"]["body"]
        self.assertEqual(catalog.count('data-machine="H1"'), 2)
        chg = changes[0]["routes"]["/school/changes"]["body"]["requests"][0]
        self.assertEqual(chg["prior"], "S2")
        self.assertEqual(chg["new"], "S4")
        self.assertEqual(changes[1]["routes"]["/school/current"]["body"]["rows"][-1]["vendor"], None)
