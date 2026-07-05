"""
telegram_bot.py
----------------
بوت تيليجرام مسؤول فقط عن توصيل رمز OTP للمستخدم (الموقع لا يرسل الرمز أبدًا مباشرة).

يعمل هذا الملف كسكربت مستقل بجانب app.py (نفس قاعدة البيانات)، عبر Long Polling
لتبسيط النشر بدون الحاجة لإعداد Webhook/HTTPS منفصل للبوت.

تشغيل:
    python telegram_bot.py

الأزرار:
- /start يعرض: زر "🔑 OTP" (يرسل آخر رمز صالح لهذا المستخدم)، زر "👨‍💻 المطور"، زر "📢 قناة المطور".
"""

import time
import requests

from config import Config
from otp import get_latest_otp_for_telegram

API_BASE = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}"

MAIN_KEYBOARD = {
    "inline_keyboard": [
        [{"text": "🔑 OTP", "callback_data": "otp"}],
        [
            {"text": "👨‍💻 المطور", "url": Config.TELEGRAM_DEV_URL},
            {"text": "📢 قناة المطور", "url": Config.TELEGRAM_CHANNEL_URL},
        ],
    ]
}

PURPOSE_LABELS = {
    "register": "إنشاء حساب",
    "reset_password": "إعادة تعيين كلمة المرور",
}


def tg_call(method: str, payload: dict) -> dict:
    """نداء عام لأي method في Telegram Bot API."""
    resp = requests.post(f"{API_BASE}/{method}", json=payload, timeout=35)
    return resp.json()


def send_welcome(chat_id: int):
    tg_call("sendMessage", {
        "chat_id": chat_id,
        "text": (
            "مرحبًا بك في بوت W Game 🎮\n\n"
            "اضغط زر 🔑 OTP لاستلام آخر رمز تحقق طلبته من الموقع "
            "(للتسجيل أو استعادة كلمة المرور)."
        ),
        "reply_markup": MAIN_KEYBOARD,
    })


def send_otp_code(chat_id: int, telegram_user_id: int, callback_query_id: str):
    otp_row = get_latest_otp_for_telegram(telegram_user_id)

    if not otp_row:
        tg_call("answerCallbackQuery", {
            "callback_query_id": callback_query_id,
            "text": "لا يوجد رمز حالي صالح. اطلب رمزًا جديدًا من الموقع أولاً.",
            "show_alert": True,
        })
        return

    purpose_label = PURPOSE_LABELS.get(otp_row["purpose"], otp_row["purpose"])
    tg_call("sendMessage", {
        "chat_id": chat_id,
        "text": f"رمز التحقق الخاص بك ({purpose_label}):\n\n<b>{otp_row['code']}</b>\n\nصالح لمدة قصيرة، لا تشاركه مع أحد.",
        "parse_mode": "HTML",
    })
    tg_call("answerCallbackQuery", {"callback_query_id": callback_query_id})


def handle_update(update: dict):
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = (message.get("text") or "").strip()
        if text.startswith("/start"):
            send_welcome(chat_id)

    elif "callback_query" in update:
        cq = update["callback_query"]
        data = cq.get("data")
        chat_id = cq["message"]["chat"]["id"]
        from_user_id = cq["from"]["id"]

        if data == "otp":
            send_otp_code(chat_id, from_user_id, cq["id"])
        else:
            tg_call("answerCallbackQuery", {"callback_query_id": cq["id"]})


def run_bot():
    print("W Game OTP bot is running (long polling)...")
    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset
            resp = requests.get(f"{API_BASE}/getUpdates", params=params, timeout=35)
            data = resp.json()

            if not data.get("ok"):
                print("Telegram API error:", data)
                time.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                try:
                    handle_update(update)
                except Exception as e:
                    print("Error handling update:", e)

        except requests.RequestException as e:
            print("Network error, retrying in 5s:", e)
            time.sleep(5)


if __name__ == "__main__":
    run_bot()
