"""
game_engine.py
--------------
المنطق الأساسي للعبة: حساب W من الضغط اليدوي، ومن الإنتاج التلقائي (روبوت/جمجمة/...)،
وفرصة ظهور الجواهر. هذه الدوال تُستخدم من صفحة اللعبة ومن الـ API معًا لضمان الاتساق.

ملاحظة مهمة حول الآلية (كما طلب المستخدم):
- الضغط اليدوي (click)      -> مصدر منفصل، يعتمد على مستوى "الرأس".
- الروبوت (robot)           -> مصدر تلقائي منفصل تمامًا، له إنتاجه الخاص بالثانية.
- الجمجمة (skull)           -> مصدر تلقائي منفصل آخر، لا يشترك مع الروبوت.
- Auto Click (بوست مؤقت)    -> يحاكي ضغطات تلقائية بمعادلة الضغط اليدوي، مصدر مستقل بحد ذاته.
كل مصدر من هذه له فرصة جواهر خاصة به (جدول gem_drop_rules) ويُسجَّل بشكل منفصل في user_stats.
"""

import random
from datetime import datetime

from database import db_cursor, fetch_all, fetch_one
from config import Config

# تحويل مفتاح المبنى إلى مصدر جدول gem_drop_rules
BUILDING_KEY_TO_GEM_SOURCE = {
    "robot": "robot",
    "skull": "skull",
}
DEFAULT_AUTO_GEM_SOURCE = "other_auto"


def _roll_gems(source: str, gem_rules: dict) -> int:
    """يقرر عشوائيًا هل نزلت جواهر لهذا الحدث، ويُرجع الكمية (قد تكون 0)."""
    rule = gem_rules.get(source)
    if not rule:
        return 0
    if random.uniform(0, 100) <= float(rule["drop_chance_percent"]):
        return random.randint(int(rule["min_amount"]), int(rule["max_amount"]))
    return 0


def _get_gem_rules() -> dict:
    rows = fetch_all("SELECT source, drop_chance_percent, min_amount, max_amount FROM gem_drop_rules")
    return {row["source"]: row for row in rows}


def _get_settings() -> dict:
    rows = fetch_all("SELECT setting_key, setting_value FROM game_settings")
    return {row["setting_key"]: row["setting_value"] for row in rows}


def get_user_buildings(user_id: int) -> list:
    """يُرجع كل مباني اللاعب مع بيانات الكتالوج (السعر الحالي، الإنتاج الحالي)."""
    rows = fetch_all(
        """SELECT b.id AS building_id, b.key_name, b.name_ar, b.description, b.production_type,
                  b.base_price, b.price_growth, b.base_production, b.image, b.sort_order,
                  ub.level
           FROM buildings_catalog b
           LEFT JOIN user_buildings ub ON ub.building_id = b.id AND ub.user_id = %s
           ORDER BY b.sort_order ASC""",
        (user_id,),
    )
    result = []
    for row in rows:
        level = row["level"] or 0
        next_price = float(row["base_price"]) * (float(row["price_growth"]) ** level)
        current_production = float(row["base_production"]) * level
        result.append({
            **row,
            "level": level,
            "next_price": round(next_price, 2),
            "current_production": round(current_production, 4),
        })
    return result


def calculate_click_value(user_id: int) -> dict:
    """
    يحسب قيمة W الناتجة عن ضغطة يدوية واحدة، بناءً على مستوى 'الرأس' + فرصة Critical.
    يُرجع dict فيه القيمة والتفاصيل (هل كانت ضربة حرجة).
    """
    head = fetch_one(
        """SELECT b.base_production, ub.level FROM buildings_catalog b
           LEFT JOIN user_buildings ub ON ub.building_id = b.id AND ub.user_id = %s
           WHERE b.key_name = 'head'""",
        (user_id,),
    )
    level = (head["level"] if head and head["level"] else 0)
    base_value = 1.0 + (float(head["base_production"]) * level if head else 0)

    settings = _get_settings()
    crit_chance = float(settings.get("critical_chance_percent", 5))
    crit_multiplier = float(settings.get("critical_multiplier", 3))

    is_critical = random.uniform(0, 100) <= crit_chance
    value = base_value * crit_multiplier if is_critical else base_value

    return {"value": round(value, 4), "is_critical": is_critical, "base_value": round(base_value, 4)}


def apply_manual_click(user_id: int) -> dict:
    """يُطبّق ضغطة يدوية واحدة: يضيف W، يفحص الجواهر، يحدّث الإحصائيات."""
    click_result = calculate_click_value(user_id)
    gem_rules = _get_gem_rules()
    gems_won = _roll_gems("click", gem_rules)

    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE users SET w_balance = w_balance + %s, gems = gems + %s WHERE id = %s",
            (click_result["value"], gems_won, user_id),
        )
        cur.execute(
            """UPDATE user_stats SET
                 total_clicks = total_clicks + 1,
                 total_w_earned = total_w_earned + %s,
                 total_w_from_click = total_w_from_click + %s,
                 total_gems_earned = total_gems_earned + %s
               WHERE user_id = %s""",
            (click_result["value"], click_result["value"], gems_won, user_id),
        )

    return {
        "gained_w": click_result["value"],
        "is_critical": click_result["is_critical"],
        "gems_won": gems_won,
    }


