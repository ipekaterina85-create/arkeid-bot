import asyncio
import logging
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "435101734"))
DEFAULT_BASE_PRICE = 1500000

# ===== БАЗА ЦЕН С УЧЁТОМ ГОДА ВЫПУСКА =====
# Формат: "марка": {"диапазон_годов": цена}
BRAND_PRICES = {
    # Российские
    "lada": {"2020-2026": 1800000, "2015-2019": 1200000, "2010-2014": 800000, "2005-2009": 500000, "до_2004": 300000},
    "ваз": {"2020-2026": 1800000, "2015-2019": 1200000, "2010-2014": 800000, "2005-2009": 500000, "до_2004": 300000},
    "уаз": {"2020-2026": 2000000, "2015-2019": 1400000, "2010-2014": 1000000, "2005-2009": 700000, "до_2004": 400000},
    
    # Китайские
    "haval": {"2020-2026": 2800000, "2015-2019": 1800000, "2010-2014": 1200000, "2005-2009": 800000, "до_2004": 500000},
    "хавейл": {"2020-2026": 2800000, "2015-2019": 1800000, "2010-2014": 1200000, "2005-2009": 800000, "до_2004": 500000},
    "chery": {"2020-2026": 2600000, "2015-2019": 1700000, "2010-2014": 1100000, "2005-2009": 700000, "до_2004": 400000},
    "чери": {"2020-2026": 2600000, "2015-2019": 1700000, "2010-2014": 1100000, "2005-2009": 700000, "до_2004": 400000},
    "geely": {"2020-2026": 2500000, "2015-2019": 1600000, "2010-2014": 1000000, "2005-2009": 600000, "до_2004": 350000},
    "джили": {"2020-2026": 2500000, "2015-2019": 1600000, "2010-2014": 1000000, "2005-2009": 600000, "до_2004": 350000},
    "changan": {"2020-2026": 2700000, "2015-2019": 1800000, "2010-2014": 1200000, "2005-2009": 800000, "до_2004": 500000},
    "чанган": {"2020-2026": 2700000, "2015-2019": 1800000, "2010-2014": 1200000, "2005-2009": 800000, "до_2004": 500000},
    "exeed": {"2020-2026": 3200000, "2015-2019": 2200000, "2010-2014": 1500000, "2005-2009": 1000000, "до_2004": 600000},
    "эксид": {"2020-2026": 3200000, "2015-2019": 2200000, "2010-2014": 1500000, "2005-2009": 1000000, "до_2004": 600000},
    "tank": {"2020-2026": 3800000, "2015-2019": 2600000, "2010-2014": 1800000, "2005-2009": 1200000, "до_2004": 700000},
    "танк": {"2020-2026": 3800000, "2015-2019": 2600000, "2010-2014": 1800000, "2005-2009": 1200000, "до_2004": 700000},
    "zeekr": {"2020-2026": 4200000, "2015-2019": 2800000, "2010-2014": 2000000, "2005-2009": 1300000, "до_2004": 800000},
    "зикер": {"2020-2026": 4200000, "2015-2019": 2800000, "2010-2014": 2000000, "2005-2009": 1300000, "до_2004": 800000},
    
    # Корейские
    "hyundai": {"2020-2026": 2600000, "2015-2019": 1800000, "2010-2014": 1200000, "2005-2009": 800000, "до_2004": 500000},
    "хендай": {"2020-2026": 2600000, "2015-2019": 1800000, "2010-2014": 1200000, "2005-2009": 800000, "до_2004": 500000},
    "kia": {"2020-2026": 2700000, "2015-2019": 1900000, "2010-2014": 1300000, "2005-2009": 850000, "до_2004": 550000},
    "киа": {"2020-2026": 2700000, "2015-2019": 1900000, "2010-2014": 1300000, "2005-2009": 850000, "до_2004": 550000},
    "genesis": {"2020-2026": 5200000, "2015-2019": 3800000, "2010-2014": 2600000, "2005-2009": 1800000, "до_2004": 1100000},
    "генезис": {"2020-2026": 5200000, "2015-2019": 3800000, "2010-2014": 2600000, "2005-2009": 1800000, "до_2004": 1100000},
    
    # Японские
    "toyota": {"2020-2026": 3500000, "2015-2019": 2400000, "2010-2014": 1600000, "2005-2009": 1100000, "до_2004": 700000},
    "тойота": {"2020-2026": 3500000, "2015-2019": 2400000, "2010-2014": 1600000, "2005-2009": 1100000, "до_2004": 700000},
    "honda": {"2020-2026": 3000000, "2015-2019": 2100000, "2010-2014": 1400000, "2005-2009": 950000, "до_2004": 600000},
    "хонда": {"2020-2026": 3000000, "2015-2019": 2100000, "2010-2014": 1400000, "2005-2009": 950000, "до_2004": 600000},
    "nissan": {"2020-2026": 2900000, "2015-2019": 2000000, "2010-2014": 1350000, "2005-2009": 900000, "до_2004": 550000},
    "ниссан": {"2020-2026": 2900000, "2015-2019": 2000000, "2010-2014": 1350000, "2005-2009": 900000, "до_2004": 550000},
    "mazda": {"2020-2026": 3100000, "2015-2019": 2200000, "2010-2014": 1450000, "2005-2009": 1000000, "до_2004": 600000},
    "мазда": {"2020-2026": 3100000, "2015-2019": 2200000, "2010-2014": 1450000, "2005-2009": 1000000, "до_2004": 600000},
    "mitsubishi": {"2020-2026": 3000000, "2015-2019": 2100000, "2010-2014": 1400000, "2005-2009": 950000, "до_2004": 600000},
    "мицубиси": {"2020-2026": 3000000, "2015-2019": 2100000, "2010-2014": 1400000, "2005-2009": 950000, "до_2004": 600000},
    "subaru": {"2020-2026": 3200000, "2015-2019": 2300000, "2010-2014": 1500000, "2005-2009": 1050000, "до_2004": 650000},
    "субару": {"2020-2026": 3200000, "2015-2019": 2300000, "2010-2014": 1500000, "2005-2009": 1050000, "до_2004": 650000},
    "lexus": {"2020-2026": 5000000, "2015-2019": 3500000, "2010-2014": 2400000, "2005-2009": 1600000, "до_2004": 1000000},
    "лексус": {"2020-2026": 5000000, "2015-2019": 3500000, "2010-2014": 2400000, "2005-2009": 1600000, "до_2004": 1000000},
    
    # Немецкие
    "volkswagen": {"2020-2026": 2800000, "2015-2019": 1900000, "2010-2014": 1300000, "2005-2009": 850000, "до_2004": 550000},
    "фольксваген": {"2020-2026": 2800000, "2015-2019": 1900000, "2010-2014": 1300000, "2005-2009": 850000, "до_2004": 550000},
    "skoda": {"2020-2026": 2700000, "2015-2019": 1850000, "2010-2014": 1250000, "2005-2009": 800000, "до_2004": 500000},
    "шкода": {"2020-2026": 2700000, "2015-2019": 1850000, "2010-2014": 1250000, "2005-2009": 800000, "до_2004": 500000},
    "bmw": {"2020-2026": 4500000, "2015-2019": 3200000, "2010-2014": 2200000, "2005-2009": 1500000, "до_2004": 900000},
    "бмв": {"2020-2026": 4500000, "2015-2019": 3200000, "2010-2014": 2200000, "2005-2009": 1500000, "до_2004": 900000},
    "бм": {"2020-2026": 4500000, "2015-2019": 3200000, "2010-2014": 2200000, "2005-2009": 1500000, "до_2004": 900000},
    "mercedes": {"2020-2026": 5000000, "2015-2019": 3600000, "2010-2014": 2500000, "2005-2009": 1700000, "до_2004": 1050000},
    "мерседес": {"2020-2026": 5000000, "2015-2019": 3600000, "2010-2014": 2500000, "2005-2009": 1700000, "до_2004": 1050000},
    "audi": {"2020-2026": 4300000, "2015-2019": 3100000, "2010-2014": 2100000, "2005-2009": 1450000, "до_2004": 850000},
    "ауди": {"2020-2026": 4300000, "2015-2019": 3100000, "2010-2014": 2100000, "2005-2009": 1450000, "до_2004": 850000},
    "porsche": {"2020-2026": 8500000, "2015-2019": 6200000, "2010-2014": 4200000, "2005-2009": 2900000, "до_2004": 1800000},
    "порше": {"2020-2026": 8500000, "2015-2019": 6200000, "2010-2014": 4200000, "2005-2009": 2900000, "до_2004": 1800000},
    "volvo": {"2020-2026": 3600000, "2015-2019": 2600000, "2010-2014": 1750000, "2005-2009": 1200000, "до_2004": 750000},
    "вольво": {"2020-2026": 3600000, "2015-2019": 2600000, "2010-2014": 1750000, "2005-2009": 1200000, "до_2004": 750000},
    
    # Американские
    "ford": {"2020-2026": 2500000, "2015-2019": 1750000, "2010-2014": 1200000, "2005-2009": 800000, "до_2004": 500000},
    "форд": {"2020-2026": 2500000, "2015-2019": 1750000, "2010-2014": 1200000, "2005-2009": 800000, "до_2004": 500000},
    "chevrolet": {"2020-2026": 2600000, "2015-2019": 1800000, "2010-2014": 1250000, "2005-2009": 850000, "до_2004": 550000},
    "шевроле": {"2020-2026": 2600000, "2015-2019": 1800000, "2010-2014": 1250000, "2005-2009": 850000, "до_2004": 550000},
    "jeep": {"2020-2026": 4200000, "2015-2019": 3000000, "2010-2014": 2050000, "2005-2009": 1400000, "до_2004": 850000},
    "джип": {"2020-2026": 4200000, "2015-2019": 3000000, "2010-2014": 2050000, "2005-2009": 1400000, "до_2004": 850000},
    "tesla": {"2020-2026": 6000000, "2015-2019": 4300000, "2010-2014": 3000000, "2005-2009": 2000000, "до_2004": 1200000},
    "тесла": {"2020-2026": 6000000, "2015-2019": 4300000, "2010-2014": 3000000, "2005-2009": 2000000, "до_2004": 1200000},
    
    # Французские
    "renault": {"2020-2026": 2100000, "2015-2019": 1450000, "2010-2014": 1000000, "2005-2009": 650000, "до_2004": 400000},
    "рено": {"2020-2026": 2100000, "2015-2019": 1450000, "2010-2014": 1000000, "2005-2009": 650000, "до_2004": 400000},
    "peugeot": {"2020-2026": 2300000, "2015-2019": 1600000, "2010-2014": 1100000, "2005-2009": 700000, "до_2004": 450000},
    "пежо": {"2020-2026": 2300000, "2015-2019": 1600000, "2010-2014": 1100000, "2005-2009": 700000, "до_2004": 450000},
    "citroen": {"2020-2026": 2200000, "2015-2019": 1550000, "2010-2014": 1050000, "2005-2009": 680000, "до_2004": 420000},
    "ситроен": {"2020-2026": 2200000, "2015-2019": 1550000, "2010-2014": 1050000, "2005-2009": 680000, "до_2004": 420000},
    
    # Британские
    "land rover": {"2020-2026": 6500000, "2015-2019": 4700000, "2010-2014": 3200000, "2005-2009": 2200000, "до_2004": 1300000},
    "ленд ровер": {"2020-2026": 6500000, "2015-2019": 4700000, "2010-2014": 3200000, "2005-2009": 2200000, "до_2004": 1300000},
    "range rover": {"2020-2026": 8200000, "2015-2019": 5900000, "2010-2014": 4000000, "2005-2009": 2800000, "до_2004": 1700000},
    "рэйндж ровер": {"2020-2026": 8200000, "2015-2019": 5900000, "2010-2014": 4000000, "2005-2009": 2800000, "до_2004": 1700000},
    "jaguar": {"2020-2026": 5300000, "2015-2019": 3800000, "2010-2014": 2600000, "2005-2009": 1800000, "до_2004": 1100000},
    "ягуар": {"2020-2026": 5300000, "2015-2019": 3800000, "2010-2014": 2600000, "2005-2009": 1800000, "до_2004": 1100000},
    
    # Итальянские
    "lamborghini": {"2020-2026": 25000000, "2015-2019": 18000000, "2010-2014": 12500000, "2005-2009": 8500000, "до_2004": 5500000},
    "ламборгини": {"2020-2026": 25000000, "2015-2019": 18000000, "2010-2014": 12500000, "2005-2009": 8500000, "до_2004": 5500000},
    "ferrari": {"2020-2026": 28000000, "2015-2019": 20000000, "2010-2014": 14000000, "2005-2009": 9500000, "до_2004": 6000000},
    "феррари": {"2020-2026": 28000000, "2015-2019": 20000000, "2010-2014": 14000000, "2005-2009": 9500000, "до_2004": 6000000},
}

