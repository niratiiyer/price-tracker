import json
import os
import urllib.request


def send_alert(message: str) -> None:
    print(f"ALERT: {message}")
    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        return
    request = urllib.request.Request(
        webhook,
        data=json.dumps({"content": message}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "crypto-market-monitor"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=10).read()
    except Exception as exc:
        print(f"Couldn't send Discord alert: {exc}")
