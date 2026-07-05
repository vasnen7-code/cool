"""
database/seed_admin.py
-----------------------
شغّل هذا الملف مرة واحدة بعد استيراد schema.sql لضبط كلمة مرور حساب الأدمن
الافتراضي (Hasnen) بشكل صحيح، لأن password_hash يولّد Salt عشوائي مختلف
في كل مرة ولا يمكن كتابته مباشرة داخل ملف SQL.

الاستخدام:
    python database/seed_admin.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import execute  # noqa: E402
from functions import hash_password  # noqa: E402

ADMIN_USERNAME = "Hasnen"
ADMIN_PASSWORD = "Hasnen1@@1"  # غيّرها فورًا بعد أول تسجيل دخول في بيئة الإنتاج


def main():
    password_hash = hash_password(ADMIN_PASSWORD)
    execute(
        "UPDATE users SET password_hash = %s WHERE username = %s",
        (password_hash, ADMIN_USERNAME),
    )
    print(f"تم ضبط كلمة مرور الأدمن ({ADMIN_USERNAME}) بنجاح.")


if __name__ == "__main__":
    main()
