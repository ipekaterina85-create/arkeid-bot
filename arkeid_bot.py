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
ADMIN_CHAT_ID = 435101734
DEFAULT_BASE_PRICE = 1500000

# ===== БАЗА ЦЕН НА 2026 ГОД =====
BRAND_PRICES = {
    # Российские
    "lada": 1100000, "ваз": 1100000, "лада": 1100000, "таз": 900000, "уаз": 1300000,
    # Китайские
    "haval": 2200000, "хавейл": 2200000, "chery": 2100000, "чери": 2100000,
    "geely": 2000000, "джили": 2000000, "changan": 2300000, "чанган": 2300000,
    "exeed": 2800000, "эксид": 2800000, "tank": 3200000, "танк": 3200000,
    "omoda": 1900000, "омода": 1900000, "jaecoo": 2400000, "byd": 2600000, "бид": 2600000,
    "zeekr": 3500000, "зикер": 3500000, "li": 3800000, "ли": 3800000, "voyah": 3300000, "ваях": 3300000,
    # Корейские
    "hyundai": 2100000, "хендай": 2100000, "хюндай": 2100000, "kia": 2200000, "киа": 2200000,
    "genesis": 4500000, "генезис": 4500000,
    # Японские
    "toyota": 2800000, "тойота": 2800000, "honda": 2400000, "хонда": 2400000,
    "nissan": 2300000, "ниссан": 2300000, "mazda": 2500000, "мазда": 2500000,
    "mitsubishi": 2400000, "мицубиси": 2400000, "subaru": 2600000, "субару": 2600000,
    "suzuki": 2000000, "сузуки": 2000000, "infiniti": 3200000, "инфинити": 3200000,
    "acura": 3000000, "акура": 3000000, "lexus": 4200000, "лексус": 4200000,
    # Немецкие
    "volkswagen": 2200000, "фольксваген": 2200000, "ваген": 2200000,
    "skoda": 2100000, "шкода": 2100000, "bmw": 3800000, "бмв": 3800000, "бм": 3800000,
    "mercedes": 4200000, "мерседес": 4200000, "мерс": 4200000, "mercedes-benz": 4200000,
    "audi": 3600000, "ауди": 3600000, "porsche": 7500000, "порше": 7500000,
    "volvo": 3000000, "вольво": 3000000, "opel": 1800000, "опель": 1800000,
    # Американские
    "ford": 2000000, "форд": 2000000, "chevrolet": 2100000, "шевроле": 2100000,
    "jeep": 3500000, "джип": 3500000, "cadillac": 5500000, "кадиллак": 5500000,
    "tesla": 5000000, "тесла": 5000000,
    # Французские
    "renault": 1700000, "рено": 1700000, "peugeot": 1900000, "пежо": 1900000,
    "citroen": 1800000, "ситроен": 1800000,
    # Британские
    "land rover": 5500000, "ленд ровер": 5500000, "range rover": 7000000, "рэйндж ровер": 7000000,
    "ровер": 5500000, "jaguar": 4500000, "ягуар": 4500000, "mini": 2800000, "мини": 2800000,
    "bentley": 15000000, "бентли": 15000000, "rolls-royce": 25000000, "роллс-ройс": 25000000,
    # Итальянские
    "fiat": 1600000, "фиат": 1600000, "lamborghini": 20000000, "ламборгини": 20000000,
    "ferrari": 22000000, "феррари": 22000000, "maserati": 6000000, "мазерати": 6000000,
}

def get_base_price(brand_text: str) -> int:
    brand_lower = brand_text.lower().strip()
    if brand_lower in BRAND_PRICES:
        return BRAND_PRICES[brand_lower]
    for brand_key, price in BRAND_PRICES.items():
        if brand_key in brand_lower:
            return price
    return DEFAULT_BASE_PRICE

def calculate_price(brand, year, mileage, condition):
    base_price = get_base_price(brand)
    age = 2026 - int(year)
    year_coeff = max(0.3, 1.0 - (age * 0.06))
    mileage_coeff = max(0.4, 1.0 - (int(mileage) / 500000))
    cond_map = {"cond_excellent": 1.0, "cond_good": 0.85, "cond_repair": 0.65}
    cond_coeff = cond_map.get(condition, 0.8)
    raw_price = base_price * year_coeff * mileage_coeff * cond_coeff
    min_p = int(raw_price * 0.9)
    max_p = int(raw_price * 1.1)
    return f"{min_p:,}".replace(",", " "), f"{max_p:,}".replace(",", " ")

# ===== ИНИЦИАЛИЗАЦИЯ =====
logging.basicConfig(level=logging.INFO)
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
CONDITIONS = {
    "cond_excellent": "✨ Отличное",
    "cond_good": "👍 Хорошее",
    "cond_repair": "🔧 Требует ремонта"
}

def get_admin_keyboard():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Связались", callback_data="admin_ok"),
            types.InlineKeyboardButton(text="❌ Отказ", callback_data="admin_no")
        ]
    ])

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
    await callback.message.answer(
        "🚙 Какой автомобиль вы рассматриваете для покупки взамен?\n(Укажите марку, модель или пожелания)",
        reply_markup=kb
    )
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
    await message.answer(
        "📸 Отправьте фото автомобиля (можно несколько):\n"
        "• Общий вид спереди и сзади\n• Салон\n• Приборная панель с пробегом\n\n"
        "Кнопка «Готово» будет появляться после каждого фото.",
        reply_markup=kb
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
    kb_finish = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Готово, отправить заявку", callback_data="finish_tradein")]
    ])
    await message.answer(
        f"✅ Фото {photos_count} получено. Отправьте еще или нажмите кнопку ниже.",
        reply_markup=kb_finish
    )

@dp.callback_query(TradeInStates.waiting_for_photos, F.data == "finish_tradein")
async def finish_tradein_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    data = user_data[user_id]
    if not data.get('photos'):
        await callback.message.answer("⚠️ Загрузите хотя бы одно фото")
        return

    min_price, max_price = calculate_price(data['brand'], data['year'], data['mileage'], data['condition'])
    condition_text = CONDITIONS.get(data['condition'], data['condition'])

    client_text = (
        f"✅ *Спасибо! Ваша заявка принята.*\n\n"
        f"💰 *Предварительная оценка вашего авто:*\n"
        f"от {min_price} ₽ до {max_price} ₽\n\n"
        f"⚠️ _Это алгоритмическая оценка на основе средних рыночных данных на 2026 год. Точную стоимость Trade-In наш эксперт назовет после осмотра._\n\n"
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

    await state.clear()
    user_data[user_id] = {}

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
    final_kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=status_text, callback_data="admin_done")]
    ])
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

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
