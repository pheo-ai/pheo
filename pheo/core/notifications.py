from __future__ import annotations

import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any
from urllib import request
from urllib.parse import quote, urljoin

from pheo.core.text import summarize


def deliver_review_packet(packet_payload: dict[str, Any]) -> dict[str, Any]:
    packet = packet_payload.get("packet") or {}
    delivery = dict(packet.get("delivery") or {})
    channels = dict(delivery.get("channels") or {})
    results: dict[str, dict[str, Any]] = {}

    if "email" in channels:
        results["email"] = _deliver_email(packet_payload, channels.get("email") or {})
    if "webhook" in channels:
        results["webhook"] = _deliver_webhook(packet_payload, channels.get("webhook") or {})
    if "slack" in channels:
        results["slack"] = _deliver_slack(packet_payload, channels.get("slack") or {})
    if "telegram" in channels:
        results["telegram"] = _deliver_telegram(packet_payload, channels.get("telegram") or {})

    if not results:
        results["local"] = {
            "status": "skipped",
            "reason": "no_notification_channels",
            "review_url": _absolute_review_url(packet.get("review_url") or ""),
        }

    delivery["notifications"] = results
    delivery["delivery_status"] = _overall_status(results)
    return delivery


def _deliver_email(packet_payload: dict[str, Any], channel: dict[str, Any]) -> dict[str, Any]:
    recipients = [item for item in channel.get("to", []) if item]
    if not recipients:
        return {"status": "skipped", "reason": "no_recipients"}

    config = _smtp_config()
    missing = [key for key in ("host", "username", "password", "sender") if not config.get(key)]
    if missing:
        return {
            "status": "not_configured",
            "reason": "missing " + ", ".join(missing),
            "to": recipients,
        }

    message = _email_message(packet_payload, recipients, config["sender"], channel)
    try:
        _send_email(message, config)
    except Exception as exc:
        return {"status": "failed", "error": str(exc), "to": recipients}
    return {
        "status": "sent",
        "to": recipients,
        "from": config["sender"],
        "review_url": _absolute_review_url((packet_payload.get("packet") or {}).get("review_url") or ""),
    }


def _deliver_webhook(packet_payload: dict[str, Any], channel: dict[str, Any]) -> dict[str, Any]:
    url = _env_or_value(channel, "url", "url_env")
    if not url:
        return {"status": "not_configured", "reason": "missing url or url_env"}
    headers = {"Content-Type": "application/json", **_headers(channel)}
    payload = _notification_payload(packet_payload, channel)
    try:
        _post_json(url, payload, headers)
    except Exception as exc:
        return {"status": "failed", "error": str(exc), "target": _safe_url(url)}
    return {"status": "sent", "target": _safe_url(url)}


def _deliver_slack(packet_payload: dict[str, Any], channel: dict[str, Any]) -> dict[str, Any]:
    url = _env_or_value(channel, "webhook_url", "webhook_url_env")
    if not url:
        return {"status": "not_configured", "reason": "missing webhook_url or webhook_url_env"}
    text = _plain_text(packet_payload, channel)
    try:
        _post_json(url, {"text": text}, {"Content-Type": "application/json"})
    except Exception as exc:
        return {"status": "failed", "error": str(exc), "target": _safe_url(url)}
    return {"status": "sent", "target": _safe_url(url)}


def _deliver_telegram(packet_payload: dict[str, Any], channel: dict[str, Any]) -> dict[str, Any]:
    token = _env_or_value(channel, "bot_token", "bot_token_env")
    chat_id = channel.get("chat_id") or os.environ.get(channel.get("chat_id_env") or "")
    if not token:
        return {"status": "not_configured", "reason": "missing bot_token or bot_token_env"}
    if not chat_id:
        return {"status": "not_configured", "reason": "missing chat_id or chat_id_env"}
    url = f"https://api.telegram.org/bot{quote(token)}/sendMessage"
    payload = {"chat_id": chat_id, "text": _plain_text(packet_payload, channel)}
    try:
        _post_json(url, payload, {"Content-Type": "application/json"})
    except Exception as exc:
        return {"status": "failed", "error": str(exc), "target": "https://api.telegram.org"}
    return {"status": "sent", "target": "telegram", "chat_id": str(chat_id)}


def _smtp_config() -> dict[str, Any]:
    return {
        "host": os.environ.get("PHEO_SMTP_HOST") or os.environ.get("PHEO_EMAIL_HOST") or "",
        "port": int(os.environ.get("PHEO_SMTP_PORT") or os.environ.get("PHEO_EMAIL_PORT") or "587"),
        "security": (os.environ.get("PHEO_SMTP_SECURITY") or os.environ.get("PHEO_EMAIL_SECURITY") or "tls").lower(),
        "username": os.environ.get("PHEO_SMTP_USERNAME") or os.environ.get("PHEO_EMAIL_USERNAME") or "",
        "password": os.environ.get("PHEO_SMTP_PASSWORD") or os.environ.get("PHEO_EMAIL_PASSWORD") or "",
        "sender": os.environ.get("PHEO_EMAIL_FROM") or "",
    }


