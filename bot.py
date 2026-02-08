import requests
import time

# ===== ТВОЇ ДАНІ =====
TELEGRAM_TOKEN = "8041379422:AAGGiA58y-SHNH5YpnIez4mcz6K3tyv9Daw"
CHAT_ID = "657959020"

# ===== ПРОСТІ ФУНКЦІЇ =====
def send_to_telegram(message):
    """Відправити повідомлення в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=data, timeout=5)
        return True
    except:
        return False

def get_mexc_data():
    """Отримати дані з MEXC"""
    try:
        response = requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=10)
        return response.json()
    except:
        return []

def find_big_gainers(data):
    """Знайти монети з великим зростанням"""
    gainers = []
    for coin in data:
        try:
            symbol = str(coin.get("symbol", ""))
            change = float(coin.get("priceChangePercent", 0))
            volume = float(coin.get("quoteVolume", 0))
            price = float(coin.get("lastPrice", 0))
            
            # Фільтри: зростання >5% та обсяг >10000 USDT
            if "USDT" in symbol and change > 5 and volume > 10000:
                gainers.append({
                    "symbol": symbol,
                    "change": change,
                    "price": price,
                    "volume": volume
                })
        except:
            continue
    
    # Сортуємо за зростанням (найбільші зверху)
    gainers.sort(key=lambda x: x["change"], reverse=True)
    return gainers[:5]  # Тільки топ-5

# ===== ОСНОВНА ПРОГРАМА =====
def main():
    print("🤖 MEXC БОТ ЗАПУЩЕНО")
    print("=" * 40)
    
    # Тестове повідомлення
    send_to_telegram("🤖 <b>Бот запущено!</b>")
    
    check_number = 0
    
    while True:
        check_number += 1
        print(f"\n📊 Перевірка #{check_number}")
        print("🔄 Отримую дані з MEXC...")
        
        try:
            # 1. Отримуємо дані
            market_data = get_mexc_data()
            
            if not market_data:
                print("❌ Не вдалося отримати дані")
                time.sleep(60)
                continue
            
            print(f"✅ Отримано {len(market_data)} монет")
            
            # 2. Шукаємо швидкі монети
            top_gainers = find_big_gainers(market_data)
            
            if not top_gainers:
                print("📉 Не знайдено монет з ростом >5%")
            else:
                print(f"📈 Знайдено {len(top_gainers)} перспективних монет")
                
                # 3. Відправляємо кожну
                for coin in top_gainers:
                    symbol = coin["symbol"]
                    change = coin["change"]
                    price = coin["price"]
                    
                    message = f"""
🚀 <b>{symbol}</b>

📊 <b>Статистика:</b>
• Зміна: <code>+{change:.2f}%</code>
• Ціна: <code>{price:.8f}</code>
• Обсяг: <code>{coin['volume']:,.0f}</code> USDT

⏰ {time.strftime("%H:%M:%S")}
"""
                    
                    if send_to_telegram(message):
                        print(f"✅ Відправлено: {symbol}")
                    else:
                        print(f"❌ Помилка: {symbol}")
                    
                    time.sleep(2)  # Затримка між повідомленнями
            
            # 4. Чекаємо 5 хвилин
            print("⏳ Наступна перевірка через 5 хвилин...")
            for i in range(300):
                time.sleep(1)
                if i % 60 == 0:
                    print(".", end="", flush=True)
            print()
            
        except KeyboardInterrupt:
            print("\n\n🛑 Бот зупинено")
            send_to_telegram("🛑 <b>Бот зупинено</b>")
            break
        except Exception as e:
            print(f"⚠️ Помилка: {e}")
            time.sleep(60)

# ===== ЗАПУСК =====
if __name__ == "__main__":
    main()
