# ════════════════════════════════════════════════════════════════════════════════
# Pro Trader Terminal v5.3.2 - CLEAN EDITION
# ════════════════════════════════════════════════════════════════════════════════

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
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Pro Trader Terminal v5.3.2",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp { background: #0e1117; }
    h1, h2, h3 { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONFIGURATION
# ============================================================

SECTOR_PEERS = {
    "Thep": ["HPG", "HSG", "NKG"],
    "Ngan hang": ["VPB", "VCB", "TCB", "CTG", "BID", "STB", "MBB", "ACB"],
    "Bat dong san": ["VRE", "NVL", "DIG", "KDH", "CRE", "ASM"],
    "Chung khoan": ["SSI", "VND", "HCM", "TCBS", "BSI", "VIS"],
    "Ban le": ["MWG", "PNJ", "DGW", "FPT", "PET"],
    "Dau khi": ["PLX", "POW", "GAS", "PVT"],
    "Thuc pham": ["VNM", "MSB", "KDC", "SBT", "GTN"],
    "Cong nghe": ["FPT", "CMG", "VGI", "SRA"],
    "Xay dung": ["VCG", "HDG", "C4G", "ROS"]
}

ALL_SYMBOLS = [sym for symbols in SECTOR_PEERS.values() for sym in symbols]

end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_symbol(sym: str) -> tuple:
    """Validate stock symbol format"""
    if not sym or not isinstance(sym, str):
        return False, "Ma co phieu khong duoc trong"
    
    sym = sym.strip().upper()
    
    if not re.match(r'^[A-Z]{3}$', sym):
        return False, "Ma co phieu phai la 3 chu cai (VD: HPG, VPB)"
    
    if sym not in ALL_SYMBOLS:
        return True, f"Canh bao: {sym} chua co trong danh sach"
    
    return True, ""

# ============================================================
# DATA FETCHING (Multi-Source)
# ============================================================

@st.cache_data(ttl=60, show_spinner=False)
def fetch_price(sym: str, days: int = 30, interval: str = "1D") -> tuple:
    """
    Fetch price data with multi-source fallback
    """
    sym = sym.upper().strip()
    info = {"source": None, "runtime": 0, "status": "pending", "rows": 0}
    
    start_time = time.time()
    
    # SOURCE 1: Yahoo Finance (most reliable)
    try:
        import yfinance as yf
        
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
            
            if 'Stock Splits' in df.columns:
                df = df.drop('Stock Splits', axis=1)
            
            df = df.dropna()
            
            if len(df) > 1:
                info["source"] = "Yahoo"
                info["runtime"] = round(time.time() - start_time, 2)
                info["status"] = "success"
                info["rows"] = len(df)
                return df, info
    except ImportError:
        info["source"] = "yfinance not installed"
    except Exception as e:
        info["source"] = f"Yahoo Error"
    
    # SOURCE 2: CafeF
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
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
                rows = data['data'][::-1]
                df = pd.DataFrame(rows)
                
                df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Avg', 'Change']
                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                
                df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
                df = df.set_index('Date')
                df = df.apply(pd.to_numeric, errors='coerce').dropna()
                
                if len(df) > 1:
                    info["source"] = "CafeF"
                    info["runtime"] = round(time.time() - start_time, 2)
                    info["status"] = "success"
                    info["rows"] = len(df)
                    return df, info
    except Exception as e:
        info["source"] = f"CafeF Error"
    
    # SOURCE 3: KBS via vnstock
    try:
        from vnstock import Quote
        df = Quote(symbol=sym, source="KBS").history(
            start=start_date, end=end_date, interval=interval
        )
        df = df.rename(columns={
            'close': 'Close', 
            'volume': 'Volume', 
            'open': 'Open', 
            'high': 'High', 
            'low': 'Low'
        })
        df = df.dropna(subset=['Close'])
        
        if len(df) > 1:
            info["source"] = "KBS"
            info["runtime"] = round(time.time() - start_time, 2)
            info["status"] = "success"
            info["rows"] = len(df)
            return df, info
    except ImportError:
        info["source"] = "vnstock not installed"
    except Exception as e:
        info["source"] = f"KBS Error"
    
    info["status"] = "failed"
    info["runtime"] = round(time.time() - start_time, 2)
    return pd.DataFrame(), info

# ============================================================
# TECHNICAL INDICATORS
# ============================================================

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    
    return true_range.rolling(window=period).mean()

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to dataframe"""
    if df is None or len(df) < 20:
        return df
    
    df = df.copy()
    
    # EMA
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
    
    # ATR
    if len(df) > 14:
        df['ATR'] = calculate_atr(df)
    else:
        df['ATR'] = 0
    
    # Volume indicators
    df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
    
    # Price change
    df['Price_Change'] = df['Close'].pct_change()
    df['Price_Change_5D'] = df['Close'].pct_change(5)
    df['Price_Change_20D'] = df['Close'].pct_change(20)
    
    return df

# ============================================================
# SIGNAL CALCULATION
# ============================================================

def calculate_signal(df: pd.DataFrame) -> tuple:
    """Calculate trading signal"""
    if df is None or len(df) < 2:
        return "KHONG DU LIEU", 0, {}
    
    latest = df.iloc[-1]
    
    score = 0
    signals = {}
    
    # RSI Analysis
    rsi = latest.get('RSI', 50)
    signals['RSI'] = rsi
    
    if rsi < 30:
        score += 3
        signals['RSI_Signal'] = "QUA BAN"
    elif rsi < 40:
        score += 2
        signals['RSI_Signal'] = "Gan qua ban"
    elif rsi > 70:
        score -= 3
        signals['RSI_Signal'] = "QUA MUA"
    elif rsi > 60:
        score -= 2
        signals['RSI_Signal'] = "Gan qua mua"
    else:
        signals['RSI_Signal'] = "Trung lap"
    
    # EMA Trend Analysis
    ema_20 = latest.get('EMA_20', latest['Close'])
    ema_50 = latest.get('EMA_50', latest['Close'])
    ema_200 = latest.get('EMA_200', latest['Close'])
    current_price = latest['Close']
    
    signals['EMA_20'] = ema_20
    signals['EMA_50'] = ema_50
    signals['EMA_200'] = ema_200
    
    if ema_20 > ema_50:
        score += 2
        signals['EMA_Trend'] = "TANG"
        if ema_50 > ema_200:
            score += 1
            signals['EMA_Strength'] = "Rat manh"
        else:
            signals['EMA_Strength'] = "Trung binh"
    else:
        score -= 2
        signals['EMA_Trend'] = "GIAM"
        if ema_50 < ema_200:
            score -= 1
            signals['EMA_Strength'] = "Rat yeu"
        else:
            signals['EMA_Strength'] = "Trung binh"
    
    if current_price > ema_20:
        score += 1
    else:
        score -= 1
    
    # MACD Analysis
    macd = latest.get('MACD', 0)
    signal_line = latest.get('Signal_Line', 0)
    
    signals['MACD'] = macd
    signals['Signal_Line'] = signal_line
    signals['MACD_Hist'] = latest.get('MACD_Hist', 0)
    
    if macd > signal_line and macd > 0:
        score += 2
        signals['MACD_Signal'] = "MUA"
    elif macd > signal_line and macd < 0:
        score += 1
        signals['MACD_Signal'] = "Dan hoi phuc"
    elif macd < signal_line and macd < 0:
        score -= 2
        signals['MACD_Signal'] = "BAN"
    else:
        score -= 1
        signals['MACD_Signal'] = "Dan suy yeu"
    
    # Bollinger Bands
    bb_upper = latest.get('BB_Upper', current_price)
    bb_lower = latest.get('BB_Lower', current_price)
    
    signals['BB_Upper'] = bb_upper
    signals['BB_Lower'] = bb_lower
    signals['BB_Middle'] = latest.get('BB_Middle', current_price)
    
    bb_width = bb_upper - bb_lower
    bb_position = (current_price - bb_lower) / bb_width if bb_width > 0 else 0.5
    
    if bb_position < 0.2:
        score += 2
        signals['BB_Position'] = "Gan duoi"
    elif bb_position > 0.8:
        score -= 2
        signals['BB_Position'] = "Gan tren"
    else:
        signals['BB_Position'] = "Giua"
    
    # Volume Analysis
    vol_ratio = latest.get('Volume_Ratio', 1)
    signals['Volume_Ratio'] = vol_ratio
    
    if vol_ratio > 1.5:
        score += 1
        signals['Volume_Signal'] = "Khoi luong tang manh"
    elif vol_ratio < 0.5:
        score -= 1
        signals['Volume_Signal'] = "Khoi luong thap"
    else:
        signals['Volume_Signal'] = "Binh thuong"
    
    # Final Signal
    if score >= 4:
        final_signal = "MUA MANH"
    elif score >= 2:
        final_signal = "TICH CUC"
    elif score <= -4:
        final_signal = "BAN MANH"
    elif score <= -2:
        final_signal = "TIEU CUC"
    else:
        final_signal = "TRUNG LAP"
    
    signals['Score'] = score
    signals['Price'] = current_price
    
    return final_signal, score, signals

# ============================================================
# CHART FUNCTIONS
# ============================================================

def create_candlestick_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Create candlestick chart with indicators"""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        x_title="Thoi gian"
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
                      name="BB Upper", line=dict(color="rgba(116,143,252,0.5)", width=1)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df['BB_Lower'], 
                      name="BB Lower", line=dict(color="rgba(116,143,252,0.5)", width=1),
                      fill='tonexty', fillcolor='rgba(116,143,252,0.1)'),
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
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    
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
    return output.getvalue()

