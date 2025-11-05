# Admin_bot.py
# База данных + админ-панель для бота-магазина.

import os
import sqlite3
from datetime import datetime, timedelta
from telebot import types

DB_PATH = os.getenv("DB_PATH", "store.db")

# FSM состояния: {user_id: {action, ...temp fields...}}
admin_fsm = {}

# ============================ БАЗА ДАННЫХ ============================

def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            min_qty INTEGER NOT NULL DEFAULT 1,
            image TEXT,
            description TEXT,
            category_id INTEGER,
            FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,      -- 'Новость' | 'Акция'
            image TEXT,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            publish_at TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pickup_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            phone TEXT,
            address TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_id INTEGER,
            total REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Принят',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            qty INTEGER NOT NULL DEFAULT 1,
            price REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            send_at TEXT NOT NULL,
            sent INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Значения по умолчанию
    cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES ('min_delivery_sum','0')")

    con.commit()
    cur.close(); con.close()

# ============================ CRUD: категории/товары/публикации ============================

def add_category(name: str) -> int:
    con = db(); cur = con.cursor()
    cur.execute("INSERT INTO categories(name) VALUES (?)", (name.strip(),))
    con.commit(); cid = cur.lastrowid
    cur.close(); con.close()
    return cid

def list_categories():
    con = db()
    rows = con.execute("SELECT id, name FROM categories ORDER BY name COLLATE NOCASE").fetchall()
    con.close()
    return [dict(r) for r in rows]

def delete_category(cat_id: int):
    con = db()
    con.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    con.commit(); con.close()

def add_product(name: str, price: float, min_qty: int, image: str, description: str, category_id: int) -> int:
    con = db(); cur = con.cursor()
    cur.execute("""
        INSERT INTO products(name, price, min_qty, image, description, category_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name.strip(), float(price), int(min_qty), image.strip(), description.strip(), int(category_id)))
    con.commit(); pid = cur.lastrowid
    cur.close(); con.close()
    return pid

def update_product(pid: int, **fields):
    if not fields: return
    allowed = {"name","price","min_qty","image","description","category_id"}
    set_parts, vals = [], []
    for k,v in fields.items():
        if k in allowed:
            set_parts.append(f"{k}=?"); vals.append(v)
    if not set_parts: return
    vals.append(pid)
    con = db(); con.execute(f"UPDATE products SET {', '.join(set_parts)} WHERE id=?", vals)
    con.commit(); con.close()

def delete_product(pid: int):
    con = db(); con.execute("DELETE FROM products WHERE id=?", (pid,))
    con.commit(); con.close()

def list_products(cat_id: int):
    con = db()
    rows = con.execute("""
        SELECT id, name, price, min_qty, image, description, category_id
        FROM products
        WHERE category_id=?
        ORDER BY name COLLATE NOCASE
    """, (cat_id,)).fetchall()
    con.close()
    return [dict(r) for r in rows]

def get_product(pid: int):
    con = db()
    r = con.execute("""
        SELECT id, name, price, min_qty, image, description, category_id
        FROM products WHERE id=?
    """, (pid,)).fetchone()
    con.close()
    return dict(r) if r else None

def add_post(ptype: str, image: str, title: str, text: str, publish_at: str|None):
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con = db(); cur = con.cursor()
    cur.execute("""
        INSERT INTO posts(type, image, title, text, publish_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ptype.strip(), image.strip(), title.strip(), text.strip(), publish_at, now_iso))
    con.commit(); pid = cur.lastrowid
    cur.close(); con.close()
    return pid

def list_posts():
    con = db()
    rows = con.execute("""
        SELECT id, type, image, title, text, publish_at, created_at
        FROM posts
        ORDER BY COALESCE(publish_at, created_at) DESC, id DESC
    """).fetchall()
    con.close()
    return [dict(r) for r in rows]

def get_post(post_id: int):
    con = db()
    r = con.execute("""
        SELECT id, type, image, title, text, publish_at, created_at
        FROM posts WHERE id=?
    """, (post_id,)).fetchone()
    con.close()
    return dict(r) if r else None

def delete_post(post_id: int):
    con = db(); con.execute("DELETE FROM posts WHERE id=?", (post_id,))
    con.commit(); con.close()

