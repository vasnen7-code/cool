"""
auth.py
-------
Blueprint لنظام الحسابات: إنشاء حساب / تسجيل دخول / تسجيل خروج / إعادة تعيين كلمة المرور.
التسجيل واستعادة كلمة المرور يتطلبان رمز OTP يصل عبر بوت تيليجرام (وليس بريد إلكتروني).
كل الاستعلامات Prepared Statements، وكل نموذج محمي بـ CSRF token.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from database import fetch_one, execute, db_cursor
from functions import (
    hash_password, verify_password,
    validate_username, validate_password, validate_telegram_id,
    generate_csrf_token, validate_csrf_token,
)
from otp import verify_otp
from config import Config

auth_bp = Blueprint("auth", __name__)


# =====================================================================
# إنشاء حساب (يتطلب: يوزر، آيدي تيليجرام، باسورد، تأكيد، رمز OTP)
# =====================================================================
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("game.index"))

    csrf_token = generate_csrf_token()
    telegram_links = {"otp_bot": Config.TELEGRAM_OTP_BOT_URL}

    if request.method == "POST":
        form_kwargs = dict(csrf_token=csrf_token, telegram_links=telegram_links)

        if not validate_csrf_token(request.form.get("csrf_token", "")):
            flash("انتهت صلاحية الجلسة، حاول مرة أخرى.", "error")
            return render_template("register.html", **form_kwargs)

        username = (request.form.get("username") or "").strip()
        telegram_id = (request.form.get("telegram_id") or "").strip()
        password = request.form.get("password") or ""
        password_confirm = request.form.get("password_confirm") or ""
        otp_code = (request.form.get("otp_code") or "").strip()

        form_kwargs.update(username=username, telegram_id=telegram_id)

        ok, msg = validate_username(username)
        if not ok:
            flash(msg, "error")
            return render_template("register.html", **form_kwargs)

        ok, msg = validate_telegram_id(telegram_id)
        if not ok:
            flash(msg, "error")
            return render_template("register.html", **form_kwargs)

        ok, msg = validate_password(password, password_confirm)
        if not ok:
            flash(msg, "error")
            return render_template("register.html", **form_kwargs)

        if not otp_code:
            flash("الرجاء إدخال رمز التحقق (OTP) المُرسل عبر البوت", "error")
            return render_template("register.html", **form_kwargs)

        # التحقق من عدم تكرار اسم المستخدم أو آيدي التيليجرام (Prepared Statements)
        existing = fetch_one(
            "SELECT id FROM users WHERE username = %s OR telegram_id = %s",
            (username, telegram_id),
        )
        if existing:
            flash("اسم المستخدم أو آيدي التيليجرام مستخدم مسبقًا", "error")
            return render_template("register.html", **form_kwargs)

        # التحقق من رمز OTP (يعلَّم كمستخدَم فور نجاح التحقق، لا يمكن إعادة استخدامه)
        if not verify_otp(int(telegram_id), "register", otp_code):
            flash("رمز التحقق غير صحيح أو منتهي الصلاحية", "error")
            return render_template("register.html", **form_kwargs)

        password_hash = hash_password(password)

        # إنشاء المستخدم + صف الإحصائيات + صفوف المباني الأساسية في معاملة واحدة
        with db_cursor(commit=True) as cur:
            cur.execute(
                """INSERT INTO users (username, telegram_id, password_hash, role, w_balance, gems, crowns, last_collect_at)
                   VALUES (%s, %s, %s, 'user', 0, 0, 0, NOW())""",
                (username, telegram_id, password_hash),
            )
            user_id = cur.lastrowid

            cur.execute("INSERT INTO user_stats (user_id) VALUES (%s)", (user_id,))

            cur.execute("SELECT id FROM buildings_catalog WHERE key_name IN ('head','skull','robot')")
            building_ids = [row["id"] for row in cur.fetchall()]
            for building_id in building_ids:
                cur.execute(
                    "INSERT INTO user_buildings (user_id, building_id, level) VALUES (%s, %s, 0)",
                    (user_id, building_id),
                )

        # تسجيل دخول تلقائي بعد إنشاء الحساب
        session.clear()
        session.permanent = True
        session["user_id"] = user_id
        session["username"] = username
        session["role"] = "user"

        flash("تم إنشاء الحساب بنجاح!", "success")
        return redirect(url_for("game.index"))

    return render_template("register.html", csrf_token=csrf_token, telegram_links=telegram_links)


# =====================================================================
# تسجيل الدخول
# =====================================================================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("game.index"))

    csrf_token = generate_csrf_token()

    if request.method == "POST":
        if not validate_csrf_token(request.form.get("csrf_token", "")):
            flash("انتهت صلاحية الجلسة، حاول مرة أخرى.", "error")
            return render_template("login.html", csrf_token=csrf_token)

        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        remember = request.form.get("remember") == "1"

        user = fetch_one(
            "SELECT id, username, password_hash, role, is_banned, ban_reason FROM users WHERE username = %s",
            (username,),
        )

        if not user or not verify_password(password, user["password_hash"]):
            flash("اسم المستخدم أو كلمة المرور غير صحيحة", "error")
            return render_template("login.html", csrf_token=csrf_token, username=username)

        if user["is_banned"]:
            flash(f"هذا الحساب محظور. السبب: {user['ban_reason'] or 'غير محدد'}", "error")
            return render_template("login.html", csrf_token=csrf_token)

        session.clear()
        session.permanent = remember  # تذكر تسجيل الدخول
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]

        execute("UPDATE users SET last_login_at = NOW() WHERE id = %s", (user["id"],))

        return redirect(url_for("admin.dashboard") if user["role"] == "admin" else url_for("game.index"))

    return render_template("login.html", csrf_token=csrf_token)


# =====================================================================
# تسجيل الخروج
# =====================================================================
@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


# =====================================================================
# إعادة تعيين كلمة المرور عبر رمز OTP من بوت تيليجرام
# خطوة واحدة: يوزر + رمز OTP (يُطلب بزر منفصل) + كلمة مرور جديدة + تأكيد.
# الرمز يُرسَل لآيدي التيليجرام المسجَّل مسبقًا مع هذا الحساب (وليس آيدي يُدخله المستخدم هنا).
# =====================================================================
@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password_request():
    csrf_token = generate_csrf_token()
    telegram_links = {"otp_bot": Config.TELEGRAM_OTP_BOT_URL}

    if request.method == "POST":
        form_kwargs = dict(csrf_token=csrf_token, telegram_links=telegram_links)

        if not validate_csrf_token(request.form.get("csrf_token", "")):
            flash("انتهت صلاحية الجلسة، حاول مرة أخرى.", "error")
            return render_template("reset_password.html", **form_kwargs)

        username = (request.form.get("username") or "").strip()
        otp_code = (request.form.get("otp_code") or "").strip()
        password = request.form.get("password") or ""
        password_confirm = request.form.get("password_confirm") or ""

        form_kwargs.update(username=username)

        ok, msg = validate_password(password, password_confirm)
        if not ok:
            flash(msg, "error")
            return render_template("reset_password.html", **form_kwargs)

        user = fetch_one("SELECT id, telegram_id FROM users WHERE username = %s", (username,))

        # رسالة عامة موحّدة سواء كان الحساب موجودًا أو لا، أو الرمز خاطئ (منع تعداد الحسابات)
        generic_error = "بيانات غير صحيحة أو رمز التحقق غير صالح"

        if not user or not user["telegram_id"] or not otp_code:
            flash(generic_error, "error")
            return render_template("reset_password.html", **form_kwargs)

        if not verify_otp(user["telegram_id"], "reset_password", otp_code):
            flash(generic_error, "error")
            return render_template("reset_password.html", **form_kwargs)

        execute("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(password), user["id"]))

        flash("تم تغيير كلمة المرور بنجاح، يمكنك تسجيل الدخول الآن.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", csrf_token=csrf_token, telegram_links=telegram_links)
