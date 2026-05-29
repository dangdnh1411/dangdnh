# ════════════════════════════════════════════════════════════════════════════════
# ██████╗ ███████╗ ██████╗ ██████╗                                        ██████╗ 
# ██╔══██╗██╔════╝██╔═══██╗██╔══██╗                                       ╚════██╗
# ██████╔╝█████╗  ██║   ██║██║  ██║█████╗  █████╗ ███╗   ██╗ █████╗       █████╔╝
# ██╔══██╗██╔══╝  ██║   ██║██║  ██║╚═══██╗██╔══██╗████╗  ██║██╔══██╗      ╚═══██╗
# ██║  ██║███████╗╚██████╔╝██████╔╝██████╔╝███████║██╔██╗ ██║███████║ ██████╔╝
# ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ 
# 
# Pro Trader Terminal v5.3 - Production Edition
# Multi-Source Data • Enhanced Signals • Production Ready
# ════════════════════════════════════════════════════════════════════════════════

# ============================================================
# 1. IMPORTS
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime, timedelta
import re
import sys
import traceback
from io import StringIO
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Pro Trader Terminal v5.3",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Main theme */
    .stApp { background: #0e1117; }
    
    /* Headers */
    h1, h2, h3 { color: #ffffff !important; }
    
    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #1e2530 0%, #161b22 100%);
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
        margin: 5px 0;
    }
    
    /* Tab styling */
    .tab-label {
        font-size: 14px;
        font-weight: 600;
        color: #58a6ff;
        margin-bottom: 10px;
        display: block;
    }
    
    /* Signal styles */
    .signal-strong-buy {
        background: linear-gradient(135deg, #00d97e 0%, #00b369 100%);
        padding: 20px; border-radius: 10px; text-align: center;
        box-shadow: 0 4px 15px rgba(0,217,126,0.4);
    }
    .signal-strong-sell {
        background: linear-gradient(135deg, #ff4757 0%, #cc1133 100%);
        padding: 20px; border-radius: 10px; text-align: center;
        box-shadow: 0 4px 15px rgba(255,71,87,0.4);
    }
    .signal-neutral {
        background: linear-gradient(135deg, #748ffc 0%, #5c7cfa 100%);
        padding: 20px; border-radius: 10px; text-align: center;
        box-shadow: 0 4px 15px rgba(116,143,252,0.4);
    }
    
    /* Sidebar */
    .css-1d391kg { background-color: #161b22; }
    
    /* Success/Error banners */
    .success-box {
        padding: 10px; border-radius: 5px;
        background: rgba(0,217,126,0.1); border-left: 4px solid #00d97e;
    }
    .error-box {
        padding: 10px; border-radius: 5px;
        background: rgba(255,71,87,0.1); border-left: 4px solid #ff4757;
    }
    
    /* Dataframe */
    .dataframe {
        border: none !important;
    }
    .dataframe thead th {
        background: #1e2530 !important;
        color: white !important;
    }
    .dataframe tbody tr:hover {
        background: rgba(88,166,255,0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. CONFIGURATION
# ============================================================

# Supported sectors and their peer stocks
SECTOR_PEERS = {
    "Thép": ["HPG", "HSG", "NKG"],
    "Ngân hàng": ["VPB", "VCB", "TCB", "CTG", "BID", "STB", "MBB", "ACB"],
    "Bất động sản": ["VRE", "NVL", "DIG", "KDH", "CRE", "ASM"],
    "Chứng khoán": ["SSI", "VND", "HCM", "TCBS", "BSI", "VIS"],
    "Bán lẻ": ["MWG", "PNJ", "DGW", "FPT", "PET"],
    "Dầu khí": ["PLX", "POW", "GAS", "PVT", "Oil"],
    "Thực phẩm": ["VNM", "MSB", "KDC", "SBT", "GTN"],
    "Công nghệ": ["FPT", "CMG", "VGI", "SRA"],
    "Xây dựng": ["VCG", "HDG", "C4G", "ROS"]
}

# All valid symbols in one list
ALL_SYMBOLS = [sym for symbols in SECTOR_PEERS.values() for sym in symbols]

# Date configuration
end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

# ============================================================
# 3. INPUT VALIDATION MODULE
# ============================================================

def validate_symbol(sym: str) -> tuple[bool, str]:
    """
    Validate stock symbol format
    Returns: (is_valid, message)
    """
    if not sym or not isinstance(sym, str):
        return False, "Mã cổ phiếu không được trống"
    
    sym = sym.strip().upper()
    
    # Check 3 letters format
    if not re.match(r'^[A-Z]{3}$', sym):
        return False, "Mã cổ phiếu phải là 3 chữ cái (VD: HPG, VPB)"
    
    # Check if in known symbols (warning only)
    if sym not in ALL_SYMBOLS:
        return True, f"Cảnh báo: {sym} chưa có trong danh sách mẫu, vẫn tiếp tục..."
    
    return True, ""

def clear_cache():
    """Clear all cached data in session state"""
    keys_to_clear = ['stock_data', 'scan_results', 'scan_key', 'last_symbol', 'price_data', 'fundamental_data']
    
    for key in keys_to_clear:
        if key in st.session_state:
            try:
                del st.session_state[key]
            except:
                pass
    
    # Clear Streamlit cache
    st.cache_data.clear()
    st.cache_resource.clear()
    
    st.success("🗑️ Đã xóa cache thành công! Trang sẽ reload...")
    st.rerun()

# ============================================================
# 4. DATA FETCHING MODULE (Multi-Source with Fallback)
# ============================================================

@st.cache_data(ttl=60)
def fetch_price(sym: str, days: int, interval: str = "1D") -> tuple[pd.DataFrame, dict]:
    """
    Fetch price data với multi-source fallback system
    Priority: KBS (vnstock) → CafeF → Yahoo Finance
    Returns: (dataframe, info_dict)
    """
    sym = sym.upper().strip()
    info = {"source": None, "runtime": 0, "status": "pending"}
    
    start_time = time.time()
    
    # ===============================
    # SOURCE 1: KBS via vnstock (Ưu tiên cao nhất)
    # ===============================
    try:
        from vnstock import Quote
        df = Quote(symbol=sym, source="KBS").history(
            start=start_date, end=end_date, interval=interval
        )
        
        # Rename columns to standard format
        df = df.rename(columns={
            'close': 'Close', 
            'volume': 'Volume', 
            'open': 'Open', 
            'high': 'High', 
            'low': 'Low'
        })
        df = df.dropna(subset=['Close'])
        
        if len(df) > 1:
            info["source"] = "KBS ✅"
            info["runtime"] = round(time.time() - start_time, 2)
            info["status"] = "success"
            info["rows"] = len(df)
            return df, info
            
    except ImportError:
        info["source"] = "vnstock not installed"
    except Exception as e:
        info["source"] = f"KBS Error: {str(e)[:30]}"
    
    # ===============================
    # SOURCE 2: CafeF (Fallback)
    # ===============================
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        url = f"https://s.cafef.vn/Ajax/PageNew/DataHistory/PriceHistory/{sym}.chn"
        params = {
            "securitiesCode": sym,
            "startDate": start_date,
            "endDate": end_date,
            "page": 1
        }
        
        r = requests.get(url, params=params, headers=headers, timeout=10)
        
        if r.status_code == 200 and r.text:
            data = r.json()
            if 'data' in data and len(data['data']) > 0:
                rows = data['data'][::-1]  # Reverse to chronological order
                df = pd.DataFrame(rows)
                
                # Standard column names
                df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Avg', 'Change']
                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                
                df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
                df = df.set_index('Date')
                df = df.apply(pd.to_numeric, errors='coerce').dropna()
                
                if len(df) > 1:
                    info["source"] = "CafeF ✅"
                    info["runtime"] = round(time.time() - start_time, 2)
                    info["status"] = "success"
                    info["rows"] = len(df)
                    return df, info
                    
    except Exception as e:
        info["source"] = f"CafeF Error: {str(e)[:30]}"
    
    # ===============================
    # SOURCE 3: Yahoo Finance (Last Resort)
    # ===============================
    try:
        import yfinance as yf
        
        # Yahoo uses .VN suffix for Vietnam
        yf_sym = f"{sym}.VN"
        ticker = yf.Ticker(yf_sym)
        df = ticker.history(start=start_date, end=end_date, interval=interval)
        
        if len(df) > 1:
            df = df.rename(columns={
                'Open': 'Open', 
                'High': 'High', 
                'Low': 'Low',
                'Close': 'Close', 
                'Volume': 'Volume'
            })
            
            # Remove splits column if exists
            if 'Stock Splits' in df.columns:
                df = df.drop('Stock Splits', axis=1)
            
            df = df.dropna()
            
            if len(df) > 1:
                info["source"] = "Yahoo ✅"
                info["runtime"] = round(time.time() - start_time, 2)
                info["status"] = "success"
                info["rows"] = len(df)
                return df, info
                
    except ImportError:
        info["source"] = "yfinance not installed"
    except Exception as e:
        info["source"] = f"Yahoo Error: {str(e)[:30]}"
    
    # ===============================
    # ALL SOURCES FAILED
    # ===============================
    info["status"] = "failed"
    info["runtime"] = round(time.time() - start_time, 2)
    return pd.DataFrame(), info

@st.cache_data(ttl=300)
def fetch_ratio(sym: str) -> pd.DataFrame:
    """Fetch financial ratios"""
    try:
        url = f"https://apipub.vietstock.vn/financefinance/get-fundamental-data"
        params = {"symbol": sym}
        r = requests.get(url, params=params, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            if data:
                return pd.DataFrame(data)
    except:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_fundamentals(sym: str) -> dict:
    """Fetch basic fundamental data"""
    try:
        url = f"https://apipub.vietstock.vn/financefinance/get-balance-sheet-data"
        params = {"symbol": sym}
        r = requests.get(url, params=params, timeout=10)
        
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {}

# ============================================================
# 5. TECHNICAL INDICATORS
# ============================================================

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to dataframe"""
    if df is None or len(df) < 20:
        return df
    
    # Copy to avoid SettingWithCopyWarning
    df = df.copy()
    
    # Trend Indicators
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal_Line']
    
    # Bollinger Bands
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * 2)
    df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
    
    # Moving Averages
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    
    # Volatility
    df['ATR'] = calculate ATR(df) if len(df) > 14 else 0
    
    # Volume indicators
    df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
    
    # Price change
    df['Price_Change'] = df['Close'].pct_change()
    df['Price_Change_5D'] = df['Close'].pct_change(5)
    df['Price_Change_20D'] = df['Close'].pct_change(20)
    
    return df

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    
    return true_range.rolling(window=period).mean()

# ============================================================
# 6. SIGNAL CALCULATION
# ============================================================

def calculate_signal(df: pd.DataFrame) -> tuple:
    """Calculate trading signal based on multiple indicators"""
    if df is None or len(df) < 2:
        return "KHÔNG ĐỦ DỮ LIỆU", 0, {}
    
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    score = 0
    signals = {}
    
    # === RSI Analysis ===
    rsi = latest.get('RSI', 50)
    signals['RSI'] = rsi
    
    if rsi < 30:
        score += 3  # Oversold - Buy signal
        signals['RSI_Signal'] = "QUÁ BÁN"
    elif rsi < 40:
        score += 2
        signals['RSI_Signal'] = "Gần quá bán"
    elif rsi > 70:
        score -= 3  # Overbought - Sell signal
        signals['RSI_Signal'] = "QUÁ MUA"
    elif rsi > 60:
        score -= 2
        signals['RSI_Signal'] = "Gần quá mua"
    else:
        signals['RSI_Signal'] = "Trung lập"
    
    # === EMA Trend Analysis ===
    ema_20 = latest.get('EMA_20', latest['Close'])
    ema_50 = latest.get('EMA_50', latest['Close'])
    ema_200 = latest.get('EMA_200', latest['Close'])
    current_price = latest['Close']
    
    signals['EMA_20'] = ema_20
    signals['EMA_50'] = ema_50
    signals['EMA_200'] = ema_200
    
    if ema_20 > ema_50:
        score += 2
        signals['EMA_Trend'] = "TĂNG"
        if ema_50 > ema_200:
            score += 1
            signals['EMA_Strength'] = "Rất mạnh"
        else:
            signals['EMA_Strength'] = "Trung bình"
    else:
        score -= 2
        signals['EMA_Trend'] = "GIẢM"
        if ema_50 < ema_200:
            score -= 1
            signals['EMA_Strength'] = "Rất yếu"
        else:
            signals['EMA_Strength'] = "Trung bình"
    
    # Price vs EMA
    if current_price > ema_20:
        score += 1
    else:
        score -= 1
    
    # === MACD Analysis ===
    macd = latest.get('MACD', 0)
    signal_line = latest.get('Signal_Line', 0)
    macd_hist = latest.get('MACD_Hist', 0)
    
    signals['MACD'] = macd
    signals['Signal_Line'] = signal_line
    signals['MACD_Hist'] = macd_hist
    
    if macd > signal_line and macd > 0:
        score += 2
        signals['MACD_Signal'] = "MUA"
    elif macd > signal_line and macd < 0:
        score += 1
        signals['MACD_Signal'] = "Dần hồi phục"
    elif macd < signal_line and macd < 0:
        score -= 2
        signals['MACD_Signal'] = "BÁN"
    else:
        score -= 1
        signals['MACD_Signal'] = "Dần suy yếu"
    
    # === Bollinger Bands Position ===
    bb_upper = latest.get('BB_Upper', current_price)
    bb_lower = latest.get('BB_Lower', current_price)
    bb_middle = latest.get('BB_Middle', current_price)
    
    signals['BB_Upper'] = bb_upper
    signals['BB_Lower'] = bb_lower
    signals['BB_Middle'] = bb_middle
    
    bb_width = bb_upper - bb_lower
    bb_position = (current_price - bb_lower) / bb_width if bb_width > 0 else 0.5
    
    if bb_position < 0.2:
        score += 2
        signals['BB_Position'] = "Gần dưới"
    elif bb_position > 0.8:
        score -= 2
        signals['BB_Position'] = "Gần trên"
    else:
        signals['BB_Position'] = "Giữa"
    
    # === Volume Analysis ===
    vol_ratio = latest.get('Volume_Ratio', 1)
    signals['Volume_Ratio'] = vol_ratio
    
    if vol_ratio > 1.5:
        score += 1
        signals['Volume_Signal'] = "Khối lượng tăng mạnh"
    elif vol_ratio < 0.5:
        score -= 1
        signals['Volume_Signal'] = "Khối lượng thấp"
    else:
        signals['Volume_Signal'] = "Bình thường"
    
    # === Final Signal ===
    if score >= 4:
        final_signal = "MUA MẠNH"
    elif score >= 2:
        final_signal = "TÍCH CỰC"
    elif score <= -4:
        final_signal = "BÁN MẠNH"
    elif score <= -2:
        final_signal = "TIÊU CỰC"
    else:
        final_signal = "TRUNG LẬP"
    
    signals['Score'] = score
    signals['Price'] = current_price
    
    return final_signal, score, signals

# ============================================================
# 7. CHART FUNCTIONS
# ============================================================

def create_candlestick_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Create candlestick chart with indicators"""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        subplot_titles=("", "", "", ""),
        x_title="Thời gian"
    )
    
    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="OHLC",
            increasing_line_color='#00d97e',
            decreasing_line_color='#ff4757',
            increasing_fillcolor='#00d97e',
            decreasing_fillcolor='#ff4757'
        ),
        row=1, col=1
    )
    
    # EMA lines
    if 'EMA_20' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['EMA_20'], 
                      name="EMA20", line=dict(color="#FFD700", width=1.5)),
            row=1, col=1
        )
    
    if 'EMA_50' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['EMA_50'], 
                      name="EMA50", line=dict(color="#FF6B6B", width=1.5)),
            row=1, col=1
        )
    
    if 'EMA_200' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['EMA_200'], 
                      name="EMA200", line=dict(color="#4ECDC4", width=2)),
            row=1, col=1
        )
    
    # Bollinger Bands
    if 'BB_Upper' in df.columns and 'BB_Lower' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['BB_Upper'], 
                      name="BB Upper", line=dict(color="rgba(116,143,252,0.5)", width=1),
                      showlegend=True),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df['BB_Lower'], 
                      name="BB Lower", line=dict(color="rgba(116,143,252,0.5)", width=1),
                      fill='tonexty', fillcolor='rgba(116,143,252,0.1)',
                      showlegend=True),
            row=1, col=1
        )
    
    # Volume
    colors = ['#00d97e' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#ff4757' 
              for i in range(len(df))]
    
    fig.add_trace(
        go.Bar(x=df.index, y=df['Volume'], name="Volume", 
               marker_color=colors, opacity=0.7),
        row=2, col=1
    )
    
    # RSI
    if 'RSI' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['RSI'], name="RSI",
                      line=dict(color="#58a6ff", width=2)),
            row=3, col=1
        )
        # RSI levels
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1,
                     annotation_text="30", annotation_position="bottom right")
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1,
                     annotation_text="70", annotation_position="bottom right")
    
    # MACD
    if 'MACD' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['MACD'], name="MACD",
                      line=dict(color="#58a6ff", width=2)),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df['Signal_Line'], name="Signal",
                      line=dict(color="#ff6b6b", width=2)),
            row=4, col=1
        )
        
        colors_macd = ['#00d97e' if val >= 0 else '#ff4757' 
                       for val in df['MACD_Hist'].fillna(0)]
        fig.add_trace(
            go.Bar(x=df.index, y=df['MACD_Hist'], name="Histogram",
                  marker_color=colors_macd, opacity=0.7),
            row=4, col=1
        )
    
    fig.update_layout(
        height=800,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        title=f"<b>{symbol}</b> - Technical Analysis",
        title_font_size=20,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    
    return fig

def to_excel(df: pd.DataFrame) -> bytes:
    """Convert dataframe to Excel bytes"""
    from io import BytesIO
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, sheet_name='Sheet1', index=True)
    writer.save()
    processed_data = output.getvalue()
    return processed_data