# ============================ Настройки / Пункты раздачи ============================

def set_min_delivery_sum(value: float):
    con = db()
    con.execute("""
        INSERT INTO settings(key,value) VALUES('min_delivery_sum', ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (str(float(value)),))
    con.commit(); con.close()

def get_min_delivery_sum() -> float:
    con = db()
    r = con.execute("SELECT value FROM settings WHERE key='min_delivery_sum'").fetchone()
    con.close()
    try:
        return float(r["value"]) if r and r["value"] is not None else 0.0
    except Exception:
        return 0.0

def add_pickup_point(address: str) -> int:
    con = db(); cur = con.cursor()
    cur.execute("INSERT INTO pickup_points(address) VALUES (?)", (address.strip(),))
    con.commit(); pid = cur.lastrowid
    cur.close(); con.close()
    return pid

def delete_pickup_point(pid: int):
    con = db(); con.execute("DELETE FROM pickup_points WHERE id=?", (pid,))
    con.commit(); con.close()

def list_pickup_points():
    con = db()
    rows = con.execute("SELECT id, address FROM pickup_points ORDER BY id DESC").fetchall()
    con.close()
    return [dict(r) for r in rows]

# ============================ Профиль пользователя ============================

def upsert_username(user_id: int, username: str|None):
    con = db()
    con.execute("""
        INSERT INTO users(user_id, username) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET username=excluded.username
    """, (user_id, username))
    con.commit(); con.close()

def get_profile(user_id: int):
    con = db()
    r = con.execute("SELECT user_id, username, phone, address FROM users WHERE user_id=?", (user_id,)).fetchone()
    con.close()
    if r:
        return dict(r)
    con = db()
    con.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
    con.commit(); con.close()
    return {"user_id": user_id, "username": None, "phone": None, "address": None}

def set_profile_phone(user_id: int, phone: str):
    con = db(); con.execute("UPDATE users SET phone=? WHERE user_id=?", (phone.strip(), user_id))
    con.commit(); con.close()

def set_profile_address(user_id: int, address: str):
    con = db(); con.execute("UPDATE users SET address=? WHERE user_id=?", (address.strip(), user_id))
    con.commit(); con.close()

# ============================ Заказы ============================

ORDER_STATUSES = ["Принят", "Сборка", "Доставка"]

def record_order(user_id: int, cart: dict, get_product_func, chat_id: int|None=None) -> int:
    if not cart: return 0
    total = 0.0; items = []
    for pid, qty in cart.items():
        p = get_product_func(pid)
        if not p: continue
        price = float(p["price"])
        total += price * qty
        items.append((pid, qty, price))
    if not items: return 0

    con = db(); cur = con.cursor()
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO orders(user_id, chat_id, total, status, created_at)
        VALUES (?, ?, ?, 'Принят', ?)
    """, (user_id, chat_id, total, now_iso))
    order_id = cur.lastrowid

    cur.executemany("""
        INSERT INTO order_items(order_id, product_id, qty, price)
        VALUES (?, ?, ?, ?)
    """, [(order_id, pid, qty, price) for (pid, qty, price) in items])

    con.commit(); cur.close(); con.close()
    return order_id

def list_orders_by_status(status: str):
    con = db()
    rows = con.execute("""
        SELECT o.id, o.user_id, o.chat_id, o.total, o.status, o.created_at,
               u.username
        FROM orders o
        LEFT JOIN users u ON u.user_id = o.user_id
        WHERE o.status=?
        ORDER BY o.created_at DESC, o.id DESC
    """, (status,)).fetchall()
    con.close()
    return [dict(r) for r in rows]

def list_orders_by_user(user_id: int, limit: int = 10):
    """
    Возвращает последние заказы пользователя:
    [{id, user_id, chat_id, total, status, created_at, username}]
    """
    con = db()
    rows = con.execute("""
        SELECT o.id, o.user_id, o.chat_id, o.total, o.status, o.created_at,
               u.username
        FROM orders o
        LEFT JOIN users u ON u.user_id = o.user_id
        WHERE o.user_id = ?
        ORDER BY o.created_at DESC, o.id DESC
        LIMIT ?
    """, (user_id, int(limit))).fetchall()
    con.close()
    return [dict(r) for r in rows]

