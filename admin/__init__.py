"""
admin/__init__.py
------------------
لوحة تحكم الأدمن. هذه نسخة أولية (Phase 1) تحتوي فقط على لوحة معلومات بسيطة
للتأكد من عمل صلاحيات الأدمن؛ باقي الأدوات (إدارة المستخدمين، الهدايا،
الأحداث، النسخ الاحتياطي...) ستُبنى في المرحلة القادمة فوق نفس الهيكل.
"""

from flask import Blueprint, render_template, session

from decorators import admin_required
from database import fetch_one

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def dashboard():
    stats = fetch_one("SELECT COUNT(*) AS total_users FROM users")
    return render_template("admin_dashboard.html", total_users=stats["total_users"], username=session.get("username"))