# ===== ФУНКЦИЯ ПОИСКА БАЗОВОЙ ЦЕНЫ С УЧЁТОМ ГОДА =====
def get_base_price(brand_text: str, year: int) -> int:
    """
    Ищет марку в словаре и возвращает цену для соответствующего диапазона годов.
    Примеры:
    - get_base_price("BMW", 2013) → 2200000 (диапазон 2010-2014)
    - get_base_price("Toyota", 2020) → 3500000 (диапазон 2020-2026)
    """
    brand_lower = brand_text.lower().strip()
    
    # Определяем диапазон годов
    if year >= 2020:
        year_range = "2020-2026"
    elif year >= 2015:
        year_range = "2015-2019"
    elif year >= 2010:
        year_range = "2010-2014"
    elif year >= 2005:
        year_range = "2005-2009"
    else:
        year_range = "до_2004"
    
    # 1. Точное совпадение марки
    if brand_lower in BRAND_PRICES:
        return BRAND_PRICES[brand_lower].get(year_range, DEFAULT_BASE_PRICE)
    
    # 2. Частичное совпадение (например, "BMW X5" → "bmw")
    for brand_key, prices in BRAND_PRICES.items():
        if brand_key in brand_lower:
            return prices.get(year_range, DEFAULT_BASE_PRICE)
    
    # 3. Если ничего не нашли
    return DEFAULT_BASE_PRICE

