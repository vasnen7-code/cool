"""
api/otp_api.py
---------------
نقاط نهاية طلب رمز OTP. لا تُرجع الرمز نفسه في الاستجابة أبدًا؛
الرمز يصل للمستخدم فقط عبر بوت تيليجرام (زر OTP داخل البوت).
"""

from flask import Blueprint, request, jsonify

from functions import validate_csrf_token, validate_telegram_id
from database import fetch_one
from otp import create_otp

otp_api_bp = Blueprint("otp_api", __name__, url_prefix="/api/otp")


def _check_csrf():
    token = request.headers.get("X-CSRF-Token") or (request.get_json(silent=True) or {}).get("csrf_token")
    return validate_csrf_token(token)


@otp_api_bp.route("/request-register", methods=["POST"])
def request_register_otp():
    """يُطلب عند التسجيل: يولّد رمز OTP جديد مرتبط بآيدي تيليجرام المُدخل في نموذج التسجيل."""
    if not _check_csrf():
        return jsonify({"success": False, "error": "رمز الحماية غير صالح"}), 403

    data = request.get_json(silent=True) or {}
    telegram_id = (data.get("telegram_id") or "").strip()

    ok, msg = validate_telegram_id(telegram_id)
    if not ok:
        return jsonify({"success": False, "error": msg}), 400

    existing = fetch_one("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
    if existing:
        return jsonify({"success": False, "error": "آيدي التيليجرام هذا مرتبط بحساب موجود مسبقًا"}), 400

    result = create_otp(int(telegram_id), "register")
    if result is None:
        return jsonify({"success": False, "error": "الرجاء الانتظار قليلاً قبل طلب رمز جديد"}), 429

    return jsonify({"success": True, "message": "تم إرسال الرمز، افتح بوت OTP واضغط زر OTP لاستلامه"})


@otp_api_bp.route("/request-reset", methods=["POST"])
def request_reset_otp():
    """
    يُطلب عند استعادة كلمة المرور: يبحث عن المستخدم بالاسم، ويولّد رمز OTP
    مرتبط بآيدي التيليجرام المسجَّل مسبقًا لهذا الحساب (وليس آيدي جديد يُدخله المستخدم).
    """
    if not _check_csrf():
        return jsonify({"success": False, "error": "رمز الحماية غير صالح"}), 403

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()

    user = fetch_one("SELECT id, telegram_id FROM users WHERE username = %s", (username,))

    # رسالة عامة دائمًا لمنع تعداد الحسابات (لا نكشف إن كان الاسم موجودًا)
    generic_response = jsonify({
        "success": True,
        "message": "إن كان الحساب موجودًا ومرتبطًا بتيليجرام، تم إرسال الرمز عبر بوت OTP",
    })

    if not user or not user["telegram_id"]:
        return generic_response

    create_otp(user["telegram_id"], "reset_password")
    return generic_response
