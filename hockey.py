import sqlite3
import time
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === Настройки =================================================================
URL = "https://match-goda.ru/"                        # 🔁 реальный адрес страницы
BUTTON_CONTAINER_ID = "molecule-174596722953362380"
DB_PATH = "button_state.db"
INTERVAL = 60                                      # ⏱ проверяем каждую минуту
DRIVER_LIFETIME = timedelta(hours=1)               # перезапуск Chrome ~раз в час
# ===============================================================================

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS button_state (
                id INTEGER PRIMARY KEY, 
                text TEXT, 
                href TEXT,
                last_notified_text TEXT,
                last_notified_href TEXT
            )
        """)
        c.execute("SELECT COUNT(*) FROM button_state WHERE id=1")
        if c.fetchone()[0] == 0:
            c.execute(
                "INSERT INTO button_state (id, text, href, last_notified_text, last_notified_href) VALUES (1, '', '', '', '')")
        conn.commit()

def load_previous_state():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        row = c.execute("SELECT text, href FROM button_state WHERE id = 1").fetchone()
    return {"text": row[0], "href": row[1]} if row else {"text": None, "href": None}

def save_state(text, href):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if load_previous_state()["text"] is None:
            c.execute("INSERT INTO button_state (id, text, href) VALUES (1, ?, ?)", (text, href))
        else:
            c.execute("UPDATE button_state SET text = ?, href = ? WHERE id = 1", (text, href))
        conn.commit()

def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    return webdriver.Chrome(options=opts)

def check_button(driver):
    driver.get(URL)
    try:
        wait = WebDriverWait(driver, 10)
        molecule = wait.until(EC.presence_of_element_located((By.ID, BUTTON_CONTAINER_ID)))
        button = molecule.find_element(By.XPATH, ".//a[contains(@class,'tn-atom')]")
        return button.text.strip(), button.get_attribute("href")
    except Exception as e:
        print(f"[!] Не удалось найти кнопку: {e}")
        return None, None

def main():
    init_db()
    driver = create_driver()
    driver_birth = datetime.utcnow()

    while True:
        try:
            # Перезапускаем драйвер, если он "старый"
            if datetime.utcnow() - driver_birth > DRIVER_LIFETIME:
                print("[i] Перезапуск драйвера по таймауту")
                driver.quit()
                driver = create_driver()
                driver_birth = datetime.utcnow()

            new_text, new_href = check_button(driver)
            if new_text is None:
                time.sleep(INTERVAL)
                continue

            prev = load_previous_state()
            if new_text != prev["text"] or new_href != prev["href"]:
                print(f"[🔔 {datetime.now():%Y-%m-%d %H:%M:%S}] Изменение!")
                print(f"    Текст : {prev['text']} → {new_text}")
                print(f"    Ссылка: {prev['href']} → {new_href}")
                save_state(new_text, new_href)
                # Здесь можно вызвать функцию отправки сообщения в Telegram

            else:
                print(f"[=] {datetime.now():%H:%M:%S} — без изменений")

        except Exception as e:
            print(f"[!] Ошибка драйвера или Selenium: {e}")
            try:
                driver.quit()
            except Exception:
                pass
            print("[i] Перезапуск драйвера после ошибки")
            driver = create_driver()
            driver_birth = datetime.utcnow()

        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()


