import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Railway сам подставит токен из переменных
ADMIN_CHAT_ID = 435101734  # Твой Telegram ID

# ===== ИНИЦИАЛИЗАЦИЯ =====
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ===== СОСТОЯНИЯ (FSM) =====
class TradeInStates(StatesGroup):
    waiting_for_brand = State()
    waiting_for_year = State()
    waiting_for_mileage = State()
    waiting_for_condition = State()
    waiting_for_contacts = State()
    waiting_for_photos = State()

# ===== ХРАНИЛИЩЕ ДАННЫХ =====
user_data = {}

# ===== КОМАНДА /start =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_data[message.from_user.id] = {}
    await message.answer(
        "🚗 *Trade-In от ARKEID*\n\n"
        "Хотите быстро и выгодно продать свой автомобиль?\n"
        "Заполните короткую анкету, и наш менеджер свяжется с вами в течение 15 минут!\n\n"
        "Начнем? Какая *марка и модель* вашего авто?",
        parse_mode="Markdown"
    )
    await state.set_state(TradeInStates.waiting_for_brand)

@dp.message(TradeInStates.waiting_for_brand)
async def process_brand(message: types.Message, state: FSMContext):
    user_data[message.from_user.id]['brand'] = message.text
    await message.answer("📅 Какой год выпуска?")
    await state.set_state(TradeInStates.waiting_for_year)

@dp.message(TradeInStates.waiting_for_year)
async def process_year(message: types.Message, state: FSMContext):
    user_data[message.from_user.id]['year'] = message.text
    await message.answer("🛣️ Какой пробег (в км)?")
    await state.set_state(TradeInStates.waiting_for_mileage)

@dp.message(TradeInStates.waiting_for_mileage)
async def process_mileage(message: types.Message, state: FSMContext):
    user_data[message.from_user.id]['mileage'] = message.text
    await message.answer(
        "🔧 Опишите состояние авто:\n"
        "• Были ли ДТП?\n"
        "• Есть ли технические неисправности?\n"
        "• В каком состоянии салон и кузов?"
    )
    await state.set_state(TradeInStates.waiting_for_condition)

@dp.message(TradeInStates.waiting_for_condition)
async def process_condition(message: types.Message, state: FSMContext):
    user_data[message.from_user.id]['condition'] = message.text
    await message.answer("📱 Оставьте контакты для связи (телефон или @username)")
    await state.set_state(TradeInStates.waiting_for_contacts)

@dp.message(TradeInStates.waiting_for_contacts)
async def process_contacts(message: types.Message, state: FSMContext):
    user_data[message.from_user.id]['contacts'] = message.text
    await message.answer(
        "📸 Отправьте 3-5 фото автомобиля:\n"
        "• Общий вид спереди и сзади\n"
        "• Салон\n"
        "• Приборная панель с пробегом\n\n"
        "Когда загрузите все фото, нажмите кнопку ✅ Готово",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="✅ Готово")]],
            resize_keyboard=True
        )
    )
    user_data[message.from_user.id]['photos'] = []
    await state.set_state(TradeInStates.waiting_for_photos)

@dp.message(TradeInStates.waiting_for_photos, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if 'photos' not in user_data[user_id]:
        user_data[user_id]['photos'] = []
    
    photo = message.photo[-1]
    user_data[user_id]['photos'].append(photo.file_id)

    photos_count = len(user_data[user_id]['photos'])
    await message.answer(f"✅ Фото {photos_count} получено. Отправьте еще или нажмите Готово")

@dp.message(TradeInStates.waiting_for_photos, F.text == "✅ Готово")
async def finish_trade_in(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = user_data[user_id]
    
    if not data.get('photos'):
        await message.answer("⚠️ Пожалуйста, загрузите хотя бы одно фото автомобиля")
        return

    application_text = (
        f"🚨 НОВАЯ ЗАЯВКА НА TRADE-IN\n\n"
        f"👤 Клиент: {message.from_user.full_name}\n"
        f"🔗 Username: @{message.from_user.username or 'отсутствует'}\n"
        f"🆔 ID: {message.from_user.id}\n\n"
        f"🚗 АВТО:\n"
        f"• Марка: {data['brand']}\n"
        f"• Год: {data['year']}\n"
        f"• Пробег: {data['mileage']} км\n"
        f"• Состояние: {data['condition']}\n\n"
        f"📞 Контакты: {data['contacts']}\n\n"
        f"📸 Фото: {len(data['photos'])} шт."
    )

    await bot.send_message(ADMIN_CHAT_ID, application_text)

    for photo_id in data['photos']:
        await bot.send_photo(ADMIN_CHAT_ID, photo_id)

    await message.answer(
        "✅ *Спасибо! Ваша заявка принята.*\n\n"
        "Наш менеджер свяжется с вами в течение 15 минут.\n"
        "ARKEID — быстрый и безопасный выкуп авто!",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )

    await state.clear()
    user_data[user_id] = {}

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
