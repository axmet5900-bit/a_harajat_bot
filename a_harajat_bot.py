import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Xush kelibsiz! Xarajat botiga xush kelibsiz.\n\n"
        "📝 Misol: 'Taksi 15000' yoki 'Ali 50000 qarz'"
    )

@dp.message(Command("stats"))
async def stats(message: types.Message):
    await message.answer("📊 Statistika tayyorlanmoqda...")

@dp.message(F.text)
async def handle_text(message: types.Message):
    text = message.text
    await message.answer(f"Siz yozdingiz: {text}")

async def main():
    print("Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
