"""
api/game_api.py
----------------
نقاط النهاية (AJAX) الخاصة بحلقة اللعب: الضغط اليدوي، مزامنة الإنتاج التلقائي، شراء التطويرات.
كل الطلبات تتطلب تسجيل دخول + رمز CSRF صالح (يُرسل في الهيدر X-CSRF-Token).
"""

from flask import Blueprint, request, jsonify, session

from decorators import login_required
from functions import validate_csrf_token
from database import fetch_one, db_cursor
from game_engine import (
    apply_manual_click,
    apply_auto_production,
    apply_auto_click_boost_production,
    get_user_buildings,
)

game_api_bp = Blueprint("game_api", __name__, url_prefix="/api")


def _check_csrf():
    token = request.headers.get("X-CSRF-Token") or (request.json or {}).get("csrf_token")
    return validate_csrf_token(token)


@game_api_bp.route("/click", methods=["POST"])
@login_required
def click():
    if not _check_csrf():
        return jsonify({"success": False, "error": "رمز الحماية غير صالح"}), 403

    user_id = session["user_id"]
    result = apply_manual_click(user_id)
    user = fetch_one("SELECT w_balance, gems, crowns FROM users WHERE id = %s", (user_id,))

    return jsonify({
        "success": True,
        "gained_w": result["gained_w"],
        "is_critical": result["is_critical"],
        "gems_won": result["gems_won"],
        "balance": {
            "w": float(user["w_balance"]),
            "gems": user["gems"],
            "crowns": user["crowns"],
        },
    })


@game_api_bp.route("/sync", methods=["POST"])
@login_required
def sync():
    """
    يُستدعى دوريًا (كل بضع ثوانٍ) من واجهة اللعبة لتحصيل إنتاج الروبوت/الجمجمة/Auto-Click
    المتراكم منذ آخر مزامنة، ولإرجاع الرصيد المحدث.
    """
    user_id = session["user_id"]
    auto_result = apply_auto_production(user_id)
    boost_result = apply_auto_click_boost_production(user_id, auto_result["seconds_elapsed"])
    user = fetch_one("SELECT w_balance, gems, crowns FROM users WHERE id = %s", (user_id,))

    return jsonify({
        "success": True,
        "auto_production": auto_result,
        "auto_click_boost": boost_result,
        "balance": {
            "w": float(user["w_balance"]),
            "gems": user["gems"],
            "crowns": user["crowns"],
        },
    })


@game_api_bp.route("/upgrade", methods=["POST"])
@login_required
def upgrade():
    if not _check_csrf():
        return jsonify({"success": False, "error": "رمز الحماية غير صالح"}), 403

    data = request.get_json(silent=True) or {}
    building_key = data.get("building_key", "")
    user_id = session["user_id"]

    building = fetch_one(
        "SELECT id, base_price, price_growth FROM buildings_catalog WHERE key_name = %s",
        (building_key,),
    )
    if not building:
        return jsonify({"success": False, "error": "عنصر غير موجود"}), 404

    user_building = fetch_one(
        "SELECT level FROM user_buildings WHERE user_id = %s AND building_id = %s",
        (user_id, building["id"]),
    )
    current_level = user_building["level"] if user_building else 0
    price = float(building["base_price"]) * (float(building["price_growth"]) ** current_level)

    user = fetch_one("SELECT w_balance FROM users WHERE id = %s", (user_id,))
    if float(user["w_balance"]) < price:
        return jsonify({"success": False, "error": "رصيد W غير كافٍ"}), 400

    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE users SET w_balance = w_balance - %s WHERE id = %s", (price, user_id))
        if user_building:
            cur.execute(
                "UPDATE user_buildings SET level = level + 1 WHERE user_id = %s AND building_id = %s",
                (user_id, building["id"]),
            )
        else:
            cur.execute(
                "INSERT INTO user_buildings (user_id, building_id, level) VALUES (%s, %s, 1)",
                (user_id, building["id"]),
            )
        cur.execute(
            "UPDATE user_stats SET total_upgrades_bought = total_upgrades_bought + 1 WHERE user_id = %s",
            (user_id,),
        )

    return jsonify({"success": True, "new_level": current_level + 1, "paid": price})


@game_api_bp.route("/state", methods=["GET"])
@login_required
def state():
    """يُرجع كامل حالة اللاعب الحالية (رصيد + مباني) لإعادة رسم الواجهة عند الحاجة."""
    user_id = session["user_id"]
    user = fetch_one("SELECT w_balance, gems, crowns FROM users WHERE id = %s", (user_id,))
    buildings = get_user_buildings(user_id)
    return jsonify({
        "success": True,
        "balance": {"w": float(user["w_balance"]), "gems": user["gems"], "crowns": user["crowns"]},
        "buildings": buildings,
    })
