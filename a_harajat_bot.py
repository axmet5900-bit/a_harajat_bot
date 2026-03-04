import os
import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv

# Token ni yuklash
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# Logging
logging.basicConfig(level=logging.INFO)

# Bot va dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Ma'lumotlar bazasini yaratish
def init_db():
    conn = sqlite3.connect('wallet.db')
    c = conn.cursor()
    
    # Xarajatlar jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS expenses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  amount REAL,
                  category TEXT,
                  date TEXT)''')
    
    # Qarzlar jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS debts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  person TEXT,
                  amount REAL,
                  status TEXT)''')
    
    conn.commit()
    conn.close()
    print("✅ Database created")

# Start komandasi
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 <b>Xush kelibsiz!</b>\n\n"
        "Men <b>Xarajat bot</b> - xarajatlaringizni hisoblab boruvchi yordamchiman.\n\n"
        "📝 <b>Qanday ishlatish:</b>\n"
        "• Xarajat yozish: <code>Taksi 15000</code>\n"
        "• Qarz yozish: <code>Ali 50000 qarz</code>\n"
        "• Statistika: /stats\n"
        "• Qarzlar: /debts",
        parse_mode="HTML"
    )

# Help komandasi
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📚 <b>Yordam</b>\n\n"
        "<b>Buyruqlar:</b>\n"
        "/start - Botni boshlash\n"
        "/stats - Xarajatlar statistikasi\n"
        "/debts - Qarzlar ro'yxati\n"
        "/help - Yordam\n\n"
        "<b>Misol:</b>\n"
        "• <code>Moshina 50000</code>\n"
        "• <code>Osh 25000</code>\n"
        "• <code>Ali 100000 qarz</code>",
        parse_mode="HTML"
    )

# Stats komandasi
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect('wallet.db')
    c = conn.cursor()
    
    # Bugungi xarajatlar
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT SUM(amount) FROM expenses WHERE user_id=? AND date=?", (user_id, today))
    today_total = c.fetchone()[0] or 0
    
    # Umumiy xarajatlar
    c.execute("SELECT SUM(amount) FROM expenses WHERE user_id=?", (user_id,))
    total = c.fetchone()[0] or 0
    
    conn.close()
    
    await message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"📅 Bugun: {today_total:,.0f} so'm\n"
        f"💰 Jami: {total:,.0f} so'm",
        parse_mode="HTML"
    )

# Debts komandasi
@dp.message(Command("debts"))
async def cmd_debts(message: types.Message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect('wallet.db')
    c = conn.cursor()
    
    c.execute("SELECT person, amount FROM debts WHERE user_id=? AND status='active'", (user_id,))
    debts = c.fetchall()
    
    conn.close()
    
    if not debts:
        await message.answer("📝 Sizda qarzlar yo'q")
        return
    
    text = "📝 <b>Qarzlar ro'yxati</b>\n\n"
    total = 0
    
    for person, amount in debts:
        text += f"👤 {person}: {amount:,.0f} so'm\n"
        total += amount
    
    text += f"\n💰 Jami: {total:,.0f} so'm"
    
    await message.answer(text, parse_mode="HTML")

# Matnli xabarlar
@dp.message(F.text)
async def handle_text(message: types.Message):
    text = message.text.strip()
    user_id = message.from_user.id
    
    # Qarzmi yoki xarajatmi?
    if "qarz" in text.lower():
        # Qarz yozish
        parts = text.split()
        try:
            # Odam va summani ajratish
            if len(parts) >= 3:
                person = parts[0]
                amount = float(parts[1].replace(',', '').replace(' ', ''))
                
                conn = sqlite3.connect('wallet.db')
                c = conn.cursor()
                c.execute("INSERT INTO debts (user_id, person, amount, status) VALUES (?, ?, ?, 'active')",
                         (user_id, person, amount))
                conn.commit()
                conn.close()
                
                await message.answer(f"✅ Qarz qo'shildi: {person} - {amount:,.0f} so'm")
            else:
                await message.answer("❌ Noto'g'ri format. Misol: Ali 50000 qarz")
        except:
            await message.answer("❌ Xatolik yuz berdi")
    
    else:
        # Xarajat yozish
        try:
            # Summa va kategoriyani ajratish
            parts = text.split()
            if len(parts) >= 2:
                category = parts[0]
                amount = float(parts[1].replace(',', '').replace(' ', ''))
                
                date_now = datetime.now().strftime('%Y-%m-%d')
                
                conn = sqlite3.connect('wallet.db')
                c = conn.cursor()
                c.execute("INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                         (user_id, amount, category, date_now))
                conn.commit()
                conn.close()
                
                await message.answer(f"✅ Xarajat qo'shildi: {category} - {amount:,.0f} so'm")
            else:
                await message.answer("❌ Noto'g'ri format. Misol: Taksi 15000")
        except:
            await message.answer("❌ Xatolik yuz berdi")

# Ovozli xabarlar
@dp.message(F.voice)
async def handle_voice(message: types.Message):
    await message.answer("🎙 Ovozli xabar qabul qilindi. Hozircha matnli buyruqlardan foydalaning.")

# Asosiy funksiya
async def main():
    # Databaseni yaratish
    init_db()
    
    # Botni ishga tushirish
    print("🤖 Bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