def get_order_items(order_id: int):
    con = db()
    rows = con.execute("""
        SELECT oi.product_id, oi.qty, oi.price, p.name
        FROM order_items oi
        LEFT JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id=?
    """, (order_id,)).fetchall()
    con.close()
    return [dict(r) for r in rows]

def get_order(order_id: int):
    con = db()
    r = con.execute("""
        SELECT o.id, o.user_id, o.chat_id, o.total, o.status, o.created_at,
               u.username
        FROM orders o
        LEFT JOIN users u ON u.user_id=o.user_id
        WHERE o.id=?
    """, (order_id,)).fetchone()
    con.close()
    return dict(r) if r else None

def update_order_status(order_id: int, new_status: str):
    con = db()
    con.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
    con.commit(); con.close()

# ============================ Уведомления (планировщик) ============================

def schedule_notification(chat_id: int, text: str, send_at: datetime):
    con = db(); cur = con.cursor()
    cur.execute("""
        INSERT INTO notifications(chat_id, text, send_at, sent)
        VALUES (?, ?, ?, 0)
    """, (chat_id, text, send_at.strftime("%Y-%m-%d %H:%M:%S")))
    con.commit(); cur.close(); con.close()

def fetch_due_notifications(now_dt: datetime):
    now_iso = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    con = db(); cur = con.cursor()
    rows = cur.execute("""
        SELECT id, chat_id, text FROM notifications
        WHERE sent=0 AND send_at <= ?
        ORDER BY send_at ASC
    """, (now_iso,)).fetchall()
    ids = [r["id"] for r in rows]
    if ids:
        cur.execute(f"UPDATE notifications SET sent=1 WHERE id IN ({','.join('?' for _ in ids)})", ids)
        con.commit()
    cur.close(); con.close()
    return [dict(r) for r in rows]

# ============================ Клиентские ридеры (для handlers_user.py) ============================

def client_list_categories():          return list_categories()
def client_list_products(cat_id: int): return list_products(cat_id)
def client_get_product(pid: int):      return get_product(pid)
def client_list_posts():               return list_posts()
def client_get_post(post_id: int):     return get_post(post_id)
def client_get_min_delivery_sum():     return get_min_delivery_sum()

def client_get_pickup_address() -> str:
    points = list_pickup_points()
    return "; ".join([p["address"] for p in points]) if points else ""

def client_list_orders_by_user(user_id: int, limit: int = 10):
    return list_orders_by_user(user_id, limit)

# ============================ Статистика ============================

def stats_get_products(start_dt, end_dt, limit=None):
    import datetime as _dt
    if isinstance(start_dt, _dt.datetime):
        start_iso = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        start_iso = str(start_dt)
    if isinstance(end_dt, _dt.datetime):
        end_iso = end_dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        end_iso = str(end_dt)

    sql = """
    SELECT
        oi.product_id            AS product_id,
        p.name                   AS name,
        SUM(oi.qty)              AS total_qty,
        SUM(oi.qty * oi.price)   AS total_sum
    FROM order_items oi
    JOIN orders o   ON o.id = oi.order_id
    JOIN products p ON p.id = oi.product_id
    WHERE o.created_at >= ? AND o.created_at <= ?
    GROUP BY oi.product_id
    ORDER BY total_qty DESC, total_sum DESC
    """
    params = [start_iso, end_iso]
    if limit and isinstance(limit, int) and limit > 0:
        sql += " LIMIT ?"; params.append(limit)

    con = db(); rows = con.execute(sql, params).fetchall(); con.close()
    return [{
        "product_id": r["product_id"],
        "name": r["name"],
        "total_qty": int(r["total_qty"] or 0),
        "total_sum": float(r["total_sum"] or 0.0),
    } for r in rows]

def build_stats_text(start_dt, end_dt):
    rows = stats_get_products(start_dt, end_dt)
    if not rows:
        return "Статистика: за указанный период продаж не найдено."
    lines = [
        "<b>📊 Статистика продаж</b>",
        f"Период: <code>{start_dt}</code> — <code>{end_dt}</code>",
        ""
    ]
    for i, r in enumerate(rows, start=1):
        lines.append(f"{i}. {r['name']} — {r['total_qty']} шт. · {r['total_sum']:.2f} RSD")
    return "\n".join(lines)

