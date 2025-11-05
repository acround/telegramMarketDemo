# main.py — точка входа
from handlers_user import get_bot
import Admin_bot
import threading, time
from datetime import datetime

def notif_scheduler(bot):
    """Простой планировщик отправки уведомлений (если они есть)."""
    print("Планировщик уведомлений запущен.")
    while True:
        print("Планировщик уведомлений: проверка…")
        try:
            due = Admin_bot.fetch_due_notifications(datetime.utcnow())
            for n in due:
                try:
                    bot.send_message(n["chat_id"], n["text"], parse_mode="HTML")
                except Exception as e:
                    print(f"[notif send error] {e}")
        except Exception as e:
            print(f"[notif_scheduler] loop error: {e}")
        time.sleep(5)

def main():
    Admin_bot.init_db()
    bot = get_bot()

    # Запускаем планировщик в фоне
    th = threading.Thread(target=notif_scheduler, args=(bot,), daemon=True)
    th.start()

    print("Бот запущен…")
    bot.polling(none_stop=True, interval=0, timeout=20)

if __name__ == "__main__":
    main()
