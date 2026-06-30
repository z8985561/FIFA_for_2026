"""Send FIFA briefing to QQ via napcat/go-cqhttp HTTP API."""

import os
import sys
import urllib.request
import json


def _config():
    return {
        "api": os.getenv("QQ_BOT_API", "http://127.0.0.1:5700"),
        "target_type": os.getenv("QQ_TARGET_TYPE", "user"),
        "target_id": os.getenv("QQ_TARGET_ID", ""),
    }


def send_qq(message: str) -> bool:
    """Send a text message via QQ bot HTTP API (napcat/go-cqhttp)."""
    cfg = _config()
    if not cfg["target_id"] or cfg["target_id"] == "your_qq_number":
        print("QQ not configured — set QQ_TARGET_ID in .env", file=sys.stderr)
        return False

    url = f"{cfg['api']}/send_msg"
    payload = {
        f"{cfg['target_type']}_id": cfg["target_id"],
        "message": message,
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data.get("status") == "ok":
            return True
        print(f"QQ send failed: {data}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"QQ API error: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    # Test
    test_msg = sys.argv[1] if len(sys.argv) > 1 else "FIFA 简报测试消息"
    ok = send_qq(test_msg)
    print("OK" if ok else "FAILED")
