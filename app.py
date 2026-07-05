"""
app.py
------
نقطة الدخول الرئيسية. يجمّع كل الـ Blueprints ويضبط إعدادات الأمان العامة.

تشغيل محلي:
    pip install -r requirements.txt
    python database/seed_admin.py   # لتوليد كلمة مرور الأدمن الحقيقية بعد استيراد schema.sql
    python app.py
"""

from flask import Flask, session, redirect, url_for
from config import Config

from auth import auth_bp
from game import game_bp
from admin import admin_bp
from api.game_api import game_api_bp
from api.otp_api import otp_api_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(auth_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(game_api_bp)
    app.register_blueprint(otp_api_bp)

    @app.after_request
    def set_security_headers(response):
        # حماية إضافية على مستوى الهيدرز (تكمّل حماية CSRF/XSS في الكود)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.errorhandler(404)
    def not_found(e):
        return redirect(url_for("game.index") if session.get("user_id") else url_for("auth.login"))

    return app


app = create_app()

if __name__ == "__main__":
    # للتطوير المحلي فقط. في الإنتاج استخدم gunicorn/uwsgi خلف Nginx مع HTTPS.
    app.run(debug=True, host="0.0.0.0", port=5000)
