import requests
import time

# ТВОЇ ДАНІ - ЗАМІНИ ЦЕ НА СВОЇ ЧИСЛА!
TELEGRAM_TOKEN = "7123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"  # Заміни на свій
CHAT_ID = "123456789"  # Заміни на свій

# Функція для відправки повідомлень
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, json=data)
        return True
    except:
        return False

# Отримання даних з MEXC
def get_mexc_data():
    url = "https://api.mexc.com/api/v3/ticker/24hr"
    try:
        return requests.get(url).json()
    except:
        return []

# Пошук швидких монет
def find_fast_growers(data):
    result = []
    for coin in data:
        try:
            change = float(coin["priceChangePercent"])
            volume = float(coin["quoteVolume"])
            if change > 3 and volume > 50000:
                result.append({
                    "symbol": coin["symbol"],
                    "change": change,
                    "price": float(coin["lastPrice"])
                })
        except:
            continue
    return result

# Отримання свічок
def get_candles(symbol):
    url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=5m&limit=100"
    try:
        return requests.get(url).json()
    except:
        return []

# Основний цикл
def main():
    print("🤖 Бот запущено!")
    
    while True:
        try:
            print("🔍 Перевіряю ринок...")
            data = get_mexc_data()
            
            if not data:
                print("😴 Немає даних, чекаю...")
                time.sleep(60)
                continue
            
            coins = find_fast_growers(data)
            
            if coins:
                print(f"📈 Знайдено {len(coins)} монет!")
                
                for coin in coins[:3]:  # Тільки 3 найкращі
                    symbol = coin["symbol"]
                    price = coin["price"]
                    change = coin["change"]
                    
                    # Проста логіка
                    message = f"🚀 {symbol}\nРіст: {change:.1f}%\nЦіна: {price}"
                    send_telegram_message(message)
                    print(f"📤 Відправив: {symbol}")
                    time.sleep(1)
            else:
                print("📉 Нічого не знайдено")
            
            print("⏳ Чекаю 5 хвилин...\n")
            time.sleep(300)
            
        except KeyboardInterrupt:
            print("\n🛑 Бот зупинено")
            break
        except Exception as e:
            print(f"⚠️ Помилка: {e}")
            time.sleep(60)

# Запуск
if __name__ == "__main__":
    main()
