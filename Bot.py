import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
    ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_USER_IDS', '').split(',') if id.strip()]
    
    # Exchanges
    MEXC_API_KEY = os.getenv('MEXC_API_KEY')
    MEXC_SECRET_KEY = os.getenv('MEXC_SECRET_KEY')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///signals.db')
    
    # Signal settings
    MIN_VOLUME = 1000000  # Мінімальний обсяг в USDT
    MIN_PUMP_PERCENT = 5.0  # Мінімальний % зростання
    MAX_RSI = 80  # Максимальний RSI для сигналу
    LEVERAGE_OPTIONS = [3, 5, 10, 20, 50]
