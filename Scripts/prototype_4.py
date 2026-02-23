import gradio as gr
from openai import OpenAI
import os
from dotenv import load_dotenv
import sqlite3
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import json

# Load environment variables
load_dotenv(override=True)

openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key:
    print(f"OpenAI API Key exists and begins {openai_api_key[:8]}")
else:
    print("OpenAI API Key not set")
    
MODEL = "gpt-4.1-mini"
openai = OpenAI()

#openai.api_key = os.getenv("OPENAI_API_KEY")

# Database setup
DB_NAME = "stocks.db"

def init_database():
    """Initialize SQLite database for stock data"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT NOT NULL,
            current_price REAL,
            previous_close REAL,
            open_price REAL,
            day_high REAL,
            day_low REAL,
            volume INTEGER,
            market_cap REAL,
            pe_ratio REAL,
            dividend_yield REAL,
            week_52_high REAL,
            week_52_low REAL,
            price_change REAL,
            percent_change REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def fetch_stock_data(symbol):
    """Fetch real-time stock data using yfinance"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="1d")
        
        if hist.empty:
            return None
        
        current_price = hist['Close'].iloc[-1]
        open_price = hist['Open'].iloc[-1]
        day_high = hist['High'].iloc[-1]
        day_low = hist['Low'].iloc[-1]
        volume = hist['Volume'].iloc[-1]
        
        previous_close = info.get('previousClose', current_price)
        price_change = current_price - previous_close
        percent_change = (price_change / previous_close) * 100 if previous_close else 0
        
        stock_data = {
            'symbol': symbol,
            'name': info.get('longName', symbol),
            'current_price': round(current_price, 2),
            'previous_close': round(previous_close, 2),
            'open_price': round(open_price, 2),
            'day_high': round(day_high, 2),
            'day_low': round(day_low, 2),
            'volume': int(volume),
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'week_52_high': info.get('fiftyTwoWeekHigh', 0),
            'week_52_low': info.get('fiftyTwoWeekLow', 0),
            'price_change': round(price_change, 2),
            'percent_change': round(percent_change, 2)
        }
        
        return stock_data
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

def save_stock_data(stock_data):
    """Save stock data to SQLite database"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO stock_data (
            symbol, name, current_price, previous_close, open_price,
            day_high, day_low, volume, market_cap, pe_ratio,
            dividend_yield, week_52_high, week_52_low,
            price_change, percent_change
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        stock_data['symbol'], stock_data['name'], stock_data['current_price'],
        stock_data['previous_close'], stock_data['open_price'],
        stock_data['day_high'], stock_data['day_low'], stock_data['volume'],
        stock_data['market_cap'], stock_data['pe_ratio'],
        stock_data['dividend_yield'], stock_data['week_52_high'],
        stock_data['week_52_low'], stock_data['price_change'],
        stock_data['percent_change']
    ))
    
    conn.commit()
    conn.close()

def get_latest_stock_data(symbols):
    """Get latest stock data for multiple symbols"""
    all_data = {}
    for symbol in symbols:
        data = fetch_stock_data(symbol)
        if data:
            save_stock_data(data)
            all_data[symbol] = data
    return all_data

def format_stock_data(stock_data):
    """Format stock data for AI context"""
    formatted = []
    for symbol, data in stock_data.items():
        formatted.append(f"""
**{data['name']} ({symbol})**
- Current Price: ${data['current_price']}
- Change: ${data['price_change']} ({data['percent_change']:+.2f}%)
- Open: ${data['open_price']}
- Day Range: ${data['day_low']} - ${data['day_high']}
- Volume: {data['volume']:,}
- 52 Week Range: ${data['week_52_low']} - ${data['week_52_high']}
- Market Cap: ${data['market_cap']:,.0f}
- P/E Ratio: {data['pe_ratio']:.2f}
""")
    return "\n".join(formatted)

def save_chat_message(role, content):
    """Save chat message to database"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (role, content) VALUES (?, ?)",
        (role, content)
    )
    conn.commit()
    conn.close()

