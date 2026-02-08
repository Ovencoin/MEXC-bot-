import requests
import time
import json
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from io import BytesIO
import ta
from collections import defaultdict, deque

# ===== ТВОЇ ДАНІ =====
TELEGRAM_TOKEN = "8041379422:AAGGiA58y-SHNH5YpnIez4mcz6K3tyv9Daw"
CHAT_ID = "657959020"

# ===== НАЛАШТУВАННЯ =====
CHECK_INTERVAL = 60  # Перевірка кожні 60 секунд
MIN_VOLUME = 100000  # Мінімальний обсяг USDT
MIN_TOUCHES = 3      # Мінімум торкань рівня
RSI_OVERBOUGHT = 70  # RSI для перекупленості

# ===== API ФУНКЦІЇ =====
def get_market_data():
    """Отримати ринкові дані"""
    url = "https://api.mexc.com/api/v3/ticker/24hr"
    try:
        response = requests.get(url, timeout=10)
        return response.json()
    except:
        return []

def get_klines(symbol, interval="15m", limit=100):
    """Отримати свічки"""
    url = "https://api.mexc.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json()
    except:
        return []

def get_order_book(symbol):
    """Отримати стакан ордерів"""
    url = f"https://api.mexc.com/api/v3/depth"
    params = {"symbol": symbol, "limit": 20}
    try:
        response = requests.get(url, params=params, timeout=5)
        return response.json()
    except:
        return {"bids": [], "asks": []}

# ===== АНАЛІЗ РІВНІВ ОПОРУ =====
def find_strong_resistance_levels(candles):
    """Знайти сильні рівні опору з кількістю торкань"""
    if len(candles) < 20:
        return []
    
    highs = [float(c[2]) for c in candles]
    
    # Групуємо близькі максимуми в рівні
    resistance_zones = defaultdict(int)
    zone_size = 0.002  # 0.2% зона
    
    for high in highs:
        # Нормалізуємо до зони
        zone_price = round(high * (1 - zone_size), 6)
        resistance_zones[zone_price] += 1
    
    # Фільтруємо та сортуємо
    strong_levels = []
    for price, touches in resistance_zones.items():
        if touches >= MIN_TOUCHES:
            distance_percent = 0
            if len(highs) > 0:
                current_price = highs[-1]
                distance_percent = ((price - current_price) / current_price) * 100
            
            strong_levels.append({
                'price': price,
                'touches': touches,
                'distance_percent': distance_percent
            })
    
    # Сортуємо за кількістю торкань
    strong_levels.sort(key=lambda x: x['touches'], reverse=True)
    return strong_levels[:5]  # Топ-5 рівнів

def calculate_price_distance(current_price, resistance_levels):
    """Розрахувати відстань до найближчого опору"""
    if not resistance_levels:
        return None, 999
    
    nearest_level = min(resistance_levels, 
                       key=lambda x: abs(x['price'] - current_price))
    
    distance = ((nearest_level['price'] - current_price) / current_price) * 100
    return nearest_level, distance

def detect_rejection_pattern(candles, resistance_price):
    """Виявити свічку відбою біля рівня опору"""
    if len(candles) < 5:
        return False
    
    last_candle = candles[-1]
    
    try:
        open_price = float(last_candle[1])
        high_price = float(last_candle[2])
        low_price = float(last_candle[3])
        close_price = float(last_candle[4])
        
        # Перевірка, чи свічка торкнулася рівня опору
        touched_resistance = high_price >= resistance_price * 0.998
        
        if not touched_resistance:
            return False
        
        # Перевірка на Pin Bar (відбій вниз)
        body_size = abs(close_price - open_price)
        upper_shadow = high_price - max(open_price, close_price)
        lower_shadow = min(open_price, close_price) - low_price
        
        # Bearish Pin Bar: велика верхня тінь, маленьке тіло
        if (upper_shadow > body_size * 2 and 
            upper_shadow > lower_shadow * 2 and
            close_price < open_price):  # Медвежа свічка
            return "PINBAR_BEARISH"
        
        # Shooting Star: маленьке тіло внизу, велика верхня тінь
        if (upper_shadow > body_size * 3 and 
            body_size / (high_price - low_price) < 0.3):
            return "SHOOTING_STAR"
        
        # Doji біля опору
        if (body_size / (high_price - low_price) < 0.1 and
            touched_resistance):
            return "DOJI_AT_RESISTANCE"
            
    except:
        pass
    
    return False

