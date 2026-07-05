"""
functions.py
------------
دوال مساعدة مشتركة تُستخدم في كل المشروع: تحقق من صحة المدخلات، CSRF، كلمات المرور.
"""

import re
import secrets
from flask import session
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config


# =====================================================================
# كلمات المرور
# =====================================================================
def hash_password(plain_password: str) -> str:
    """يشفّر كلمة المرور (مكافئ password_hash في PHP)."""
    return generate_password_hash(plain_password, method="pbkdf2:sha256", salt_length=16)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """يتحقق من كلمة المرور (مكافئ password_verify في PHP)."""
    return check_password_hash(password_hash, plain_password)


# =====================================================================
# التحقق من اسم المستخدم وكلمة المرور
# =====================================================================
def validate_username(username: str):
    """
    يتحقق من اسم المستخدم حسب الشروط:
    - 4 أحرف على الأقل.
    - أحرف إنجليزية وأرقام وشرطة سفلية (_) فقط.
    - منع النقطة وأي رموز أخرى.
    يُرجع (True, "") عند النجاح أو (False, "رسالة الخطأ") عند الفشل.
    """
    if not username or len(username) < Config.USERNAME_MIN_LENGTH:
        return False, f"اسم المستخدم يجب ألا يقل عن {Config.USERNAME_MIN_LENGTH} أحرف"
    if len(username) > Config.USERNAME_MAX_LENGTH:
        return False, f"اسم المستخدم يجب ألا يزيد عن {Config.USERNAME_MAX_LENGTH} حرفًا"
    if not re.match(Config.USERNAME_REGEX, username):
        return False, "اسم المستخدم يسمح فقط بأحرف إنجليزية وأرقام وشرطة سفلية (_)"
    return True, ""


def validate_password(password: str, password_confirm: str):
    """يتحقق من قوة كلمة المرور وتطابقها مع التأكيد."""
    if not password or len(password) < Config.PASSWORD_MIN_LENGTH:
        return False, f"كلمة المرور يجب ألا تقل عن {Config.PASSWORD_MIN_LENGTH} أحرف"
    if password != password_confirm:
        return False, "كلمة المرور وتأكيد كلمة المرور غير متطابقين"
    return True, ""


# =====================================================================
# حماية CSRF (Cross-Site Request Forgery)
# =====================================================================
def generate_csrf_token() -> str:
    """يولّد ويخزّن رمز CSRF في الجلسة إن لم يكن موجودًا مسبقًا."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validate_csrf_token(submitted_token: str) -> bool:
    """يقارن رمز CSRF المُرسل مع الموجود في الجلسة بطريقة آمنة زمنيًا."""
    real_token = session.get("csrf_token")
    if not real_token or not submitted_token:
        return False
    return secrets.compare_digest(real_token, submitted_token)


# =====================================================================
# حماية XSS
# =====================================================================
def sanitize_text(value: str, max_length: int = 255) -> str:
    """
    تنظيف نص مُدخل من المستخدم قبل تخزينه.
    ملاحظة: القوالب (Jinja2) تقوم بـ auto-escape تلقائيًا عند العرض، لكن هذا
    يمنع تخزين نصوص طويلة أو تحتوي أحرف تحكم غير مرغوبة في قاعدة البيانات.
    """
    if value is None:
        return ""
    value = value.strip()[:max_length]
    # إزالة أحرف التحكم غير المرئية
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
    return value


# =====================================================================
# أرقام آمنة
# =====================================================================
def generate_otp_code(length: int = 5) -> str:
    """يولّد رمز تحقق عشوائي مكوّن من أرقام فقط (افتراضيًا 5 أرقام)."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def validate_telegram_id(telegram_id: str):
    """يتحقق أن آيدي تيليجرام يتكون من أرقام فقط بطول منطقي."""
    if not telegram_id or not re.match(r"^\d{5,15}$", telegram_id):
        return False, "آيدي تيليجرام غير صالح (أرقام فقط)"
    return True, ""


def to_positive_int(value, default=0):
    try:
        n = int(value)
        return n if n >= 0 else default
    except (TypeError, ValueError):
        return default