def _email_message(packet_payload: dict[str, Any], recipients: list[str], sender: str, channel: dict[str, Any]) -> EmailMessage:
    point = packet_payload.get("review_point") or {}
    workflow = packet_payload.get("workflow") or {}
    subject = channel.get("subject") or f"Review ready: {point.get('name') or workflow.get('name') or 'Pheo Data Store'}"
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(_plain_text(packet_payload, channel))
    return message


def _send_email(message: EmailMessage, config: dict[str, Any]) -> None:
    if config["security"] == "ssl":
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(config["host"], config["port"], context=context, timeout=30) as server:
            server.login(config["username"], config["password"])
            server.send_message(message)
        return
    with smtplib.SMTP(config["host"], config["port"], timeout=30) as server:
        if config["security"] in {"tls", "starttls"}:
            server.starttls(context=ssl.create_default_context())
        server.login(config["username"], config["password"])
        server.send_message(message)


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> None:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with request.urlopen(req, timeout=30) as response:
        response.read()


def _notification_payload(packet_payload: dict[str, Any], channel: dict[str, Any]) -> dict[str, Any]:
    packet = packet_payload.get("packet") or {}
    point = packet_payload.get("review_point") or {}
    workflow = packet_payload.get("workflow") or {}
    observation = packet_payload.get("observation") or {}
    recommended = packet_payload.get("recommended") or {}
    return {
        "schema": "pheo.review_notification.v1",
        "workflow": {"id": workflow.get("id"), "name": workflow.get("name"), "domain": workflow.get("domain")},
        "review_point": {"id": point.get("id"), "name": point.get("name")},
        "packet": {
            "id": packet.get("id"),
            "status": packet.get("status"),
            "review_url": _absolute_review_url(packet.get("review_url") or ""),
        },
        "observation": {"id": observation.get("id"), "summary": summarize(observation.get("output") or "", 600)},
        "recommended": {
            "index": recommended.get("index"),
            "summary": summarize(recommended.get("output") or "", 600),
            "scores": recommended.get("scores") or {},
        },
        "instructions": channel.get("instructions") or "",
    }


def _plain_text(packet_payload: dict[str, Any], channel: dict[str, Any]) -> str:
    payload = _notification_payload(packet_payload, channel)
    packet_id = payload["packet"]["id"]
    selected = payload["recommended"]["index"]
    cli = ""
    if packet_id and selected is not None:
        cli = "\n".join(
            [
                "CLI approval command:",
                f"pheo review capture --packet {packet_id} --selected {selected} --action approve --reason \"Reviewed and approved.\"",
            ]
        )
    scores = payload["recommended"].get("scores") or {}
    score_line = ""
    if scores:
        score_line = "Recommended quality: " + ", ".join(
            f"{label.replace('_', ' ')} {round(value * 100)}%"
            for label, value in scores.items()
            if isinstance(value, (int, float))
        )
    return "\n\n".join(
        part
        for part in [
            f"Pheo Data Store review ready: {payload['workflow'].get('name') or 'workflow'}",
            channel.get("instructions") or "",
            f"Review point: {payload['review_point'].get('name') or ''}",
            f"Observed output:\n{payload['observation']['summary']}",
            f"Recommended output:\n{payload['recommended']['summary']}" if payload["recommended"].get("summary") else "",
            score_line,
            f"Open locally:\n{payload['packet']['review_url']}" if payload["packet"].get("review_url") else "",
            cli,
        ]
        if part
    )


def _headers(channel: dict[str, Any]) -> dict[str, str]:
    headers = dict(channel.get("headers") or {})
    env_name = channel.get("headers_env")
    if env_name and os.environ.get(env_name):
        headers.update(json.loads(os.environ[env_name]))
    return headers


def _env_or_value(channel: dict[str, Any], value_key: str, env_key: str) -> str:
    env_name = channel.get(env_key) or ""
    return os.environ.get(env_name, "") if env_name else channel.get(value_key, "")


def _absolute_review_url(path: str) -> str:
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = os.environ.get("PHEO_REVIEW_BASE_URL") or "http://127.0.0.1:8787"
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def _safe_url(url: str) -> str:
    if not url:
        return ""
    if "://" not in url:
        return url.split("?", 1)[0]
    scheme, rest = url.split("://", 1)
    host = rest.split("/", 1)[0]
    return f"{scheme}://{host}"


def _overall_status(results: dict[str, dict[str, Any]]) -> str:
    statuses = {result.get("status") for result in results.values()}
    if "sent" in statuses:
        return "notified"
    if "failed" in statuses:
        return "notification_failed"
    if "not_configured" in statuses:
        return "notification_not_configured"
    return "local_review"
