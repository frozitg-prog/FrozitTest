import asyncio
import html
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CUSTOM_EMOJI_ID = "5368324170671202286"

if not BOT_TOKEN:

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    user = message.from_user
    name = html.escape(user.first_name if user else "друг")

keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Привет, подпишитесь на наш тг-канал",
                url="https://t.me/Frizak67"

async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    try:
        me = await bot.get_me()
        logger.info("Бот запущен: @%s", me.username)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
