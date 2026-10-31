"""Progress messages to WhatsApp (via CallMeBot) and/or Telegram. Configure with GitHub secrets:

  WhatsApp:  WHATSAPP_PHONE  (e.g. 919876543210, country code, no +)   WHATSAPP_APIKEY (from CallMeBot)
  Telegram:  TELEGRAM_BOT_TOKEN                                         TELEGRAM_CHAT_ID

Any channel without secrets is skipped. A failed message never stops trading."""
import json
import os
import urllib.parse
import urllib.request


def _whatsapp(text: str) -> bool:
    phone, key = os.environ.get("WHATSAPP_PHONE"), os.environ.get("WHATSAPP_APIKEY")
    if not phone or not key:
        return False
    url = "https://api.callmebot.com/whatsapp.php?" + urllib.parse.urlencode(
        {"phone": "+" + phone.strip().lstrip("+"), "text": text, "apikey": key})
    body = urllib.request.urlopen(url, timeout=30).read().decode(errors="ignore")
    if "error" in body.lower() and "queued" not in body.lower():
        raise RuntimeError(body[:200])
    return True


def _telegram(text: str) -> bool:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat, "text": text}).encode(),
        headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15).read()
    return True


def send(text: str):
    sent = []
    for name, fn in (("whatsapp", _whatsapp), ("telegram", _telegram)):
        try:
            if fn(text):
                sent.append(name)
        except Exception as e:
            print(f"[notify] {name} failed: {e}")
    print(f"[notify] sent via: {', '.join(sent) or 'none configured'}")
