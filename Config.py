import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8041379422:AAGGiA58y-SHNH5YpnIez4mcz6K3tyv9Daw')
    CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID', '@your_channel_username')
    
    # Admin IDs
    admin_ids_str = os.getenv('ADMIN_USER_IDS', '657959020')
    ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]
    
    # ВАЖЛИВО: Якщо використовуєте .env, то значення з нього перезапише ці
