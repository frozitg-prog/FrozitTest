import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = 9178506943:AAHcuXtM6nBgeB29sQGH1VX1OR35QuUUpL8

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Подпишись на наш канал ❤",
                url="https://t.me/Frizak67"
            )
        ],
        [
            InlineKeyboardButton(
                text="Проверить сабку",
                callback_data="check_sub"
            )
        ]   
    ]
) 

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
