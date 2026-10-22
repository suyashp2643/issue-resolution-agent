"""Local HTTP protocol tests: these are NOT evidence of real model performance."""
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from portfolio.eval_runtime import Chat, summarize


def test_http_usage_and_invalid_json():
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            content = '{"findings": []}' if len(requests) == 1 else 'not-json'
            body = json.dumps({"model": "protocol-test-only", "usage": {"total_tokens": 12},
                "choices": [{"message": {"content": content}}]}).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *_):
            pass
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        chat = Chat("protocol-test", endpoint=f"http://127.0.0.1:{server.server_port}/v1", key="fake-test-key")
        assert chat.ask([{"role": "user", "content": "test"}]) == {"findings": []}
        assert chat.calls[0]["usage"]["total_tokens"] == 12
        with pytest.raises(json.JSONDecodeError):
            chat.ask([{"role": "user", "content": "test"}])
        assert len(chat.calls) == 2
        assert requests[0]["max_tokens"] == 1600
        assert requests[0]["model"] == "protocol-test"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_errors_stay_in_denominator_and_pairing():
    rows = [
        {"case": "x", "repeat": 0, "method": "single_shot", "success": True, "seconds": 1},
        {"case": "x", "repeat": 0, "method": "agent", "status": "error", "seconds": 2},
        {"case": "y", "repeat": 0, "method": "agent", "success": True, "seconds": 3},
        {"case": "y", "repeat": 0, "method": "single_shot", "success": False, "seconds": 1}]
    summary = summarize(rows)
    assert summary["methods"]["agent"]["success_rate"] == 0.5
    assert summary["methods"]["agent"]["errors"] == 1
    assert summary["paired"] == [{"baseline": "single_shot", "pairs": 2, "agent_only_success": 1, "baseline_only_success": 1}]

import os
from portfolio.evaluate import CASES, check


@pytest.mark.skipif(os.environ.get("RUN_DOCKER_TESTS") != "1", reason="Docker integration runs in CI")
def test_docker_grading_rejects_bug_and_accepts_fix():
    case = json.loads(CASES.read_text())[0]
    assert not check(case["source"], case["public_tests"])["passed"]
    repair = "def chunks(values,size):\n    if size <= 0: raise ValueError('size')\n    return [values[i:i+size] for i in range(0,len(values),size)]\n"
    assert check(repair, case["public_tests"])["passed"]
    assert check(repair, case["hidden_tests"])["passed"]
    result = check("while True: pass", "")
    assert not result["passed"] and result["returncode"] == 124


def test_new_tasks_exclude_original_fixtures_and_define_final_tests():
    cases = json.loads(CASES.read_text())
    assert len(cases) == len({case["id"] for case in cases}) == 6
    assert not {case["id"] for case in cases} & {"empty_average", "inclusive_overlap", "stable_unique"}
    assert all(case["public_tests"] and case["hidden_tests"] for case in cases)


@pytest.mark.skipif(os.environ.get("RUN_DOCKER_TESTS") != "1", reason="Docker integration runs in CI")
def test_repair_feedback_loop_hides_final_assertions():
    from portfolio.evaluate import solve
    case = json.loads(CASES.read_text())[0]
    requests = []
    replies = [case["source"], "def chunks(values,size):\n    if size <= 0: raise ValueError('size')\n    return [values[i:i+size] for i in range(0,len(values),size)]\n"]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            body = {"choices": [{"message": {"content": json.dumps({"source": replies[len(requests)-1]})}}]}
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())
        def log_message(self, *_):
            pass
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = solve(case, "agent", Chat("protocol-test", f"http://127.0.0.1:{server.server_port}/v1", "fake-key"))
        assert result["success"] and len(result["calls"]) == 2
        assert not result["trace"][0]["public"]["passed"]
        assert result["trace"][1]["public"]["passed"]
        for request in requests:
            assert case["hidden_tests"] not in [message["content"] for message in request["messages"]]
            assert all("hidden_tests" not in message["content"] for message in request["messages"])
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
