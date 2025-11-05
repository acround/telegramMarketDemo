# i18n.py
# Простейшая i18n: словарь строк + помощники для переводов

from typing import Dict
import Admin_bot  # используем профиль для чтения языка

# Доступные языки
LANGS = {
    "ru": "Русский",
    "en": "English",
    "sr": "Srpski",
}

# Ключи переводов
STRINGS: Dict[str, Dict[str, str]] = {
    # === Главные кнопки ===
    "btn.catalog":     {"ru": "🛍 Каталог", "en": "🛍 Catalog", "sr": "🛍 Katalog"},
    "btn.news":        {"ru": "📰 Новости и акции", "en": "📰 News & Deals", "sr": "📰 Vesti i akcije"},
    "btn.cart":        {"ru": "🛒 Корзина", "en": "🛒 Cart", "sr": "🛒 Korpa"},
    "btn.profile":     {"ru": "👤 Личный кабинет", "en": "👤 Profile", "sr": "👤 Profil"},
    "btn.admin":       {"ru": "🛠 Админ-панель", "en": "🛠 Admin Panel", "sr": "🛠 Admin panel"},
    "btn.lang":        {"ru": "🌐 Язык", "en": "🌐 Language", "sr": "🌐 Jezik"},

    # === Общие тексты ===
    "hello":           {"ru": "Привет! 👋 Это демо бот-магазин.",
                        "en": "Hi! 👋 This is a demo shop bot.",
                        "sr": "Ćao! 👋 Ovo je demo prodajni bot."},
    "tip.demo_admin":  {"ru": "Подсказка: отправьте <code>demo admin</code>, чтобы открыть админ-панель.",
                        "en": "Tip: send <code>demo admin</code> to open the admin panel.",
                        "sr": "Savet: pošaljite <code>demo admin</code> da otvorite admin panel."},
    "main.menu":       {"ru": "Главное меню:", "en": "Main menu:", "sr": "Glavni meni:"},
    "catalog.title":   {"ru": "<b>Категории товаров</b>:", "en": "<b>Product categories</b>:", "sr": "<b>Kategorije proizvoda</b>:"},
    "cart.empty":      {"ru": "Ваша корзина пуста.", "en": "Your cart is empty.", "sr": "Vaša korpa je prazna."},
    "cart.cleared":    {"ru": "Корзина очищена. /catalog", "en": "Cart cleared. /catalog", "sr": "Korpa je obrisana. /catalog"},
    "orders.accepted": {"ru": "✅ Заказ принят (демо).\nПозиции: {qty} шт., сумма: <b>{total}</b>.\nСпасибо!",
                        "en": "✅ Order accepted (demo).\nItems: {qty} pcs, total: <b>{total}</b>.\nThank you!",
                        "sr": "✅ Porudžbina prihvaćena (demo).\nStavki: {qty} kom, ukupno: <b>{total}</b>.\nHvala!"},
    "admin.require":   {"ru": "⛔ Доступ к админ-панели доступен после сообщения: demo admin",
                        "en": "⛔ Admin panel is available after sending: demo admin",
                        "sr": "⛔ Admin panel je dostupan nakon poruke: demo admin"},
    "choose.from.menu":{"ru": "Выберите раздел в меню ниже:", "en": "Choose a section from the menu below:", "sr": "Izaberite sekciju iz menija ispod:"},

    # === Новости ===
    "news.title":      {"ru": "<b>📰 Новости и акции</b>\nВыберите публикацию:",
                        "en": "<b>📰 News & deals</b>\nChoose a post:",
                        "sr": "<b>📰 Vesti i akcije</b>\nIzaberite objavu:"},
    "news.empty":      {"ru": "<b>📰 Новости и акции</b>\nПока пусто.",
                        "en": "<b>📰 News & deals</b>\nEmpty for now.",
                        "sr": "<b>📰 Vesti i akcije</b>\nZa sada prazno."},

    # === Профиль ===
    "profile.title":   {"ru": "<b>👤 Личный кабинет</b>",
                        "en": "<b>👤 Profile</b>",
                        "sr": "<b>👤 Profil</b>"},
    "profile.username":{"ru": "<b>Username:</b> @{u}",
                        "en": "<b>Username:</b> @{u}",
                        "sr": "<b>Username:</b> @{u}"},
    "profile.phone":   {"ru": "<b>Телефон:</b> {p}",
                        "en": "<b>Phone:</b> {p}",
                        "sr": "<b>Telefon:</b> {p}"},
    "profile.address": {"ru": "<b>Адрес доставки:</b> {a}",
                        "en": "<b>Delivery address:</b> {a}",
                        "sr": "<b>Adresa za dostavu:</b> {a}"},
    "profile.edit.phone.ask": {"ru": "Отправьте ваш номер телефона (кнопкой ниже) или введите вручную.",
                               "en": "Send your phone (button below) or type it manually.",
                               "sr": "Pošaljite svoj broj telefona (dugme ispod) ili unesite ručno."},
    "profile.edit.address.ask":{"ru": "Введите ваш адрес доставки одной строкой:",
                                "en": "Enter your delivery address in one line:",
                                "sr": "Unesite adresu za dostavu u jednom redu:"},
    "profile.saved.phone":    {"ru": "✅ Телефон сохранён.", "en": "✅ Phone saved.", "sr": "✅ Telefon sačuvan."},
    "profile.saved.address":  {"ru": "✅ Адрес сохранён.", "en": "✅ Address saved.", "sr": "✅ Adresa sačuvana."},

    # === Кнопки профиля ===
    "btn.profile.edit.phone": {"ru": "📱 Изменить телефон", "en": "📱 Edit phone", "sr": "📱 Izmeni telefon"},
    "btn.profile.edit.addr":  {"ru": "🏠 Изменить адрес", "en": "🏠 Edit address", "sr": "🏠 Izmeni adresu"},
    "btn.profile.orders":     {"ru": "🧾 Мои заказы", "en": "🧾 My orders", "sr": "🧾 Moje porudžbine"},

    # === Заказы пользователя ===
    "myorders.title":         {"ru": "<b>🧾 Мои заказы</b>", "en": "<b>🧾 My orders</b>", "sr": "<b>🧾 Moje porudžbine</b>"},
    "order.view.repeat":      {"ru": "↩️ Повторить этот заказ", "en": "↩️ Repeat this order", "sr": "↩️ Ponovi ovu porudžbinu"},
    "back.to.profile":        {"ru": "← К профилю", "en": "← Back to profile", "sr": "← Nazad na profil"},
    "back.to.orders":         {"ru": "← К списку моих заказов", "en": "← Back to my orders", "sr": "← Nazad na moje porudžbine"},

    # === Язык ===
    "lang.choose":            {"ru": "Выберите язык:", "en": "Choose language:", "sr": "Izaberite jezik:"},
    # ВАЖНО: используем {lang_name}, НЕ {lang}
    "lang.set.ok":            {"ru": "✅ Язык сохранён: {lang_name}", "en": "✅ Language saved: {lang_name}", "sr": "✅ Jezik sačuvan: {lang_name}"},
    "send.contact":           {"ru": "📲 Отправить мой номер", "en": "📲 Send my number", "sr": "📲 Pošalji moj broj"},
    # === Выход в главное меню (пользовательская часть) ===
    "exit.to.menu": {"ru": "⬅️ Выйти в меню", "en": "⬅️ Exit to menu", "sr": "⬅️ Nazad u meni"},

}