# ============================ Разметка меню ============================

def admin_menu_markup() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📦 Каталог", callback_data="admin:catalog"),
        types.InlineKeyboardButton("📰 Публикации", callback_data="admin:posts"),
    )
    kb.add(
        types.InlineKeyboardButton("🧾 Заказы", callback_data="admin:orders"),
        types.InlineKeyboardButton("⚙️ Настройки", callback_data="admin:settings"),
    )
    kb.add(
        types.InlineKeyboardButton("📊 Статистика", callback_data="admin:stats"),
        types.InlineKeyboardButton("⬅️ Выйти", callback_data="admin:exit"),
    )
    return kb

def catalog_menu_markup():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("➕ Добавить категорию", callback_data="admin:cat:add"))
    kb.add(types.InlineKeyboardButton("🗑 Удалить категорию", callback_data="admin:cat:del"))
    kb.add(types.InlineKeyboardButton("➕ Добавить товар", callback_data="admin:prod:add"))
    kb.add(types.InlineKeyboardButton("✏️ Редактировать товар", callback_data="admin:prod:edit"))
    kb.add(types.InlineKeyboardButton("🗑 Удалить товар", callback_data="admin:prod:del"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:back"))
    return kb

def posts_menu_markup():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("➕ Добавить публикацию", callback_data="admin:post:add"))
    kb.add(types.InlineKeyboardButton("🗑 Удалить публикацию", callback_data="admin:post:del"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:back"))
    return kb

def orders_menu_markup():
    kb = types.InlineKeyboardMarkup(row_width=1)
    for s in ORDER_STATUSES:
        kb.add(types.InlineKeyboardButton(f"Показать: {s}", callback_data=f"admin:orders:list:{s}"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:back"))
    return kb

def settings_menu_markup():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("💰 Min сумма заказа", callback_data="admin:set:minsum"))
    kb.add(types.InlineKeyboardButton("📍 Пункты раздачи", callback_data="admin:set:pickup"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:back"))
    return kb

def pickup_menu_markup():
    kb = types.InlineKeyboardMarkup(row_width=1)
    pts = list_pickup_points()
    if pts:
        for p in pts:
            kb.add(types.InlineKeyboardButton(f"🗑 {p['address']}", callback_data=f"admin:set:pickup:del:{p['id']}"))
    kb.add(types.InlineKeyboardButton("➕ Добавить адрес", callback_data="admin:set:pickup:add"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:settings"))
    return kb

def _stats_prompt_markup():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Последние 7 дней", callback_data="admin:stats:preset:7"))
    kb.add(types.InlineKeyboardButton("Последние 30 дней", callback_data="admin:stats:preset:30"))
    kb.add(types.InlineKeyboardButton("Этот месяц", callback_data="admin:stats:preset:month"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:back"))
    return kb

def _month_bounds(dt: datetime):
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year+1, month=1) - timedelta(seconds=1)
    else:
        end = start.replace(month=start.month+1) - timedelta(seconds=1)
    return start, end

# ============================ Делегатор callback ============================

def handle_callback(bot, call, get_product_func):
    data = call.data or ""
    if not data.startswith("admin:"):
        return False

    cid = call.message.chat.id
    uid = call.from_user.id

    # Навигация
    if data == "admin:exit":
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Вы вышли из админ-панели.")
        return True

    if data == "admin:back":
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "<b>🛠 Админ-панель</b>", reply_markup=admin_menu_markup())
        return True

    # --- Каталог ---
    if data == "admin:catalog":
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "<b>📦 Каталог</b>", reply_markup=catalog_menu_markup())
        return True

    if data == "admin:cat:add":
        admin_fsm[uid] = {"action": "adm_cat_add"}
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Введите название новой категории:")
        return True

    if data == "admin:cat:del":
        cats = list_categories()
        kb = types.InlineKeyboardMarkup(row_width=1)
        if not cats:
            kb.add(types.InlineKeyboardButton("Нет категорий", callback_data="noop"))
        else:
            for c in cats:
                kb.add(types.InlineKeyboardButton(f"🗑 {c['name']}", callback_data=f"admin:cat:del:{c['id']}"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:catalog"))
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Выберите категорию для удаления:", reply_markup=kb)
        return True

    if data.startswith("admin:cat:del:"):
        cat_id = int(data.split(":")[-1])
        delete_category(cat_id)
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Категория удалена.")
        return True

    if data == "admin:prod:add":
        cats = list_categories()
        if not cats:
            bot.answer_callback_query(call.id)
            bot.send_message(cid, "Сначала добавьте категории.")
            return True
        kb = types.InlineKeyboardMarkup(row_width=1)
        for c in cats:
            kb.add(types.InlineKeyboardButton(c["name"], callback_data=f"admin:prod:add:cat:{c['id']}"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:catalog"))
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Выберите категорию для нового товара:", reply_markup=kb)
        return True

    if data.startswith("admin:prod:add:cat:"):
        cat_id = int(data.split(":")[-1])
        admin_fsm[uid] = {"action":"adm_prod_add_name", "cat_id":cat_id}
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Название товара:")
        return True

    if data == "admin:prod:edit":
        cats = list_categories()
        if not cats:
            bot.answer_callback_query(call.id)
            bot.send_message(cid, "Каталог пуст.")
            return True
        kb = types.InlineKeyboardMarkup(row_width=1)
        for c in cats:
            kb.add(types.InlineKeyboardButton(c["name"], callback_data=f"admin:prod:edit:cat:{c['id']}"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:catalog"))
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Выберите категорию:", reply_markup=kb)
        return True

    if data.startswith("admin:prod:edit:cat:"):
        cat_id = int(data.split(":")[-1])
        prods = list_products(cat_id)
        kb = types.InlineKeyboardMarkup(row_width=1)
        if not prods:
            kb.add(types.InlineKeyboardButton("Нет товаров", callback_data="noop"))
        else:
            for p in prods:
                kb.add(types.InlineKeyboardButton(p["name"], callback_data=f"admin:prod:edit:pick:{p['id']}"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:prod:edit"))
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Выберите товар для редактирования:", reply_markup=kb)
        return True

    if data.startswith("admin:prod:edit:pick:"):
        pid = int(data.split(":")[-1])
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("Название", callback_data=f"admin:prod:edit:set:{pid}:name"))
        kb.add(types.InlineKeyboardButton("Цена", callback_data=f"admin:prod:edit:set:{pid}:price"))
        kb.add(types.InlineKeyboardButton("Min qty", callback_data=f"admin:prod:edit:set:{pid}:min_qty"))
        kb.add(types.InlineKeyboardButton("Image URL", callback_data=f"admin:prod:edit:set:{pid}:image"))
        kb.add(types.InlineKeyboardButton("Описание", callback_data=f"admin:prod:edit:set:{pid}:description"))
        kb.add(types.InlineKeyboardButton("Категория", callback_data=f"admin:prod:edit:set:{pid}:category_id"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:prod:edit"))
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Что изменить?", reply_markup=kb)
        return True

    if data.startswith("admin:prod:edit:set:"):
        _,_,_, pid, field = data.split(":")
        pid = int(pid)
        if field == "category_id":
            cats = list_categories()
            kb = types.InlineKeyboardMarkup(row_width=1)
            for c in cats:
                kb.add(types.InlineKeyboardButton(c["name"], callback_data=f"admin:prod:edit:setcat:{pid}:{c['id']}"))
            kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"admin:prod:edit:pick:{pid}"))
            bot.answer_callback_query(call.id)
            bot.send_message(cid, "Выберите новую категорию:", reply_markup=kb)
            return True
        admin_fsm[uid] = {"action": "adm_prod_edit_value", "pid": pid, "field": field}
        bot.answer_callback_query(call.id)
        bot.send_message(cid, f"Введите новое значение для «{field}»:")
        return True

    if data.startswith("admin:prod:edit:setcat:"):
        _,_,_, pid, new_cat = data.split(":")
        pid = int(pid); new_cat = int(new_cat)
        update_product(pid, category_id=new_cat)
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Категория товара обновлена.")
        return True

    if data == "admin:prod:del":
        cats = list_categories()
        if not cats:
            bot.answer_callback_query(call.id)
            bot.send_message(cid, "Каталог пуст.")
            return True
        kb = types.InlineKeyboardMarkup(row_width=1)
        for c in cats:
            kb.add(types.InlineKeyboardButton(c["name"], callback_data=f"admin:prod:del:cat:{c['id']}"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:catalog"))
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Выберите категорию:", reply_markup=kb)
        return True

    if data.startswith("admin:prod:del:cat:"):
        cat_id = int(data.split(":")[-1])
        prods = list_products(cat_id)
        kb = types.InlineKeyboardMarkup(row_width=1)
        if not prods:
            kb.add(types.InlineKeyboardButton("Нет товаров", callback_data="noop"))
        else:
            for p in prods:
                kb.add(types.InlineKeyboardButton(f"🗑 {p['name']}", callback_data=f"admin:prod:del:id:{p['id']}"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:prod:del"))
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Выберите товар для удаления:", reply_markup=kb)
        return True

    if data.startswith("admin:prod:del:id:"):
        pid = int(data.split(":")[-1])
        delete_product(pid)
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Товар удалён.")
        return True

    # --- Публикации ---
    if data == "admin:posts":
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "<b>📰 Публикации</b>", reply_markup=posts_menu_markup())
        return True

    if data == "admin:post:add":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Новость", callback_data="admin:post:add:type:Новость"))
        kb.add(types.InlineKeyboardButton("Акция", callback_data="admin:post:add:type:Акция"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:posts"))
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Выберите тип публикации:", reply_markup=kb)
        return True

    if data.startswith("admin:post:add:type:"):
        ptype = data.split(":")[-1]
        admin_fsm[uid] = {"action":"adm_post_add_image", "ptype":ptype}
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Пришлите URL изображения (или - , чтобы пропустить):")
        return True

    if data == "admin:post:del":
        posts = list_posts()
        kb = types.InlineKeyboardMarkup(row_width=1)
        if not posts:
            kb.add(types.InlineKeyboardButton("Нет публикаций", callback_data="noop"))
        else:
            for p in posts[:50]:
                kb.add(types.InlineKeyboardButton(f"🗑 [{p['type']}] {p['title']}", callback_data=f"admin:post:del:{p['id']}"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:posts"))
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Выберите публикацию для удаления:", reply_markup=kb)
        return True

    if data.startswith("admin:post:del:"):
        pid = int(data.split(":")[-1])
        delete_post(pid)
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Публикация удалена.")
        return True

    # --- Заказы ---
    if data == "admin:orders":
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "<b>🧾 Заказы</b>", reply_markup=orders_menu_markup())
        return True

    if data.startswith("admin:orders:list:"):
        status = data.split(":")[-1]
        orders = list_orders_by_status(status)
        if not orders:
            bot.answer_callback_query(call.id)
            bot.send_message(cid, f"Заказы со статусом «{status}» не найдены.")
            return True

        lines = [f"<b>Заказы: {status}</b>", ""]
        kb = types.InlineKeyboardMarkup(row_width=1)
        for o in orders[:50]:
            items = get_order_items(o["id"])
            items_str = ", ".join([f"{it['name']}×{it['qty']}" for it in items]) if items else "—"
            when = o["created_at"]
            uname = f"@{o['username']}" if o.get("username") else str(o["user_id"])
            lines.append(f"{when} | {status} | #{o['id']} | {uname} | {items_str}")
            kb.add(types.InlineKeyboardButton(f"Править #{o['id']}", callback_data=f"admin:order:view:{o['id']}"))
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "\n".join(lines), reply_markup=kb)
        return True

    if data.startswith("admin:order:view:"):
        oid = int(data.split(":")[-1])
        o = get_order(oid)
        if not o:
            bot.answer_callback_query(call.id)
            bot.send_message(cid, "Заказ не найден.")
            return True
        items = get_order_items(oid)
        items_str = "\n".join([f"• {it['name']} — {it['qty']} × {it['price']:.2f}" for it in items]) or "—"
        text = (
            f"<b>Заказ #{o['id']}</b>\n"
            f"Статус: <b>{o['status']}</b>\n"
            f"Сумма: {o['total']:.2f}\n"
            f"Пользователь: @{o['username'] or ''} (id {o['user_id']})\n"
            f"Создан: {o['created_at']}\n\n"
            f"<b>Товары:</b>\n{items_str}"
        )
        kb = types.InlineKeyboardMarkup(row_width=3)
        for s in ORDER_STATUSES:
            kb.add(types.InlineKeyboardButton(s, callback_data=f"admin:order:status:{oid}:{s}"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад к списку", callback_data=f"admin:orders"))
        bot.answer_callback_query(call.id)
        bot.send_message(cid, text, reply_markup=kb)
        return True

    if data.startswith("admin:order:status:"):
        _,_,_, oid, new_status = data.split(":")
        oid = int(oid)
        o = get_order(oid)
        if not o:
            bot.answer_callback_query(call.id)
            bot.send_message(cid, "Заказ не найден.")
            return True
        update_order_status(oid, new_status)
        bot.answer_callback_query(call.id)
        bot.send_message(cid, f"Статус заказа #{oid} изменён на «{new_status}».")
        if o.get("chat_id"):
            try:
                bot.send_message(o["chat_id"], f"Ваш заказ #{oid}: статус обновлён на «{new_status}».")
            except Exception as e:
                print(f"[notify user] send error: {e}")
        return True

    # --- Настройки ---
    if data == "admin:settings":
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "<b>⚙️ Настройки магазина</b>", reply_markup=settings_menu_markup())
        return True

    if data == "admin:set:minsum":
        admin_fsm[uid] = {"action":"adm_set_minsum"}
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Введите минимальную сумму заказа (число):")
        return True

    if data == "admin:set:pickup":
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "<b>📍 Пункты раздачи</b>", reply_markup=pickup_menu_markup())
        return True

    if data == "admin:set:pickup:add":
        admin_fsm[uid] = {"action":"adm_pickup_add"}
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Введите адрес пункта раздачи одной строкой:")
        return True

    if data.startswith("admin:set:pickup:del:"):
        pid = int(data.split(":")[-1])
        delete_pickup_point(pid)
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Адрес удалён.", reply_markup=pickup_menu_markup())
        return True

    # --- Статистика ---
    if data == "admin:stats":
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Выберите период:", reply_markup=_stats_prompt_markup())
        return True

    if data.startswith("admin:stats:preset:"):
        preset = data.split(":")[-1]
        now = datetime.now()
        if preset == "7":
            start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0); end = now
        elif preset == "30":
            start = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0); end = now
        elif preset == "month":
            start, end = _month_bounds(now)
        else:
            bot.answer_callback_query(call.id)
            bot.send_message(cid, "Неизвестный пресет.")
            return True
        txt = build_stats_text(start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S"))
        bot.answer_callback_query(call.id)
        bot.send_message(cid, txt)
        return True

    return True  # поймали admin:*, но неизвестное — чтобы не упало

# ============================ Делегатор текстов (FSM) ============================

def handle_text(bot, message, get_product_func):
    uid = message.from_user.id
    st = admin_fsm.get(uid)
    if not st: 
        return False

    # --- Категории ---
    if st.get("action") == "adm_cat_add":
        name = (message.text or "").strip()
        if not name:
            bot.send_message(message.chat.id, "Пустое имя. Введите снова:")
            return True
        add_category(name)
        admin_fsm.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ Категория «{name}» добавлена.", reply_markup=catalog_menu_markup())
        return True

    # --- Добавление товара (многошагово) ---
    if st.get("action") == "adm_prod_add_name":
        name = (message.text or "").strip()
        if not name:
            bot.send_message(message.chat.id, "Имя пустое. Введите название товара:")
            return True
        st["name"] = name
        st["action"] = "adm_prod_add_price"
        bot.send_message(message.chat.id, "Цена (число):")
        return True

    if st.get("action") == "adm_prod_add_price":
        try:
            price = float((message.text or "").replace(",", "."))
        except Exception:
            bot.send_message(message.chat.id, "Некорректная цена. Введите число:")
            return True
        st["price"] = price
        st["action"] = "adm_prod_add_minqty"
        bot.send_message(message.chat.id, "Минимальное количество (целое число):")
        return True

    if st.get("action") == "adm_prod_add_minqty":
        try:
            min_qty = int((message.text or "").strip())
            if min_qty < 1: raise ValueError
        except Exception:
            bot.send_message(message.chat.id, "Некорректное значение. Введите целое число ≥1:")
            return True
        st["min_qty"] = min_qty
        st["action"] = "adm_prod_add_image"
        bot.send_message(message.chat.id, "URL изображения (или - чтобы пропустить):")
        return True

    if st.get("action") == "adm_prod_add_image":
        img = (message.text or "").strip()
        st["image"] = "" if img == "-" else img
        st["action"] = "adm_prod_add_desc"
        bot.send_message(message.chat.id, "Описание товара (можно кратко):")
        return True

    if st.get("action") == "adm_prod_add_desc":
        st["description"] = (message.text or "").strip()
        pid = add_product(
            st["name"], st["price"], st["min_qty"],
            st["image"], st["description"], st["cat_id"]
        )
        admin_fsm.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ Товар добавлен (ID {pid}).", reply_markup=catalog_menu_markup())
        return True

    # --- Редактирование товара (одно поле) ---
    if st.get("action") == "adm_prod_edit_value":
        field = st.get("field"); pid = int(st.get("pid"))
        val = (message.text or "").strip()
        try:
            if field == "price":
                val = float(val.replace(",", "."))
            elif field == "min_qty":
                val = int(val)
            update_product(pid, **{field: val})
            admin_fsm.pop(uid, None)
            bot.send_message(message.chat.id, "✅ Товар обновлён.", reply_markup=catalog_menu_markup())
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка: {e}\nВведите новое значение для «{field}» ещё раз:")
        return True

    # --- Публикации (многошагово) ---
    if st.get("action") == "adm_post_add_image":
        st["image"] = "" if (message.text or "").strip() == "-" else (message.text or "").strip()
        st["action"] = "adm_post_add_title"
        bot.send_message(message.chat.id, "Заголовок публикации:")
        return True

    if st.get("action") == "adm_post_add_title":
        st["title"] = (message.text or "").strip()
        if not st["title"]:
            bot.send_message(message.chat.id, "Пустой заголовок. Введите ещё раз:")
            return True
        st["action"] = "adm_post_add_text"
        bot.send_message(message.chat.id, "Текст публикации:")
        return True

    if st.get("action") == "adm_post_add_text":
        st["text"] = (message.text or "").strip()
        st["action"] = "adm_post_add_when"
        bot.send_message(message.chat.id, "Когда публиковать? Укажите 'YYYY-MM-DD HH:MM' или '-' (сейчас):")
        return True

    if st.get("action") == "adm_post_add_when":
        txt = (message.text or "").strip()
        publish_at = None
        if txt != "-":
            try:
                dt = datetime.strptime(txt, "%Y-%m-%d %H:%M")
                publish_at = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                bot.send_message(message.chat.id, "Неверный формат. Укажите 'YYYY-MM-DD HH:MM' или '-' :")
                return True
        pid = add_post(st["ptype"], st["image"], st["title"], st["text"], publish_at)
        admin_fsm.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ Публикация добавлена (ID {pid}).", reply_markup=posts_menu_markup())
        return True

    # --- Настройки ---
    if st.get("action") == "adm_set_minsum":
        try:
            val = float((message.text or "0").replace(",", "."))
            if val < 0: raise ValueError
        except Exception:
            bot.send_message(message.chat.id, "Введите неотрицательное число:")
            return True
        set_min_delivery_sum(val)
        admin_fsm.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ Минимальная сумма заказа установлена: {val:.2f}", reply_markup=settings_menu_markup())
        return True

    if st.get("action") == "adm_pickup_add":
        addr = (message.text or "").strip()
        if not addr:
            bot.send_message(message.chat.id, "Адрес пуст. Введите снова:")
            return True
        add_pickup_point(addr)
        admin_fsm.pop(uid, None)
        bot.send_message(message.chat.id, "✅ Адрес добавлен.", reply_markup=pickup_menu_markup())
        return True

    return False
