"""离线覆盖 HTTP 边界与 SDK 调用映射，不消耗模型额度。"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from playground.server import app


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def request(self, path, payload=None, headers=None):
        response = self.client.request(
            "GET" if payload is None else "POST", path,
            content=None if payload is None else json.dumps(payload),
            headers=headers or {"Content-Type": "application/json"},
        )
        return response.status_code, response.content

    def payload(self, mode="noul"):
        criteria = {"true": "明确提出", "false": "未提出"}
        if mode == "choice":
            criteria = {"billing": "账单", "technical": "故障"}
        elif mode == "score":
            criteria = ["低", "中", "高"]
        return {"mode": mode, "state": "用户修改后的内容", "instructions": "用户的问题", "criteria": criteria}

    def test_all_modes_forward_edited_input_and_return_sdk_answer(self):
        for mode, answer in (
            ("noul", SimpleNamespace(noul=0.23)),
            ("choice", SimpleNamespace(choice="technical", probabilities={"billing": .1, "technical": .9}, confidence=.7)),
            ("score", SimpleNamespace(score=1.3, probabilities={0: .1, 1: .5, 2: .4}, confidence=.4)),
        ):
            with self.subTest(mode=mode), patch.dict("os.environ", TYPESAFE_API_KEY="test-key"), patch("playground.server.create_client") as factory:
                result = SimpleNamespace(nouls={}, choices={}, scores={})
                getattr(result, {"noul": "nouls", "choice": "choices", "score": "scores"}[mode])["evaluation"] = answer
                client = MagicMock()
                client.system_one.return_value = result
                factory.return_value.__enter__.return_value = client
                payload = self.payload(mode)
                status, body = self.request("/api/evaluate", payload)
                data = json.loads(body)
                self.assertEqual(status, 200)
                self.assertEqual(data["answer"][mode], getattr(answer, mode))
                self.assertEqual(data["input"]["state"], payload["state"])
                call = client.system_one.call_args.kwargs
                self.assertEqual(call["state"], payload["state"])
                self.assertEqual(call["questions"]["evaluation"].instructions, payload["instructions"])
                self.assertEqual(call["questions"]["evaluation"].criteria, payload["criteria"])

    def test_invalid_inputs_never_call_model(self):
        with patch("playground.server.create_client") as factory:
            for payload in ([], {}, self.payload() | {"state": " "}, self.payload() | {"criteria": {"true": "x"}}, self.payload("score") | {"criteria": ["one"]}, self.payload("score") | {"criteria": {"a": "低", "b": "高"}}, self.payload() | {"criteria": {"true": " ", "false": "否"}}, self.payload("choice") | {"criteria": {" ": "空键", "other": "其他"}}):
                self.assertEqual(self.request("/api/evaluate", payload)[0], 400)
            factory.assert_not_called()

    def test_missing_key_and_upstream_error(self):
        with patch.dict("os.environ", TYPESAFE_API_KEY=""), patch("playground.server.load_dotenv"):
            self.assertEqual(self.request("/api/evaluate", self.payload())[0], 503)
        with patch.dict("os.environ", TYPESAFE_API_KEY="test-key"), patch("playground.server.create_client", side_effect=RuntimeError("SECRET")):
            status, body = self.request("/api/evaluate", self.payload())
            self.assertEqual(status, 502)
            self.assertNotIn(b"SECRET", body)

    def test_health_and_no_static_files(self):
        self.assertEqual(self.request("/api/health")[0], 200)
        for path in ("/", "/docs/playground.html", "/playground.js", "/docs/playground.css", "/.env", "/runtime.py"):
            self.assertEqual(self.request(path)[0], 404)

    def test_any_origin_allowed_and_non_json_rejected(self):
        response = self.client.options("/api/evaluate", headers={
            "Origin": "https://example.com", "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "*")
        self.assertEqual(self.request("/api/evaluate", self.payload(), {"Content-Type": "text/plain"})[0], 400)

    def test_file_origin_preflight_and_error_are_readable(self):
        headers = {"Origin": "null", "Access-Control-Request-Method": "POST",
                   "Access-Control-Request-Headers": "content-type"}
        response = self.client.options("/api/evaluate", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "*")
        with patch.dict("os.environ", TYPESAFE_API_KEY=""), patch("playground.server.load_dotenv"):
            response = self.client.post("/api/evaluate", json=self.payload(), headers={"Origin": "null"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["access-control-allow-origin"], "*")
        for origin in ("http://localhost:5500", "http://127.0.0.1:8766"):
            response = self.client.get("/api/health", headers={"Origin": origin})
            self.assertEqual(response.headers["access-control-allow-origin"], "*")

    def test_invalid_json(self):
        response = self.client.post("/api/evaluate", content="{", headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 400)

    def test_fastapi_docs(self):
        self.assertEqual(self.client.get("/docs").status_code, 200)
        schema = self.client.get("/openapi.json").json()
        self.assertIn("requestBody", schema["paths"]["/api/evaluate"]["post"])


if __name__ == "__main__":
    unittest.main()