# ===== УПРОЩЁННАЯ ФУНКЦИЯ РАСЧЕТА СТОИМОСТИ =====
def calculate_price(brand, year, mileage, condition):
    # Базовая цена уже учитывает год выпуска
    base_price = get_base_price(brand, int(year))
    
    # Коэффициент пробега (теряет цену с пробегом, минимум 50% от базы)
    mileage_coeff = max(0.5, 1.0 - (int(mileage) / 600000))
    
    # Коэффициент состояния
    cond_map = {"cond_excellent": 1.0, "cond_good": 0.85, "cond_repair": 0.65}
    cond_coeff = cond_map.get(condition, 0.8)
    
    # Итоговая цена
    raw_price = base_price * mileage_coeff * cond_coeff
    
    # Диапазон +/- 10%
    min_p = int(raw_price * 0.9)
    max_p = int(raw_price * 1.1)
    
    return f"{min_p:,}".replace(",", " "), f"{max_p:,}".replace(",", " ")

# ===== ИНИЦИАЛИЗАЦИЯ =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class TradeInStates(StatesGroup):
    waiting_for_brand = State()
    waiting_for_year = State()
    waiting_for_mileage = State()
    waiting_for_condition = State()
    waiting_for_desired_car = State()
    waiting_for_contacts = State()
    waiting_for_photos = State()

