import json
from threading import Thread
import unittest

from playwright.sync_api import sync_playwright

from source_fixture import Exchange, load


class PortalTests(unittest.TestCase):
    def test_visible_form_and_receipt(self):
        with Exchange(("127.0.0.1", 0)) as server:
            thread = Thread(target=server.serve_forever, kwargs={"poll_interval":0.05}, daemon=True)
            thread.start()
            try:
                self.exercise_portal(server.server_port)
            finally:
                server.shutdown()
                thread.join()

    def exercise_portal(self, port):
        config = load()
        origin = f"http://127.0.0.1:{port}"
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(4000)
            try:
                for path, route in config["initial"].items():
                    if route["kind"] == "html":
                        response = page.goto(origin + path)
                        self.assertEqual(response.status, 200)
                        page.locator("body").wait_for(state="visible")
                for path, form in config["forms"].items():
                    if form["browser"]:
                        self.submit_form(page, origin + path, form["operations"][0])
            finally:
                browser.close()

    def submit_form(self, page, url, operation):
        page.goto(url)
        page.get_by_label("业务请求号").fill("浏览器-001")
        page.get_by_label("业务动作").select_option(operation)
        page.get_by_label("条目编号").fill("DEMO-1, DEMO-2")
        page.get_by_label("业务明细（JSON）").fill('{"DEMO-2":{"备注":"交接"}}')
        page.get_by_role("button", name="提交").click()
        page.get_by_role("heading", name="请求回执").wait_for()
        receipt = json.loads(page.locator("pre").inner_text())
        self.assertEqual(receipt["request"], "浏览器-001")
        self.assertEqual([row["item"] for row in receipt["rows"]], ["DEMO-1","DEMO-2"])
        self.assertEqual(receipt["details"]["DEMO-2"]["备注"], "交接")
        page.goto(url)
        page.get_by_label("查回执").fill("浏览器-001")
        page.get_by_role("button", name="查询").click()
        self.assertEqual(json.loads(page.locator("pre").inner_text()), receipt)
