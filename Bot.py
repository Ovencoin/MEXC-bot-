import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from datetime import datetime

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ВАШІ ДАНІ (безпечніше через .env, але для швидкого старту)
BOT_TOKEN = "8041379422:AAGGiA58y-SHNH5YpnIez4mcz6K3tyv9Daw"
ADMIN_IDS = [657959020]  # Ваш ID
CHANNEL_ID = "@your_channel_username"  # Замініть на ваш канал

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("🚫 У вас немає доступу до цього бота.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
        [InlineKeyboardButton("🔔 Створити сигнал", callback_data='create_signal')],
        [InlineKeyboardButton("📈 Останні сигнали", callback_data='recent_signals')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Вітаю, адміне! Ваш ID: {user_id}\n"
        f"🤖 Бот готовий до роботи!\n"
        f"📢 Канал: {CHANNEL_ID}",
        reply_markup=reply_markup
    )

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Відправка сигналу в канал"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Немає доступу.")
        return
    
    # Парсимо аргументи: /signal FHE 0.09809 0.1054 50
    if len(context.args) < 4:
        await update.message.reply_text(
            "📋 Формат: /signal <монета> <вхід> <ціль> <плече> [обсяг]\n"
            "📝 Приклад: /signal FHE 0.09809 0.1054 50 1000000\n"
            "💰 Плече: 3, 5, 10, 20, 50"
        )
        return
    
    try:
        coin = context.args[0].upper()
        entry_price = float(context.args[1])
        target_price = float(context.args[2])
        leverage = int(context.args[3])
        volume = float(context.args[4]) if len(context.args) > 4 else 1000000
        
        # Розраховуємо зміну в %
        pump_percent = round(((target_price - entry_price) / entry_price) * 100, 2)
        
        # Форматуємо повідомлення
        message = f"""
🔔 **{coin} NEW**
Pump {pump_percent}% ({entry_price} -> {target_price})
x{leverage} / {volume:,.0f}$ / 0.005

**Trade:**
- Mexc
- Bybit

**RSI (1h):** 72.3%
Prev Day: open: {entry_price * 0.95:.5f} / close: {entry_price * 0.97:.5f}

📊 **Статистика по монеті #{coin}**
- Винрейт шорта: 24.24%
- Лосс сигнали: 9.09%
- Нейтральные сигнали: 66.67%
- Сигналов в статистике: 33
- Средний откат после сигнала: 3.45%
- Среднее продолжение роста после сигнала: 3.5%
        """
        
        # Кнопки під повідомленням
        keyboard = [
            [
                InlineKeyboardButton("📈 Графік", callback_data=f'chart_{coin}'),
                InlineKeyboardButton("📊 Статистика", callback_data=f'stats_{coin}')
            ],
            [
                InlineKeyboardButton("✅ Успішний", callback_data=f'success_{coin}'),
                InlineKeyboardButton("❌ Неуспішний", callback_data=f'fail_{coin}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Відправляємо в канал
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Підтвердження адміну
        await update.message.reply_text(
            f"✅ Сигнал для {coin} відправлено в канал!\n"
            f"📊 Дані: {entry_price} → {target_price} (x{leverage})\n"
            f"📢 Перевірте канал: {CHANNEL_ID}"
        )
        
    except Exception as e:
        logger.error(f"Помилка: {e}")
        await update.message.reply_text(f"❌ Помилка: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'stats':
        stats_message = """
📊 **Загальна статистика:**

- Винрейт шорта: 24.24%
- Лосс сигнали: 9.09%
- Нейтральные сигнали: 66.67%
- Сигналов в статистике: 33
- Средний откат после сигнала: 3.45%
- Среднее продолжение роста после сигнала: 3.5%
        """
        await query.edit_message_text(stats_message, parse_mode=ParseMode.MARKDOWN)
    
    elif query.data == 'create_signal':
        await query.edit_message_text(
            "📝 Для створення сигналу використовуйте команду:\n"
            "`/signal FHE 0.09809 0.1054 50 1000000`\n\n"
            "📋 Формат: /signal <монета> <вхід> <ціль> <плече> [обсяг]",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == 'recent_signals':
        recent_message = """
📋 **Останні сигнали:**

1. **FHE** - 02.09 20:15
   Вхід: 0.09809, Ціль: 0.1054
   Плече: x50, Статус: 📈 Активний

2. **DUSK** - 02.09 18:30
   Вхід: 0.1251, Ціль: 0.1150
   Плече: x20, Статус: 📉 -3.2%

3. **PYR** - 02.09 16:45
   Вхід: 0.2884, Ціль: 0.2572
   Плече: x10, Статус: ✅ +10.8%
        """
        await query.edit_message_text(recent_message, parse_mode=ParseMode.MARKDOWN)

async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Закріпити повідомлення в каналі"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    if update.message.reply_to_message:
        try:
            # Спробуємо закріпити в каналі
            await context.bot.pin_chat_message(
                chat_id=CHANNEL_ID,
                message_id=update.message.reply_to_message.message_id
            )
            await update.message.reply_text("📌 Повідомлення закріплено в каналі!")
        except Exception as e:
            await update.message.reply_text(f"❌ Помилка: {e}")

async def test_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовий запис в канал"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text="🔔 Тестове повідомлення від бота!\nБот готовий до роботи! 🚀"
        )
        await update.message.reply_text(f"✅ Тестове повідомлення відправлено в {CHANNEL_ID}")
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка: {e}\nПеревірте права бота в каналі!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Довідка"""
    help_text = """
🤖 **Торговий сигнал бот - Довідка**

🔹 **Основні команди:**
/start - Панель управління
/signal - Відправити сигнал в канал
/test - Тест каналу
/pin - Закріпити повідомлення (відповісти на повідомлення)
/help - Ця довідка

🔹 **Формат сигналу:**
`/signal FHE 0.09809 0.1054 50 1000000`
• FHE - монета
• 0.09809 - ціна входу
• 0.1054 - цільова ціна
• 50 - плече
• 1000000 - обсяг (опціонально)

🔹 **Налаштування:**
1. Бот повинен бути адміном в каналі
2. Ваш ID: 657959020
3. Канал: задайте в коді CHANNEL_ID
    """
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def main():
    """Запуск бота"""
    # Створюємо додаток
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Додаємо обробники команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signal", signal))
    application.add_handler(CommandHandler("pin", pin_message))
    application.add_handler(CommandHandler("test", test_channel))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаємо бота
    logger.info("🤖 Бот запускається...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Безкінечний цикл
    await asyncio.Event().wait()

if __name__ == '__main__':
    # Перевірка налаштувань
    print(f"🔑 Бот токен: {BOT_TOKEN[:10]}...")
    print(f"👤 Admin ID: {ADMIN_IDS}")
    print(f"📢 Канал: {CHANNEL_ID}")
    print("🚀 Запуск бота...")
    
    asyncio.run(main())