user_data = {}
CONDITIONS = {"cond_excellent": "✨ Отличное", "cond_good": "👍 Хорошее", "cond_repair": "🔧 Требует ремонта"}

def get_admin_keyboard():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Связались", callback_data="admin_ok"),
         types.InlineKeyboardButton(text="❌ Отказ", callback_data="admin_no")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_data[message.from_user.id] = {}
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_process")]])
    await message.answer("🚗 *Trade-In от ARKEID*\n\nХотите быстро и выгодно продать свой автомобиль?\nЗаполните короткую анкету, и наш менеджер свяжется с вами в течение 15 минут!\n\nНачнем? Какая *марка и модель* вашего авто?", parse_mode="Markdown", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_brand)

@dp.message(TradeInStates.waiting_for_brand)
async def process_brand(message: types.Message, state: FSMContext):
    user_data[message.from_user.id]['brand'] = message.text
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_brand")]])
    await message.answer("📅 Какой год выпуска?", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_year)

@dp.message(TradeInStates.waiting_for_year)
async def process_year(message: types.Message, state: FSMContext):
    clean_text = message.text.strip()
    if not clean_text.isdigit():
        await message.answer("⚠️ Укажите год выпуска *только цифрами*. Например: 2018", parse_mode="Markdown")
        return
    year = int(clean_text)
    if year < 1950 or year > 2030:
        await message.answer("⚠️ Год кажется нереалистичным. Укажите корректный год.")
        return
    user_data[message.from_user.id]['year'] = clean_text
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_year")]])
    await message.answer("🛣️ Какой пробег (в км)?", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_mileage)

