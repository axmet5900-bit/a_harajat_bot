import os
import asyncio
import logging
from datetime import datetime, timedelta
import io
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from database import db
from utils import *
from keyboards import *
from config import config

load_dotenv()
TOKEN = config.BOT_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== STATES ==========

class TransactionStates(StatesGroup):
    waiting_amount = State()
    waiting_category = State()
    waiting_description = State()
    waiting_person = State()
    waiting_pin = State()

# ========== HANDLERS ==========

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    await message.answer(
        "👋 <b>Smart Wallet Botga xush kelibsiz!</b>\n\n"
        "💰 Barcha moliyaviy operatsiyalaringizni bir joyda boshqaring.\n\n"
        "📌 <b>Asosiy funksiyalar:</b>\n"
        "• Daromad/xarajatlarni kiritish\n"
        "• Kategoriyalar bo'yicha tahlil\n"
        "• Oylik hisobotlar\n"
        "• Byudjet rejalashtirish\n"
        "• To'lov eslatmalari\n"
        "• Qarzlar hisobi\n"
        "• Bank kartalarini ulash\n"
        "• Valyuta kurslari\n"
        "• Cheklarni suratga olish\n"
        "• Ovozli buyruqlar\n\n"
        "📊 <b>Buyruqlar:</b>\n"
        "/menu - Asosiy menyu\n"
        "/stats - Statistika\n"
        "/report - Hisobot\n"
        "/debts - Qarzlar\n"
        "/cards - Kartalar\n"
        "/settings - Sozlamalar",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await message.answer("Asosiy menyu:", reply_markup=get_main_keyboard())

@dp.message(F.text == "💰 Daromad")
async def add_income(message: types.Message, state: FSMContext):
    await state.set_state(TransactionStates.waiting_amount)
    await state.update_data(type='income')
    await message.answer(
        "💰 Daromad summasini kiriting:",
        reply_markup=get_cancel_keyboard()
    )

@dp.message(F.text == "💸 Xarajat")
async def add_expense(message: types.Message, state: FSMContext):
    await state.set_state(TransactionStates.waiting_amount)
    await state.update_data(type='expense')
    await message.answer(
        "💸 Xarajat summasini kiriting:",
        reply_markup=get_cancel_keyboard()
    )

@dp.message(TransactionStates.waiting_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(' ', ''))
        await state.update_data(amount=amount)
        
        # Kategoriyalarni ko'rsatish
        categories = db.get_categories(message.from_user.id)
        await message.answer(
            "Kategoriyani tanlang:",
            reply_markup=get_categories_keyboard(categories)
        )
        await state.set_state(TransactionStates.waiting_category)
    except:
        await message.answer("❌ Noto'g'ri format. Qayta urinib ko'ring:")

@dp.callback_query(lambda c: c.data.startswith('cat_'))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data.replace('cat_', '')
    data = await state.get_data()
    
    trans_id = db.add_transaction(
        callback.from_user.id,
        data['amount'],
        category,
        data['type']
    )
    
    # Byudjetni tekshirish
    budget_check, budget, spent = db.check_budget(callback.from_user.id, category, data['amount'])
    if budget_check:
        await callback.message.answer(
            f"⚠️ <b>Ogohlantirish!</b>\n"
            f"Kategoriya: {category}\n"
            f"Byudjet: {budget:,.0f} so'm\n"
            f"Jami: {spent + data['amount']:,.0f} so'm",
            parse_mode="HTML"
        )
    
    await callback.message.edit_text(
        f"✅ {data['type'] == 'income' and 'Daromad' or 'Xarajat'} qo'shildi:\n"
        f"📌 {category}: {data['amount']:,.0f} so'm"
    )
    await state.clear()
    await callback.answer()

@dp.message(F.text == "📊 Statistika")
async def show_stats_menu(message: types.Message):
    await message.answer("Davrni tanlang:", reply_markup=get_period_keyboard())

@dp.callback_query(lambda c: c.data.startswith('period_'))
async def process_period(callback: types.CallbackQuery):
    period = callback.data.replace('period_', '')
    
    # Kategoriyalar bo'yicha statistika
    data = db.get_transactions_by_category(callback.from_user.id, period)
    
    if not data:
        await callback.message.edit_text("📭 Ma'lumot yo'q")
        return
    
    # Diagramma yaratish
    chart = create_expense_chart(data)
    
    # Matn
    total = sum(data.values())
    text = f"📊 <b>{period.capitalize()}lik statistika</b>\n\n"
    text += f"💰 Jami: {total:,.0f} so'm\n\n"
    
    for cat, amt in sorted(data.items(), key=lambda x: x[1], reverse=True):
        percent = (amt / total) * 100
        text += f"• {cat}: {amt:,.0f} so'm ({percent:.1f}%)\n"
    
    await callback.message.answer_photo(
        types.BufferedInputFile(chart.getvalue(), filename="stats.png"),
        caption=text,
        parse_mode="HTML"
    )
    await callback.message.delete()
    await callback.answer()

@dp.message(F.text == "📝 Qarzlar")
async def show_debts(message: types.Message):
    debts = db.get_debts(message.from_user.id)
    
    if not debts:
        await message.answer("📭 Qarzlar yo'q")
        return
    
    await message.answer(
        "📝 Qarzlar ro'yxati:",
        reply_markup=get_debts_keyboard(debts)
    )

@dp.callback_query(lambda c: c.data.startswith('debt_'))
async def process_debt(callback: types.CallbackQuery):
    debt_id = int(callback.data.replace('debt_', ''))
    
    if db.pay_debt(debt_id):
        await callback.answer("✅ Qarz to'landi", show_alert=True)
        await show_debts(callback.message)
    else:
        await callback.answer("❌ Xatolik", show_alert=True)

@dp.callback_query(lambda c: c.data == "new_debt")
async def new_debt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(TransactionStates.waiting_person)
    await callback.message.edit_text(
        "Kimdan qarz olgansiz?\n"
        "Misol: Ali"
    )
    await callback.answer()

@dp.message(TransactionStates.waiting_person)
async def process_debt_person(message: types.Message, state: FSMContext):
    await state.update_data(person=message.text)
    await state.set_state(TransactionStates.waiting_amount)
    await message.answer("Qarz summasini kiriting:")

@dp.message(TransactionStates.waiting_amount)
async def process_debt_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(' ', ''))
        data = await state.get_data()
        
        db.add_debt(
            message.from_user.id,
            data['person'],
            amount,
            'debt'
        )
        
        await message.answer(f"✅ Qarz qo'shildi: {data['person']} - {amount:,.0f} so'm")
        await state.clear()
    except:
        await message.answer("❌ Noto'g'ri format. Qayta urinib ko'ring:")