def get_chat_history(limit=10):
    """Retrieve recent chat history"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM chat_history ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    messages = cursor.fetchall()
    conn.close()
    return [(role, content) for role, content in reversed(messages)]

def chat_with_assistant(message, history, stock_symbols):
    """Main chat function with OpenAI integration"""
    try:
        # Fetch latest stock data
        stock_data = get_latest_stock_data(stock_symbols)
        stock_context = format_stock_data(stock_data)
        
        # Build system message with stock context
        system_message = f"""You are a specialized finance AI assistant focused on commodity stocks analysis, particularly precious metals and commodities.

Current Stock Data (Real-Time):
{stock_context}

Your expertise includes:
- Analyzing stock performance and trends
- Comparing multiple stocks
- Providing insights on gold, silver, and copper markets
- Explaining price movements and market factors
- Offering educational financial information

Always base your analysis on the current data provided above. Be accurate, professional, and helpful. Do not provide investment advice, but rather educational analysis."""

        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": system_message}]
        
        # Add conversation history
        for human, assistant in history:
            messages.append({"role": "user", "content": human})
            messages.append({"role": "assistant", "content": assistant})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo" for faster/cheaper
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        assistant_message = response.choices[0].message.content
        
        # Save to database
        save_chat_message("user", message)
        save_chat_message("assistant", assistant_message)
        
        return assistant_message
        
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}\n\nPlease check your OpenAI API key in the .env file."
        return error_msg

def refresh_stock_display(symbols):
    """Refresh and display current stock data"""
    stock_data = get_latest_stock_data(symbols)
    return format_stock_data(stock_data)

# Initialize database
init_database()

# Default commodity symbols
DEFAULT_SYMBOLS = ["GC=F", "SI=F", "HG=F"]  # Gold, Silver, Copper futures

# Create Gradio Interface
with gr.Blocks(title="📈 Finance AI Assistant", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 📈 Finance AI Assistant - Commodity Stock Analyzer")
    gr.Markdown("**Specialized in Gold, Silver, and Copper Performance Analysis**")
    
    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown("### 💬 Chat with Finance AI")
            
            chatbot = gr.Chatbot(
                label="Conversation",
                height=400,
                show_label=True
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    label="Your Message",
                    placeholder="Ask about stock performance, trends, comparisons...",
                    lines=2,
                    scale=4
                )
                submit_btn = gr.Button("Send 📤", variant="primary", scale=1)
            
            gr.Markdown("### 💡 Example Questions:")
            gr.Markdown("""
- Compare the performance of gold vs silver today
- What's driving copper prices?
- Which commodity has the best performance this week?
- Analyze the current trends in precious metals
- What are the key factors affecting gold prices?
            """)
        
        with gr.Column(scale=1):
            gr.Markdown("### 📊 Live Stock Data")
            
            stock_symbols = gr.State(value=DEFAULT_SYMBOLS)
            
            stock_display = gr.Markdown(
                value=refresh_stock_display(DEFAULT_SYMBOLS)
            )
            
            refresh_btn = gr.Button("🔄 Refresh Data", variant="secondary")
            
            gr.Markdown("---")
            gr.Markdown("### 📌 Tracking:")
            gr.Markdown("""
- **GC=F**: Gold Futures
- **SI=F**: Silver Futures
- **HG=F**: Copper Futures
            """)
            
            gr.Markdown("---")
            gr.Markdown("### ℹ️ Data Source")
            gr.Markdown("Real-time data from **Yahoo Finance** via yfinance API")
    
    # Event handlers
    def respond(message, chat_history, symbols):
        bot_message = chat_with_assistant(message, chat_history, symbols)
        chat_history.append((message, bot_message))
        return "", chat_history
    
    msg.submit(respond, [msg, chatbot, stock_symbols], [msg, chatbot])
    submit_btn.click(respond, [msg, chatbot, stock_symbols], [msg, chatbot])
    
    refresh_btn.click(
        fn=lambda symbols: refresh_stock_display(symbols),
        inputs=stock_symbols,
        outputs=stock_display
    )
    
    gr.Markdown("---")
    gr.Markdown("⚠️ **Disclaimer:** This tool is for educational purposes only. Not financial advice.")

# Launch the app
if __name__ == "__main__":
    app.launch(share=False)


