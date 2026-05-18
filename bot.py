import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime
import pytz

# --- Configuration ---
# Binance Futures (USDT-M Perpetual) ke liye symbol format 'ETH/USDT' hota hai
SYMBOL = 'ETH/USDT'  
TIMEFRAME = '1h'
EMA_LENGTH = 28
MIN_PERCENT = 0.4
TELEGRAM_TOKEN = '8203153392:AAFbZ23HI0QQnIDZSh22bsg2IUzBnnGtBBo'
CHAT_ID = '6036761046'

# Binance USDT-Margined Futures Market Configuration
exchange = ccxt.binanceusdm({
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'  # Isse Binance Futures market ka data aayega
    }
})

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
        requests.get(url)
    except Exception as e:
        print(f"Telegram error: {e}")

def is_any_session_active():
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz).strftime('%H:%M')
    # Sessions: 08:30-11:30, 12:30-16:30, 17:30-19:30, 20:30-22:30
    sessions = [("09:29", "09:30"), ("10:29", "10:30"), ("11:29", "11:30"), ("13:29", "13:30"), ("14:29","14:30"), ("15:29", "15:30"), ("16:29", "16:30"), ("18:29", "18:30"), ("19:29", "19:30"), ("21:29", "21:30"), ("22:29", "22:30")]
    for start, end in sessions:
        if start <= now <= end:
            return True
    return False

def check_strategy():
    # Binance Futures Data fetch karna
    bars = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=100)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    # Indicators
    df['ema'] = ta.ema(df['close'], length=EMA_LENGTH)

    # Current Candle (Index -1) and Previous Candle (Index -2)
    c = df.iloc[-1]
    p = df.iloc[-2]

    body_size = abs(c['close'] - c['open'])
    total_range = c['high'] - c['low']
    is_strong_body = body_size > (total_range * 0.5)

    p_high_low_avg = (p['high'] + p['low']) / 2
    candle_prev_range = p['high'] - p['low']
    price_percentage = (candle_prev_range / p['close']) * 100

    # Signals
    is_session = is_any_session_active()
    nb1 = is_strong_body and c['close'] > c['ema']
    ns1 = is_strong_body and c['close'] < c['ema']

    buy_signal = is_session and price_percentage >= MIN_PERCENT and (c['low'] < p['low']) and c['close'] > p_high_low_avg and nb1
    sell_signal = is_session and price_percentage >= MIN_PERCENT and (c['high'] > p['high']) and c['close'] < p_high_low_avg and ns1

    # --- LIVE FUTURES PRICE PRINTING ---
    current_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%H:%M:%S')
    print(f"[{current_time}] {SYMBOL} (Binance Futures) Live Price: {c['close']} | EMA({EMA_LENGTH}): {c['ema']:.2f}")

    if buy_signal:
        send_telegram_msg(f"🚀 BUY SIGNAL: {SYMBOL} (Binance Futures) on 1H timeframe! Price: {c['close']}")
        print("-> BUY SIGNAL SENT TO TELEGRAM!")
    elif sell_signal:
        send_telegram_msg(f"🔻 SELL SIGNAL: {SYMBOL} (Binance Futures) on 1H timeframe! Price: {c['close']}")
        print("-> SELL SIGNAL SENT TO TELEGRAM!")

# Infinite Loop
print("Binance Futures Bot Start Ho Gaya Hai...")
while True:
    try:
        check_strategy()
        time.sleep(60) # Har 60 seconds me check aur update karega
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(30)