@dp.message(TradeInStates.waiting_for_mileage)
async def process_mileage(message: types.Message, state: FSMContext):
    clean_text = message.text.strip().replace(" ", "")
    if not clean_text.isdigit():
        await message.answer("⚠️ Укажите пробег *только цифрами*. Например: 150000", parse_mode="Markdown")
        return
    mileage = int(clean_text)
    if mileage > 2000000:
        await message.answer("⚠️ Пробег слишком большой. Проверьте и введите верно.")
        return
    user_data[message.from_user.id]['mileage'] = clean_text
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✨ Отличное", callback_data="cond_excellent")],
        [types.InlineKeyboardButton(text="👍 Хорошее", callback_data="cond_good")],
        [types.InlineKeyboardButton(text="🔧 Требует ремонта", callback_data="cond_repair")],
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_mileage")]
    ])
    await message.answer("🔧 Оцените состояние авто:", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_condition)

@dp.callback_query(TradeInStates.waiting_for_condition, F.data.startswith("cond_"))
async def process_condition_callback(callback: types.CallbackQuery, state: FSMContext):
    user_data[callback.from_user.id]['condition'] = callback.data
    await callback.answer()
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_condition")]])
    await callback.message.answer("🚙 Какой автомобиль вы рассматриваете для покупки взамен?\n(Укажите марку, модель или пожелания)", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_desired_car)

@dp.message(TradeInStates.waiting_for_desired_car)
async def process_desired_car(message: types.Message, state: FSMContext):
    user_data[message.from_user.id]['desired_car'] = message.text
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_desired_car")]])
    await message.answer("📱 Оставьте номер телефона (например, +79991234567)", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_contacts)

@dp.message(TradeInStates.waiting_for_contacts)
async def process_contacts(message: types.Message, state: FSMContext):
    clean_phone = re.sub(r'[^\d+]', '', message.text.strip())
    digits = clean_phone.replace('+', '')
    if len(digits) == 11 and digits.startswith('8'):
        formatted_phone = '+7' + digits[1:]
    elif len(digits) == 11 and digits.startswith('7'):
        formatted_phone = '+' + digits
    elif 10 <= len(digits) <= 15:
        formatted_phone = clean_phone if clean_phone.startswith('+') else '+' + digits
    else:
        await message.answer("⚠️ Неверный формат. Введите номер в формате +79991234567 или 89991234567")
        return
    user_data[message.from_user.id]['contacts'] = formatted_phone
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_contacts")]])
    await message.answer("📸 Отправьте фото автомобиля (можно несколько):\n• Общий вид спереди и сзади\n• Салон\n• Приборная панель с пробегом\n\nКнопка «Готово» будет появляться после каждого фото.", reply_markup=kb)
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
    kb_finish = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Готово, отправить заявку", callback_data="finish")]
    ])
    await message.answer(f"✅ Фото {photos_count} получено. Отправьте еще или нажмите кнопку ниже.", reply_markup=kb_finish)

