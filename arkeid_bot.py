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
    waiting_for_desired_car = State()
    waiting_for_contacts = State()
    waiting_for_photos = State()

# ===== ХРАНИЛИЩЕ И МАППИНГ =====
user_data = {}
CONDITIONS = {
    "cond_excellent": "✨ Отличное (без ДТП и неисправностей)",
    "cond_good": "👍 Хорошее (небольшие косметические дефекты)",
    "cond_repair": "🔧 Требует ремонта (есть технические неисправности)"
}

# ===== КЛАВИАТУРА ДЛЯ АДМИНА =====
def get_admin_keyboard():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Связались", callback_data="admin_ok"),
            types.InlineKeyboardButton(text="❌ Отказ", callback_data="admin_no")
        ]
    ])

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
    await state.set_state(TradeInStates.waiting_for_year)

# ===== ШАГ 2: Год =====
@dp.message(TradeInStates.waiting_for_year)
async def process_year(message: types.Message, state: FSMContext):
    clean_text = message.text.strip()
    if not clean_text.isdigit():
        await message.answer("⚠️ Пожалуйста, укажите год выпуска *только цифрами*. Например: 2018", parse_mode="Markdown")
        return
    year = int(clean_text)
    if year < 1950 or year > 2030:
        await message.answer("⚠️ Год кажется нереалистичным. Пожалуйста, укажите корректный год.")
        return

    user_data[message.from_user.id]['year'] = clean_text
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_year")]
    ])
    await message.answer("🛣️ Какой пробег (в км)?", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_mileage)

# ===== ШАГ 3: Пробег =====
@dp.message(TradeInStates.waiting_for_mileage)
async def process_mileage(message: types.Message, state: FSMContext):
    clean_text = message.text.strip().replace(" ", "")
    if not clean_text.isdigit():
        await message.answer("⚠️ Пожалуйста, укажите пробег *только цифрами*. Например: 150000", parse_mode="Markdown")
        return
    mileage = int(clean_text)
    if mileage > 2000000:
        await message.answer("⚠️ Пробег кажется слишком большим. Пожалуйста, проверьте и введите верно.")
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

# ===== ШАГ 4: Состояние =====
@dp.callback_query(TradeInStates.waiting_for_condition, F.data.startswith("cond_"))
async def process_condition_callback(callback: types.CallbackQuery, state: FSMContext):
    user_data[callback.from_user.id]['condition'] = CONDITIONS.get(callback.data, callback.data)
    await callback.answer()
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_condition")]
    ])
    
    await callback.message.answer(
        "🚙 Какой автомобиль вы рассматриваете для покупки взамен?\n"
        "(Укажите марку, модель или просто пожелания)", 
        reply_markup=kb
    )
    await state.set_state(TradeInStates.waiting_for_desired_car)

# ===== ШАГ 5: Желаемый авто =====
@dp.message(TradeInStates.waiting_for_desired_car)
async def process_desired_car(message: types.Message, state: FSMContext):
    user_data[message.from_user.id]['desired_car'] = message.text
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_desired_car")]
    ])
    
    await message.answer("📱 Оставьте номер телефона для связи (например, +79991234567)", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_contacts)

# ===== ШАГ 6: Контакты =====
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
        await message.answer("⚠️ Неверный формат номера. Пожалуйста, введите номер в формате +79991234567 или 89991234567")
        return
        
    user_data[message.from_user.id]['contacts'] = formatted_phone
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_contacts")]
    ])
    
    await message.answer(
        "📸 Отправьте фото автомобиля (можно несколько):\n"
        "• Общий вид спереди и сзади\n"
        "• Салон\n"
        "• Приборная панель с пробегом\n\n"
        "Отправьте первое фото, а кнопка «Готово» будет появляться после каждого фото.",
        reply_markup=kb
    )
    user_data[message.from_user.id]['photos'] = []
    await state.set_state(TradeInStates.waiting_for_photos)

# ===== ШАГ 7: Загрузка фото =====
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

