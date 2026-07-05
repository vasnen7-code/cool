"""
database.py
-----------
طبقة وصول واحدة لقاعدة البيانات، تعادل استخدام PDO في PHP.
- تُستخدم PyMySQL فقط.
- كل استعلام يمر عبر Prepared Statements (باراميترات %s) لمنع SQL Injection نهائياً.
- لا تُبنى أي استعلامات عبر تجميع نصوص (string concatenation) في أي مكان بالمشروع.
"""

import pymysql
import pymysql.cursors
from contextlib import contextmanager
from config import Config


def get_connection():
    """يفتح اتصال جديد بقاعدة البيانات مع إعدادات آمنة."""
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset=Config.DB_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


@contextmanager
def db_cursor(commit: bool = False):
    """
    Context manager يوفر cursor جاهز للاستخدام ويغلق الاتصال تلقائياً.
    استخدم commit=True للاستعلامات التي تُعدّل البيانات (INSERT/UPDATE/DELETE).

    مثال:
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE users SET w_balance = %s WHERE id = %s", (balance, user_id))
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_one(query: str, params: tuple = ()):
    """يُرجع صفًا واحدًا (dict) أو None. الاستعلام دائمًا Prepared Statement."""
    with db_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchone()


def fetch_all(query: str, params: tuple = ()):
    """يُرجع كل الصفوف كقائمة dict."""
    with db_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def execute(query: str, params: tuple = ()) -> int:
    """لتنفيذ INSERT/UPDATE/DELETE. يُرجع lastrowid (مفيد بعد INSERT)."""
    with db_cursor(commit=True) as cur:
        cur.execute(query, params)
        return cur.lastrowid


def execute_many(query: str, params_list: list) -> None:
    """لتنفيذ عدة عمليات INSERT/UPDATE دفعة واحدة بنفس الاستعلام."""
    with db_cursor(commit=True) as cur:
        cur.executemany(query, params_list)
