import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "9178506943:AAHcuXtM6nBgeB29sQGH1VX1OR35QuUUpL8"
CHANNEL_ID = -1003912887034

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


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Привет! чтобы продолжить",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    member = await bot.get_chat_member(
        chat_id=CHANNEL_ID,
        user_id=user_id
    )

    if member.status in ["member", "administrator", "creator"]:
        await callback.message.edit_text(
            "Спасибо за подписку!"
        )
    else:
        await callback.message.edit_text(
            "Ты ещё не подписан не ебень мозги!!!",
            reply_markup=keyboard
        )

    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

