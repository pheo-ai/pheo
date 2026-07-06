from __future__ import annotations

import json
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse


def call_openai_compatible_endpoint(body: dict[str, Any]) -> str:
    endpoint_url = (body.get("endpoint_url") or "").strip()
    api_key = (body.get("api_key") or "").strip()
    model = (body.get("model") or "").strip()
    messages = body.get("messages") or []
    if not endpoint_url:
        raise ValueError("Endpoint URL is required")
    if not api_key:
        raise ValueError("API key is required")
    if not model:
        raise ValueError("Model is required")
    if not messages:
        task = body.get("task") or {}
        goal = task.get("goal") if isinstance(task, dict) else str(task)
        messages = [{"role": "user", "content": goal or "Generate a workflow output for review."}]
    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(body.get("temperature", 0.7)),
    }
    req = request.Request(
        chat_completions_url(endpoint_url),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://pheo.ai",
            "X-OpenRouter-Title": "Pheo Data Store",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=int(body.get("timeout", 60))) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"Endpoint returned {exc.code}: {detail[:500]}") from exc
    except URLError as exc:
        raise ValueError(f"Endpoint request failed: {exc.reason}") from exc
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("Endpoint returned no choices")
    first = choices[0]
    message = first.get("message") or {}
    content = message.get("content") or first.get("text") or ""
    if isinstance(content, list):
        content = "\n".join(str(part.get("text") or part) if isinstance(part, dict) else str(part) for part in content)
    content = str(content).strip()
    if not content:
        raise ValueError("Endpoint returned an empty output")
    return content


def chat_completions_url(endpoint_url: str) -> str:
    endpoint_url = endpoint_url.rstrip("/")
    if endpoint_url.endswith("/chat/completions"):
        return endpoint_url
    if endpoint_url.endswith("/v1"):
        return f"{endpoint_url}/chat/completions"
    return f"{endpoint_url}/v1/chat/completions"


def safe_endpoint(endpoint_url: str) -> str:
    parsed = urlparse(endpoint_url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"