def apply_auto_production(user_id: int) -> dict:
    """
    يُحتسب منذ آخر مرة تم فيها التحديث (last_collect_at) وحتى الآن، إنتاج كل المباني
    التلقائية (auto_second) مثل الروبوت والجمجمة، كل واحد كمصدر منفصل تمامًا،
    مع فرصة جواهر مستقلة لكل مصدر في كل ثانية محتسبة. النتيجة تُجمَّع ثم تُكتب دفعة واحدة.
    """
    user = fetch_one("SELECT last_collect_at FROM users WHERE id = %s", (user_id,))
    if not user or not user["last_collect_at"]:
        execute_now = datetime.utcnow()
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE users SET last_collect_at = %s WHERE id = %s", (execute_now, user_id))
        return {"gained_w": 0, "gems_won": 0, "seconds_elapsed": 0, "by_source": {}}

    now = datetime.utcnow()
    elapsed_seconds = int((now - user["last_collect_at"]).total_seconds())
    elapsed_seconds = max(0, min(elapsed_seconds, Config.MAX_OFFLINE_SECONDS))

    if elapsed_seconds <= 0:
        return {"gained_w": 0, "gems_won": 0, "seconds_elapsed": 0, "by_source": {}}

    auto_buildings = fetch_all(
        """SELECT b.key_name, b.base_production, ub.level FROM buildings_catalog b
           JOIN user_buildings ub ON ub.building_id = b.id AND ub.user_id = %s
           WHERE b.production_type = 'auto_second' AND ub.level > 0""",
        (user_id,),
    )

    if not auto_buildings:
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE users SET last_collect_at = %s WHERE id = %s", (now, user_id))
        return {"gained_w": 0, "gems_won": 0, "seconds_elapsed": elapsed_seconds, "by_source": {}}

    gem_rules = _get_gem_rules()

    total_w = 0.0
    total_gems = 0
    by_source = {}  # key_name -> {"w": x, "gems": y}
    stat_column_map = {"robot": "total_w_from_robot", "skull": "total_w_from_skull"}

    for b in auto_buildings:
        per_second = float(b["base_production"]) * int(b["level"])
        source = BUILDING_KEY_TO_GEM_SOURCE.get(b["key_name"], DEFAULT_AUTO_GEM_SOURCE)
        bucket = by_source.setdefault(b["key_name"], {"w": 0.0, "gems": 0})

        # نحسب الإنتاج دفعة واحدة (سريع)، ونطبّق فرصة الجواهر لكل ثانية محتسبة (منطق دقيق وعادل)
        bucket["w"] += per_second * elapsed_seconds
        for _ in range(elapsed_seconds):
            gems = _roll_gems(source, gem_rules)
            if gems:
                bucket["gems"] += gems

        total_w += bucket["w"]
        total_gems += bucket["gems"]

    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE users SET w_balance = w_balance + %s, gems = gems + %s, last_collect_at = %s WHERE id = %s",
            (total_w, total_gems, now, user_id),
        )
        robot_w = by_source.get("robot", {}).get("w", 0.0)
        skull_w = by_source.get("skull", {}).get("w", 0.0)
        cur.execute(
            """UPDATE user_stats SET
                 total_w_earned = total_w_earned + %s,
                 total_w_from_robot = total_w_from_robot + %s,
                 total_w_from_skull = total_w_from_skull + %s,
                 total_gems_earned = total_gems_earned + %s
               WHERE user_id = %s""",
            (total_w, robot_w, skull_w, total_gems, user_id),
        )

    return {"gained_w": round(total_w, 4), "gems_won": total_gems, "seconds_elapsed": elapsed_seconds, "by_source": by_source}


def get_active_auto_click_boost(user_id: int):
    """يتحقق إن كان لدى اللاعب بوست Auto Click فعّال حاليًا (من المتجر)."""
    return fetch_one(
        """SELECT uab.expires_at, si.effect_value FROM user_active_boosts uab
           JOIN shop_items si ON si.id = uab.shop_item_id
           WHERE uab.user_id = %s AND si.effect_type = 'auto_click' AND uab.expires_at > NOW()
           ORDER BY uab.expires_at DESC LIMIT 1""",
        (user_id,),
    )


def apply_auto_click_boost_production(user_id: int, seconds_elapsed: int) -> dict:
    """
    ينتج W من بوست Auto Click المؤقت (إن كان مفعّلاً): يحاكي ضغطات تلقائية بمعادلة
    الضغط اليدوي نفسها، لكنه مصدر مستقل تمامًا عن الضغط الحقيقي وعن الروبوت/الجمجمة.
    effect_value هنا = عدد المحاكاة للضغطات في الثانية.
    """
    boost = get_active_auto_click_boost(user_id)
    if not boost or seconds_elapsed <= 0:
        return {"gained_w": 0, "gems_won": 0}

    clicks_per_second = float(boost["effect_value"])
    simulated_clicks = int(clicks_per_second * seconds_elapsed)
    if simulated_clicks <= 0:
        return {"gained_w": 0, "gems_won": 0}

    gem_rules = _get_gem_rules()
    click_info = calculate_click_value(user_id)  # نفس معادلة الضغطة اليدوية (بدون كريتيكال عشوائي لكل واحدة لتوفير الأداء)
    total_w = click_info["base_value"] * simulated_clicks
    total_gems = 0
    for _ in range(min(simulated_clicks, 5000)):  # حد أقصى للتكرار حفاظًا على الأداء
        total_gems += _roll_gems("auto_click", gem_rules)

    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE users SET w_balance = w_balance + %s, gems = gems + %s WHERE id = %s",
            (total_w, total_gems, user_id),
        )
        cur.execute(
            """UPDATE user_stats SET
                 total_w_earned = total_w_earned + %s,
                 total_w_from_auto_click = total_w_from_auto_click + %s,
                 total_gems_earned = total_gems_earned + %s
               WHERE user_id = %s""",
            (total_w, total_w, total_gems, user_id),
        )

    return {"gained_w": round(total_w, 4), "gems_won": total_gems}
