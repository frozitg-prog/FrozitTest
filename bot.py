import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STICKER_FILE_ID = os.getenv("STICKER_FILE_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN. Добавь токен в файл .env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: Message, bot: Bot) -> None:
    user = message.from_user
    name = user.first_name if user else "друг"

    # Сначала отправляем приветствие.
    await message.answer(
        f"Привет, {name}, рады тебя видеть! ♡"
    )

    # Настоящий анимированный стикер отправляется по Telegram file_id.
    # Укажи его в STICKER_FILE_ID в .env.
    if STICKER_FILE_ID:
        try:
            await bot.send_sticker(
                chat_id=message.chat.id,
                sticker=STICKER_FILE_ID,
            )
        except Exception:
            logger.exception("Не удалось отправить стикер")
            await message.answer("💗")
    else:
        await message.answer(
            "💗\nДобавь file_id анимированного сердечка в STICKER_FILE_ID, "
            "чтобы бот отправлял стикер."
        )


@dp.message(F.sticker)
async def sticker_id_handler(message: Message) -> None:
    """Показывает file_id присланного стикера для настройки .env."""
    sticker = message.sticker
    await message.answer(
        "Вот file_id этого стикера. Скопируй его в .env в переменную "
        "STICKER_FILE_ID:\n\n"
        f"<code>{sticker.file_id}</code>",
        parse_mode="HTML",
    )


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
