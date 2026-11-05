import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Настройки
TOKEN = "9168109636:AAFfWdlp7oauqFKQz33vPgllyvCpWylw71E"
CHANNEL_ID = -1004379579253

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Кнопки
keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📢 Подписаться",
                url="https://t.me/FroziTest"
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Проверить подписку",
                callback_data="check_sub"
            )
        ]
    ]
)


# Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Привет! Чтобы продолжить, подпишись на канал 👇",
        reply_markup=keyboard
    )


# Проверка подписки
@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    try:
        member = await bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )

    except Exception as error:
        print("Ошибка:", error)

        await callback.message.answer(
            "Не удалось проверить подписку. Попробуй позже."
        )
        await callback.answer()
        return

    if member.status in ["member", "administrator", "creator"]:
        await callback.message.edit_text(
            "Спасибо за подписку!"
        )
    else:
        await callback.message.edit_text(
            "Ты ещё не подписан на канал!",
            reply_markup=keyboard
        )

    await callback.answer()


# Запуск бота
async def main():
    await dp.start_polling(bot)


asyncio.run(main())
