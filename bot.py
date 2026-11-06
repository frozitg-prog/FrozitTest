import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Настройки
TOKEN = "9168109636:AAFfWdlp7oauqFKQz33vPgllyvCpWylw71E"
CHANNEL_ID = -1004379579253

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Клавиатура для проверки подписки
sub_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url="https://t.me/FroziTest")],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")]
    ]
)

# Главное меню (доступно только после подписки)
main_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="open_profile")],
        [InlineKeyboardButton(text="⚙️ Функции (в разработке)", callback_data="features")]
    ]
)

# Кнопка возврата в главное меню
back_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
    ]
)


# Функция-помощник для проверки статуса подписки в Telegram
async def is_user_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as error:
        print("Ошибка проверки подписки:", error)
        return False


# Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    
    # Сразу проверяем: если уже подписан, даем меню. Если нет — просим подписаться.
    if await is_user_subscribed(user_id):
        await message.answer(
            f"👋 Добро пожаловать назад, {message.from_user.first_name}!\nВы успешно авторизованы.", 
            reply_markup=main_keyboard
        )
    else:
        await message.answer(
            "Привет! Чтобы продолжить и получить доступ к функциям, подпишись на наш канал 👇",
            reply_markup=sub_keyboard
        )


# Кнопка «Проверить подписку»
@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if await is_user_subscribed(user_id):
        # Меняем текст и выдаем Главное меню
        await callback.message.edit_text(
            f"🎉 Успешно! Спасибо за подписку.\n\nДобро пожаловать в Главное Меню:",
            reply_markup=main_keyboard
        )
    else:
        # Если кликнул, но не подписался — высылаем уведомление (alert) и обновляем меню подписки
        await callback.answer("❌ Вы все еще не подписались на канал!", show_alert=True)
        try:
            await callback.message.edit_text(
                "Ты ещё не подписан на канал! Подпишись, чтобы разблокировать профиль 👇",
                reply_markup=sub_keyboard
            )
        except Exception:
            pass  # Игнорируем ошибку, если текст остался прежним


# Раздел «Профиль»
@dp.callback_query(F.data == "open_profile")
async def open_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Безопасность: проверяем подписку перед открытием профиля
    if not await is_user_subscribed(user_id):
        await callback.answer("🔒 Доступ ограничен. Подпишитесь на канал!", show_alert=True)
        await callback.message.edit_text("Вы отписались от канала. Доступ закрыт 👇", reply_markup=sub_keyboard)
        return

    # Формируем данные профиля
    username = f"@{callback.from_user.username}" if callback.from_user.username else "Не установлен"
    
    profile_text = (
        f"👤 **Ваш профиль:**\n\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"🏷 **Имя:** {callback.from_user.first_name}\n"
        f"🌐 **Юзернейм:** {username}\n"
        f"⭐ **Статус:** VIP (Подписчик канала)"
    )
    
    await callback.message.edit_text(profile_text, reply_markup=back_keyboard, parse_mode="Markdown")
    await callback.answer()


# Раздел «В разработке»
@dp.callback_query(F.data == "features")
async def features_stub(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_user_subscribed(user_id):
        await callback.answer("🔒 Доступ ограничен. Подпишитесь на канал!", show_alert=True)
        await callback.message.edit_text("Вы отписались от канала. Доступ закрыт 👇", reply_markup=sub_keyboard)
        return

    await callback.message.edit_text(
        "⚙️ **Раздел функций**\n\nЗдесь будет находиться полный функционал вашего бота после разработки. Пока что этот раздел наполняется.",
        reply_markup=back_keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


# Возврат в главное меню
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not await is_user_subscribed(user_id):
        await callback.message.edit_text("Вы отписались от канала. Доступ закрыт 👇", reply_markup=sub_keyboard)
        return

    await callback.message.edit_text("📱 **Главное меню:**", reply_markup=main_keyboard, parse_mode="Markdown")
    await callback.answer()


# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
