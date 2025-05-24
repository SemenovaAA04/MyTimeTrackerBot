import logging
import os
import sqlite3
from datetime import datetime, date, timedelta
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = os.getenv("API_TOKEN", "7644227252:AAFOJb5DJlONCNziYAEJTT3oKJhPoa0n504")

# ──────────────────────────────────────────────────────────────────────────────
# Настраиваем соединение с базой (database.py просто делает conn и cursor)
# ──────────────────────────────────────────────────────────────────────────────
db_path = "trackers.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS trackers (
    user_id TEXT,
    name    TEXT,
    PRIMARY KEY(user_id, name)
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS active_sessions (
    user_id TEXT PRIMARY KEY,
    name    TEXT,
    start   TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    user_id TEXT,
    name    TEXT,
    minutes INTEGER,
    date    TEXT
)
""")
conn.commit()

# ──────────────────────────────────────────────────────────────────────────────
# Инициализируем бота и клавиатуру меню
# ──────────────────────────────────────────────────────────────────────────────
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(
    KeyboardButton("/add"),
    KeyboardButton("/my"),
    KeyboardButton("/begin"),
    KeyboardButton("/end")
).add(
    KeyboardButton("/report"),
    KeyboardButton("/day"),
    KeyboardButton("/week")
)

# временные флаги ожидания
waiting_for_begin = {}
waiting_for_tracker_name = {}

# ──────────────────────────────────────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.reply(
        "Привет! 👋 Я твой трекер. Нажимай кнопки ниже ⬇️",
        reply_markup=main_menu
    )

# ──────────────────────────────────────────────────────────────────────────────
# /add — ждем название нового трекера
# ──────────────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["add"])
async def cmd_add(message: types.Message):
    uid = str(message.from_user.id)
    waiting_for_tracker_name[uid] = True
    await message.reply(
        "📝 Отлично! Напиши название трекера, который хочешь добавить.",
        reply_markup=main_menu
    )

# ──────────────────────────────────────────────────────────────────────────────
# /my — показать список своих трекеров
# ──────────────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["my"])
async def cmd_my(message: types.Message):
    uid = str(message.from_user.id)
    cursor.execute("SELECT name FROM trackers WHERE user_id = ?", (uid,))
    rows = cursor.fetchall()

    if not rows:
        await message.reply("У тебя пока нет трекеров. Добавь командой /add", reply_markup=main_menu)
        return

    text = "\n".join(f"• {r[0]}" for r in rows)
    await message.reply(f"📋 Твои трекеры:\n{text}", reply_markup=main_menu)

# ──────────────────────────────────────────────────────────────────────────────
# /begin — предложить выбрать трекер для запуска
# ──────────────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["begin"])
async def cmd_begin(message: types.Message):
    uid = str(message.from_user.id)
    cursor.execute("SELECT name FROM trackers WHERE user_id = ?", (uid,))
    rows = cursor.fetchall()

    if not rows:
        await message.reply("У тебя нет трекеров. Добавь командой /add", reply_markup=main_menu)
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for (name,) in rows:
        kb.add(KeyboardButton(name))

    waiting_for_begin[uid] = True
    await message.reply("🏁 Какой трекер запустить?", reply_markup=kb)

# ──────────────────────────────────────────────────────────────────────────────
# /end — завершить текущий таймер
# ──────────────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["end"])
async def cmd_end(message: types.Message):
    uid = str(message.from_user.id)
    cursor.execute("SELECT name, start FROM active_sessions WHERE user_id = ?", (uid,))
    row = cursor.fetchone()

    if not row:
        await message.reply("Ты не запускал таймер. Напиши /begin.", reply_markup=main_menu)
        return

    name, start_str = row
    start_dt = datetime.fromisoformat(start_str)
    minutes = (datetime.now() - start_dt).seconds // 60

    # сохраняем в логи
    cursor.execute(
        "INSERT INTO logs (user_id, name, minutes, date) VALUES (?, ?, ?, ?)",
        (uid, name, minutes, date.today().isoformat())
    )
    # удаляем сессию
    cursor.execute("DELETE FROM active_sessions WHERE user_id = ?", (uid,))
    conn.commit()

    await message.reply(f"✅ Завершено: «{name}» — {minutes} мин.", reply_markup=main_menu)

# ──────────────────────────────────────────────────────────────────────────────
# Обработчик «всех остальных сообщений» — т.н. FSM-lite
# (только для тех случаев, когда мы ждём имени трекера или начала сессии)
# ──────────────────────────────────────────────────────────────────────────────
@dp.message_handler(lambda msg: not msg.text.startswith("/"))
async def catch_tracker_name(message: types.Message):
    uid = str(message.from_user.id)
    text = message.text.strip()

    # ★ Запускаем трекер
    if waiting_for_begin.get(uid):
        # проверяем, существует ли такой
        cursor.execute("SELECT 1 FROM trackers WHERE user_id = ? AND name = ?", (uid, text))
        if not cursor.fetchone():
            await message.reply("Такого трекера нет 🫣", reply_markup=main_menu)
        else:
            cursor.execute(
                "REPLACE INTO active_sessions (user_id, name, start) VALUES (?, ?, ?)",
                (uid, text, datetime.now().isoformat())
            )
            conn.commit()
            await message.reply(f"⏱ Засекли «{text}»!", reply_markup=main_menu)
        waiting_for_begin.pop(uid)
        return

    # ★ Добавляем новый трекер
    if waiting_for_tracker_name.get(uid):
        # проверяем на дубли
        cursor.execute("SELECT 1 FROM trackers WHERE user_id = ? AND name = ?", (uid, text))
        if cursor.fetchone():
            await message.reply("Такой трекер уже есть.", reply_markup=main_menu)
        else:
            cursor.execute("INSERT INTO trackers (user_id, name) VALUES (?, ?)", (uid, text))
            conn.commit()
            await message.reply(f"✅ Трекер «{text}» добавлен!", reply_markup=main_menu)
        waiting_for_tracker_name.pop(uid)
        return

# ──────────────────────────────────────────────────────────────────────────────
# /report — общий отчёт по всем трекерам
# ──────────────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["report"])
async def cmd_report(message: types.Message):
    uid = str(message.from_user.id)
    cursor.execute("""
        SELECT name, SUM(minutes)
        FROM logs
        WHERE user_id = ?
        GROUP BY name
    """, (uid,))
    rows = cursor.fetchall()

    if not rows:
        await message.reply("Пока нет завершённых трекеров.", reply_markup=main_menu)
        return

    text = "\n".join(f"• {name} — {minutes} мин." for name, minutes in rows)
    await message.reply("📊 Отчёт:\n" + text, reply_markup=main_menu)

# ──────────────────────────────────────────────────────────────────────────────
# /day — отчёт за сегодня
# ──────────────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["day"])
async def cmd_day(message: types.Message):
    uid = str(message.from_user.id)
    today = date.today().isoformat()
    cursor.execute("""
        SELECT name, SUM(minutes)
        FROM logs
        WHERE user_id = ? AND date = ?
        GROUP BY name
    """, (uid, today))
    rows = cursor.fetchall()

    if not rows:
        await message.reply("Сегодня ты ещё ничего не засекала.", reply_markup=main_menu)
        return

    text = "\n".join(f"• {name} — {minutes} мин." for name, minutes in rows)
    await message.reply(f"📅 Сегодняшний отчёт:\n{text}", reply_markup=main_menu)

# ──────────────────────────────────────────────────────────────────────────────
# /week — отчёт за последние 7 дней
# ──────────────────────────────────────────────────────────────────────────────
@dp.message_handler(commands=["week"])
async def cmd_week(message: types.Message):
    uid = str(message.from_user.id)
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    cursor.execute("""
        SELECT name, SUM(minutes)
        FROM logs
        WHERE user_id = ? AND date >= ?
        GROUP BY name
    """, (uid, week_ago))
    rows = cursor.fetchall()

    if not rows:
        await message.reply("За последнюю неделю нет засеченного времени.", reply_markup=main_menu)
        return

    text = "\n".join(f"• {name} — {minutes} мин." for name, minutes in rows)
    await message.reply(f"📅 Отчёт за 7 дней:\n{text}", reply_markup=main_menu)

# простой HTTP-сервер для «здоровья» (healthcheck)
app = Flask(__name__)

@app.route("/")
def healthcheck():
    return "OK", 200

def run_web():
    # Render ожидает порт 8080
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    keep_alive()                       # запустили веб-сервер на 8080
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)

