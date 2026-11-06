"""Sending messages to the Telegram group via the Bot API.

The bot token is read from the TELEGRAM_BOT_TOKEN environment variable (an
environment secret — never committed) and the chat id from TELEGRAM_CHAT_ID
or config/telegram.json. The token never appears in the repository.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from typing import Optional

API = "https://api.telegram.org"
CHAT_CONFIG = "config/telegram.json"


class TelegramError(RuntimeError):
    pass


def _token() -> str:
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not tok:
        raise TelegramError("TELEGRAM_BOT_TOKEN غير موجود في متغيرات البيئة")
    return tok


def _chat_id(explicit: Optional[str] = None) -> str:
    cid = explicit or os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not cid:
        try:
            with open(CHAT_CONFIG) as f:
                cid = str(json.load(f).get("chat_id", "")).strip()
        except OSError:
            pass
    if not cid:
        raise TelegramError(
            "معرف المحادثة غير محدد — حدده في TELEGRAM_CHAT_ID أو config/telegram.json"
        )
    return cid


def _call(method: str, payload: dict, timeout: float = 20.0) -> dict | list:
    req = urllib.request.Request(
        f"{API}/bot{_token()}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        out = json.load(resp)
    if not isinstance(out, dict) or not out.get("ok"):
        raise TelegramError(f"رفض تيليجرام الطلب: {out}")
    return out["result"]


def send_message(text: str, chat_id: Optional[str] = None) -> dict:
    return _call(
        "sendMessage",
        {
            "chat_id": _chat_id(chat_id),
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
    )


def discover_chats() -> dict[str, str]:
    """List chats the bot can currently see (send a message in the group first)."""
    seen: dict[str, str] = {}
    for update in _call("getUpdates", {"timeout": 0}):
        holder = (
            update.get("message")
            or update.get("channel_post")
            or update.get("my_chat_member")
            or {}
        )
        chat = holder.get("chat") or {}
        if chat.get("id") is not None:
            title = chat.get("title") or chat.get("username") or chat.get("first_name") or ""
            seen[str(chat["id"])] = f"{title} ({chat.get('type', '')})"
    return seen


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="إرسال رسائل تيليجرام واكتشاف معرف القروب")
    p.add_argument("--discover", action="store_true",
                   help="اعرض المحادثات اللي يشوفها البوت (أرسل رسالة بالقروب أولاً)")
    p.add_argument("--send", help="نص الرسالة")
    p.add_argument("--send-file", help="ملف نصي يُرسل محتواه")
    p.add_argument("--chat-id", default=None)
    args = p.parse_args(argv)

    if args.discover:
        chats = discover_chats()
        if not chats:
            print("ما شفت أي محادثة — أرسل أي رسالة داخل القروب وجرب مرة ثانية.")
        for cid, title in chats.items():
            print(f"{cid}\t{title}")
        return 0
    text = args.send
    if args.send_file:
        with open(args.send_file) as f:
            text = f.read()
    if not text:
        p.error("حدد --send أو --send-file أو --discover")
    result = send_message(text, args.chat_id)
    print(f"وصلت الرسالة (message_id={result.get('message_id')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