@dp.message(F.text == "💰 Byudjet")
async def manage_budget(message: types.Message):
    categories = db.get_categories(message.from_user.id)
    
    text = "💰 <b>Byudjetlar</b>\n\n"
    for cat in categories:
        if cat[5] > 0:  # budget
            # Shu oylik xarajat
            db.c.execute('''SELECT SUM(amount) FROM transactions 
                          WHERE user_id=? AND category=? AND type='expense' 
                          AND date>=date('now', 'start of month')''',
                          (message.from_user.id, cat[2]))
            spent = db.c.fetchone()[0] or 0
            
            percent = (spent / cat[5]) * 100
            bar = "█" * int(percent/10) + "░" * (10 - int(percent/10))
            
            text += f"{cat[3]} <b>{cat[2]}</b>\n"
            text += f"   {bar} {percent:.1f}%\n"
            text += f"   {spent:,.0f} / {cat[5]:,.0f} so'm\n\n"
    
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "📅 Eslatmalar")
async def show_reminders(message: types.Message):
    reminders = db.get_reminders(message.from_user.id)
    
    if not reminders:
        await message.answer("📭 Eslatmalar yo'q")
        return
    
    text = "📅 <b>To'lov eslatmalari</b>\n\n"
    for r in reminders:
        due = datetime.strptime(r[4], '%Y-%m-%d')
        days_left = (due - datetime.now()).days
        text += f"• {r[2]}: {r[3]:,.0f} so'm\n"
        text += f"  Muddati: {days_left} kun\n\n"
    
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "📁 Hisobot")
async def report_menu(message: types.Message):
    await message.answer(
        "Hisobot turini tanlang:",
        reply_markup=get_report_keyboard()
    )

