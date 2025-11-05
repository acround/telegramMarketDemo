# handlers_user.py
# Пользовательские обработчики + делегирование админ-панели в Admin_bot
# История заказов в личном кабинете + «Повторить заказ»

import os
import io
import re
import requests
import telebot
from telebot import types
import Admin_bot

# === Инициализация ===
API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    raise SystemExit("BOT_TOKEN не установлен в окружении.")

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# Инициализируем БД (создаст таблицы и применит миграции)
Admin_bot.init_db()

# ====== Главное меню ======
BTN_CATALOG = "🛍 Каталог"
BTN_NEWS = "📰 Новости и акции"
BTN_CART = "🛒 Корзина"
BTN_PROFILE = "👤 Личный кабинет"
BTN_ADMIN = "🛠 Админ-панель"
BTN_EXIT_ADMIN = "⬅️ Выйти из админ-панели"

# Флаг “демо-админ” (кто прислал "demo admin")
demo_admin_access = set()

def has_demo_admin(user_id:int)->bool:
    return user_id in demo_admin_access

def build_main_menu(user_id:int)->types.ReplyKeyboardMarkup:
    """
    В меню всегда 4 кнопки пользователя.
    Пятая кнопка — либо «Админ-панель», либо «Выйти из админ-панели» если режим активен.
    """
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(types.KeyboardButton(BTN_CATALOG), types.KeyboardButton(BTN_NEWS))
    kb.add(types.KeyboardButton(BTN_CART), types.KeyboardButton(BTN_PROFILE))
    kb.add(types.KeyboardButton(BTN_EXIT_ADMIN if has_demo_admin(user_id) else BTN_ADMIN))
    return kb

# ====== Помощники ======
def fmt_price(v) -> str:
    try:
        return f"{float(v):.2f} RSD"
    except Exception:
        return f"{v} RSD"

def safe_send_photo(chat_id: int, image_url: str, caption: str, reply_markup=None):
    """
    Универсальная отправка фото:
    1) Пытаемся отправить URL напрямую (Telegram сам скачает).
    2) Если это HTML-страница (ibb.co и т.п.), вытягиваем <meta property="og:image" ...>.
    3) Затем пробуем отправить найденный прямой URL.
    4) Если не получилось — скачиваем байты и отправляем как файл.
    5) В крайнем случае — отправляем текст.
    """
    try:
        return bot.send_photo(chat_id, image_url, caption=caption, reply_markup=reply_markup)
    except Exception as e:
        print(f"[safe_send_photo] direct url send failed: {e}")

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"
    }
    try:
        r = requests.get(image_url, timeout=20, allow_redirects=True, headers=headers)
        r.raise_for_status()
        ctype = r.headers.get("Content-Type", "")
        if "text/html" in ctype.lower():
            html = r.text
            m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if m:
                direct = m.group(1)
                try:
                    return bot.send_photo(chat_id, direct, caption=caption, reply_markup=reply_markup)
                except Exception as e2:
                    print(f"[safe_send_photo] og:image send failed: {e2}")
                    rr = requests.get(direct, timeout=20, allow_redirects=True, headers=headers)
                    rr.raise_for_status()
                    content = rr.content
                    if not content or len(content) < 10:
                        raise ValueError("Empty og:image content")
                    fileobj = io.BytesIO(content)
                    fileobj.name = "photo.jpg"
                    return bot.send_photo(chat_id, fileobj, caption=caption, reply_markup=reply_markup)

        content = r.content
        if not content or len(content) < 10:
            raise ValueError("Empty content")
        fileobj = io.BytesIO(content)
        fileobj.name = "photo.jpg"
        return bot.send_photo(chat_id, fileobj, caption=caption, reply_markup=reply_markup)

    except Exception as e:
        print(f"[safe_send_photo] fallback to text: {e}")
        return bot.send_message(chat_id, caption, reply_markup=reply_markup)

# ====== Доступ к данным (через Admin_bot) ======
def DB_categories():
    return Admin_bot.client_list_categories()

def DB_products(cat_id: int):
    return Admin_bot.client_list_products(cat_id)

def DB_get_product(pid: int):
    return Admin_bot.client_get_product(pid)

def DB_posts():
    return Admin_bot.client_list_posts()

