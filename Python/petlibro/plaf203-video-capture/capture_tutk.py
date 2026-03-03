#!/usr/bin/env python3
"""
mitmproxy addon to capture Petlibro video bootstrap calls and extract TUTK/Kalay creds.
Run:
  mitmdump -s capture_tutk.py -p 8080
"""
import json
import os
import re
from datetime import datetime, timezone
from mitmproxy import http, ctx

OUT_DIR = os.path.expanduser("~//.openclaw/workspace/petlibro/captures").replace("//", "/")
OUT_JSONL = os.path.join(OUT_DIR, "petlibro_video_flows.jsonl")
OUT_PRETTY = os.path.join(OUT_DIR, "latest_video_bootstrap.json")

TARGET_HOST = "api.us.petlibro.com"
TARGET_PATH_HINTS = [
    "/app/device/video",
    "/app/device/camera",
    "/app/video/token",
    "/app/camera/liveStream",
]

KEY_PATTERNS = re.compile(r"(tutk|kalay|iotc|av|uid|token|auth|relay|server)", re.I)


def _ensure_out_dir():
    os.makedirs(OUT_DIR, exist_ok=True)


def _safe_json_loads(raw: bytes):
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except Exception:
        return None


def _find_interesting(obj, path=""):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else str(k)
            if KEY_PATTERNS.search(str(k)):
                hits.append({"path": p, "value": v})
            hits.extend(_find_interesting(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{path}[{i}]"
            hits.extend(_find_interesting(v, p))
    elif isinstance(obj, str):
        if KEY_PATTERNS.search(obj):
            hits.append({"path": path, "value": obj})
    return hits


def _is_target(flow: http.HTTPFlow) -> bool:
    host = flow.request.pretty_host or ""
    path = flow.request.path or ""
    if host != TARGET_HOST:
        return False
    return any(h in path for h in TARGET_PATH_HINTS)


def response(flow: http.HTTPFlow):
    if not _is_target(flow):
        return

    _ensure_out_dir()

    req_json = _safe_json_loads(flow.request.raw_content or b"")
    res_json = _safe_json_loads(flow.response.raw_content or b"") if flow.response else None

    headers = dict(flow.request.headers)
    token_hdr = headers.get("token")

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request": {
            "method": flow.request.method,
            "scheme": flow.request.scheme,
            "host": flow.request.pretty_host,
            "path": flow.request.path,
            "headers": {
                "source": headers.get("source"),
                "language": headers.get("language"),
                "version": headers.get("version"),
                "token": token_hdr,
            },
            "json": req_json,
            "raw_text": (flow.request.get_text(strict=False) or "")[:5000],
        },
        "response": {
            "status_code": flow.response.status_code if flow.response else None,
            "headers": dict(flow.response.headers) if flow.response else {},
            "json": res_json,
            "raw_text": ((flow.response.get_text(strict=False) if flow.response else "") or "")[:10000],
        },
    }

    interesting = []
    if req_json is not None:
        interesting.extend(_find_interesting(req_json, "request.json"))
    if res_json is not None:
        interesting.extend(_find_interesting(res_json, "response.json"))
    record["interesting"] = interesting

    with open(OUT_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    with open(OUT_PRETTY, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    ctx.log.info(
        f"[PETLIBRO] captured {flow.request.path} status={record['response']['status_code']} "
        f"interesting={len(interesting)} token_present={bool(token_hdr)}"
    )