# ============================================================
# SECTOR SCANNER
# ============================================================

def scan_sector(symbols: list, days: int = 30) -> pd.DataFrame:
    """Scan multiple stocks"""
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, sym in enumerate(symbols):
        status_text.text(f"Dang phan tich {sym}...")
        progress_bar.progress((i + 1) / len(symbols))
        
        try:
            df, info = fetch_price(sym, days)
            
            if len(df) > 0:
                df = add_indicators(df)
                signal, score, signals = calculate_signal(df)
                latest = df.iloc[-1]
                
                results.append({
                    'Ma': sym,
                    'Gia': round(latest['Close'], 2),
                    'RSI': round(signals.get('RSI', 50), 1),
                    'Xu huong': signals.get('EMA_Trend', 'N/A'),
                    'MACD': signals.get('MACD_Signal', 'N/A'),
                    'Khoi luong': f"{signals.get('Volume_Ratio', 1):.1f}x",
                    'Tin hieu': signal,
                    'Diem': score,
                    'Nguon': info.get('source', 'Unknown')
                })
        except Exception as e:
            results.append({
                'Ma': sym, 'Gia': 'Loi', 'RSI': 'N/A',
                'Xu huong': 'N/A', 'MACD': 'N/A',
                'Khoi luong': 'N/A', 'Tin hieu': 'Loi',
                'Diem': 0, 'Nguon': 'Failed'
            })
        
        time.sleep(0.5)
    
    status_text.text("Hoan tat!")
    progress_bar.empty()
    
    return pd.DataFrame(results)

# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    # === SIDEBAR ===
    with st.sidebar:
        st.markdown("### Pro Trader Terminal")
        st.markdown("**v5.3.2**")
        
        st.divider()
        
        # Symbol Input
        st.markdown("**Nhap ma co phieu**")
        symbol = st.text_input(
            "Ma co phieu", 
            value="HPG", 
            placeholder="VD: HPG, VPB, SSI",
            label_visibility="collapsed"
        ).upper().strip()
        
        is_valid, msg = validate_symbol(symbol)
        if not is_valid:
            st.error(msg)
            return
        elif "Canh bao" in msg:
            st.warning(msg)
        
        st.divider()
        
        # Time Period
        st.markdown("**Khoang thoi gian**")
        days = st.slider("Days", 10, 365, 60, label_visibility="collapsed")
        
        # Resolution
        st.markdown("**Do phan giai**")
        resolution = st.selectbox(
            "Resolution",
            ["1D", "1H", "15m", "30m"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Sector Selection
        st.markdown("**Chon nganh**")
        sector_options = ["Tat ca"] + list(SECTOR_PEERS.keys())
        selected_sector = st.selectbox("Sector", sector_options)
    
    # === MAIN CONTENT ===
    st.markdown("# PHAN TICH KY THUAT CO PHIEU")
    st.markdown("Pro Trader Terminal v5.3.2 - Multi-Source Data")
    
    st.divider()
    
    # === FETCH DATA ===
    with st.spinner("Dang tai du lieu..."):
        df, info = fetch_price(symbol, days, resolution)
    
    if df.empty or info.get("status") == "failed":
        st.error(f"Khong the lay du lieu cho {symbol}. Vui long thu lai sau.")
        return
    
    # Calculate indicators
    df = add_indicators(df)
    signal, score, signals = calculate_signal(df)
    latest = df.iloc[-1]
    prev_day = df.iloc[-2] if len(df) > 1 else latest
    
    # Price change
    price_change = latest['Close'] - prev_day['Close']
    price_change_pct = (price_change / prev_day['Close']) * 100
    change_icon = "+" if price_change >= 0 else ""
    
    # === METRICS ROW ===
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Gia hien tai",
            f"{latest['Close']:,.0f}",
            f"{change_icon}{price_change_pct:.2f}%"
        )
    
    with col2:
        st.metric("Cao nhat", f"{latest['High']:,.0f}")
    
    with col3:
        st.metric("Thap nhat", f"{latest['Low']:,.0f}")
    
    with col4:
        st.metric("RSI (14)", f"{signals.get('RSI', 50):.1f}")
    
    with col5:
        st.metric("Nguon", info.get('source', 'N/A'))
    
    # === SIGNAL BOX ===
    st.divider()
    
    if signal == "MUA MANH":
        st.success(f"**MUA MANH** | Diem: {score:.1f} | RSI: {signals.get('RSI', 50):.1f}")
    elif signal == "BAN MANH":
        st.error(f"**BAN MANH** | Diem: {score:.1f} | RSI: {signals.get('RSI', 50):.1f}")
    elif signal == "TICH CUC":
        st.info(f"**TICH CUC** | Diem: {score:.1f} | RSI: {signals.get('RSI', 50):.1f}")
    elif signal == "TIEU CUC":
        st.warning(f"**TIEU CUC** | Diem: {score:.1f} | RSI: {signals.get('RSI', 50):.1f}")
    else:
        st.info(f"**TRUNG LAP** | Diem: {score:.1f} | RSI: {signals.get('RSI', 50):.1f}")
    
    # === SIGNALS DETAILS ===
    with st.expander("Chi tiet tin hieu", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Chi bao**")
            st.write(f"RSI: {signals.get('RSI', 50):.1f} ({signals.get('RSI_Signal', 'N/A')})")
            st.write(f"Xu huong EMA: {signals.get('EMA_Trend', 'N/A')} ({signals.get('EMA_Strength', 'N/A')})")
            st.write(f"MACD: {signals.get('MACD_Signal', 'N/A')}")
            st.write(f"Bollinger: {signals.get('BB_Position', 'N/A')}")
            st.write(f"Khoi luong: {signals.get('Volume_Signal', 'N/A')}")
        
        with col2:
            st.markdown("**Gia & EMA**")
            st.write(f"Gia: {latest['Close']:,.0f}")
            st.write(f"EMA20: {signals.get('EMA_20', latest['Close']):,.0f}")
            st.write(f"EMA50: {signals.get('EMA_50', latest['Close']):,.0f}")
            st.write(f"EMA200: {signals.get('EMA_200', latest['Close']):,.0f}")
            st.write(f"BB Upper: {signals.get('BB_Upper', latest['Close']):,.0f}")
            st.write(f"BB Lower: {signals.get('BB_Lower', latest['Close']):,.0f}")
    
    # === CHART ===
    st.divider()
    
    fig = create_candlestick_chart(df, symbol)
    st.plotly_chart(fig)
    
    # === DOWNLOAD ===
    st.divider()
    excel_data = to_excel(df)
    st.download_button(
        label="Tai Xuong Du Lieu (Excel)",
        data=excel_data,
        file_name=f"{symbol}_technical_analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # === SECTOR SCANNER ===
    st.divider()
    st.markdown("### So sanh nganh")
    
    if selected_sector == "Tat ca":
        scan_symbols = ALL_SYMBOLS
    else:
        scan_symbols = SECTOR_PEERS.get(selected_sector, [])
    
    if st.button("Bat dau quet", type="primary"):
        results_df = scan_sector(scan_symbols, days)
        
        if not results_df.empty:
            results_df = results_df.sort_values('Diem', ascending=False)
            
            st.dataframe(
                results_df,
                use_container_width=True,
                height=500
            )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Mua manh", len(results_df[results_df['Tin hieu'] == 'MUA MANH']))
            with col2:
                st.metric("Ban manh", len(results_df[results_df['Tin hieu'] == 'BAN MANH']))
            with col3:
                st.metric("Tong co phieu", len(results_df))
    
    # === FOOTER ===
    st.divider()
    source = info.get('source', 'N/A')
    runtime = info.get('runtime', 0)
    st.markdown(f"Pro Trader Terminal v5.3.2 | Data: {source} | Runtime: {runtime}s")

if __name__ == "__main__":
    main()