def DB_get_post(post_id: int):
    return Admin_bot.client_get_post(post_id)

def DB_min_delivery_sum() -> float:
    return Admin_bot.client_get_min_delivery_sum()

def DB_pickup_address() -> str:
    try:
        return Admin_bot.client_get_pickup_address()
    except Exception as e:
        print(f"[pickup address read error] {e}")
        return ""

# ====== Корзины (в памяти процесса) ======
carts = {}  # {user_id: {product_id: qty}}

def get_cart(user_id:int)->dict:
    return carts.setdefault(user_id, {})

def cart_totals(cart:dict):
    total_qty,total_sum = 0,0.0
    for pid,qty in cart.items():
        p = DB_get_product(pid)
        if not p:
            continue
        total_qty += qty
        total_sum += float(p["price"]) * qty
    return total_qty,total_sum

def build_cart_keyboard(cart: dict) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    for pid, qty in cart.items():
        p = DB_get_product(pid)
        if not p:
            continue
        kb.row(
            types.InlineKeyboardButton("−", callback_data=f"dec:{pid}"),
            types.InlineKeyboardButton(f"{p['name']} × {qty}", callback_data="noop"),
            types.InlineKeyboardButton("+", callback_data=f"inc:{pid}")
        )
        kb.add(types.InlineKeyboardButton(f"Удалить «{p['name']}»", callback_data=f"del:{pid}"))
    if cart:
        kb.add(types.InlineKeyboardButton("🧹 Очистить корзину", callback_data="cart:clear"))
        kb.add(types.InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout:start"))
    return kb

def render_cart_text(user_id: int) -> str:
    cart = get_cart(user_id)
    if not cart:
        return "Ваша корзина пуста."
    lines = ["<b>🛒 Ваша корзина</b>", ""]
    for pid, qty in list(cart.items()):
        p = DB_get_product(pid)
        if not p:
            cart.pop(pid, None)
            continue
        lines.append(f"• {p['name']} — {qty} × {fmt_price(p['price'])} = <b>{fmt_price(float(p['price'])*qty)}</b>")
    total_qty, total_sum = cart_totals(cart)
    lines += ["", f"Итого: {total_qty} шт. на сумму <b>{fmt_price(total_sum)}</b>"]
    try:
        min_sum = float(DB_min_delivery_sum() or 0)
    except Exception:
        min_sum = 0.0
    addr = DB_pickup_address()
    if min_sum > 0:
        lines += [f"\nМинимальная сумма для доставки на дом: <b>{fmt_price(min_sum)}</b>"]
    if addr:
        lines += [f"Адрес(а) раздачи: <b>{addr}</b>"]
    return "\n".join(lines)

def build_product_keyboard(pid: int, user_id: int) -> types.InlineKeyboardMarkup:
    p = DB_get_product(pid)
    min_qty = int((p or {}).get("min_qty", 1))
    _, total_sum = cart_totals(get_cart(user_id))
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(f"➕ В корзину — {min_qty} шт.", callback_data=f"add:{pid}"),
        types.InlineKeyboardButton(f"🛒 Корзина — {fmt_price(total_sum)}", callback_data="cart:open"),
    )
    return kb

# ========== Команды ==========
@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    Admin_bot.upsert_username(message.from_user.id, message.from_user.username)
    bot.send_message(
        message.chat.id,
        "Привет! Это демо-бот. Напишите <code>demo admin</code>, чтобы открыть админ-панель.",
        reply_markup=build_main_menu(message.from_user.id)
    )

@bot.message_handler(commands=["admin"])
def cmd_admin(message: types.Message):
    """Открыть админ-панель командой, даже если в меню сейчас только «Выйти из админ-панели»."""
    uid, cid = message.from_user.id, message.chat.id
    if not has_demo_admin(uid):
        bot.send_message(cid, "⛔ Доступ появится после сообщения: demo admin")
        return
    kb = Admin_bot.admin_menu_markup()
    bot.send_message(cid, "<b>🛠 Админ-панель</b>", reply_markup=kb)

