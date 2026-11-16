"""Interpret a narrow timing preference using a loopback llama.cpp server."""

from http.client import HTTPException
import json
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ENDPOINT = "http://127.0.0.1:8089/v1/chat/completions"
MODEL = "pawpal-qwen"
VALUES = ("earlier", "later", "balanced", "clarify")
SCHEMA = {
    "type": "object",
    "properties": {"preference": {"type": "string", "enum": list(VALUES)}},
    "required": ["preference"],
    "additionalProperties": False,
}
SYSTEM = """Classify a soft time preference for untimed flexible tasks.
Return earlier for morning, earlier, or finish before lunch.
Return later for afternoon, evening, or later.
Return balanced for no timing preference or either time.
Return clarify if the input asks for a specific time, medical change, other action, or conflicting preferences.
Return a JSON object with the preference field only.
Examples:
'Do untimed activities first thing' -> {"preference":"earlier"}
'Leave the flexible activities until the evening' -> {"preference":"later"}
'Either time works' -> {"preference":"balanced"}
'Give the medication at 10' -> {"preference":"clarify"}"""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "Local model redirect refused", headers, fp)


def parse_preference(content: str) -> str:
    if not isinstance(content, str):
        raise ValueError("Model content must be text")
    result = json.loads(content)
    if type(result) is not dict or set(result) != {"preference"} or result["preference"] not in VALUES:
        raise ValueError("Unexpected model response schema")
    return result["preference"]


def interpret_preference(goal: str) -> str:
    request = Request(
        ENDPOINT,
        data=json.dumps({
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": goal},
            ],
            "response_format": {"type": "json_schema", "json_schema": {"name": "timing", "schema": SCHEMA}},
            "temperature": 0,
            "seed": 42,
            "max_tokens": 48,
            "stream": False,
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=6) as response:
            payload = json.loads(response.read(16384))
        choice = payload["choices"][0]
        if choice["finish_reason"] != "stop":
            raise ValueError("Model response did not finish")
        return parse_preference(choice["message"]["content"])
    except (KeyError, IndexError, TypeError, HTTPException) as error:
        raise ValueError("Incomplete local model response") from error
