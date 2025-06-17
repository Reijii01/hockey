import sqlite3
import time
from datetime import datetime
import telegram  # для версии 13.15
import os
from dotenv import load_dotenv

load_dotenv()  # загружаем переменные из .env

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DB_PATH = "button_state.db"


bot = telegram.Bot(token=BOT_TOKEN)
INTERVAL = 60

def fetch_current_state():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        row = c.execute("SELECT text, href, last_notified_text, last_notified_href FROM button_state WHERE id = 1").fetchone()
        if row:
            return {
                "text": row[0],
                "href": row[1],
                "notified_text": row[2],
                "notified_href": row[3]
            }
        return None

def update_notified_state(text, href):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE button_state SET last_notified_text = ?, last_notified_href = ? WHERE id = 1", (text, href))
        conn.commit()

def send_notification(old_text, new_text, old_href, new_href):
    msg = (
        "🔔 *Обновление кнопки!*\n\n"
        f"*Текст:* `{old_text or '-'} → {new_text}`\n"
        f"*Ссылка:* `{old_href or '-'} → {new_href}`"
    )
    try:
        bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)
    except telegram.error.TelegramError as e:
        print(f"Ошибка при отправке сообщения: {e}")

def main():
    has_sent_greeting = False

    while True:
        state = fetch_current_state()

        if state:
            if not has_sent_greeting:
                msg = (
                    "✅ Бот запущен.\n"
                    "Изменений пока нет.\n\n"
                    f"*Текущий текст:* `{state['text'] or '—'}`\n"
                    f"*Текущая ссылка:* `{state['href'] or '—'}`"
                )
                try:
                    bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)
                except telegram.error.TelegramError as e:
                    print(f"Ошибка при отправке приветственного сообщения: {e}")
                has_sent_greeting = True

            if state["text"] != state["notified_text"] or state["href"] != state["notified_href"]:
                print(f"[{datetime.now():%H:%M:%S}] Изменение — отправляем уведомление")
                send_notification(state["notified_text"], state["text"], state["notified_href"], state["href"])
                update_notified_state(state["text"], state["href"])
        else:
            print("❌ Нет данных в базе")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()