# ============================================================
# 8. SECTOR SCANNER
# ============================================================

def scan_sector(symbols: list, days: int = 30) -> pd.DataFrame:
    """Scan multiple stocks and return comparison table"""
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, sym in enumerate(symbols):
        status_text.text(f"⏳ Đang phân tích {sym}...")
        progress_bar.progress((i + 1) / len(symbols))
        
        try:
            df, info = fetch_price(sym, days)
            
            if len(df) > 0:
                df = add_indicators(df)
                signal, score, signals = calculate_signal(df)
                latest = df.iloc[-1]
                
                results.append({
                    'Mã': sym,
                    'Giá': round(latest['Close'], 2),
                    'RSI': round(signals.get('RSI', 50), 1),
                    'Xu hướng': signals.get('EMA_Trend', 'N/A'),
                    'MACD': signals.get('MACD_Signal', 'N/A'),
                    'Khối lượng': f"{signals.get('Volume_Ratio', 1):.1f}x",
                    'Tín hiệu': signal,
                    'Điểm': score,
                    'Nguồn': info.get('source', 'Unknown')
                })
                
        except Exception as e:
            results.append({
                'Mã': sym,
                'Giá': 'Lỗi',
                'RSI': 'N/A',
                'Xu hướng': 'N/A',
                'MACD': 'N/A',
                'Khối lượng': 'N/A',
                'canonical': 'Lỗi',
                'Điểm': 0,
                'Nguồn': 'Failed'
            })
        
        time.sleep(0.5)  # Rate limiting
    
    status_text.text("✅ Hoàn tất!")
    progress_bar.empty()
    
    return pd.DataFrame(results)

