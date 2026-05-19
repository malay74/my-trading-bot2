import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime, timedelta
import pytz

# --- Configuration ---
SYMBOL = 'ETH/USDT'  
# FIX: Hum 30m data uthayenge custom 1H candle banane ke liye
TIMEFRAME = '30m' 
EMA_LENGTH = 28
MIN_PERCENT = 0.4
TELEGRAM_TOKEN = '8203153392:AAGLC-NYca3qd7Iu6J-oKsn1YjLKSZIDse0'
CHAT_ID = '6036761046'

exchange = ccxt.binanceusdm({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={'chat_id': CHAT_ID, 'text': message})
    except Exception as e:
        print(f"Telegram error: {e}")

def is_any_session_active():
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz).strftime('%H:%M')
    sessions = [("12:31", "16:30"), ("17:31", "19:30"), ("20:31", "22:30")]
    for start, end in sessions:
        if start <= now <= end:
            return True
    return False

def check_strategy():
    try:
        # 1. 30 Minutes ki candles fetch karna (Safely 400 bars taaki conversion sahi ho)
        bars = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=400)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Timestamp ko readable datetime mein badalna aur Kolkata timezone lagana
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        df.set_index('datetime', inplace=True)

        # FIX: 30-min ki candles ko 1-Hour custom candle mein convert karna (Offset 30 Min ke sath)
        # Isse candle automatic 17:30 se 18:30 ke format mein group ho jayengi
        custom_1h = df.resample('1h', offset='30min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        # 2. Indicators (Ab custom 1H candles par EMA calculation hoga)
        custom_1h['ema'] = ta.ema(custom_1h['close'], length=EMA_LENGTH)

        # Current (Index -1) aur Previous (Index -2) Custom Candles
        c = custom_1h.iloc[-1]
        p = custom_1h.iloc[-2]

        body_size = abs(c['close'] - c['open'])
        total_range = c['high'] - c['low']
        if total_range == 0: return 
        
        is_strong_body = body_size > (total_range * 0.5)
        p_high_low_avg = (p['high'] + p['low']) / 2
        candle_prev_range = p['high'] - p['low']
        price_percentage = (candle_prev_range / p['close']) * 100

        # Signals
        is_session = is_any_session_active()
        nb1 = is_strong_body and c['close'] > c['ema']
        ns1 = is_strong_body and c['close'] < c['ema']

        buy_signal = is_session and c['close'] > c['open']
        sell_signal = is_session and c['close'] < c['open']

        # --- LIVE STATUS PRINT ---
        candle_start = custom_1h.index[-1].strftime('%H:%M')
        print(f"[{datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%H:%M:%S')}] "
              f"Custom 1H Candle ({candle_start} ki Close): {c['close']} | EMA: {c['ema']:.2f}")

        if buy_signal:
            send_telegram_msg(f"🚀 BUY SIGNAL: {SYMBOL} (Custom 1H: {candle_start})!\nPrice: {c['close']}\nEMA: {c['ema']:.2f}")
            print("-> BUY SIGNAL SENT TO TELEGRAM!")
        elif sell_signal:
            send_telegram_msg(f"🔻 SELL SIGNAL: {SYMBOL} (Custom 1H: {candle_start})!\nPrice: {c['close']}\nEMA: {c['ema']:.2f}")
            print("-> SELL SIGNAL SENT TO TELEGRAM!")
            
    except Exception as e:
        print(f"Strategy Error: {e}")

# Infinite Loop
print("Binance Custom 1H Futures Bot Start Ho Gaya Hai...")

while True:
    try:
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)
        
        # FIX: Ab candle har ghante ke 29th minute ke 58th second par close hogi (Jaise: 18:29:58, 19:29:58)
        if now.minute == 29 and now.second == 58:
            print(f"\n[Custom Candle Closing] Checking strategy at {now.strftime('%H:%M:%S')}...")
            check_strategy()
            time.sleep(3) 
        else:
            time.sleep(0.8) 
            
    except Exception as e:
        print(f"Loop Error: {e}")
        time.sleep(10)