# Демо-включение админки
@bot.message_handler(func=lambda m: isinstance(m.text,str) and m.text.strip().lower()=="demo admin")
def enable_demo_admin(message: types.Message):
    demo_admin_access.add(message.from_user.id)
    bot.send_message(message.chat.id, "✅ Режим демо-администратора активирован", reply_markup=build_main_menu(message.from_user.id))
    # сразу откроем админ-меню для удобства
    kb = Admin_bot.admin_menu_markup()
    bot.send_message(message.chat.id, "<b>🛠 Админ-панель</b>", reply_markup=kb)

# Главные кнопки
@bot.message_handler(func=lambda m: m.text in {BTN_CATALOG, BTN_NEWS, BTN_CART, BTN_PROFILE, BTN_ADMIN, BTN_EXIT_ADMIN})
def main_buttons(message: types.Message):
    uid, cid = message.from_user.id, message.chat.id
    txt = message.text

    if txt == BTN_ADMIN:
        if not has_demo_admin(uid):
            bot.send_message(cid, "⛔ Доступ появится после сообщения: demo admin")
            return
        kb = Admin_bot.admin_menu_markup()
        bot.send_message(cid, "<b>🛠 Админ-панель</b>", reply_markup=kb)
        bot.send_message(cid, "Режим админ-панели активен.", reply_markup=build_main_menu(uid))
        return

    if txt == BTN_EXIT_ADMIN:
        if uid in demo_admin_access:
            demo_admin_access.remove(uid)
        bot.send_message(cid, "Вы вышли из админ-панели.", reply_markup=build_main_menu(uid))
        return

    if txt == BTN_PROFILE:
        prof = Admin_bot.get_profile(uid)
        # Карточка профиля + кнопки редактирования
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("✏️ Телефон", callback_data="profile:phone"))
        kb.add(types.InlineKeyboardButton("✏️ Адрес доставки", callback_data="profile:addr"))
        bot.send_message(
            cid,
            f"<b>👤 Личный кабинет</b>\n"
            f"Username: @{(prof.get('username') or '')}\n"
            f"Телефон: {prof.get('phone') or '—'}\n"
            f"Адрес: {prof.get('address') or '—'}",
            reply_markup=kb
        )
        # История заказов
        orders = Admin_bot.list_orders_by_user(uid, limit=10)
        if not orders:
            bot.send_message(cid, "📦 История заказов: пока пусто.")
        else:
            lines = ["<b>📦 История заказов (последние 10):</b>", ""]
            kb2 = types.InlineKeyboardMarkup(row_width=2)
            for o in orders:
                when = o["created_at"]
                lines.append(f"• {when} | {o['status']} | #{o['id']} | {fmt_price(o['total'])}")
                kb2.add(
                    types.InlineKeyboardButton(f"ℹ️ #{o['id']}", callback_data=f"order:view:{o['id']}"),
                    types.InlineKeyboardButton(f"🧺 Повторить #{o['id']}", callback_data=f"order:readd:{o['id']}")
                )
            bot.send_message(cid, "\n".join(lines), reply_markup=kb2)
        return

    if txt == BTN_CATALOG:
        cats = DB_categories()
        if not cats:
            bot.send_message(cid, "Каталог пуст. Добавьте категории в админ-панели.")
            return
        kb = types.InlineKeyboardMarkup(row_width=1)
        for c in cats:
            kb.add(types.InlineKeyboardButton(c["name"], callback_data=f"cat:{c['id']}"))
        bot.send_message(cid, "<b>Категории:</b>", reply_markup=kb)
        return

    if txt == BTN_NEWS:
        posts = DB_posts()
        if not posts:
            bot.send_message(cid, "Пока нет публикаций.")
            return
        # Список с картинкой и кнопкой «Читать»
        for p in posts[:10]:
            when = p.get('publish_at') or p.get('created_at') or ''
            cap = f"<b>[{p['type']}] {p['title']}</b>\nДата: {when}"
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("Читать", callback_data=f"post:{p['id']}"))
            safe_send_photo(cid, p["image"], caption=cap, reply_markup=kb)
        return

    if txt == BTN_CART:
        text = render_cart_text(uid)
        kb = build_cart_keyboard(get_cart(uid))
        bot.send_message(cid, text, reply_markup=kb)
        return

# ====== CALLBACKS ======