# ============================================================
# 9. MAIN APPLICATION LAYOUT
# ============================================================

def main():
    # === SIDEBAR ===
    with st.sidebar:
        st.markdown("""
            <div style="text-align:center; margin-bottom:15px;">
                <h1 style="font-size:20px; color:#58a6ff;">📊 Pro Trader Terminal</h1>
                <p style="color:#8b949e; font-size:12px;">v5.3 - Production Edition</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # === Symbol Input với Validation ===
        st.markdown("**🔍 Nhập mã cổ phiếu**")
        symbol = st.text_input(
            "Mã cổ phiếu", 
            value="HPG", 
            placeholder="VD: HPG, VPB, SSI",
            label_visibility="collapsed"
        ).upper().strip()
        
        # Validate input
        is_valid, msg = validate_symbol(symbol)
        if not is_valid:
            st.error(f"❌ {msg}")
            st.stop()
        elif "Cảnh báo" in msg:
            st.warning(msg)
        
        st.divider()
        
        # === Time Period ===
        st.markdown("**⏱️ Khoảng thời gian**")
        days = st.slider("", 10, 365, 60, label_visibility="collapsed")
        
        # === Resolution ===
        st.markdown("**📊 Độ phân giải**")
        resolution = st.selectbox(
            "Resolution",
            ["1D", "1H", "15m", "30m"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # === Control Buttons ===
        st.markdown("**🎛️ Điều khiển**")
        col1, col2 = st.columns(2)
        with col1:
            refresh = st.button("🔄 Refresh", use_container_width=True)
        with col2:
            clear = st.button("🗑️ Clear Cache", use_container_width=True)
        
        if clear:
            clear_cache()
        
        st.divider()
        
        # === Sector Selection ===
        st.markdown("**📂 Chọn ngành**")
        sector_options = ["Tất cả"] + list(SECTOR_PEERS.keys())
        selected_sector = st.selectbox("Sector", sector_options)
        
        st.divider()
        
        # === Settings ===
        with st.expander("⚙️ Cài đặt"):
            show_volume = st.checkbox("Hiển thị Volume", value=True)
            show_ema = st.checkbox("Hiển thị EMA", value=True)
            dark_mode = st.checkbox("Dark Mode", value=True)
    
    # === MAIN CONTENT ===
    st.markdown("""
        <div style="text-align:center; margin-bottom:20px;">
            <h1 style="font-size:28px; margin-bottom:5px;">
                📊 PHÂN TÍCH KỸ THUẬT CỔ PHIẾU
            </h1>
            <p style="color:#8b949e;">Pro Trader Terminal v5.3 - Multi-Source Data</p>
        </div>
    """, unsafe_allow_html=True)
    
    # === TABS ===
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Phân tích kỹ thuật",
        "📊 So sánh ngành",
        "📋 Dữ liệu giá",
        "📰 Tin tức",
        "ℹ️ Hướng dẫn"
    ])
    
    # ============================================================
    # TAB 1: TECHNICAL ANALYSIS
    # ============================================================
    with tab1:
        st.markdown('<p class="tab-label">PHÂN TÍCH KỸ THUẬT</p>', unsafe_allow_html=True)
        
        with st.spinner("⏳ Đang tải dữ liệu..."):
            df, info = fetch_price(symbol, resolution)
            
            if df.empty or info.get("status") == "failed":
                st.error(f"""
                    ❌ **Không thể lấy dữ liệu cho {symbol}**
                    
                    **Nguyên nhân:** Tất cả các nguồn dữ liệu đều không hoạt động
                    
                    **Giải pháp:**
                    1. Kiểm tra mã cổ phiếu có đúng không
                    2. Thử lại sau vài phút
                    3. Liên hệ hỗ trợ nếu vấn đề tiếp tục
                """)
                st.stop()
            
            # Calculate indicators
            df = add_indicators(df)
            signal, score, signals = calculate_signal(df)
            latest = df.iloc[-1]
            prev_day = df.iloc[-2] if len(df) > 1 else latest
            
            # Price change
            price_change = latest['Close'] - prev_day['Close']
            price_change_pct = (price_change / prev_day['Close']) * 100
            change_color = "#00d97e" if price_change >= 0 else "#ff4757"
            change_icon = "📈" if price_change >= 0 else "📉"
            
            # === METRICS ROW ===
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(
                    "💰 Giá hiện tại",
                    f"{latest['Close']:,.0f}",
                    f"{change_icon} {price_change_pct:+.2f}%"
                )
            
            with col2:
                st.metric("📉 Cao nhất", f"{latest['High']:,.0f}")
            
            with col3:
                st.metric("📈 Thấp nhất", f"{latest['Low']:,.0f}")
            
            with col4:
                rsi_val = signals.get('RSI', 50)
                rsi_color = "normal" if 30 < rsi_val < 70 else "inverse"
                st.metric("📊 RSI (14)", f"{rsi_val:.1f}")
            
            with col5:
                st.metric("💾 Nguồn", info.get('source', 'N/A'))
            
            # === SIGNAL BOX ===
            st.divider()
            
            if signal == "MUA MẠNH":
                st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #00d97e 0%, #00b369 100%); 
                                padding: 25px; border-radius: 12px; text-align: center; 
                                box-shadow: 0 4px 20px rgba(0,217,126,0.4); margin: 15px 0;">
                        <h1 style="color: white; margin: 0; font-size: 32px;">🚀 MUA MẠNH</h1>
                        <p style="color: white; margin-top: 10px; font-size: 18px;">
                            Điểm số: <b>{score:.1f}</b>/10 • RSI: <b>{signals.get('RSI', 50):.1f}</b>
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
            elif signal == "BÁN MẠNH":
                st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #ff4757 0%, #cc1133 100%); 
                                padding: 25px; border-radius: 12px; text-align: center; 
                                box-shadow: 0 4px 20px rgba(255,71,87,0.4); margin: 15px 0;">
                        <h1 style="color: white; margin: 0; font-size: 32px;">🚨 BÁN MẠNH</h1>
                        <p style="color: white; margin-top: 10px; font-size: 18px;">
                            Điểm số: <b>{score:.1f}</b>/10 • RSI: <b>{signals.get('RSI', 50):.1f}</b>
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
            else:
                st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #748ffc 0%, #5c7cfa 100%); 
                                padding: 25px; border-radius: 12px; text-align: center; 
                                box-shadow: 0 4px 20px rgba(116,143,252,0.4); margin: 15px 0;">
                        <h1 style="color: white; margin: 0; font-size: 32px;">⚖️ {signal}</h1>
                        <p style="color: white; margin-top: 10px; font-size: 18px;">
                            Điểm số: <b>{score:.1f}</b>/10 • RSI: <b>{signals.get('RSI', 50):.1f}</b>
                        </p>
                    </div>
                """, unsafe_allow_html=True)
            
            # === SIGNALS DETAILS ===
            with st.expander("📋 Chi tiết tín hiệu", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Chỉ báo**")
                    st.write(f"📊 RSI: **{signals.get('RSI', 50):.1f}** ({signals.get('RSI_Signal', 'N/A')})")
                    st.write(f"📈 Xu hướng EMA: **{signals.get('EMA_Trend', 'N/A')}** ({signals.get('EMA_Strength', 'N/A')})")
                    st.write(f"💹 MACD: **{signals.get('MACD_Signal', 'N/A')}**")
                    st.write(f"📐 Bollinger: **{signals.get('BB_Position', 'N/A')}**")
                    st.write(f"📦 Khối lượng: **{signals.get('Volume_Signal', 'N/A')}**")
                
                with col2:
                    st.markdown("**Giá & EMA**")
                    st.write(f"💰 Giá: **{latest['Close']:,.0f}**")
                    st.write(f"📈 EMA20: **{signals.get('EMA_20', latest['Close']):,.0f}**")
                    st.write(f"📈 EMA50: **{signals.get('EMA_50', latest['Close']):,.0f}**")
                    st.write(f"📈 EMA200: **{signals.get('EMA_200', latest['Close']):,.0f}**")
                    st.write(f"📐 BB Upper: **{signals.get('BB_Upper', latest['Close']):,.0f}**")
                    st.write(f"📐 BB Lower: **{signals.get('BB_Lower', latest['Close']):,.0f}**")
            
            # === CHART ===
            st.divider()
            
            fig = create_candlestick_chart(df, symbol)
            st.plotly_chart(fig, use_container_width=True, theme="dark")
            
            # === DOWNLOAD ===
            excel_data = to_excel(df)
            st.download_button(
                label="📥 Tải Xuống Dữ Liệu (Excel)",
                data=excel_data,
                file_name=f"{symbol}_technical_analysis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # ============================================================
    # TAB 2: SECTOR COMPARISON
    # ============================================================
    with tab2:
        st.markdown('<p class="tab-label">SO SÁNH NGÀNH</p>', unsafe_allow_html=True)
        
        if selected_sector == "Tất cả":
            scan_symbols = ALL_SYMBOLS
            st.info("🔍 Đang quét tất cả cổ phiếu trong danh sách...")
        else:
            scan_symbols = SECTOR_PEERS.get(selected_sector, [])
            st.info(f"🔍 Đang quét ngành: **{selected_sector}**")
        
        if st.button("🚀 Bắt đầu quét", type="primary"):
            results_df = scan_sector(scan_symbols, days)
            
            if not results_df.empty:
                # Sort by score
                results_df = results_df.sort_values('Điểm', ascending=False)
                
                # Highlight signals
                def highlight_signal(val):
                    if val == 'MUA MẠNH':
                        return 'background-color: rgba(0,217,126,0.3); color: #00d97e'
                    elif val == 'BÁN MẠNH':
                        return 'background-color: rgba(255,71,87,0.3); color: #ff4757'
                    elif val == 'TÍCH CỰC':
                        return 'background-color: rgba(0,217,126,0.2); color: #7bed9f'
                    elif val == 'TIÊU CỰC':
                        return 'background-color: rgba(255,71,87,0.2); color: #ff6b6b'
                    return ''
                
                st.dataframe(
                    results_df.style.applymap(highlight_signal, subset=['Tín hiệu']),
                    use_container_width=True,
                    height=500
                )
                
                # Summary
                buy_count = len(results_df[results_df['Tín hiệu'] == 'MUA MẠNH'])
                sell_count = len(results_df[results_df['Tín hiệu'] == 'BÁN MẠNH'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🟢 Mua mạnh", buy_count)
                with col2:
                    st.metric("🔴 Bán mạnh", sell_count)
                with col3:
                    st.metric("📊 Tổng cổ phiếu", len(results_df))
            else:
                st.warning("⚠️ Không có dữ liệu nào được tìm thấy")
    
    # ============================================================
    # TAB 3: PRICE DATA
    # ============================================================
    with tab3:
        st.markdown('<p class="tab-label">DỮ LIỆU GIÁ</p>', unsafe_allow_html=True)
        
        if not df.empty:
            st.dataframe(
                df.tail(50).style.format({
                    'Open': '{:,.0f}',
                    'High': '{:,.0f}',
                    'Low': '{:,.0f}',
                    'Close': '{:,.0f}',
                    'Volume': '{:,.0f}'
                }),
                use_container_width=True,
                height=500
            )
        else:
            st.info("📭 Không có dữ liệu để hiển thị")
    
    # ============================================================
    # TAB 4: NEWS (Placeholder)
    # ============================================================
    with tab4:
        st.markdown('<p class="tab-label">TIN TỨC</p>', unsafe_allow_html=True)
        
        st.info("""
            📰 **Tính năng đang phát triển**
            
            Chúng tôi đang làm việc để tích hợp tin tức cổ phiếu.
            Phiên bản tiếp theo sẽ bao gồm:
            - Tin tức từ cafefvn
            - Báo cáo tài chính
            - Sự kiện doanh nghiệp
        """)
    
    # ============================================================
    # TAB 5: GUIDE
    # ============================================================
    with tab5:
        st.markdown('<p class="tab-label">HƯỚNG DẪN SỬ DỤNG</p>', unsafe_allow_html=True)
        
        st.markdown("""
            ## 📖 Cách sử dụng Pro Trader Terminal v5.3
            
            ### 1. Nhập mã cổ phiếu
            - Nhập mã 3 chữ cái (VD: HPG, VPB, SSI)
            - Hệ thống sẽ tự động kiểm tra định dạng
            
            ### 2. Xem phân tích kỹ thuật
            - **Tab 1**: Xem chart và tín hiệu MUA/BÁN
            - Các chỉ báo: RSI, MACD, EMA, Bollinger Bands
            
            ### 3. So sánh ngành
            - **Tab 2**: So sánh nhiều cổ phiếu cùng ngành
            - Chọn ngành từ sidebar
            - Nhấn "Bắt đầu quét" để phân tích
            
            ### 4. Hiểu tín hiệu
            
            | Tín hiệu | Mô tả | Hành động |
            |----------|-------|-----------|
            | 🚀 MUA MẠNH | Điểm ≥ 4 | Cân nhắc MUA |
            | ✅ TÍCH CỰC | Điểm 2-3 | Theo dõi |
            | ⚖️ TRUNG LẬP | Điểm -1 đến 1 | Chờ đợi |
            | ⚠️ TIÊU CỰC | Điểm -2 đến -3 | Cẩn trọng |
            | 🚨 BÁN MẠNH | Điểm ≤ -4 | Cân nhắc BÁN |
            
            ### 5. Giải thích RSI
            
            - **RSI < 30**: Quá bán → Có thể là đáy
            - **RSI 30-50**: Trung lập phía tích cực
            - **RSI 50-70**: Trung lập phía tiêu cực
            - **RSI > 70**: Quá mua → Có thể là đỉnh
            
            ### 6. DATA NGUỒN CUNG CẤP
            
            App sử dụng 3 nguồn dữ liệu backup:
            1. **KBS (vnstock)** - Ưu tiên cao nhất
            2. **CafeF** - Fallback
            3. **Yahoo Finance** - Last resort
            
            Nếu không load được, thử nhấn "Clear Cache" và thử lại.
            
            ### ⚠️ Cảnh báo
            
            - Ứng dụng chỉ mang tính chất THAM KHẢO
            - Không phải lời khuyên đầu tư
            - Luôn nghiên cứu kỹ trước khi quyết định
        """)
    
    # === FOOTER ===
    st.divider()
    st.markdown(f"""
        <div style="text-align:center; color:#8b949e; padding:10px;">
            <p style="margin:0;">Pro Trader Terminal v5.3 | Data: {info.get('source', 'N/A')} | 
            Runtime: {info.get('runtime', 0)}s | © 2024</p>
        </div>
    """, unsafe_allow_html=True)

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