# ===== ШАГ 8: Завершение и отправка админу =====
@dp.callback_query(TradeInStates.waiting_for_photos, F.data == "finish_tradein")
async def finish_tradein_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    data = user_data[user_id]
    
    if not data.get('photos'):
        await callback.message.answer("⚠️ Пожалуйста, загрузите хотя бы одно фото автомобиля")
        return

    application_text = (
        f"🚨 НОВАЯ ЗАЯВКА НА TRADE-IN\n\n"
        f"👤 Клиент: {callback.from_user.full_name}\n"
        f"🔗 Username: @{callback.from_user.username or 'отсутствует'}\n"
        f"🆔 ID: {callback.from_user.id}\n\n"
        f"🚗 ПРОДАЕТ:\n"
        f"• Марка: {data['brand']}\n"
        f"• Год: {data['year']}\n"
        f"• Пробег: {data['mileage']} км\n"
        f"• Состояние: {data['condition']}\n\n"
        f"🚙 ХОЧЕТ КУПИТЬ:\n"
        f"• {data.get('desired_car', 'Не указано')}\n\n"
        f"📞 Контакты: {data['contacts']}\n\n"
        f"📸 Фото: {len(data['photos'])} шт."
    )

    # Отправляем фото админу
    for photo_id in data['photos']:
        await bot.send_photo(ADMIN_CHAT_ID, photo_id)

    # Отправляем текст заявки админу С КНОПКАМИ
    await bot.send_message(
        ADMIN_CHAT_ID, 
        application_text, 
        reply_markup=get_admin_keyboard()
    )

    await callback.message.answer(
        "✅ *Спасибо! Ваша заявка принята.*\n\n"
        "Наш менеджер свяжется с вами в течение 15 минут.\n"
        "ARKEID — быстрый и безопасный выкуп авто!",
        parse_mode="Markdown"
    )

    await state.clear()
    user_data[user_id] = {}

# ===== ОБРАБОТКА КНОПОК АДМИНА =====
@dp.callback_query(F.data.in_({"admin_ok", "admin_no"}))
async def process_admin_actions(callback: types.CallbackQuery):
    # Проверка: нажал ли именно админ?
    if callback.from_user.id != ADMIN_CHAT_ID:
        await callback.answer("⛔ У вас нет прав для этого действия", show_alert=True)
        return

    current_text = callback.message.text
    
    # Определяем новый статус
    if callback.data == "admin_ok":
        status_text = "✅ В РАБОТЕ (Связались)"
    else:
        status_text = "❌ ОТКАЗ"

    # Если статус уже был обновлен, удаляем старую строку, чтобы не дублировать
    if "📊 СТАТУС:" in current_text:
        current_text = current_text.split("📊 СТАТУС:")[0].strip()

    new_text = f"{current_text}\n\n📊 СТАТУС: {status_text}"
    
    # Делаем кнопку неактивной (меняем текст и ставим пустой callback)
    final_kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=status_text, callback_data="admin_done")]
    ])

    await callback.message.edit_text(new_text, reply_markup=final_kb)
    await callback.answer("Статус заявки обновлен!")

# Обработчик для неактивной кнопки (чтобы Telegram не ругался)
@dp.callback_query(F.data == "admin_done")
async def process_admin_done(callback: types.CallbackQuery):
    await callback.answer("Заявка уже обработана")

# ===== НАВИГАЦИЯ "НАЗАД" =====
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
    await callback.message.answer("🚙 Какой автомобиль вы рассматриваете для покупки взамен?", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_desired_car)

@dp.callback_query(F.data == "back_to_contacts")
async def back_to_contacts(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_desired_car")]])
    await callback.message.answer("📱 Оставьте номер телефона для связи (например, +79991234567)", reply_markup=kb)
    await state.set_state(TradeInStates.waiting_for_contacts)

# ===== ОТМЕНА ЗАЯВКИ =====
@dp.callback_query(F.data == "cancel_process")
async def cancel_process(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Заявка отменена")
    await state.clear()
    user_data.pop(callback.from_user.id, None)
    await callback.message.edit_text("❌ Заявка отменена. Если передумаете, просто нажмите /start")

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
