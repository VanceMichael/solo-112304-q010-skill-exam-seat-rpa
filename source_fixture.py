"""提供本地演练来源与合作端回执。"""
from __future__ import annotations

import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlsplit


def load():
    return json.loads(Path(__file__).with_name("inputs").joinpath("exchange.json").read_text(encoding="utf-8"))


def page(content):
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>合作端</title><main>' + content + '</main></html>'


class Exchange(ThreadingHTTPServer):
    def __init__(self, address):
        super().__init__(address, Handler)
        config = load()
        self.routes = config["initial"]
        self.changes = config["changes"]
        self.forms = config["forms"]
        self.scene = 0
        self.receipts = {}
        self.hidden_receipts = set()
        self.lock = Lock()


class Handler(BaseHTTPRequestHandler):
    def send_document(self, body, status=200, kind="json"):
        mime = {
            "json": "application/json",
            "html": "text/html",
            "xml": "application/xml",
            "csv": "text/csv",
        }[kind]
        data = (json.dumps(body, ensure_ascii=False) if kind == "json" else body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_form(self, path, form):
        options = "".join(f"<option>{escape(op)}</option>" for op in form["operations"])
        self.send_document(page(f'<form method="post" action="{escape(path)}">'
                                '<label>业务请求号 <input name="request" required></label>'
                                f'<label>业务动作 <select name="operation">{options}</select></label>'
                                '<label>条目编号 <input name="items" required></label>'
                                '<label>业务明细（JSON） <textarea name="details"></textarea></label>'
                                '<button>提交</button></form>'
                                f'<form method="get" action="{escape(path)}">'
                                '<label>查回执 <input name="request" required></label>'
                                '<button>查询</button></form>'), kind="html")

    def send_receipt(self, receipt, as_html):
        if as_html:
            data = escape(json.dumps(receipt, ensure_ascii=False))
            self.send_document(page(f'<h1>请求回执</h1><pre>{data}</pre>'), kind="html")
        else:
            self.send_document(receipt)

    def do_GET(self):
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        with self.server.lock:
            if url.path == "/__scene":
                self.send_document({"index": self.server.scene, "count": len(self.server.changes) + 1})
                return
            form = self.server.forms.get(url.path)
            if form:
                if "request" not in query and form["browser"]:
                    self.serve_form(url.path, form)
                    return
                key = (url.path, query.get("request", [""])[0])
                existing = self.server.receipts.get(key)
                if key in self.server.hidden_receipts:
                    self.server.hidden_receipts.remove(key)
                    existing = None
                if existing:
                    self.send_receipt(existing[1], form["browser"])
                else:
                    self.send_document({"message": "当前查不到该请求"}, 404)
                return
            route = self.server.routes.get(self.path)
            if route is None:
                self.send_document({"message": "此来源没有该地址"}, 404)
            else:
                self.send_document(route["body"], route["status"], route["kind"])

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                raise ValueError("请求长度超出范围")
            raw = self.rfile.read(length).decode("utf-8")
            if self.headers.get_content_type() == "application/x-www-form-urlencoded":
                fields = parse_qs(raw)
                data = {k: v[0] for k, v in fields.items()}
                data["items"] = [item.strip() for item in data.get("items", "").split(",") if item.strip()]
                data["details"] = json.loads(data.get("details", "{}"))
            else:
                data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("请求字段无效")
            with self.server.lock:
                self.handle_submission(data)
        except (ValueError, TypeError, KeyError) as exc:
            self.send_document({"message": str(exc)}, 400)

    def handle_submission(self, data):
        if self.path == "/__scene":
            index = data.get("index")
            if type(index) is not int or index != self.server.scene + 1 or index > len(self.server.changes):
                raise ValueError("按顺序进入下一时间点")
            scene = self.server.changes[index - 1]
            self.server.scene = index
            self.server.routes.update(scene["routes"])
            self.send_document({"index": index, "label": scene["label"]})
            return
        form = self.server.forms.get(self.path)
        if form is None:
            self.send_document({"message": "此合作端没有该地址"}, 404)
            return
        request, op, items = data.get("request"), data.get("operation"), data.get("items")
        if (not isinstance(request, str) or not request.strip() or op not in form["operations"]
                or not isinstance(items, list) or not items or any(not isinstance(item, str) for item in items)):
            raise ValueError("需要有效的请求号、业务动作和条目编号")
        if len(set(items)) != len(items):
            raise ValueError("同一请求内条目不得重复")
        details = data.get("details", {})
        if not isinstance(details, dict) or not set(details).issubset(items):
            raise ValueError("业务明细须按本次条目编号填写")
        identity = (self.path, request)
        previous = self.server.receipts.get(identity)
        if previous:
            if previous[0] != (op, items, details):
                self.send_document({"message": "业务请求号已有不同内容"}, 409)
                return
            self.send_receipt(previous[1], form["browser"])
            return
        plan = form["outcomes"].get(str(self.server.scene), {}).get(op, {})
        rows = [{"item":item, "status":plan.get(item, plan.get("*", "accepted"))} for item in items]
        receipt = {"request":request, "receipt":f'{form["identifier"]}-{len(self.server.receipts)+1:05d}',
                   "operation":op, "rows":rows, "details":details}
        self.server.receipts[identity] = ((op, items, details), receipt)
        if plan.get("@response") == "lost":
            self.server.hidden_receipts.add(identity)
            self.send_document({"message": "暂未取得合作端回应"}, 503)
            return
        self.send_receipt(receipt, form["browser"])

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with Exchange(("127.0.0.1", args.port)) as server:
        print(f"本地资料服务 http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()