@dp.callback_query(lambda c: c.data == "report_excel")
async def export_excel(callback: types.CallbackQuery):
    transactions = db.get_transactions(callback.from_user.id, 365)
    
    if not transactions:
        await callback.message.answer("📭 Ma'lumot yo'q")
        return
    
    excel_file = export_to_excel(transactions, "report.xlsx")
    
    await callback.message.answer_document(
        types.BufferedInputFile(excel_file.getvalue(), filename="report.xlsx"),
        caption="📊 Hisobot"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "report_pdf")
async def export_pdf(callback: types.CallbackQuery):
    transactions = db.get_transactions(callback.from_user.id, 365)
    
    if not transactions:
        await callback.message.answer("📭 Ma'lumot yo'q")
        return
    
    pdf_file = export_to_pdf(transactions, "report.pdf")
    
    await callback.message.answer_document(
        types.BufferedInputFile(pdf_file.getvalue(), filename="report.pdf"),
        caption="📊 Hisobot"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "report_chart")
async def show_chart(callback: types.CallbackQuery):
    data = db.get_transactions_by_category(callback.from_user.id, 'month')
    
    if not data:
        await callback.message.answer("📭 Ma'lumot yo'q")
        return
    
    chart = create_expense_chart(data, "Oylik xarajatlar")
    
    await callback.message.answer_photo(
        types.BufferedInputFile(chart.getvalue(), filename="chart.png"),
        caption="📊 Oylik xarajatlar diagrammasi"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "report_analysis")
async def show_analysis(callback: types.CallbackQuery):
    transactions = db.get_transactions(callback.from_user.id, 90)
    
    if not transactions:
        await callback.message.answer("📭 Ma'lumot yo'q")
        return
    
    habits = analyze_spending_habits(transactions)
    
    text = "📊 <b>Xarajat odatlari tahlili</b>\n\n"
    text += f"🏆 Eng ko'p xarajat: {habits.get('top_category', 'Noma')}\n"
    text += f"💰 Jami: {habits.get('top_category_amount', 0):,.0f} so'm\n\n"
    text += f"📅 O'rtacha kunlik: {habits.get('avg_daily', 0):,.0f} so'm\n"
    text += f"📆 Eng ko'p xarajat kuni: {habits.get('max_spending_day', 'Noma')}\n\n"
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

@dp.message(F.text == "⚙️ Sozlamalar")
async def show_settings(message: types.Message):
    await message.answer(
        "⚙️ <b>Sozlamalar</b>",
        parse_mode="HTML",
        reply_markup=get_settings_keyboard()
    )

@dp.callback_query(lambda c: c.data == "set_lang")
async def set_language(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🌐 Tilni tanlang:\n\n"
        "uz - O'zbekcha\n"
        "ru - Русский\n"
        "en - English"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "set_currency")
async def set_currency(callback: types.CallbackQuery):
    # Valyuta kurslarini olish
    rates = get_currency_rates()
    
    text = "💰 <b>Valyuta kurslari</b>\n\n"
    for currency, rate in rates.items():
        text += f"• {currency}: {rate:,.0f} so'm\n"
    
    text += "\nAsosiy valyutani tanlang:"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="UZS", callback_data="curr_UZS"),
        InlineKeyboardButton(text="USD", callback_data="curr_USD"),
        InlineKeyboardButton(text="EUR", callback_data="curr_EUR")
    )
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("curr_"))
async def process_currency(callback: types.CallbackQuery):
    currency = callback.data.replace('curr_', '')
    db.update_user_settings(callback.from_user.id, currency=currency)
    await callback.message.edit_text(f"✅ Valyuta o'zgartirildi: {currency}")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "set_pin")
