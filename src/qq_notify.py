"""Send FIFA briefing to QQ via QQ Official Bot API or Reasonix bridge."""

import os
import sys
import urllib.request
import json
from pathlib import Path


def _load_env():
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_env()


def send_qq(message: str) -> bool:
    """Send QQ message via QQ Official Bot OpenAPI.

    Uses the bot token to call the QQ message API directly.
    """
    token = os.environ.get("QQ_BOT_TOKEN", "")
    appid = os.environ.get("QQ_BOT_APP_ID", "1903460939")
    openid = os.environ.get("QQ_BOT_TARGET_OPENID", "")

    if not token:
        # Fallback: try Reasonix internal bridge
        return _send_reasonix(message)

    url = f"https://api.sgroup.qq.com/v2/users/{openid}/messages" if openid else None

    if not url:
        print("Set QQ_BOT_TARGET_OPENID in .env", file=sys.stderr)
        return False

    payload = {
        "content": message,
        "msg_type": 0,
        "msg_id": f"fifa_{int(__import__('time').time())}",
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"QQBot {token}",
            },
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data.get("code") == 0:
            return True
        print(f"QQ API: {data}", file=sys.stderr)
    except Exception as e:
        print(f"QQ API error: {e}", file=sys.stderr)

    return _send_reasonix(message)


def _send_reasonix(message: str) -> bool:
    """Fallback: try Reasonix internal QQ bridge."""
    secret = os.environ.get("QQ_BOT_APP_SECRET", "")
    for port in [9674, 9675, 9676]:
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/qq/send",
                data=json.dumps(
                    {"appSecret": secret, "content": message}
                ).encode(),
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            if data.get("code") == 0 or data.get("status") == "ok":
                return True
        except Exception:
            continue
    return False


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "FIFA test"
    ok = send_qq(msg)
    print("OK" if ok else "FAILED")
