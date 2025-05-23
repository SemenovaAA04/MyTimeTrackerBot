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

# Сохраняем время старта
start_times = {}
waiting_for_tracker_name = {}
waiting_for_begin = {}
waiting_for_delete = {}
tracker_logs = {}


@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.reply(
        "Привет! 👋 Я твой трекер. Нажимай кнопки ниже ⬇️",
        reply_markup=main_menu
    )


@dp.message_handler(commands=["begin"])
async def ask_which_to_begin(message: types.Message):
    uid = str(message.from_user.id)

    # Запрашиваем трекеры из базы
    cursor.execute("SELECT name FROM trackers WHERE user_id = ?", (uid,))
    rows = cursor.fetchall()

    if not rows:
        await message.reply("У тебя нет трекеров. Добавь командой /add", reply_markup=main_menu)
        return

    # Формируем клавиатуру
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for row in rows:
        keyboard.add(KeyboardButton(row[0]))

    waiting_for_begin[uid] = True
    await message.reply("🏁 Какой трекер запустить?", reply_markup=keyboard)


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



    tracker_logs.setdefault(user_id, [])
    tracker_logs[user_id].append({
        "name": name,
        "minutes": minutes,
        "date": str(date.today())
    })
        cursor.execute(
    "INSERT INTO logs (user_id, name, minutes, date) VALUES (?, ?, ?, ?)",
    (user_id, name, minutes, str(date.today()))
)
conn.commit()


    await message.reply(f"✅ Завершено: «{name}» — {minutes} мин.")
    del start_times[user_id]


@dp.message_handler(commands=["add"])
async def ask_for_tracker_name(message: types.Message):
    uid = str(message.from_user.id)
    waiting_for_tracker_name[uid] = True
    await message.reply(
        "📝 Отлично! Напиши название трекера, который хочешь добавить.", reply_markup=main_menu)

@dp.message_handler()
async def catch_tracker_name(message: types.Message):
    uid = str(message.from_user.id)

    # 🟡 Если ждём запуск трекера
    if waiting_for_begin.get(uid):
        name = message.text.strip()
        if name not in user_trackers.get(uid, []):
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

    # 🟢 Если ждём добавление нового трекера
        if waiting_for_tracker_name.get(uid):
        name = message.text.strip()
        user_trackers.setdefault(uid, [])

        if name in user_trackers[uid]:
            await message.reply("Такой трекер уже есть.")
        else:
            user_trackers[uid].append(name)
            cursor.execute(
                "INSERT INTO trackers (user_id, name) VALUES (?, ?)",
                (uid, name)
            )
            conn.commit()
            await message.reply(f"✅ Трекер «{name}» добавлен!")
        waiting_for_tracker_name.pop(uid)


@dp.message_handler(commands=["report"])
async def report(message: types.Message):
    uid = str(message.from_user.id)
    logs = tracker_logs.get(uid, [])

    if not logs:
        await message.reply("Пока нет завершённых трекеров.")
        return

    summary = {}
    for entry in logs:
        name = entry["name"]
        summary[name] = summary.get(name, 0) + entry["minutes"]

    text = "\n".join(f"• {name} — {minutes} мин." for name, minutes in summary.items())
    await message.reply("📊 Отчёт:\n" + text)

@dp.message_handler(commands=["day"])
async def report_today(message: types.Message):
    from datetime import date
    today = str(date.today())
    uid = str(message.from_user.id)
    logs = tracker_logs.get(uid, [])

    today_logs = [entry for entry in logs if entry["date"] == today]

    if not today_logs:
        await message.reply("Сегодня ты ещё ничего не засекала.")
        return

    summary = {}
    for entry in today_logs:
        name = entry["name"]
        summary[name] = summary.get(name, 0) + entry["minutes"]

    text = "\n".join(f"• {name} — {minutes} мин." for name, minutes in summary.items())
    await message.reply(f"📅 Сегодняшний отчёт:\n{text}")

@dp.message_handler(commands=["week"])
async def report_week(message: types.Message):
    from datetime import datetime, timedelta
    uid = str(message.from_user.id)
    logs = tracker_logs.get(uid, [])

    if not logs:
        await message.reply("У тебя пока нет завершённых трекеров.")
        return

    today = datetime.today()
    week_ago = today - timedelta(days=7)

    summary = {}
    for entry in logs:
        try:
            entry_date = datetime.strptime(entry["date"], "%Y-%m-%d")
        except:
            continue 

        if week_ago <= entry_date <= today:
            name = entry["name"]
            summary[name] = summary.get(name, 0) + entry["minutes"]

    if not summary:
        await message.reply("За последнюю неделю нет засеченного времени.")
        return

    text = "\n".join(f"• {name} — {minutes} мин." for name, minutes in summary.items())
    await message.reply(f"📅 Отчёт за 7 дней:\n{text}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
