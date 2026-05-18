import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime
import pytz

# --- Configuration ---
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
        'defaultType': 'future'  
    }
})

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {'chat_id': CHAT_ID, 'text': message}
        requests.post(url, json=payload) # POST request is more reliable
    except Exception as e:
        print(f"Telegram error: {e}")

def is_any_session_active():
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz).strftime('%H:%M')
    
    # FIX: Pure Session Windows define kiye hain (sirf 1 minute ka nahi)
    # Crypto 24/7 hai, aap isko apne hisab se ghanto mein customize kar sakte hain
    sessions = [
        ("08:30", "11:30"), 
        ("12:30", "16:30"), 
        ("17:30", "19:30"), 
        ("20:30", "22:30")
    ]
    for start, end in sessions:
        if start <= now <= end:
            return True
    return False

def check_strategy():
    try:
        # FIX: Limit badha kar 200 ki taaki EMA calculation sahi ho
        bars = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        # Indicators
        df['ema'] = ta.ema(df['close'], length=EMA_LENGTH)

        # Current Candle (Index -1) and Previous Candle (Index -2)
        c = df.iloc[-1]
        p = df.iloc[-2]

        body_size = abs(c['close'] - c['open'])
        total_range = c['high'] - c['low']
        if total_range == 0: return # Doji/Zero movement error protection
        
        is_strong_body = body_size > (total_range * 0.5)

        p_high_low_avg = (p['high'] + p['low']) / 2
        candle_prev_range = p['high'] - p['low']
        price_percentage = (candle_prev_range / p['close']) * 100

        # Signals
        is_session = is_any_session_active()
        nb1 = is_strong_body and c['close'] > c['ema']
        ns1 = is_strong_body and c['close'] < c['ema']

        buy_signal = close > open
        sell_signal = close < open 

        # --- LIVE FUTURES PRICE PRINTING ---
        current_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{current_time}] {SYMBOL} Price: {c['close']} | EMA: {c['ema']:.2f} | Session Active: {is_session}")

        if buy_signal:
            send_telegram_msg(f"🚀 BUY SIGNAL: {SYMBOL} (1H Timeframe)!\nPrice: {c['close']}\nEMA: {c['ema']:.2f}")
            print("-> BUY SIGNAL SENT TO TELEGRAM!")
        elif sell_signal:
            send_telegram_msg(f"🔻 SELL SIGNAL: {SYMBOL} (1H Timeframe)!\nPrice: {c['close']}\nEMA: {c['ema']:.2f}")
            print("-> SELL SIGNAL SENT TO TELEGRAM!")
            
    except Exception as e:
        print(f"Strategy Error: {e}")

# Infinite Loop
print("Binance Futures Bot Start Ho Gaya Hai...")

while True:
    try:
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)
        
        # FIX: Chunki aapka timeframe 1 Hour ('1h') hai, to hum har ghante ke AKHRI MINUTE (:59) ke 
        # 58th second par check karenge taaki close hone wali candle ka reliable data mile.
        if now.minute == 59 and now.second == 58:
            print(f"\n[Candle Closing] Strategy checking at {now.strftime('%H:%M:%S')}...")
            check_strategy()
            time.sleep(3) # Loop ko double-triggering se rokne ke liye 3 sec ka sleep
        else:
            time.sleep(0.8) # CPU usage kam rakhne ke liye chhota sleep
            
    except Exception as e:
        print(f"Loop Error: {e}")
        time.sleep(10)