async def set_pin(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(TransactionStates.waiting_pin)
    await callback.message.edit_text(
        "🔐 4 xonali PIN kod kiriting:"
    )
    await callback.answer()

@dp.message(TransactionStates.waiting_pin)
async def process_pin(message: types.Message, state: FSMContext):
    if len(message.text) == 4 and message.text.isdigit():
        pin_hash = generate_pin_hash(message.text)
        db.update_user_settings(message.from_user.id, pin_code=pin_hash)
        await message.answer("✅ PIN kod o'rnatildi")
        await state.clear()
    else:
        await message.answer("❌ PIN kod 4 xonali son bo'lishi kerak")

@dp.callback_query(lambda c: c.data == "backup")
async def create_backup(callback: types.CallbackQuery):
    filename = db.create_backup(callback.from_user.id)
    
    with open(filename, 'rb') as f:
        await callback.message.answer_document(
            types.BufferedInputFile(f.read(), filename=filename),
            caption="💾 Ma'lumotlar zaxirasi"
        )
    
    await callback.answer()

@dp.callback_query(lambda c: c.data == "export")
async def export_all(callback: types.CallbackQuery):
    transactions = db.get_transactions(callback.from_user.id, 3650)
    
    if not transactions:
        await callback.message.answer("📭 Ma'lumot yo'q")
        return
    
    # Excel
    excel_file = export_to_excel(transactions, "all_data.xlsx")
    
    # JSON
    data = {
        'transactions': transactions,
        'date': datetime.now().isoformat()
    }
    json_file = io.BytesIO(json.dumps(data, default=str).encode())
    
    media = [
        types.InputMediaDocument(
            types.BufferedInputFile(excel_file.getvalue(), filename="data.xlsx")
        ),
        types.InputMediaDocument(
            types.BufferedInputFile(json_file.getvalue(), filename="data.json")
        )
    ]
    
    await callback.message.answer_media_group(media)
    await callback.answer()

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    # Chekni saqlash
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    
    await message.answer("📸 Chek qabul qilindi. Tez orada tahlil qilinadi.")

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    await message.answer(
        "🎙 Ovozli buyruq qabul qilindi.\n"
        "Tez orada matnga aylantiriladi."
    )

@dp.message(F.text)
async def smart_input(message: types.Message):
    """Aqlli matnli kiritish"""
    text = message.text.strip()
    
    # Qarzmi?
    if "qarz" in text.lower():
        person = extract_person(text)
        amount = extract_amount(text)
        if amount:
            db.add_debt(message.from_user.id, person, amount, 'debt')
            await message.answer(f"✅ Qarz qo'shildi: {person} - {amount:,.0f} so'm")
            return
    
    # Oddiy xarajat
    amount = extract_amount(text)
    if amount:
        # Birinchi so'z kategoriya
        words = text.split()
        category = words[0] if not words[0].replace(',', '').isdigit() else "Xarajat"
        
        db.add_transaction(message.from_user.id, amount, category, 'expense', text)
        await message.answer(f"✅ Xarajat qo'shildi: {category} - {amount:,.0f} so'm")
        return
    
    await message.answer("❌ Tushunilmadi. Menyudan foydalaning.")

# ========== ADMIN COMMANDS ==========

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    # Foydalanuvchilar soni
    db.c.execute('SELECT COUNT(*) FROM users')
    users = db.c.fetchone()[0]
    
    # Xarajatlar soni
    db.c.execute('SELECT COUNT(*) FROM transactions')
    trans = db.c.fetchone()[0]
    
    # Jami xarajat
    db.c.execute('SELECT SUM(amount) FROM transactions WHERE type="expense"')
    total_expense = db.c.fetchone()[0] or 0
    
    await message.answer(
        f"👑 <b>Admin panel</b>\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"📊 Tranzaksiyalar: {trans}\n"
        f"💰 Jami xarajat: {total_expense:,.0f} so'm",
        parse_mode="HTML"
    )

# ========== BACKGROUND TASKS ==========

async def check_reminders():
    """Eslatmalarni tekshirish"""
    while True:
        reminders = db.check_reminders()
        for r in reminders:
            try:
                await bot.send_message(
                    r[1],
                    f"⏰ <b>Eslatma!</b>\n\n"
                    f"{r[2]}: {r[3]:,.0f} so'm\n"
                    f"To'lov muddati bugun!",
                    parse_mode="HTML"
                )
            except:
                pass
        await asyncio.sleep(3600)  # Har soatda

async def check_recurring():
    """Takrorlanuvchi to'lovlarni aniqlash"""
    while True:
        # Har kuni ertalab tekshirish
        await asyncio.sleep(86400)  # 24 soat

# ========== MAIN ==========

async def main():
    print("🚀 Bot ishga tushmoqda...")
    
    # Background tasklarni ishga tushirish
    asyncio.create_task(check_reminders())
    asyncio.create_task(check_recurring())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
