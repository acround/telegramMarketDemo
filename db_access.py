# db_access.py
# Обёртки-ридеры для клиентской части поверх Admin_bot.py (SQLite)

import Admin_bot

def DB_categories():
    return Admin_bot.client_list_categories() if hasattr(Admin_bot, "client_list_categories") else Admin_bot.list_categories()

def DB_products(cat_id: int):
    return Admin_bot.client_list_products(cat_id) if hasattr(Admin_bot, "client_list_products") else Admin_bot.list_products(cat_id)

def DB_get_product(pid: int):
    return Admin_bot.client_get_product(pid) if hasattr(Admin_bot, "client_get_product") else Admin_bot.get_product(pid)

def DB_posts():
    return Admin_bot.client_list_posts() if hasattr(Admin_bot, "client_list_posts") else Admin_bot.list_posts()

def DB_get_post(post_id: int):
    return Admin_bot.client_get_post(post_id) if hasattr(Admin_bot, "client_get_post") else Admin_bot.get_post(post_id)

def DB_min_delivery_sum() -> float:
    return Admin_bot.client_get_min_delivery_sum() if hasattr(Admin_bot, "client_get_min_delivery_sum") else float(Admin_bot.get_setting("min_delivery_sum","0"))

def DB_pickup_address() -> str:
    return Admin_bot.client_get_pickup_address() if hasattr(Admin_bot, "client_get_pickup_address") else Admin_bot.get_setting("pickup_address","")

def DB_category_by_id(cat_id: int):
    for c in DB_categories():
        if c["id"] == cat_id:
            return c
    return None

# ---------- Профиль ----------
def DB_upsert_username(user_id: int, username: str | None):
    Admin_bot.upsert_username(user_id, username or "")

def DB_get_profile(user_id: int):
    return Admin_bot.get_profile(user_id)

def DB_set_phone(user_id: int, phone: str):
    Admin_bot.set_profile_phone(user_id, phone)

def DB_set_address(user_id: int, address: str):
    Admin_bot.set_profile_address(user_id, address)

# ---------- Заказы пользователя ----------
def DB_list_orders_by_user(user_id: int, limit: int = 20):
    return Admin_bot.list_orders_by_user(user_id, limit)

def DB_get_order(order_id: int):
    return Admin_bot.get_order(order_id)

def DB_record_order(user_id: int, cart: dict, products_lookup, chat_id: int):
    return Admin_bot.record_order(user_id, cart, products_lookup, chat_id)

# ---------- Язык ----------
def DB_get_lang(user_id: int) -> str:
    prof = Admin_bot.get_profile(user_id)
    return (prof or {}).get("lang", "ru")

def DB_set_lang(user_id: int, lang: str):
    Admin_bot.set_profile_lang(user_id, lang)
