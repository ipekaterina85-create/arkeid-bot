import asyncio
import logging
import os  # <-- Добавили для чтения переменных окружения
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ===== НАСТРОЙКИ =====
# Токен теперь берется из переменных окружения Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = 435101734

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

# ===== ХРАНИЛИЩЕ И МАППИНГ =====
user_data = {}
CONDITIONS = {
    "cond_excellent": "✨ Отличное (без ДТП и неисправностей)",
    "cond_good": "👍 Хорошее (небольшие косметические дефекты)",
    "cond_repair": "🔧 Требует ремонта (есть технические неисправности)"
}

# ===== КОМАНДА /start =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_data[message.from_user.id] = {}
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_process")]
    ])
    
    await message.answer(
        "🚗 *Trade-In от ARKEID*\n\n"
        "Хотите быстро и выгодно продать свой автомобиль?\n"
        "Заполните короткую анкету, и наш менеджер свяжется с вами в течение 15 минут!\n\n"
        "Начнем? Какая *марка и модель* вашего авто?",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await state.set_state(TradeInStates.waiting_for_brand)

# ===== ШАГ 1: Марка =====
@dp.message(TradeInStates.waiting_for_brand)
async def process_brand(message: types.Message, state: FSMContext):
    user_data[message.from_user.id]['brand'] = message.text
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_brand")]
    ])
    await message.answer("📅 Какой год выпуска?", reply_markup=kb)
    await state.set_state(
