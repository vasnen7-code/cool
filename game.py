"""
game.py
-------
Blueprint صفحة اللعبة الرئيسية (Collection + عرض المباني).
"""

from flask import Blueprint, render_template, session

from decorators import login_required
from functions import generate_csrf_token
from database import fetch_one
from game_engine import get_user_buildings, apply_auto_production, apply_auto_click_boost_production

game_bp = Blueprint("game", __name__)


@game_bp.route("/")
@login_required
def index():
    user_id = session["user_id"]

    # عند فتح الصفحة، نحتسب فورًا أي إنتاج تلقائي تراكم أثناء غياب اللاعب
    auto_result = apply_auto_production(user_id)
    apply_auto_click_boost_production(user_id, auto_result["seconds_elapsed"])

    user = fetch_one("SELECT username, w_balance, gems, crowns FROM users WHERE id = %s", (user_id,))
    buildings = get_user_buildings(user_id)

    return render_template(
        "index.html",
        csrf_token=generate_csrf_token(),
        username=user["username"],
        w_balance=float(user["w_balance"]),
        gems=user["gems"],
        crowns=user["crowns"],
        buildings=buildings,
        offline_gained_w=auto_result["gained_w"],
    )