# ===== ТЕХНІЧНИЙ АНАЛІЗ =====
def calculate_technical_indicators(candles):
    """Розрахувати технічні індикатори"""
    if len(candles) < 20:
        return {}
    
    closes = [float(c[4]) for c in candles]
    highs = [float(c[2]) for c in candles]
    lows = [float(c[3]) for c in candles]
    
    df = pd.DataFrame({'close': closes, 'high': highs, 'low': lows})
    
    indicators = {}
    
    # RSI
    rsi = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    indicators['rsi'] = round(rsi.iloc[-1], 2)
    
    # MACD
    macd = ta.trend.MACD(df['close'])
    indicators['macd'] = round(macd.macd().iloc[-1], 4)
    indicators['macd_signal'] = round(macd.macd_signal().iloc[-1], 4)
    indicators['macd_diff'] = round(macd.macd_diff().iloc[-1], 4)
    
    # Stochastic
    stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
    indicators['stoch_k'] = round(stoch.stoch().iloc[-1], 2)
    indicators['stoch_d'] = round(stoch.stoch_signal().iloc[-1], 2)
    
    # Вольатільність (ATR)
    atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'])
    indicators['atr'] = round(atr.average_true_range().iloc[-1], 6)
    indicators['atr_percent'] = round((indicators['atr'] / closes[-1]) * 100, 2)
    
    # Тренд (EMA)
    ema_20 = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator()
    ema_50 = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
    indicators['trend'] = "BULLISH" if ema_20.iloc[-1] > ema_50.iloc[-1] else "BEARISH"
    
    return indicators

# ===== ГРАФІКИ З РІВНЯМИ =====
def create_resistance_chart(symbol, candles, resistance_levels, current_price):
    """Створити графік з рівнями опору"""
    if len(candles) < 20:
        return None
    
    # Підготуємо дані
    closes = [float(c[4]) for c in candles[-50:]]
    times = list(range(len(closes)))
    
    # Створимо графік
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                   gridspec_kw={'height_ratios': [3, 1]},
                                   facecolor='#0f0f23')
    
    # Графік ціни
    ax1.set_facecolor('#0f0f23')
    ax1.plot(times, closes, color='#00ff88', linewidth=2, label='Ціна закриття')
    ax1.axhline(y=current_price, color='#ffff00', linestyle='--', 
                alpha=0.5, label='Поточна ціна')
    
    # Додаємо рівні опору
    colors = ['#ff5555', '#ff8888', '#ffaaaa']
    for i, level in enumerate(resistance_levels[:3]):
        color = colors[i % len(colors)]
        ax1.axhline(y=level['price'], color=color, linestyle='--', 
                   linewidth=2, alpha=0.7, 
                   label=f"Опір {i+1}: {level['price']:.6f} ({level['touches']}x)")
        
        # Підпис рівня
        ax1.text(times[-1] + 1, level['price'], 
                f"  {level['price']:.6f}", 
                color=color, verticalalignment='center',
                bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.2))
    
    # Область ризику (між поточною ціною та опором)
    if resistance_levels:
        nearest_resistance = resistance_levels[0]['price']
        ax1.fill_between(times, current_price, nearest_resistance, 
                        where=(nearest_resistance > current_price),
                        color='#ff5555', alpha=0.2, label='Зона ризику')
    
    ax1.set_title(f'{symbol} - Аналіз рівнів опору для ШОРТУ', 
                 color='white', fontsize=16, pad=20)
    ax1.set_ylabel('Ціна (USDT)', color='white')
    ax1.tick_params(colors='white')
    ax1.grid(True, alpha=0.2, color='gray')
    ax1.legend(loc='upper left', facecolor='#0f0f23', 
              edgecolor='white', labelcolor='white', fontsize=9)
    
    # Графік RSI
    ax2.set_facecolor('#0f0f23')
    
    if len(closes) >= 14:
        df_temp = pd.DataFrame({'close': closes})
        rsi_series = ta.momentum.RSIIndicator(df_temp['close']).rsi()
        
        ax2.plot(times[-len(rsi_series):], rsi_series, 
                color='#ff5555', linewidth=1.5)
        ax2.axhline(y=70, color='#ff8888', linestyle='--', alpha=0.7)
        ax2.axhline(y=30, color='#88ff88', linestyle='--', alpha=0.7)
        ax2.fill_between(times[-len(rsi_series):], rsi_series, 70, 
                        where=(rsi_series >= 70), 
                        color='#ff5555', alpha=0.3, label='Перекупленість')
        ax2.fill_between(times[-len(rsi_series):], rsi_series, 30, 
                        where=(rsi_series <= 30), 
                        color='#44ff44', alpha=0.3, label='Перепроданість')
    
    ax2.set_xlabel('Свічки (15хв)', color='white')
    ax2.set_ylabel('RSI', color='white')
    ax2.set_ylim(0, 100)
    ax2.tick_params(colors='white')
    ax2.grid(True, alpha=0.2, color='gray')
    ax2.legend(facecolor='#0f0f23', edgecolor='white', labelcolor='white')
    
    plt.tight_layout()
    
    # Збереження
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', 
                facecolor='#0f0f23', edgecolor='none')
    plt.close()
    buf.seek(0)
    
    return buf

