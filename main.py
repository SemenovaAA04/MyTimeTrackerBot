import json
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, date
import os

API_TOKEN = "7644227252:AAFYp3aKLB6HlZWxX4h_PBFlDIx1TwHOGaE"

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
user_trackers = {}
waiting_for_tracker_name = {}
waiting_for_begin = {}
waiting_for_delete = {}
tracker_logs = {}


def save_data():
    with open("data.json", "w") as f:
        json.dump({
            "user_trackers": user_trackers,
            "start_times": start_times,
            "tracker_logs": tracker_logs
        }, f, indent=2)


@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.reply(
        "Привет! 👋 Я твой трекер. Нажимай кнопки ниже ⬇️",
        reply_markup=main_menu
    )


@dp.message_handler(commands=["begin"])
async def ask_which_to_begin(message: types.Message):
    uid = str(message.from_user.id)
    if uid not in user_trackers or not user_trackers[uid]:
        await message.reply("У тебя нет трекеров. Добавь командой /add", reply_markup=main_menu)
        return
    waiting_for_begin[uid] = True
    await message.reply("🏁 Какой трекер запустить?")


@dp.message_handler(commands=["my"])
async def my_trackers(message: types.Message):
    uid = str(message.from_user.id)
    trackers = user_trackers.get(uid, [])

    if not trackers:
        await message.reply("У тебя пока нет трекеров. Добавь командой /add", reply_markup=main_menu)
    else:
        text = "\n".join(f"• {name}" for name in trackers)
        await message.reply("📋 Твои трекеры:\n" + text)


@dp.message_handler(commands=["end"])
async def end_timer(message: types.Message):
    user_id = str(message.from_user.id)

    if user_id not in start_times:
        await message.reply("Ты не запускал таймер. Напиши /begin.", reply_markup=main_menu)
        return

    start_info = start_times[user_id]
    duration = datetime.now() - start_info["start"]
    minutes = duration.seconds // 60
    name = start_info["name"]

    tracker_logs.setdefault(user_id, [])
    tracker_logs[user_id].append({
        "name": name,
        "minutes": minutes,
        "date": str(date.today())
    })
    save_data()

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
            start_times[uid] = {"name": name, "start": datetime.now().isoformat()}
            await message.reply(f"⏱ Засекли «{name}»!")
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
            save_data()
            await message.reply(f"✅ Трекер «{name}» добавлен!")
        waiting_for_tracker_name.pop(uid)

def load_data():
    global user_trackers, start_times, tracker_logs
    try:
        with open("data.json", "r") as f:
            saved = json.load(f)
            user_trackers = saved.get("user_trackers", {})
            start_times = saved.get("start_times", {})
            tracker_logs = saved.get("tracker_logs", {})
    except FileNotFoundError:
        user_trackers = {}
        start_times = {}
        tracker_logs = {}

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

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Бот работает!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    load_data()
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
