import io
import json

from groundgate.mcp_server import handle_request, serve


def _call(method, params=None, request_id=1):
    request = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        request["params"] = params
    return handle_request(request)


def test_initialize_advertises_tools():
    response = _call("initialize", {"protocolVersion": "2025-06-18"})
    assert response["result"]["serverInfo"]["name"] == "groundgate"
    assert "tools" in response["result"]["capabilities"]


def test_tools_list_exposes_verify_grounding():
    response = _call("tools/list")
    (tool,) = response["result"]["tools"]
    assert tool["name"] == "verify_grounding"
    assert set(tool["inputSchema"]["required"]) == {"answer", "context"}


def test_tools_call_returns_structured_verdict():
    response = _call(
        "tools/call",
        {
            "name": "verify_grounding",
            "arguments": {
                "answer": "A carencia e de 12 horas [1].",
                "context": [{"id": "1", "text": "A carencia do plano e de 24 horas."}],
            },
        },
    )
    result = response["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["status"] == "fail"
    text_payload = json.loads(result["content"][0]["text"])
    assert text_payload == result["structuredContent"]


def test_tools_call_unknown_tool_is_an_error():
    response = _call("tools/call", {"name": "nope", "arguments": {}})
    assert response["error"]["code"] == -32602


def test_notifications_produce_no_response():
    assert handle_request({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_unknown_method_returns_method_not_found():
    assert _call("resources/list")["error"]["code"] == -32601


def test_serve_round_trip_over_streams():
    stdin = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        + "\n"
    )
    stdout = io.StringIO()
    serve(stdin=stdin, stdout=stdout)
    lines = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert lines[0]["id"] == 1 and "serverInfo" in lines[0]["result"]
    assert lines[1]["id"] == 2 and lines[1]["result"]["tools"]