# ===== ПОШУК ШОРТ-СИГНАЛІВ БІЛЯ ОПОРУ =====
def find_short_signals_near_resistance():
    """Знайти монети біля рівнів опору для шорту"""
    market_data = get_market_data()
    signals = []
    
    if not market_data:
        return signals
    
    # Сортуємо за зростанням (шукаємо монети що виросли)
    sorted_coins = sorted(market_data, 
                         key=lambda x: float(x.get('priceChangePercent', 0)), 
                         reverse=True)[:50]  # Топ-50 за зростанням
    
    for coin in sorted_coins:
        try:
            symbol = coin.get("symbol", "")
            
            # Тільки USDT пари
            if not symbol.endswith("USDT"):
                continue
            
            current_price = float(coin.get("lastPrice", 0))
            price_change = float(coin.get("priceChangePercent", 0))
            volume = float(coin.get("quoteVolume", 0))
            
            # Фільтр: монета повинна бути в рості (>3%)
            if price_change < 3:
                continue
            
            # Фільтр обсягу
            if volume < MIN_VOLUME:
                continue
            
            # Отримуємо свічки для аналізу
            candles = get_klines(symbol, "15m", 100)
            if len(candles) < 30:
                continue
            
            # Знаходимо рівні опору
            resistance_levels = find_strong_resistance_levels(candles)
            if not resistance_levels:
                continue
            
            # Визначаємо найближчий опір та дистанцію
            nearest_resistance, distance = calculate_price_distance(
                current_price, resistance_levels
            )
            
            # Фільтр: повинні бути ближче ніж на 2% до опору
            if distance > 2 or distance < 0.1:
                continue
            
            # Перевіряємо свічку відбою
            rejection_pattern = detect_rejection_pattern(
                candles, nearest_resistance['price']
            )
            
            # Технічні індикатори
            indicators = calculate_technical_indicators(candles)
            
            # Стакан ордерів
            order_book = get_order_book(symbol)
            sell_pressure = sum([float(ask[1]) for ask in order_book.get("asks", [])[:5]])
            buy_pressure = sum([float(bid[1]) for bid in order_book.get("bids", [])[:5]])
            pressure_ratio = sell_pressure / buy_pressure if buy_pressure > 0 else 1
            
            # Розраховуємо силу сигналу
            signal_score = 0
            if distance < 1:
                signal_score += 2
            if rejection_pattern:
                signal_score += 2
            if indicators['rsi'] > RSI_OVERBOUGHT:
                signal_score += 2
            if pressure_ratio > 1.2:
                signal_score += 1
            if indicators['macd_diff'] < 0:
                signal_score += 1
            
            # Мінімальний скор для сигналу
            if signal_score >= 5:
                # Розраховуємо цілі для шорту
                # Знаходимо найближчу підтримку (мінімуми свічок)
                lows = [float(c[3]) for c in candles[-20:]]
                nearest_support = min(lows) if lows else current_price * 0.95
                
                stop_loss = nearest_resistance['price'] * 1.01  # Стоп на 1% вище опору
                take_profit = nearest_support * 0.99  # Тейк на підтримці
                
                risk = stop_loss - current_price
                reward = current_price - take_profit
                risk_reward = reward / risk if risk > 0 else 0
                
                signals.append({
                    'symbol': symbol,
                    'current_price': current_price,
                    'price_change': price_change,
                    'volume': volume,
                    'resistance_levels': resistance_levels[:3],
                    'nearest_resistance': nearest_resistance,
                    'distance_to_resistance': distance,
                    'rejection_pattern': rejection_pattern,
                    'indicators': indicators,
                    'pressure_ratio': round(pressure_ratio, 2),
                    'signal_score': signal_score,
                    'stop_loss': round(stop_loss, 6),
                    'take_profit': round(take_profit, 6),
                    'risk_reward': round(risk_reward, 2),
                    'candles': candles[-50:]  # Для графіка
                })
                
        except Exception as e:
            continue
    
    # Сортуємо за силою сигналу
    signals.sort(key=lambda x: x['signal_score'], reverse=True)
    return signals[:5]  # Тільки топ-5

