import asyncio
import logging
import os
import uuid
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import aiosqlite
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.deep_linking import create_start_link, decode_payload

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "streaks.db")
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Europe/Warsaw"))
REMINDER_HOURS = {18: "⏰ До конца дня осталось 6 часов!", 23: "🚨 Остался всего 1 час!"}

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("firestreak")
dp = Dispatcher()


def today() -> date:
    return datetime.now(TIMEZONE).date()


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Мои огоньки", callback_data="my_pairs"),
         InlineKeyboardButton(text="➕ Создать огонёк", callback_data="new_pair")],
        [InlineKeyboardButton(text="🏆 Топ огоньков", callback_data="top_streaks"),
         InlineKeyboardButton(text="📊 Топ активности", callback_data="top_activity")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
         InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])


def pair_keyboard(pair_id: int, checked: bool):
    rows = []
    if not checked:
        rows.append([InlineKeyboardButton(text="✅ Я сегодня написал(а)", callback_data=f"checkin:{pair_id}")])
    rows.append([InlineKeyboardButton(text="🔙 В меню", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY, name TEXT NOT NULL, username TEXT
        );
        CREATE TABLE IF NOT EXISTS invites(
            code TEXT PRIMARY KEY, inviter_id INTEGER NOT NULL, created_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS pairs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1 INTEGER NOT NULL, user2 INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_on TEXT NOT NULL,
            streak INTEGER NOT NULL DEFAULT 0,
            best_streak INTEGER NOT NULL DEFAULT 0,
            last_mutual_day TEXT,
            mutual_days INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user1, user2)
        );
        CREATE TABLE IF NOT EXISTS checkins(
            pair_id INTEGER NOT NULL, user_id INTEGER NOT NULL, day TEXT NOT NULL,
            PRIMARY KEY(pair_id, user_id, day),
            FOREIGN KEY(pair_id) REFERENCES pairs(id)
        );
        CREATE TABLE IF NOT EXISTS reminders(
            pair_id INTEGER NOT NULL, user_id INTEGER NOT NULL, day TEXT NOT NULL, hour INTEGER NOT NULL,
            PRIMARY KEY(pair_id, user_id, day, hour)
        );
        CREATE TABLE IF NOT EXISTS daily_finalized(
            pair_id INTEGER NOT NULL, day TEXT NOT NULL,
            PRIMARY KEY(pair_id, day)
        );
        """)
        await db.commit()


async def save_user(user):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users(user_id,name,username) VALUES(?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET name=excluded.name, username=excluded.username",
            (user.id, user.first_name or "Пользователь", user.username)
        )
        await db.commit()


async def user_name(db, user_id: int) -> str:
    cur = await db.execute("SELECT name FROM users WHERE user_id=?", (user_id,))
    row = await cur.fetchone()
    return row[0] if row else f"ID {user_id}"


async def get_pairs(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM pairs WHERE status='active' AND (user1=? OR user2=?) ORDER BY streak DESC",
            (user_id, user_id)
        )
        return await cur.fetchall()


async def has_checkin(pair_id: int, user_id: int, day: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM checkins WHERE pair_id=? AND user_id=? AND day=?",
            (pair_id, user_id, day)
        )
        return await cur.fetchone() is not None


async def render_pair(bot: Bot, user_id: int, pair):
    other_id = pair["user2"] if pair["user1"] == user_id else pair["user1"]
    async with aiosqlite.connect(DB_PATH) as db:
        other = await user_name(db, other_id)
    day = today().isoformat()
    own = await has_checkin(pair["id"], user_id, day)
    other_checked = await has_checkin(pair["id"], other_id, day)
    status = "✅ Вы отметились" if own else "⏳ Вы ещё не отметились"
    partner = "✅ Друг отметился" if other_checked else "⏳ Друг ещё не отметился"
    text = (
        f"🔥 <b>Огонёк с {other}</b>\n\n"
        f"Текущая серия: <b>{pair['streak']} дн.</b>\n"
        f"Рекорд: <b>{pair['best_streak']} дн.</b>\n\n"
        f"{status}\n{partner}\n\n"
        "Чтобы засчитать день, оба участника должны нажать кнопку до 23:59."
    )
    await bot.send_message(user_id, text, reply_markup=pair_keyboard(pair["id"], own), parse_mode="HTML")


@dp.message(CommandStart())
async def start(message: Message, bot: Bot):
    await save_user(message.from_user)
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        try:
            code = decode_payload(args[1])
        except Exception:
            code = args[1]
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT inviter_id, used FROM invites WHERE code=?", (code,))
            invite = await cur.fetchone()
            if invite and not invite[1] and invite[0] != message.from_user.id:
                inviter_id = invite[0]
                cur = await db.execute(
                    "SELECT 1 FROM pairs WHERE status='active' AND "
                    "((user1=? AND user2=?) OR (user1=? AND user2=?))",
                    (inviter_id, message.from_user.id, message.from_user.id, inviter_id)
                )
                exists = await cur.fetchone()
                if exists:
                    await message.answer("У вас уже есть активный огонёк с этим человеком.", reply_markup=main_menu())
                else:
                    cur = await db.execute("SELECT name FROM users WHERE user_id=?", (inviter_id,))
                    row = await cur.fetchone()
                    inviter_name = row[0] if row else "Пользователь"
                    await message.answer(
                        f"🔥 <b>{inviter_name}</b> приглашает тебя создать огонёк!\n"
                        "Подтверди приглашение, чтобы начать совместную серию.",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔥 Принять приглашение", callback_data=f"accept:{code}")],
                            [InlineKeyboardButton(text="Отклонить", callback_data=f"decline:{code}")]
                        ]), parse_mode="HTML"
                    )
                return
        await message.answer("Это приглашение недействительно или уже использовано.", reply_markup=main_menu())
        return
    await message.answer(
        f"Привет, {message.from_user.first_name}! 🔥\n\n"
        "Создавай огоньки с друзьями, ежедневно подтверждайте активность "
        "и собирайте достижения.\n\n"
        "<i>Важно: Telegram не позволяет обычному боту читать вашу личную переписку. "
        "Поэтому в этой версии каждый участник подтверждает активность кнопкой.</i>",
        reply_markup=main_menu(), parse_mode="HTML"
    )


@dp.callback_query(F.data == "home")
async def home(call: CallbackQuery):
    await call.message.answer("🔥 Главное меню", reply_markup=main_menu())
    await call.answer()


@dp.callback_query(F.data == "new_pair")
async def new_pair(call: CallbackQuery, bot: Bot):
    code = uuid.uuid4().hex[:20]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO invites(code,inviter_id,created_at) VALUES(?,?,?)",
                         (code, call.from_user.id, datetime.now(TIMEZONE).isoformat()))
        await db.commit()
    link = await create_start_link(bot, code, encode=True)
    await call.message.answer(
        "🔥 <b>Приглашение готово!</b>\n\n"
        "Отправь эту ссылку человеку, с которым хочешь создать огонёк. "
        "Когда он примет приглашение, серия будет активирована.\n\n"
        f"<code>{link}</code>",
        parse_mode="HTML"
    )
    await call.answer()


@dp.callback_query(F.data.startswith("accept:"))
async def accept_invite(call: CallbackQuery):
    code = call.data.split(":", 1)[1]
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT inviter_id,used FROM invites WHERE code=?", (code,))
        invite = await cur.fetchone()
        if not invite or invite[1] or invite[0] == call.from_user.id:
            await call.answer("Приглашение недействительно.", show_alert=True)
            return
        a, b = sorted((invite[0], call.from_user.id))
        try:
            await db.execute(
                "INSERT INTO pairs(user1,user2,created_on) VALUES(?,?,?)",
                (a, b, today().isoformat())
            )
        except aiosqlite.IntegrityError:
            pass
        await db.execute("UPDATE invites SET used=1 WHERE code=?", (code,))
        await db.commit()
    await call.message.edit_text("🎉 Огонёк создан! Сегодня каждый из вас должен подтвердить активность.")
    await call.answer("Огонёк активирован!")
    try:
        await call.bot.send_message(invite[0], f"🎉 {call.from_user.first_name} принял(а) приглашение! Ваш огонёк создан.")
    except Exception:
        pass


@dp.callback_query(F.data.startswith("decline:"))
async def decline_invite(call: CallbackQuery):
    await call.message.edit_text("Приглашение отклонено.")
    await call.answer()


@dp.callback_query(F.data == "my_pairs")
async def my_pairs(call: CallbackQuery):
    pairs = await get_pairs(call.from_user.id)
    if not pairs:
        await call.message.answer("Пока нет огоньков. Нажми «Создать огонёк», чтобы пригласить друга.", reply_markup=main_menu())
    else:
        for pair in pairs:
            await render_pair(call.bot, call.from_user.id, pair)
    await call.answer()


@dp.callback_query(F.data.startswith("checkin:"))
async def checkin(call: CallbackQuery):
    pair_id = int(call.data.split(":")[1])
    day = today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM pairs WHERE id=? AND status='active' AND (user1=? OR user2=?)",
            (pair_id, call.from_user.id, call.from_user.id)
        )
        pair = await cur.fetchone()
        if not pair:
            await call.answer("Огонёк не найден.", show_alert=True)
            return
        await db.execute(
            "INSERT OR IGNORE INTO checkins(pair_id,user_id,day) VALUES(?,?,?)",
            (pair_id, call.from_user.id, day)
        )
        cur = await db.execute("SELECT COUNT(DISTINCT user_id) FROM checkins WHERE pair_id=? AND day=?", (pair_id, day))
        count = (await cur.fetchone())[0]
        old_streak = pair["streak"]
        if count == 2 and pair["last_mutual_day"] != day:
            yesterday = (today() - timedelta(days=1)).isoformat()
            new_streak = pair["streak"] + 1 if pair["last_mutual_day"] == yesterday else 1
            best = max(pair["best_streak"], new_streak)
            await db.execute(
                "UPDATE pairs SET streak=?,best_streak=?,last_mutual_day=?,mutual_days=mutual_days+1 WHERE id=?",
                (new_streak, best, day, pair_id)
            )
        await db.commit()
        cur = await db.execute("SELECT * FROM pairs WHERE id=?", (pair_id,))
        pair = await cur.fetchone()
    await call.answer("Активность отмечена! 🔥")
    if count == 2:
        await call.message.answer(f"🔥 Взаимная активность подтверждена! Серия: <b>{pair['streak']} дн.</b>", parse_mode="HTML")
        other = pair["user2"] if pair["user1"] == call.from_user.id else pair["user1"]
        try:
            await call.bot.send_message(other, f"✅ Ваш друг тоже подтвердил активность за сегодня! Серия: {pair['streak']} дн.")
        except Exception:
            pass
        milestones = {10, 30, 50, 100, 200, 300, 400, 500}
        if old_streak < pair["streak"] and pair["streak"] in milestones:
            reward = "🏆 <b>Новое достижение!</b>\n\n"
            reward += f"Вы поддерживаете огонёк уже {pair['streak']} дней! "
            reward += "Новый уровень огонька разблокирован 🔥"
            for uid in (pair["user1"], pair["user2"]):
                try:
                    await call.bot.send_message(uid, reward, parse_mode="HTML")
                except Exception:
                    pass
    else:
        await call.message.answer("⏳ Твоя отметка сохранена. Ждём подтверждение второго участника.")
    await call.message.answer("🔥 Меню огонька", reply_markup=pair_keyboard(pair_id, True))


@dp.callback_query(F.data == "top_streaks")
async def top_streaks(call: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM pairs WHERE status='active' ORDER BY streak DESC,best_streak DESC LIMIT 3")
        rows = await cur.fetchall()
        lines = []
        for i, p in enumerate(rows, 1):
            n1, n2 = await user_name(db, p["user1"]), await user_name(db, p["user2"])
            lines.append(f"{['🥇','🥈','🥉'][i-1]} {n1} + {n2} — 🔥 {p['streak']} дн. (рекорд {p['best_streak']})")
    await call.message.answer("🏆 <b>Топ-3 огоньков</b>\n\n" + ("\n".join(lines) if lines else "Пока рейтинга нет."), parse_mode="HTML", reply_markup=main_menu())
    await call.answer()


@dp.callback_query(F.data == "top_activity")
async def top_activity(call: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM pairs WHERE status='active' ORDER BY mutual_days DESC LIMIT 3")
        rows = await cur.fetchall()
        lines = []
        for i, p in enumerate(rows, 1):
            n1, n2 = await user_name(db, p["user1"]), await user_name(db, p["user2"])
            lines.append(f"{['🥇','🥈','🥉'][i-1]} {n1} + {n2} — {p['mutual_days']} совместных дней")
    await call.message.answer(
        "📊 <b>Топ-3 активности</b>\n\n" + ("\n".join(lines) if lines else "Пока рейтинга нет.") +
        "\n\n<i>Здесь учитываются совместные дни подтверждения, а не реальные сообщения: бот не видит личную переписку.</i>",
        parse_mode="HTML", reply_markup=main_menu()
    )
    await call.answer()


@dp.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):
    pairs = await get_pairs(call.from_user.id)
    best = max((p["best_streak"] for p in pairs), default=0)
    await call.message.answer(
        f"👤 <b>Профиль</b>\n\nИмя: {call.from_user.first_name}\n"
        f"Активных огоньков: {len(pairs)}\nЛучший личный рекорд: {best} дней",
        parse_mode="HTML", reply_markup=main_menu()
    )
    await call.answer()


@dp.callback_query(F.data == "help")
async def help_page(call: CallbackQuery):
    await call.message.answer(
        "❓ <b>Как работают огоньки</b>\n\n"
        "1. Создай приглашение и отправь другу.\n"
        "2. Друг должен принять его.\n"
        "3. Каждый день оба нажимают кнопку подтверждения.\n"
        "4. Если оба отметились до конца календарных суток, серия продолжается.\n"
        "5. Если день пропущен, серия сбрасывается.\n\n"
        "Напоминания отправляются за 6 часов и за 1 час до конца дня. "
        "Достижения открываются на отметках 10, 30, 50, 100, 200, 300, 400 и 500 дней.\n\n"
        "Важно: обычный Telegram-бот не может читать сообщения в личной переписке пользователей.",
        parse_mode="HTML", reply_markup=main_menu()
    )
    await call.answer()


async def notify(bot: Bot, pair, text: str):
    for uid in (pair["user1"], pair["user2"]):
        try:
            await bot.send_message(uid, text)
        except Exception as exc:
            log.info("Cannot notify %s: %s", uid, exc)


async def scheduler(bot: Bot):
    while True:
        now = datetime.now(TIMEZONE)
        day = now.date().isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM pairs WHERE status='active'")
            pairs = await cur.fetchall()
            for pair in pairs:
                cur = await db.execute("SELECT COUNT(DISTINCT user_id) FROM checkins WHERE pair_id=? AND day=?",
                                       (pair["id"], day))
                checked_count = (await cur.fetchone())[0]
                if now.hour in REMINDER_HOURS and checked_count < 2:
                    for uid in (pair["user1"], pair["user2"]):
                        cur = await db.execute(
                            "SELECT 1 FROM checkins WHERE pair_id=? AND user_id=? AND day=?",
                            (pair["id"], uid, day)
                        )
                        already_checked = await cur.fetchone()
                        cur = await db.execute(
                            "SELECT 1 FROM reminders WHERE pair_id=? AND user_id=? AND day=? AND hour=?",
                            (pair["id"], uid, day, now.hour)
                        )
                        already_reminded = await cur.fetchone()
                        if not already_checked and not already_reminded:
                            await db.execute("INSERT OR IGNORE INTO reminders VALUES(?,?,?,?)",
                                             (pair["id"], uid, day, now.hour))
                            try:
                                await bot.send_message(uid, f"{REMINDER_HOURS[now.hour]}\nНе забудь подтвердить активность в огоньке 🔥")
                            except Exception:
                                pass
            await db.commit()

        # После полуночи один раз закрываем предыдущий календарный день.
        if now.hour == 0 and now.minute >= 5:
            yesterday = (now.date() - timedelta(days=1)).isoformat()
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                cur = await db.execute("SELECT * FROM pairs WHERE status='active'")
                all_pairs = await cur.fetchall()
                for pair in all_pairs:
                    cur = await db.execute(
                        "SELECT 1 FROM daily_finalized WHERE pair_id=? AND day=?",
                        (pair["id"], yesterday)
                    )
                    if await cur.fetchone():
                        continue
                    cur = await db.execute(
                        "SELECT COUNT(DISTINCT user_id) FROM checkins WHERE pair_id=? AND day=?",
                        (pair["id"], yesterday)
                    )
                    completed = (await cur.fetchone())[0] == 2
                    if not completed and pair["streak"] > 0:
                        await db.execute("UPDATE pairs SET streak=0 WHERE id=?", (pair["id"],))
                        await notify(bot, pair, "💔 Огонёк погас: за вчерашний день не было двух подтверждений. Можно начать новую серию сегодня.")
                    await db.execute("INSERT OR IGNORE INTO daily_finalized(pair_id,day) VALUES(?,?)",
                                     (pair["id"], yesterday))
                await db.commit()
        await asyncio.sleep(60)


async def main():
    if not TOKEN:
        raise RuntimeError("Укажи BOT_TOKEN в переменных окружения или .env")
    await init_db()
    bot = Bot(TOKEN)
    me = await bot.get_me()
    log.info("Bot started: @%s", me.username)
    asyncio.create_task(scheduler(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
