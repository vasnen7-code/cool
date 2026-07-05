"""
decorators.py
-------------
Decorators للحماية: تسجيل الدخول مطلوب / صلاحية أدمن مطلوبة.
"""

from functools import wraps
from flask import session, redirect, url_for, jsonify, request
from database import fetch_one


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "يجب تسجيل الدخول"}), 401
            return redirect(url_for("auth.login"))

        # تحقق من الحظر في كل طلب (قد يتم حظر المستخدم أثناء وجوده متصلاً)
        user = fetch_one("SELECT is_banned, ban_reason FROM users WHERE id = %s", (session["user_id"],))
        if not user:
            session.clear()
            return redirect(url_for("auth.login"))
        if user["is_banned"]:
            session.clear()
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "الحساب محظور"}), 403
            return redirect(url_for("auth.login"))

        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id") or session.get("role") != "admin":
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "صلاحية أدمن مطلوبة"}), 403
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped
