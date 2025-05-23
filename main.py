import json
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, date
from database import conn, cursor
import os

API_TOKEN = "7644227252:AAFOJb5DJlONCNziYAEJTT3oKJhPoa0n504"

bot = Bot(token=API_TOKEN)
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

dp = Dispatcher(bot)

# Временные состояния
start_times = {}
waiting_for_tracker_name = {}
waiting_for_begin = {}


@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.reply(
        "Привет! 👋 Я твой трекер. Нажимай кнопки ниже ⬇️",
        reply_markup=main_menu
    )


@dp.message_handler(commands=["begin"])
async def ask_which_to_begin(message: types.Message):
    uid = str(message.from_user.id)
    cursor.execute("SELECT name FROM trackers WHERE user_id = ?", (uid,))
    rows = cursor.fetchall()

    if not rows:
        await message.reply("У тебя нет трекеров. Добавь командой /add", reply_markup=main_menu)
        return

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for row in rows:
        keyboard.add(KeyboardButton(row[0]))

    waiting_for_begin[uid] = True
    await message.reply("🏋️ Какой трекер запустить?", reply_markup=keyboard)


@dp.message_handler(commands=["my"])
async def my_trackers(message: types.Message):
    uid = str(message.from_user.id)
    cursor.execute("SELECT name FROM trackers WHERE user_id = ?", (uid,))
    rows = cursor.fetchall()

    if not rows:
        await message.reply("У тебя пока нет трекеров. Добавь командой /add", reply_markup=main_menu)
        return

    text = "\n".join(f"• {row[0]}" for row in rows)
    await message.reply("📋 Твои трекеры:\n" + text)


@dp.message_handler(commands=["end"])
async def end_timer(message: types.Message):
    user_id = str(message.from_user.id)

    cursor.execute("SELECT name, start FROM active_sessions WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if not result:
        await message.reply("Ты не запускал таймер. Напиши /begin.", reply_markup=main_menu)
        return

    name, start_str = result
    start_dt = datetime.fromisoformat(start_str)
    duration = datetime.now() - start_dt
    minutes = duration.seconds // 60

    cursor.execute(
        "INSERT INTO logs (user_id, name, minutes, date) VALUES (?, ?, ?, ?)",
        (user_id, name, minutes, str(date.today()))
    )
    cursor.execute("DELETE FROM active_sessions WHERE user_id = ?", (user_id,))
    conn.commit()

    await message.reply(f"✅ Завершено: «{name}» — {minutes} мин.", reply_markup=main_menu)


@dp.message_handler(commands=["add"])
async def ask_for_tracker_name(message: types.Message):
    uid = str(message.from_user.id)
    waiting_for_tracker_name[uid] = True
    await message.reply(
        "🗘️ Отлично! Напиши название трекера, который хочешь добавить.", reply_markup=main_menu)


@dp.message_handler()
async def catch_tracker_name(message: types.Message):
    uid = str(message.from_user.id)

    if waiting_for_begin.get(uid):
        name = message.text.strip()
        cursor.execute("SELECT 1 FROM trackers WHERE user_id = ? AND name = ?", (uid, name))
        if not cursor.fetchone():
            await message.reply("Такого трекера нет.", reply_markup=main_menu)
        else:
            cursor.execute(
                "REPLACE INTO active_sessions (user_id, name, start) VALUES (?, ?, ?)",
                (uid, name, datetime.now().isoformat())
            )
            conn.commit()
            await message.reply(f"⏱ Засекли «{name}»!", reply_markup=main_menu)
        waiting_for_begin.pop(uid)
        return

    if waiting_for_tracker_name.get(uid):
        name = message.text.strip()
        cursor.execute("SELECT 1 FROM trackers WHERE user_id = ? AND name = ?", (uid, name))
        if cursor.fetchone():
            await message.reply("Такой трекер уже есть.")
        else:
            cursor.execute("INSERT INTO trackers (user_id, name) VALUES (?, ?)", (uid, name))
            conn.commit()
            await message.reply(f"✅ Трекер «{name}» добавлен!")
        waiting_for_tracker_name.pop(uid)


@dp.message_handler(commands=["report"])
async def report(message: types.Message):
    uid = str(message.from_user.id)
    cursor.execute("""
        SELECT name, SUM(minutes)
        FROM logs
        WHERE user_id = ?
        GROUP BY name
    """, (uid,))
    rows = cursor.fetchall()

    if not rows:
        await message.reply("Пока нет завершённых трекеров.")
        return

    text = "\n".join(f"• {name} — {minutes} мин." for name, minutes in rows)
    await message.reply("📊 Отчёт:\n" + text)


@dp.message_handler(commands=["day"])
async def report_today(message: types.Message):
    uid = str(message.from_user.id)
    today = str(date.today())
    cursor.execute("""
        SELECT name, SUM(minutes)
        FROM logs
        WHERE user_id = ? AND date = ?
        GROUP BY name
    """, (uid, today))
    rows = cursor.fetchall()

    if not rows:
        await message.reply("Сегодня ты ещё ничего не засекала.")
        return

    text = "\n".join(f"• {name} — {minutes} мин." for name, minutes in rows)
    await message.reply(f"📅 Сегодняшний отчёт:\n{text}")


@dp.message_handler(commands=["week"])
async def report_week(message: types.Message):
    uid = str(message.from_user.id)
    week_ago = (datetime.today() - timedelta(days=7)).date().isoformat()
    cursor.execute("""
        SELECT name, SUM(minutes)
        FROM logs
        WHERE user_id = ? AND date >= ?
        GROUP BY name
    """, (uid, week_ago))
    rows = cursor.fetchall()

    if not rows:
        await message.reply("За последнюю неделю нет засеченного времени.")
        return

    text = "\n".join(f"• {name} — {minutes} мин." for name, minutes in rows)
    await message.reply(f"📅 Отчёт за 7 дней:\n{text}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
