"""
otp.py
------
إدارة رموز التحقق (OTP) المرسلة عبر بوت تيليجرام.
يُستخدم هذا الملف من الموقع (Flask) ومن سكربت البوت (telegram_bot.py) معًا،
لأن كليهما يقرأ/يكتب على نفس جدول otp_codes بنفس قاعدة البيانات.
"""

from datetime import datetime, timedelta

from database import fetch_one, execute, db_cursor
from functions import generate_otp_code
from config import Config


def create_otp(telegram_id: int, purpose: str) -> dict | None:
    """
    يولّد رمز OTP جديد لآيدي تيليجرام معيّن ولغرض معيّن (register / reset_password).
    يُطبَّق حد أدنى بين الطلبات (Cooldown) لمنع السبام.
    يُرجع dict فيه معلومات النجاح، أو None إذا كان لازال داخل فترة الانتظار.
    """
    last = fetch_one(
        """SELECT created_at FROM otp_codes
           WHERE telegram_id = %s AND purpose = %s
           ORDER BY id DESC LIMIT 1""",
        (telegram_id, purpose),
    )
    if last:
        elapsed = (datetime.utcnow() - last["created_at"]).total_seconds()
        if elapsed < Config.OTP_RESEND_COOLDOWN_SECONDS:
            return None  # لازال داخل فترة الانتظار

    code = generate_otp_code(Config.OTP_LENGTH)
    expires_at = datetime.utcnow() + timedelta(seconds=Config.OTP_TTL_SECONDS)

    execute(
        """INSERT INTO otp_codes (telegram_id, purpose, code, used, expires_at)
           VALUES (%s, %s, %s, 0, %s)""",
        (telegram_id, purpose, code, expires_at),
    )
    return {"code": code, "expires_at": expires_at}


def verify_otp(telegram_id: int, purpose: str, submitted_code: str) -> bool:
    """يتحقق من رمز OTP مُدخل من المستخدم، ويعلّمه كمستخدَم عند النجاح (لا يُستخدم مرتين)."""
    if not submitted_code or not submitted_code.isdigit():
        return False

    row = fetch_one(
        """SELECT id FROM otp_codes
           WHERE telegram_id = %s AND purpose = %s AND code = %s
                 AND used = 0 AND expires_at > NOW()
           ORDER BY id DESC LIMIT 1""",
        (telegram_id, purpose, submitted_code),
    )
    if not row:
        return False

    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE otp_codes SET used = 1 WHERE id = %s", (row["id"],))
    return True


def get_latest_otp_for_telegram(telegram_id: int):
    """
    يُستخدم من البوت فقط: يُرجع آخر رمز صالح (غير مستخدم وغير منتهي) لآيدي تيليجرام معيّن،
    بغض النظر عن الغرض، لأن زر OTP بالبوت يرسل ببساطة "آخر رمز وصله".
    """
    return fetch_one(
        """SELECT code, purpose, expires_at FROM otp_codes
           WHERE telegram_id = %s AND used = 0 AND expires_at > NOW()
           ORDER BY id DESC LIMIT 1""",
        (telegram_id,),
    )