# ===== TELEGRAM ФУНКЦІЇ =====
def send_telegram_message(text):
    """Відправити повідомлення в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=data, timeout=5)
        return response.status_code == 200
    except:
        return False

def send_telegram_photo(photo_bytes, caption=""):
    """Відправити фото в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    
    # Збережемо в тимчасовий файл
    with open("temp_chart.png", "wb") as f:
        f.write(photo_bytes.getvalue())
    
    try:
        with open("temp_chart.png", "rb") as photo:
            files = {"photo": photo}
            data = {"chat_id": CHAT_ID, "caption": caption[:1024]}
            response = requests.post(url, files=files, data=data, timeout=10)
        return True
    except Exception as e:
        print(f"Помилка відправки фото: {e}")
        return False

def format_short_signal(signal):
    """Форматувати сигнал для шорту"""
    symbol = signal['symbol']
    price = signal['current_price']
    resistance = signal['nearest_resistance']
    distance = signal['distance_to_resistance']
    score = signal['signal_score']
    
    # Визначаємо рівень впевненості
    if score >= 7:
        confidence = "🔴 ВИСОКИЙ"
        emoji = "⚠️🔥⚠️"
    elif score >= 5:
        confidence = "🟡 СЕРЕДНІЙ"
        emoji = "🔻🔻"
    else:
        confidence = "🟢 НИЗЬКИЙ"
        emoji = "🔻"
    
    message = f"""
{emoji} <b>ШОРТ СИГНАЛ БІЛЯ ОПОРУ</b> {emoji}

📊 <b>{symbol}</b>
💰 <b>Поточна ціна:</b> <code>{price:.8f}</code>
📈 <b>Зміна 24г:</b> <code>+{signal['price_change']:.2f}%</code>

🎯 <b>АНАЛІЗ ОПОРУ:</b>
• Найближчий опір: <code>{resistance['price']:.8f}</code>
• Торкань рівня: <code>{resistance['touches']} разів</code>
• Дистанція: <code>{distance:.2f}%</code>
• Паттерн: <code>{signal['rejection_pattern'] or "Очікуємо відбою"}</code>

📊 <b>ТЕХНІЧНІ ІНДИКАТОРИ:</b>
• RSI: <code>{signal['indicators']['rsi']}</code> {"(ПЕРЕКУПЛЕНІСТЬ)" if signal['indicators']['rsi'] > 70 else ""}
• MACD: <code>{signal['indicators']['macd_diff']:.4f}</code>
• Stochastic: K={signal['indicators']['stoch_k']}, D={signal['indicators']['stoch_d']}
• Тренд: <code>{signal['indicators']['trend']}</code>
• Натиск продавців: <code>{signal['pressure_ratio']}x</code>

⚡ <b>РІВНІ ОПОРУ (ТОП-3):</b>
{chr(10).join([f'{i+1}. <code>{level["price"]:.8f}</code> ({level["touches"]}x, +{level["distance_percent"]:.2f}%)' for i, level in enumerate(signal['resistance_levels'])])}

🎯 <b>ТОРГІВЕЛЬНІ ПАРАМЕТРИ:</b>
• Вхід: <code>{price:.8f}</code>
• Стоп-лос: <code>{signal['stop_loss']:.8f}</code> (+{((signal['stop_loss']/price-1)*100):.2f}%)
• Тейк-профіт: <code>{signal['take_profit']:.8f}</code> (-{((1-signal['take_profit']/price)*100):.2f}%)
• Ризик/Прибуток: <code>1:{signal['risk_reward']:.2f}</code>
• Плече: <b>3-5x</b> (рекомендовано)

📈 <b>ОЦІНКА СИГНАЛУ:</b>
• Сила: <code>{score}/10</code>
• Впевненість: {confidence}
• Вірогідність відбою: <code>{min(85, score * 12)}%</code>

💡 <b>СТРАТЕГІЯ ШОРТУ:</b>
1. Вхід: при досягненні <code>{resistance['price']:.8f}</code>
2. Стоп: вище рівня опору на 1%
3. Тейк 1: 50% на -1% (перша підтримка)
4. Тейк 2: 50% на -2-3% (друга підтримка)
5. Слідкувати за RSI < 30 для виходу

⚠️ <b>РИЗИКИ:</b>
• Пробиття опору → негайний вихід
• Загальний ринок у рості → обережність
• Високий ATR ({signal['indicators']['atr_percent']}%) → ширші стопи

⏰ <i>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""
    return message

# ===== ОСНОВНИЙ ЦИКЛ =====
def main():
    """Головна функція бота"""
    print("=" * 70)
    print("🤖 MEXC SHORT SIGNALS BOT - РІВНІ ОПОРУ")
    print("=" * 70)
    
    # Тестове повідомлення
    send_telegram_message("🤖 <b>Short Resistance Bot запущено!</b>\n🎯 Пошук шортів біля рівнів опору")
    
    sent_signals = {}
    cycle = 0
    
    while True:
        cycle += 1
        current_time = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n🔁 Цикл #{cycle} | {current_time}")
        print("🎯 Сканую ринок на шорти біля опорів...")
        
        try:
            # Пошук сигналів
            signals = find_short_signals_near_resistance()
            
            if not signals:
                print("📭 Сигналів не знайдено")
            else:
                print(f"🎯 Знайдено {len(signals)} шорт-кандидатів біля опорів")
                
                for signal in signals:
                    symbol = signal['symbol']
                    
                    # Уникаємо дублікатів
                    if symbol in sent_signals:
                        time_passed = time.time() - sent_signals[symbol]
                        if time_passed < 10800:  # 3 години
                            print(f"⏭️ Пропускаю {symbol} (нещодавній сигнал)")
                            continue
                    
                    print(f"🔍 Обробляю {symbol} (опір: {signal['nearest_resistance']['price']:.6f}, скор: {signal['signal_score']}/10)")
                    
                    # Створюємо графік
                    chart = create_resistance_chart(
                        symbol,
                        signal['candles'],
                        signal['resistance_levels'],
                        signal['current_price']
                    )
                    
                    # Відправляємо графік
                    if chart:
                        chart_caption = f"📊 {symbol} | Ціна: {signal['current_price']:.6f} | Опір: {signal['nearest_resistance']['price']:.6f}"
                        if send_telegram_photo(chart, chart_caption):
                            print(f"📸 Графік відправлено для {symbol}")
                        time.sleep(1)
                    
                    # Відправляємо детальний сигнал
                    message = format_short_signal(signal)
                    if send_telegram_message(message):
                        print(f"✅ Шорт-сигнал відправлено: {symbol}")
                        sent_signals[symbol] = time.time()
                        
                        # Логування
                        with open("short_resistance_log.txt", "a") as f:
                            log_entry = f"{current_time} | {symbol} | Ціна: {signal['current_price']:.6f} | Опір: {signal['nearest_resistance']['price']:.6f} | Скор: {signal['signal_score']}\n"
                            f.write(log_entry)
                    else:
                        print(f"❌ Помилка відправки: {symbol}")
                    
                    # Затримка між сигналами
                    time.sleep(3)
            
            # Статус кожні 10 циклів
            if cycle % 10 == 0:
                status_msg = f"""
📊 <b>Статус Short Resistance Bot</b>
⏳ Працює: {cycle * CHECK_INTERVAL // 60} хв
🔁 Циклів: {cycle}
📉 Сигналів сьогодні: {len(sent_signals)}
🎯 Наступний сканер через {CHECK_INTERVAL // 60} хв
                """
                send_telegram_message(status_msg)
                print("📊 Статус відправлено")
            
            # Чекаємо перед наступною перевіркою
            print(f"⏳ Наступна перевірка через {CHECK_INTERVAL // 60} хвилин...")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n🛑 Бот зупинено користувачем")
            send_telegram_message("🛑 <b>Short Resistance Bot зупинено</b>")
            break
        except Exception as e:
            print(f"⚠️ Помилка в циклі: {e}")
            time.sleep(60)

# ===== ЗАПУСК =====
if __name__ == "__main__":
    print("⚙️  Запускаю Short Resistance Bot...")
    main()
