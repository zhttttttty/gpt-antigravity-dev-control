from __future__ import annotations
import json, urllib.error, urllib.request

def request_json(method: str, url: str, *, headers=None, payload=None, timeout=300) -> dict:
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or {}).items(): req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8'); return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace'); raise RuntimeError(f'HTTP {exc.code} {url}: {body}') from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f'Network error calling {url}: {exc}') from exc
