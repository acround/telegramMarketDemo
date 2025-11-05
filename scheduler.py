# scheduler.py
# Фоновый планировщик уведомлений: каждые 10 сек берёт due-уведомления из БД и отправляет их.

import threading
import time
from datetime import datetime
import Admin_bot

def start_notification_scheduler(bot):
    def loop():
        while True:
            try:
                now = datetime.utcnow()
                due = Admin_bot.fetch_due_notifications(now)
                for n in due:
                    try:
                        bot.send_message(n["chat_id"], n["text"], parse_mode="HTML")
                    except Exception as e:
                        print(f"[notif_scheduler] send error: {e}")
            except Exception as e:
                print(f"[notif_scheduler] loop error: {e}")
            time.sleep(10)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
