import ccxt
import time
from datetime import datetime

# Налаштування
exchange = ccxt.mexc()
symbol = 'ARCSOLUS/USDT'  # Замініть на потрібну пару
timeframes = ['1m', '5m']  # Таймфрейми для аналізу
rally_threshold = 2  # 2% зміна для виявлення ралі
resistance_proximity = 5  # 5% до опору для сповіщення

def get_candle_data(symbol, timeframe, limit=10):
    """Отримує останні свічники"""
    candles = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    return candles

def detect_rally(candles, threshold):
    """Виявляє швидкий злет"""
    if len(candles) < 2:
        return False, 0
    
    current_close = candles[-1][4]
    previous_close = candles[-2][4]
    
    if previous_close == 0:
        return False, 0
    
    percent_change = ((current_close - previous_close) / previous_close) * 100
    
    if percent_change >= threshold:
        return True, percent_change
    return False, percent_change

def find_resistance_level(candles, current_price):
    """Знаходить рівень опору (наприклад, останній локальний максимум)"""
    if len(candles) < 10:
        return None
    
    # Шукаємо максимуми в останніх 10 свічниках
    highs = [candle[2] for candle in candles[-10:]]
    resistance = max(highs)
    
    # Фільтруємо, якщо опір надто далеко або під поточною ціною
    if resistance <= current_price:
        # Шукаємо наступний рівень у історії
        all_highs = [candle[2] for candle in candles]
        potential_resistances = [h for h in all_highs if h > current_price]
        if potential_resistances:
            resistance = min(potential_resistances)
        else:
            return None
    
    return resistance

def calculate_distance(current_price, resistance):
    """Розраховує відстань до опору у відсотках"""
    if resistance is None:
        return None
    distance_percent = ((resistance - current_price) / current_price) * 100
    return distance_percent

def monitor():
    print(f"Моніторинг {symbol} на MEXC...")
    print(f"Таймфрейми: {timeframes}")
    print(f"Поріг ралі: {rally_threshold}%")
    print(f"Сповіщення при 5% до опору\n")
    
    while True:
        try:
            for tf in timeframes:
                # Отримуємо дані
                candles = get_candle_data(symbol, tf)
                if not candles:
                    continue
                
                current_price = candles[-1][4]
                
                # Детектуємо ралі
                is_rally, change = detect_rally(candles, rally_threshold)
                
                # Знаходимо опір
                resistance = find_resistance_level(candles, current_price)
                
                # Розраховуємо відстань до опору
                resistance_distance = None
                if resistance:
                    resistance_distance = calculate_distance(current_price, resistance)
                
                # Виводимо інформацію
                timestamp = datetime.now().strftime("%H:%M:%S")
                output = f"[{timestamp}] {tf} | Ціна: {current_price:.6f}"
                
                if is_rally:
                    output += f" | 🚀 РАЛІ: +{change:.2f}%"
                
                if resistance:
                    output += f" | Опір: {resistance:.6f}"
                    if resistance_distance:
                        output += f" (залишилось: {resistance_distance:.2f}%)"
                        
                        # Сповіщення якщо до опору 5% або менше
                        if resistance_distance <= resistance_proximity:
                            output += " ⚠️ БЛИЗЬКО ДО ОПОРУ!"
                
                print(output)
                
                # Додаткова логіка для сповіщень/сигналів
                if is_rally and resistance_distance and resistance_distance <= resistance_proximity:
                    print(f"🔔 СИГНАЛ: {symbol} | {tf} | Ралі {change:.2f}% | До опору {resistance_distance:.2f}%")
            
            # Пауза між перевірками
            time.sleep(30)  # Перевірка кожні 30 секунд
            
        except Exception as e:
            print(f"Помилка: {e}")
            time.sleep(60)

if __name__ == "__main__":
    monitor()
