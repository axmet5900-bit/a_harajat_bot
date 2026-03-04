import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
    DATABASE_URL = 'sqlite:///wallet.db'
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    TIMEZONE = 'Asia/Tashkent'
    CURRENCY_API_KEY = os.getenv('CURRENCY_API_KEY', '')
    
config = Config()
