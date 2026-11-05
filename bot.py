import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 1. Настройки
TOKEN = "9168109636:AAFfWdlp7oauqFKQz33vPgllyvCpWylw71E"
CHANNEL_ID = -1004379579253

# 2. Создаём бота
bot = Bot(token=TOKEN)
dp = Dispatcher()


# 3. Создаём кнопки
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


# 4. Обработчик команды START
@dp.message(Command("start"))
async def start(message: types.Message):

    await message.answer(
        "Привет! Чтобы продолжить, подпишись на наш канал 👇",
        reply_markup=keyboard
    )


# 5. Обработчик кнопки проверки
@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: types.CallbackQuery):

    # Получаем ID пользователя
    user_id = callback.from_user.id

    # Проверяем подписку
    member = await bot.get_chat_member(
        chat_id=CHANNEL_ID,
        user_id=user_id
    )

    # Проверяем статус
    if member.status in ["member", "administrator", "creator"]:

        await callback.message.answer(
            "Привет, спасибо за подписку! 🎉"
        )

    else:

        await callback.message.answer(
            "Ты ещё не подписан на канал!\n"
            "Подпишись и попробуй снова.",
            reply_markup=keyboard
        )

    # Подтверждаем нажатие кнопки
    await callback.answer()


# 6. Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
