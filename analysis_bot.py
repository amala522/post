print("🚀 DEBUG: ANALIZ BOTU BASLADI!")

import os
import time
import json
import requests
import pandas as pd
import mplfinance as mpf
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
from beem import Hive
from beembase.operations import Comment
from beem.transactionbuilder import TransactionBuilder

# --- AYARLAR ---
HIVE_NODE = "https://api.hive.blog"
USERNAME = os.getenv("HIVE_USERNAME")
POSTING_KEY = os.getenv("HIVE_POSTING_KEY")

MAIN_TAG = "hive-120022" # Crypto News topluluğu
TAGS = ["hive-120022", "hive", "crypto", "trading", "technicalanalysis"]

def get_hive_data():
    """Binance'den HIVE/USDT 1 saatlik son 50 mum verisini çeker"""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "HIVEUSDT", "interval": "1h", "limit": 50}
    
    try:
        response = requests.get(url, params=params, timeout=10).json()
        
        # Binance bazen hata durumunda sözlük (dict) döndürür
        if isinstance(response, dict):
            print(f"❌ Binance API Hatası: {response}")
            return None
            
        if not response or len(response) == 0:
            print("❌ Binance'den veri alınamadı (boş yanıt).")
            return None
            
        df = pd.DataFrame(response, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'quote_volume', 'trades', 'taker_buy_base', 
            'taker_buy_quote', 'ignore'
        ])
        
        # Veriyi sayısal formata çevir
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df.set_index('time', inplace=True)
        
        # Boş veya hatalı satırları temizle
        df.dropna(inplace=True)
        
        print(f"✅ {len(df)} satır veri başarıyla çekildi.")
        return df
        
    except Exception as e:
        print(f"❌ Veri çekme hatası: {e}")
        return None

def calculate_indicators(df):
    """RSI ve SMA hesaplar"""
    df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()
    df['SMA20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
    return df

def generate_chart(df):
    """Son 24 saati (24 mum) koyu temalı grafik olarak çizer ve kaydeder"""
    # Sadece son 24 saati al
    plot_df = df.tail(24)
    
    if plot_df.empty:
        print("❌ Çizilecek veri yok!")
        return False
    
    # Koyu tema ayarları
    mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', edge='inherit', wick='inherit', volume='inherit')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', gridcolor='#2d2d2d', facecolor='#121212', edgecolor='#121212')
    
    # Grafiği kaydet
    mpf.plot(plot_df, type='candle', style=s, volume=True, 
             title='HIVE/USDT 24H Chart', 
             savefig='hive_chart.png', figsize=(10, 6))
    print("✅ Grafik çizildi: hive_chart.png")
    return True

def upload_image():
    """Grafiği ücretsiz 0x0.st sunucusuna yükler"""
    try:
        url = "https://0x0.st"
        with open('hive_chart.png', 'rb') as f:
            response = requests.post(url, files={'file': f}, timeout=10)
        if response.status_code == 200:
            return response.text.strip()
        else:
            print(f"❌ Resim yükleme hatası: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Resim yükleme hatası: {e}")
        return None

def generate_text(current_price, rsi, sma, support, resistance, image_url):
    """Blogger uslubu, kısa ve net metin"""
    
    rsi_status = "oversold" if rsi < 30 else ("overbought" if rsi > 70 else "neutral")
    trend_status = "bullish" if current_price > sma else "bearish"
    
    # Resim URL'si yoksa uyarı metni ekle
    image_md = f"![HIVE 24h Chart]({image_url})" if image_url else "*(Chart image upload failed)*"
    
    text = f"""# HIVE/USDT 24 Hour Market Update

Hello Hive friends.

Here is the daily technical look at HIVE. I pulled the 1-hour chart data from Binance to see what the buyers and sellers are doing today.

{image_md}

### Current Price Action
HIVE is trading at ${current_price:.4f}. The 24-hour trend shows clear momentum in the market.

### Technical Indicators
The 14-period RSI is at {rsi:.2f}. This level tells us the asset is currently in the {rsi_status} zone. 

The 20-period Simple Moving Average is at ${sma:.4f}. Price is currently {trend_status} against this line. This usually means the short-term trend is {trend_status}.

### Key Levels to Watch
Support is sitting around ${support:.4f}. Resistance is near ${resistance:.4f}. 

What do you think about the chart today? Let me know in the comments.

#hive #crypto #trading #technicalanalysis
"""
    return f"HIVE/USDT 24H Technical Analysis - {time.strftime('%Y-%m-%d')}", text

def publish_post(title, body):
    try:
        hive = Hive(node=HIVE_NODE, nobroadcast=False)
        permlink = f"hive-analysis-{time.strftime('%Y-%m-%d')}"
        json_metadata = json.dumps({"tags": TAGS, "app": "hive-analysis-bot/1.0"})
        
        print("📡 Publishing to Hive...")
        
        op = Comment(
            parent_author="",
            parent_permlink=MAIN_TAG,
            author=USERNAME,
            permlink=permlink,
            title=title,
            body=body,
            json_metadata=json_metadata
        )
        
        tx = TransactionBuilder(blockchain_instance=hive)
        tx.appendOps(op)
        tx.appendWif(POSTING_KEY)
        tx.sign()
        response = tx.broadcast()
        
        if response and isinstance(response, dict) and "signatures" in response:
            print(f"✅ SUCCESSFULLY PUBLISHED!")
        else:
            print(f"⚠️ Blockchain yanıtı alındı.")
            
    except Exception as e:
        print(f"❌ Publishing Error: {e}")

def main():
    print("=" * 60)
    print("🐝 Hive Analysis Bot Starting...")
    print("=" * 60)
    
    if not USERNAME or not POSTING_KEY:
        print("❌ ERROR: HIVE_USERNAME or HIVE_POSTING_KEY is missing in Secrets!")
        return
    
    print("📡 Fetching Binance Data...")
    df = get_hive_data()
    
    if df is None or df.empty:
        print("❌ Veri alınamadı, bot durduruldu.")
        return
        
    print("📊 Calculating Indicators...")
    df = calculate_indicators(df)
    
    print("📈 Generating Chart...")
    chart_success = generate_chart(df)
    
    if not chart_success:
        print("❌ Grafik oluşturulamadı, bot durduruldu.")
        return
    
    current_price = df['close'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    sma = df['SMA20'].iloc[-1]
    support = df['low'].tail(24).min()
    resistance = df['high'].tail(24).max()
    
    print(f"   Price: {current_price}, RSI: {rsi:.2f}, SMA: {sma:.4f}")
    
    print("📤 Uploading Image...")
    image_url = upload_image()
    
    print("📝 Generating Text...")
    title, body = generate_text(current_price, rsi, sma, support, resistance, image_url)
    
    print("🚀 Publishing...")
    publish_post(title, body)
    print("=" * 60)
    print("✅ Bot finished successfully!")

if __name__ == "__main__":
    main()
