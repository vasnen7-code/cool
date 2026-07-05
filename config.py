"""
config.py
---------
كل إعدادات المشروع في مكان واحد.
لا تضع بيانات حساسة حقيقية هنا في بيئة الإنتاج، استخدم متغيرات البيئة (.env).
"""

import os
from dotenv import load_dotenv

load_dotenv()  # يقرأ ملف .env إن وجد


class Config:
    # ---------- قاعدة البيانات ----------
    DB_HOST = os.environ.get("WGAME_DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("WGAME_DB_PORT", "3306"))
    DB_NAME = os.environ.get("WGAME_DB_NAME", "wgame")
    DB_USER = os.environ.get("WGAME_DB_USER", "root")
    DB_PASSWORD = os.environ.get("WGAME_DB_PASSWORD", "")
    DB_CHARSET = "utf8mb4"

    # ---------- أمان الجلسة ----------
    # غيّر هذا المفتاح في بيئة الإنتاج (مثلاً: python -c "import secrets;print(secrets.token_hex(32))")
    SECRET_KEY = os.environ.get("WGAME_SECRET_KEY", "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # فعّل هذا عند التشغيل خلف HTTPS في الإنتاج
    SESSION_COOKIE_SECURE = os.environ.get("WGAME_HTTPS", "0") == "1"

    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # أسبوع (تذكر تسجيل الدخول)

    # ---------- قواعد اسم المستخدم وكلمة المرور ----------
    USERNAME_MIN_LENGTH = 4
    USERNAME_MAX_LENGTH = 20
    USERNAME_REGEX = r"^[A-Za-z0-9_]+$"  # إنجليزي + أرقام + شرطة سفلية فقط، بدون نقطة
    PASSWORD_MIN_LENGTH = 6

    # ---------- إعدادات اللعبة الأساسية ----------
    AUTO_PRODUCTION_TICK_SECONDS = 1  # مدة تجميع الإنتاج التلقائي (الجمجمة/الروبوت/...)
    MAX_OFFLINE_SECONDS = 60 * 60 * 12  # أقصى مدة يُحتسب عنها إنتاج أثناء غياب اللاعب (12 ساعة)

    # ---------- رفع الملفات (صور الأدمن لاحقاً) ----------
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "images", "uploads")
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

    # ---------- بوت تيليجرام والتحقق عبر OTP ----------
    # مهم: لا تشارك هذا التوكن علنًا (لا ترفعه لريبو عام). يُفضّل نقله لملف .env في الإنتاج.
    TELEGRAM_BOT_TOKEN = os.environ.get(
        "WGAME_TELEGRAM_BOT_TOKEN", "8766004985:AAHrfo4JlQF4gSj8dFwJKFXUi9HC7MzIwg0"
    )
    TELEGRAM_OTP_BOT_URL = "https://t.me/APP1OTPBOT"   # زر "OTP Bot" في الموقع
    TELEGRAM_DEV_URL = "https://t.me/Y0YY22"            # زر "المطور" داخل البوت
    TELEGRAM_CHANNEL_URL = "https://t.me/sc_fn"          # زر "قناة المطور" داخل البوت

    OTP_LENGTH = 5
    OTP_TTL_SECONDS = 300              # صلاحية الرمز: 5 دقائق
    OTP_RESEND_COOLDOWN_SECONDS = 45   # منع طلب رمز جديد بسرعة (حماية من الإزعاج/السبام)
    TELEGRAM_ID_REGEX = r"^\d{5,15}$"  # آيدي تيليجرام أرقام فقط