@bot.callback_query_handler(func=lambda c: True)
def all_callbacks(call: types.CallbackQuery):
    """
    Порядок:
    1) админ-панель
    2) пользовательские действия (каталог/корзина/новости/профиль/заказы)
    """
    try:
        # 1) Админка
        if Admin_bot.handle_callback(bot, call, DB_get_product):
            return

        # 2) Пользовательские
        data = call.data or ""
        cid = call.message.chat.id
        uid = call.from_user.id

        # --- Каталог ---
        if data.startswith("cat:"):
            _, cat_id = data.split(":")
            cat_id = int(cat_id)
            prods = DB_products(cat_id)
            if not prods:
                bot.answer_callback_query(call.id)
                bot.send_message(cid, "В этой категории пока нет товаров.")
                return
            kb = types.InlineKeyboardMarkup(row_width=1)
            for p in prods:
                kb.add(types.InlineKeyboardButton(f"{p['name']} — {fmt_price(p['price'])}", callback_data=f"prod:{p['id']}"))
            try:
                if getattr(call.message, "content_type", "") == "text" and call.message.text:
                    bot.edit_message_text("<b>Товары:</b>", cid, call.message.message_id, reply_markup=kb)
                else:
                    bot.send_message(cid, "<b>Товары:</b>", reply_markup=kb)
            except Exception:
                bot.send_message(cid, "<b>Товары:</b>", reply_markup=kb)
            bot.answer_callback_query(call.id); return

        if data.startswith("prod:"):
            pid = int(data.split(":")[1])
            p = DB_get_product(pid)
            if not p:
                bot.answer_callback_query(call.id, "Товар не найден"); return
            caption = (
                f"<b>{p['name']}</b>\n\n"
                f"{p['description']}\n\n"
                f"Минимум: <b>{p.get('min_qty',1)} шт.</b>\n"
                f"Цена/шт: <b>{fmt_price(p['price'])}</b>"
            )
            kb = build_product_keyboard(pid, uid)
            safe_send_photo(cid, p["image"], caption=caption, reply_markup=kb)
            bot.answer_callback_query(call.id); return

        # --- Корзина (просмотр/редактирование/оформление) ---
        if data == "cart:open":
            text = render_cart_text(uid)
            kb = build_cart_keyboard(get_cart(uid))
            if getattr(call.message, "content_type", "") == "text" and call.message.text:
                try:
                    bot.edit_message_text(text, cid, call.message.message_id, reply_markup=kb)
                except Exception as e:
                    print(f"[cart:open] edit_message_text failed, send new: {e}")
                    bot.send_message(cid, text, reply_markup=kb)
            else:
                bot.send_message(cid, text, reply_markup=kb)
            bot.answer_callback_query(call.id); return

        if data == "cart:clear":
            carts[uid] = {}
            text = render_cart_text(uid)
            kb = build_cart_keyboard(get_cart(uid))
            bot.send_message(cid, text, reply_markup=kb)
            bot.answer_callback_query(call.id, "Корзина очищена"); return

        if data.startswith("inc:") or data.startswith("dec:"):
            pid = int(data.split(":")[1])
            cart = get_cart(uid)
            if pid in cart:
                cart[pid] += 1 if data.startswith("inc:") else -1
                if cart[pid] <= 0: del cart[pid]
            text = render_cart_text(uid)
            kb = build_cart_keyboard(cart)
            bot.send_message(cid, text, reply_markup=kb)
            bot.answer_callback_query(call.id); return

        if data.startswith("del:"):
            pid = int(data.split(":")[1])
            cart = get_cart(uid)
            if pid in cart: del cart[pid]
            text = render_cart_text(uid)
            kb = build_cart_keyboard(cart)
            bot.send_message(cid, text, reply_markup=kb)
            bot.answer_callback_query(call.id, "Товар удалён"); return

        if data.startswith("add:"):
            pid = int(data.split(":")[1])
            p = DB_get_product(pid)
            if not p:
                bot.answer_callback_query(call.id, "Товар не найден"); return
            cart = get_cart(uid)
            add_qty = int(p.get("min_qty", 1))
            cart[pid] = cart.get(pid, 0) + add_qty
            new_kb = build_product_keyboard(pid, uid)
            try:
                bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=new_kb)
            except Exception as e:
                if "message is not modified" not in str(e).lower():
                    print(f"[add] edit_message_reply_markup error: {e}")
            bot.answer_callback_query(call.id, f"Добавлено: {p['name']} × {add_qty}")
            return

        if data == "checkout:start":
            cart = get_cart(uid)
            tqty, tsum = cart_totals(cart)
            if tqty == 0:
                bot.answer_callback_query(call.id, "Корзина пуста"); return

            # Порог для доставки на дом
            try:
                min_sum = float(DB_min_delivery_sum() or 0)
            except Exception:
                min_sum = 0.0
            need_home = tsum >= min_sum  # True => нужно спросить адрес, False => выберем пункт раздачи

            # ВСЕГДА сначала телефон (и заменить в профиле)
            Admin_bot.admin_fsm[uid] = {"action": "checkout_phone", "need_home": need_home}
            bot.answer_callback_query(call.id)
            bot.send_message(cid, "Введите номер телефона (будет сохранён в вашем профиле):")
            return

        if data.startswith("choose_pickup:"):
            pid = int(data.split(":")[1])
            points = {p["id"]: p for p in Admin_bot.list_pickup_points()}
            addr_txt = points.get(pid, {}).get("address", "")

            cart = get_cart(uid)
            tqty, tsum = cart_totals(cart)
            if tqty == 0:
                bot.answer_callback_query(call.id, "Корзина пуста"); return

            order_id = Admin_bot.record_order(uid, cart, DB_get_product, call.message.chat.id)
            carts[uid] = {}
            Admin_bot.admin_fsm.pop(uid, None)
            bot.answer_callback_query(call.id)
            bot.send_message(
                cid,
                f"✅ Заказ <b>#{order_id}</b> принят.\n"
                f"Позиции: {tqty} шт., сумма: <b>{fmt_price(tsum)}</b>.\n"
                f"Пункт раздачи: <b>{addr_txt or '—'}</b>"
            )
            return

        # --- Новости и акции ---
        if data.startswith("post:"):
            pid = int(data.split(":")[1])
            post = DB_get_post(pid)
            if not post:
                bot.answer_callback_query(call.id, "Публикация не найдена"); return
            cap = f"<b>{post['title']}</b>\n\n{post['text']}"
            safe_send_photo(cid, post["image"], caption=cap)
            bot.answer_callback_query(call.id); return

        # --- История заказов: подробно + повторить ---
        if data.startswith("order:view:"):
            oid = int(data.split(":")[2])
            o = Admin_bot.get_order(oid)
            if not o or o.get("user_id") != uid:
                bot.answer_callback_query(call.id, "Заказ не найден")
                return
            items = Admin_bot.get_order_items(oid)
            items_str = "\n".join([f"• {it['name']} — {it['qty']} × {fmt_price(it['price'])}" for it in items]) or "—"
            text = (
                f"<b>Заказ #{o['id']}</b>\n"
                f"Статус: <b>{o['status']}</b>\n"
                f"Сумма: {fmt_price(o['total'])}\n"
                f"Создан: {o['created_at']}\n\n"
                f"<b>Товары:</b>\n{items_str}"
            )
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton(f"🧺 Повторить #{o['id']}", callback_data=f"order:readd:{o['id']}"))
            kb.add(types.InlineKeyboardButton("🛒 Открыть корзину", callback_data="cart:open"))
            bot.answer_callback_query(call.id)
            bot.send_message(cid, text, reply_markup=kb)
            return

        if data.startswith("order:readd:"):
            oid = int(data.split(":")[2])
            o = Admin_bot.get_order(oid)
            if not o or o.get("user_id") != uid:
                bot.answer_callback_query(call.id, "Заказ не найден")
                return
            items = Admin_bot.get_order_items(oid)
            if not items:
                bot.answer_callback_query(call.id, "В заказе нет товаров")
                return
            cart = get_cart(uid)
            for it in items:
                pid = it["product_id"]
                qty = int(it["qty"] or 0)
                if qty <= 0:
                    continue
                cart[pid] = cart.get(pid, 0) + qty
            text = render_cart_text(uid)
            kb = build_cart_keyboard(cart)
            bot.answer_callback_query(call.id, f"Товары из заказа #{oid} добавлены в корзину")
            bot.send_message(cid, text, reply_markup=kb)
            return

        # --- Профиль (редактирование) ---
        if data == "profile:phone":
            bot.answer_callback_query(call.id)
            bot.send_message(cid, "Введите номер телефона (только вы его можете изменить):")
            Admin_bot.admin_fsm[uid] = {"action":"user_edit_phone"}
            return

        if data == "profile:addr":
            bot.answer_callback_query(call.id)
            bot.send_message(cid, "Введите адрес доставки:")
            Admin_bot.admin_fsm[uid] = {"action":"user_edit_addr"}
            return

        bot.answer_callback_query(call.id, "Ок")

    except Exception as e:
        print(f"[Callback error] {e}")
        try: bot.answer_callback_query(call.id, "Ошибка")
        except Exception: pass

