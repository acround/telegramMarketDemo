# utils.py
import io
import requests
from telebot import TeleBot

from db_access import DB_get_product
from state import carts

def fmt_price(value: float) -> str:
    return f"{float(value):,.2f} RSD".replace(",", " ")

def get_cart(user_id: int) -> dict:
    return carts.setdefault(user_id, {})

def cart_totals(cart: dict):
    """Итоги по корзине, цены берём из БД на текущий момент."""
    total_qty = 0
    total_sum = 0.0
    for pid, qty in cart.items():
        p = DB_get_product(pid)
        if not p:
            continue  # товар могли удалить
        total_qty += qty
        total_sum += float(p["price"]) * qty
    return total_qty, total_sum

def safe_send_product_photo(bot: TeleBot, chat_id: int, image_url: str, caption: str, reply_markup=None):
    """Безопасная отправка фото по URL (скачиваем → отправляем как файл). При ошибке — текстом."""
    try:
        resp = requests.get(image_url, timeout=15)
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "")
        allowed = ("image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif")
        if not any(ctype.startswith(x) for x in allowed):
            raise ValueError(f"Bad Content-Type: {ctype}")
        fileobj = io.BytesIO(resp.content)
        fileobj.name = "photo.jpg"
        return bot.send_photo(chat_id, fileobj, caption=caption, reply_markup=reply_markup)
    except Exception as e:
        print(f"[safe_send_product_photo] fallback to text: {e}")
        return bot.send_message(chat_id, caption, reply_markup=reply_markup)