def _safe_lang(language: str) -> str:
    return language if language in LANGS else "ru"

def tr_by_lang(language: str, key: str, **kwargs) -> str:
    language = _safe_lang(language)
    v = STRINGS.get(key, {})
    txt = v.get(language) or v.get("ru") or key
    if kwargs:
        try:
            return txt.format(**kwargs)
        except Exception:
            return txt
    return txt

def get_user_lang(user_id: int) -> str:
    try:
        prof = Admin_bot.get_profile(user_id)
        language = (prof or {}).get("lang") or "ru"
        return _safe_lang(language)
    except Exception:
        return "ru"

def tr(user_id: int, key: str, **kwargs) -> str:
    return tr_by_lang(get_user_lang(user_id), key, **kwargs)

# Наборы текста кнопок (для сопоставления входящих сообщений)
BTN_SETS = {
    "catalog": {STRINGS["btn.catalog"][l] for l in LANGS},
    "news":    {STRINGS["btn.news"][l] for l in LANGS},
    "cart":    {STRINGS["btn.cart"][l] for l in LANGS},
    "profile": {STRINGS["btn.profile"][l] for l in LANGS},
    "admin":   {STRINGS["btn.admin"][l] for l in LANGS},
    "lang":    {STRINGS["btn.lang"][l] for l in LANGS},
}
