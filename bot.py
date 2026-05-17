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

# --- FIXED BINANCE CONNECTION FOR INDIA/RESTRICTED REGIONS ---
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {
        'adjustForTimeDifference': True,
    },
    # Agar aap normal system pe ho, toh ye alternative regional URLs use karega
    'urls': {
        'api': {
            'public': 'https://api.binance.me/api',
            'private': 'https://api.binance.me/api',
        }
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
    sessions = [("08:30", "11:30"), ("12:30", "16:30"), ("17:30", "19:30"), ("20:30", "22:30")]
    for start, end in sessions:
        if start <= now <= end:
            return True
    return False

def check_strategy():
    # Data fetch karna
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

    if buy_signal:
        send_telegram_msg(f"🚀 BUY SIGNAL: {SYMBOL} on 1H timeframe!")
    elif sell_signal:
        send_telegram_msg(f"🔻 SELL SIGNAL: {SYMBOL} on 1H timeframe!")

# Infinite Loop
print("Bot Start Ho Gaya Hai...")
while True:
    try:
        check_strategy()
        time.sleep(60) # Har ek minute me check karega close ke liye
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(30)
