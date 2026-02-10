# Nifty 50 Chart Viewer (Streamlit)

Interactive **Nifty 50** charting app for Indian markets using **Streamlit + Plotly + yfinance**.

## Features

- **Interactive candlestick charts** with Volume and MACD subplots
- **Technical indicators**: SMA 20/50, EMA (customizable), WAP/VWAP, Fibonacci retracement
- **RSI (14)** chart with overbought/oversold levels
- **Pushya Nakshatra view**: Compare day before and day of Pushya Nakshatra
- **Week comparison**: Compare same week across up to 5 years
- **Month comparison**: Compare same month across up to 5 years
- **Summary tables** with OHLCV data

## Project Structure

```
stock_chart_app/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── utils/
    ├── __init__.py
    ├── data_fetcher.py    # Data fetching from yfinance
    ├── chart_builder.py   # Plotly chart rendering
    ├── pushya_dates.py    # Pushya Nakshatra date utilities
    └── week_comparison.py # Week/month comparison utilities
```

## Local Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone or download this repository**

2. **Install dependencies:**
```bash
cd stock_chart_app
pip install -r requirements.txt
```

3. **Run the app:**
```bash
streamlit run app.py
```

Or on Windows if `streamlit` is not recognized:
```bash
python -m streamlit run app.py
```

4. **Open your browser** to `http://localhost:8501`

## Deployment

### Option 1: Streamlit Cloud (Recommended - Free & Easy)

**Streamlit Cloud** is the easiest way to deploy Streamlit apps for free.

#### Steps:

1. **Push your code to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/stock-chart-app.git
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account
   - Click "New app"
   - Select your repository: `stock-chart-app`
   - Main file path: `app.py`
   - Click "Deploy"

3. **Your app will be live** at: `https://YOUR_APP_NAME.streamlit.app`

#### Streamlit Cloud Configuration

Create `.streamlit/config.toml` (optional) for custom settings:
```toml
[server]
headless = true
port = 8501

[browser]
gatherUsageStats = false
```

### Option 2: Other Platforms

#### Railway
1. Sign up at [railway.app](https://railway.app)
2. Create new project from GitHub repo
3. Add start command: `streamlit run app.py --server.port $PORT`
4. Deploy

#### Render
1. Sign up at [render.com](https://render.com)
2. Create new Web Service
3. Connect GitHub repo
4. Build command: `pip install -r requirements.txt`
5. Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

#### Heroku
1. Create `Procfile`:
   ```
   web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
   ```
2. Deploy via Heroku CLI or GitHub integration

## Usage

1. **Select a period** (1 Month to 2 Years) or Custom Range
2. Click **"Load Chart"** to view Nifty 50 data
3. **Enable technical indicators** (WAP/VWAP, EMA, Fibonacci) from sidebar
4. **Pushya Nakshatra**: Enable to view specific astrological dates
5. **Week/Month Comparison**: Compare same period across multiple years

## Data Source

- **Yahoo Finance** via `yfinance` library
- Ticker: `^NSEI` (Nifty 50 Index)
- Data includes: OHLCV (Open, High, Low, Close, Volume)

## Requirements

See `requirements.txt` for exact versions:
- streamlit>=1.54.0
- plotly>=6.5.2
- yfinance>=1.1.0
- pandas>=2.3.3
- pandas-ta>=0.4.71b0
- matplotlib>=3.10.8
- mplfinance>=0.12.10b0

## Notes

- Data may have a 15-20 minute delay (free tier)
- Requires internet connection to fetch market data
- Charts are interactive - use mouse wheel to zoom, double-click to reset

## License

This project is open source and available for personal use.

