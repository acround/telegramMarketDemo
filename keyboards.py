# keyboards.py
from telebot import types
from settings import PAGE_SIZE
from utils import fmt_price, get_cart, cart_totals
from db_access import DB_categories, DB_products, DB_get_product
from i18n import tr, tr_by_lang, LANGS

# Reply-клавиатура главного меню (по user_id)
def build_main_menu(user_id: int, has_admin: bool) -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton(tr(user_id, "btn.catalog")),
        types.KeyboardButton(tr(user_id, "btn.news"))
    )
    kb.add(
        types.KeyboardButton(tr(user_id, "btn.cart")),
        types.KeyboardButton(tr(user_id, "btn.profile"))
    )
    kb.add(types.KeyboardButton(tr(user_id, "btn.lang")))
    if has_admin:
        kb.add(types.KeyboardButton(tr(user_id, "btn.admin")))
    return kb

# Инлайн: выбор языка
def build_language_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(
        types.InlineKeyboardButton("Русский", callback_data="lang:ru"),
        types.InlineKeyboardButton("English", callback_data="lang:en"),
        types.InlineKeyboardButton("Srpski",  callback_data="lang:sr"),
    )
    return kb

# Инлайн: список категорий
def build_categories_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    cats = DB_categories()
    if not cats:
        kb.add(types.InlineKeyboardButton("∅", callback_data="noop"))
    for c in cats:
        kb.add(types.InlineKeyboardButton(c["name"], callback_data=f"cat:{c['id']}:0"))
    kb.add(types.InlineKeyboardButton("🛒", callback_data="cart:open"))
    return kb

# Инлайн: товары в категории
def build_category_keyboard(cat_id: int, page: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    items = DB_products(cat_id)
    all_ids = [p["id"] for p in items]
    start, end = page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE
    page_ids = all_ids[start:end]
    idx = {p["id"]: p for p in items}

    for pid in page_ids:
        p = idx[pid]
        kb.add(types.InlineKeyboardButton(f"{p['name']} — {fmt_price(p['price'])}", callback_data=f"prod:{pid}"))

    total_pages = (len(all_ids) + PAGE_SIZE - 1) // PAGE_SIZE if all_ids else 1
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("«", callback_data=f"cat:{cat_id}:{page-1}"))
    if page < total_pages - 1:
        nav.append(types.InlineKeyboardButton("»", callback_data=f"cat:{cat_id}:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.add(types.InlineKeyboardButton("🛒", callback_data="cart:open"))
    kb.add(types.InlineKeyboardButton("←", callback_data="cats"))
    return kb

# Инлайн: карточка товара
def build_product_keyboard(pid: int, user_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    prod = DB_get_product(pid)
    min_qty = int(prod.get("min_qty", 1)) if prod else 1
    _, total_sum = cart_totals(get_cart(user_id))
    kb.add(
        types.InlineKeyboardButton(f"➕ {min_qty} шт.", callback_data=f"add:{pid}"),
        types.InlineKeyboardButton(f"🛒 {fmt_price(total_sum)}", callback_data="cart:open"),
    )
    if prod and prod.get("category_id"):
        kb.add(types.InlineKeyboardButton("←", callback_data=f"cat:{prod['category_id']}:0"))
    kb.add(types.InlineKeyboardButton("⇦", callback_data="cats"))
    return kb

# Инлайн: корзина
def build_cart_keyboard(cart: dict) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    for pid, qty in cart.items():
        prod = DB_get_product(pid)
        if not prod:
            continue
        kb.row(
            types.InlineKeyboardButton("−", callback_data=f"dec:{pid}"),
            types.InlineKeyboardButton(f"{prod['name']} × {qty}", callback_data="noop"),
            types.InlineKeyboardButton("+", callback_data=f"inc:{pid}"),
        )
        kb.add(types.InlineKeyboardButton(f"🗑 {prod['name']}", callback_data=f"del:{pid}"))
    if cart:
        kb.add(types.InlineKeyboardButton("🧹", callback_data="cart:clear"))
        kb.add(types.InlineKeyboardButton("✅", callback_data="checkout:start"))
    kb.add(types.InlineKeyboardButton("⇦", callback_data="cats"))
    return kb

# Инлайн: профиль
def build_profile_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(tr(user_id, "btn.profile.edit.phone"), callback_data="profile:edit_phone"))
    kb.add(types.InlineKeyboardButton(tr(user_id, "btn.profile.edit.addr"),  callback_data="profile:edit_address"))
    kb.add(types.InlineKeyboardButton(tr(user_id, "btn.profile.orders"),     callback_data="profile:orders"))
    # Кнопка выхода в главное меню
    kb.add(types.InlineKeyboardButton(tr(user_id, "exit.to.menu"),           callback_data="profile:exit"))
    return kb