@dp.callback_query(TradeInStates.waiting_for_photos, F.data == "finish")
async def finish_tradein_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    data = user_data[user_id]

    if not data.get('photos'):
        await callback.message.answer("⚠️ Загрузите хотя бы одно фото")
        return

    try:
        min_price, max_price = calculate_price(data['brand'], data['year'], data['mileage'], data['condition'])
        condition_text = CONDITIONS.get(data['condition'], data['condition'])

        client_text = (
            f"✅ *Спасибо! Ваша заявка принята.*\n\n"
            f"💰 *Предварительная оценка вашего авто:*\n"
            f"от {min_price} ₽ до {max_price} ₽\n\n"
            f"⚠️ _Это алгоритмическая оценка на основе средних рыночных данных. Точную стоимость Trade-In наш эксперт назовет после осмотра._\n\n"
            f"Наш менеджер свяжется с вами в течение 15 минут.\n"
            f"ARKEID — быстрый и безопасный выкуп авто!"
        )

        application_text = (
            f"🚨 НОВАЯ ЗАЯВКА НА TRADE-IN\n\n"
            f"👤 Клиент: {callback.from_user.full_name}\n"
            f"🔗 Username: @{callback.from_user.username or 'отсутствует'}\n"
            f"🆔 ID: {callback.from_user.id}\n\n"
            f"🚗 ПРОДАЕТ:\n"
            f"• Марка: {data['brand']}\n"
            f"• Год: {data['year']}\n"
            f"• Пробег: {data['mileage']} км\n"
            f"• Состояние: {condition_text}\n\n"
            f"🚙 ХОЧЕТ КУПИТЬ:\n"
            f"• {data.get('desired_car', 'Не указано')}\n\n"
            f"📞 Контакты: {data['contacts']}\n"
            f"📸 Фото: {len(data['photos'])} шт.\n\n"
            f"💰 ОЦЕНКА БОТА: {min_price} - {max_price} ₽"
        )

        for photo_id in data['photos']:
            await bot.send_photo(ADMIN_CHAT_ID, photo_id)
        await bot.send_message(ADMIN_CHAT_ID, application_text, reply_markup=get_admin_keyboard())
        await callback.message.answer(client_text, parse_mode="Markdown")
        logging.info(f"✅ Заявка успешно отправлена от пользователя {user_id}")

    except Exception as e:
        logging.error(f"❌ ОТПРАВКА ЗАЯВКИ УПАЛА: {e}")
        await callback.message.answer("⚠️ Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже.")
        return

    finally:
        await state.clear()
        user_data.pop(user_id, None)

@dp.callback_query(F.data.in_({"admin_ok", "admin_no"}))
async def process_admin_actions(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_CHAT_ID:
        await callback.answer("⛔ У вас нет прав", show_alert=True)
        return
    current_text = callback.message.text
    status_text = "✅ В РАБОТЕ (Связались)" if callback.data == "admin_ok" else "❌ ОТКАЗ"
    if "📊 СТАТУС:" in current_text:
        current_text = current_text.split("📊 СТАТУС:")[0].strip()
    new_text = f"{current_text}\n\n📊 СТАТУС: {status_text}"
    final_kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=status_text, callback_data="admin_done")]])
    await callback.message.edit_text(new_text, reply_markup=final_kb)
    await callback.answer("Статус обновлен!")

@dp.callback_query(F.data == "admin_done")
async def process_admin_done(callback: types.CallbackQuery):
    await callback.answer("Заявка уже обработана")

@dp.callback_query(F.data == "back_to_brand")
async def back_to_brand(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("🚗 Какая *марка и модель* вашего авто?", parse_mode="Markdown")
    await state.set_state(TradeInStates.waiting_for_brand)

@dp.callback_query(F.data == "back_to_year")
async def back_to_year(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_brand")]])
    await callback.message.answer("📅 Какой год выпуска?", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_year)

@dp.callback_query(F.data == "back_to_mileage")
async def back_to_mileage(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_year")]])
    await callback.message.answer("🛣️ Какой пробег (в км)?", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_mileage)

@dp.callback_query(F.data == "back_to_condition")
async def back_to_condition(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✨ Отличное", callback_data="cond_excellent")],
        [types.InlineKeyboardButton(text="👍 Хорошее", callback_data="cond_good")],
        [types.InlineKeyboardButton(text="🔧 Требует ремонта", callback_data="cond_repair")],
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_mileage")]
    ])
    await callback.message.answer("🔧 Оцените состояние авто:", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_condition)

@dp.callback_query(F.data == "back_to_desired_car")
async def back_to_desired_car(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_condition")]])
    await callback.message.answer("🚙 Какой автомобиль рассматриваете для покупки взамен?", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_desired_car)

@dp.callback_query(F.data == "back_to_contacts")
async def back_to_contacts(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_desired_car")]])
    await callback.message.answer("📱 Оставьте номер телефона", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_contacts)

@dp.callback_query(F.data == "cancel_process")
async def cancel_process(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Заявка отменена")
    await state.clear()
    user_data.pop(callback.from_user.id, None)
    await callback.message.edit_text("❌ Заявка отменена. Нажмите /start, если передумаете")
# ===== ЗАЩИТА ОТ УСТАРЕВШИХ КНОПОК =====
@dp.callback_query()
async def unknown_callback(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "⚠️ Эта кнопка устарела. Пожалуйста, начните заново: нажмите /start"
    )
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
