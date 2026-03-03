import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Assalomu alaykum! Bot ishlayapti ✅")

@dp.message(Command("stats"))
async def stats(message: types.Message):
    await message.answer("Statistika tayyorlanmoqda...")

@dp.message()
async def echo(message: types.Message):
    await message.answer(f"Siz yozdingiz: {message.text}")

async def main():
    print("✅ Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