# ====== FALLBACK: текст → сначала админ-панель (FSM), затем шаги чекаута, затем профиль ======

@bot.message_handler(func=lambda m: True)
def fallback(message: types.Message):
    uid = message.from_user.id

    # 1) Дадим шанс админ-панели обработать пошаговый ввод (категории, посты, настройки и т.д.)
    if Admin_bot.handle_text(bot, message, DB_get_product):
        return

    st = Admin_bot.admin_fsm.get(uid)

    # 2) Чекаут — шаг 1: телефон (всегда)
    if st and st.get("action") == "checkout_phone":
        phone = (message.text or "").strip()
        if not phone:
            bot.send_message(message.chat.id, "Номер пуст. Введите номер телефона:")
            return
        Admin_bot.set_profile_phone(uid, phone)

        need_home = bool(st.get("need_home"))
        if need_home:
            Admin_bot.admin_fsm[uid] = {"action": "checkout_addr_home"}  # следующий шаг
            bot.send_message(message.chat.id, "Введите адрес доставки (будет сохранён в вашем профиле):")
            return
        else:
            points = Admin_bot.list_pickup_points()
            if not points:
                bot.send_message(message.chat.id, "Пункты раздачи не настроены. Обратитесь к администратору.")
                Admin_bot.admin_fsm.pop(uid, None)
                return
            kb = types.InlineKeyboardMarkup(row_width=1)
            for p in points[:20]:
                kb.add(types.InlineKeyboardButton(p["address"], callback_data=f"choose_pickup:{p['id']}"))
            Admin_bot.admin_fsm[uid] = {"action": "checkout_pickup"}
            bot.send_message(message.chat.id, "<b>Выберите адрес раздачи:</b>", reply_markup=kb)
            return

    # 3) Чекаут — шаг 2 (только при доставке на дом): адрес
    if st and st.get("action") == "checkout_addr_home":
        addr_text = (message.text or "").strip()
        if not addr_text:
            bot.send_message(message.chat.id, "Адрес пустой. Введите адрес доставки одной строкой:")
            return

        Admin_bot.set_profile_address(uid, addr_text)

        cart = get_cart(uid)
        tqty, tsum = cart_totals(cart)
        if tqty == 0:
            Admin_bot.admin_fsm.pop(uid, None)
            bot.send_message(message.chat.id, "Корзина пуста.")
            return

        order_id = Admin_bot.record_order(uid, cart, DB_get_product, message.chat.id)
        carts[uid] = {}
        Admin_bot.admin_fsm.pop(uid, None)

        bot.send_message(
            message.chat.id,
            f"✅ Заказ <b>#{order_id}</b> принят.\n"
            f"Позиции: {tqty} шт., сумма: <b>{fmt_price(tsum)}</b>.\n"
            f"Адрес доставки: <b>{addr_text}</b>"
        )
        return

    # 4) Профильные поля (ручное редактирование)
    if st and st.get("action") == "user_edit_phone":
        Admin_bot.set_profile_phone(uid, message.text.strip())
        Admin_bot.admin_fsm.pop(uid, None)
        bot.send_message(message.chat.id, "✅ Телефон обновлён", reply_markup=build_main_menu(uid))
        return
    if st and st.get("action") == "user_edit_addr":
        Admin_bot.set_profile_address(uid, message.text.strip())
        Admin_bot.admin_fsm.pop(uid, None)
        bot.send_message(message.chat.id, "✅ Адрес обновлён", reply_markup=build_main_menu(uid))
        return

    # 5) По умолчанию — главное меню
    bot.send_message(message.chat.id, "Выберите раздел:", reply_markup=build_main_menu(uid))


# ====== Экспорт бота для main.py ======
def get_bot():
    return bot
