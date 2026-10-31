"""Progress messages to WhatsApp (official Meta WhatsApp Cloud API) and/or Telegram.
Configure with GitHub repo secrets — any channel without secrets is skipped:

  WhatsApp:  WA_TOKEN            permanent access token (Meta Business settings → System users)
             WA_PHONE_NUMBER_ID  "Phone number ID" from the app's WhatsApp → API Setup page
             WA_TO               your WhatsApp number with country code, digits only (e.g. 919876543210)
             WA_TEMPLATE         (optional) approved template name, default "trading_update"
             WA_TEMPLATE_LANG    (optional) template language code, default "en"
  Telegram:  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

WhatsApp only lets businesses start a chat with an approved template, so the bot sends a template
whose body is "...: {{1}}" and fills {{1}} with the update. Templates can't contain line breaks,
so lines are joined with " | ". A failed message never stops trading."""
import json
import os
import re
import urllib.error
import urllib.request


def _post(url, payload, headers):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=20).read() or b"{}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode(errors="ignore")[:400]) from None


def _whatsapp(text: str) -> bool:
    token, pid, to = (os.environ.get(k) for k in ("WA_TOKEN", "WA_PHONE_NUMBER_ID", "WA_TO"))
    if not (token and pid and to):
        return False
    ver = os.environ.get("WA_API_VERSION", "v23.0")
    url = f"https://graph.facebook.com/{ver}/{pid}/messages"
    hdr = {"Authorization": f"Bearer {token}"}
    to = re.sub(r"\D", "", to)
    # Always a template: Meta accepts plain text outside the 24h window but silently never delivers it.
    # Template parameters can't contain newlines or 4+ spaces.
    flat = re.sub(r"\s*\n\s*", " | ", text.replace("*", "")).strip()
    flat = re.sub(r" {4,}", "   ", flat)[:950]
    _post(url, {"messaging_product": "whatsapp", "to": to, "type": "template",
                "template": {"name": os.environ.get("WA_TEMPLATE") or "trading_update",
                             "language": {"code": os.environ.get("WA_TEMPLATE_LANG") or "en"},
                             "components": [{"type": "body", "parameters": [{"type": "text", "text": flat}]}]}}, hdr)
    return True


def _telegram(text: str) -> bool:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    _post(f"https://api.telegram.org/bot{token}/sendMessage",
          {"chat_id": chat, "text": text.replace("*", "")}, {})
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
