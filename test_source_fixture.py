import json
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from source_fixture import Exchange, load


class SourceFixtureTests(unittest.TestCase):
    def setUp(self):
        self.server = Exchange(("127.0.0.1", 0))
        self.addCleanup(self.server.server_close)
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        thread = Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.shutdown)

    def call(self, path, data=None):
        request = Request(self.origin + path, data=None if data is None else json.dumps(data).encode(),
                          headers={"Content-Type":"application/json"})
        try:
            response = urlopen(request, timeout=2)
        except HTTPError as exc:
            response = exc
        with response:
            payload = response.read().decode()
            return response.status, json.loads(payload) if response.headers.get_content_type() == "application/json" else payload

    def check_routes(self, routes):
        for path, expected in routes.items():
            with self.subTest(path=path):
                self.assertEqual(self.call(path), (expected["status"], expected["body"]))

    def test_source_routes_over_time(self):
        exchange = load()
        self.check_routes(exchange["initial"])
        for index, change in enumerate(exchange["changes"], 1):
            self.assertEqual(self.call("/__scene", {"index":index})[0], 200)
            self.check_routes(change["routes"])

    def test_repeated_submission_is_same_request(self):
        for path, form in load()["forms"].items():
            if form["browser"]:
                self.assertIn('name="items"', self.call(path)[1])
            request = {"request":"演练-002", "operation":form["operations"][0], "items":["EXAMPLE"]}
            status, first = self.call(path, request)
            self.assertEqual(status, 200)
            self.assertEqual(self.call(path, request), (status,first))
            self.assertEqual(self.call(path, dict(request, items=["EXAMPLE-2"]))[0], 409)
            self.assertEqual(self.call(path + "?request=%E6%BC%94%E7%BB%83-002"), (status, first))
