#Investment Chatbot version 2
#Credit: Edwar Donner LLM Engineering
#for web scraper

# imports

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
import sqlite3

# Initialization

load_dotenv(override=True)

openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key:
    print(f"OpenAI API Key exists and begins {openai_api_key[:8]}")
else:
    print("OpenAI API Key not set")
    
MODEL = "gpt-4.1-mini"
openai = OpenAI()

# Set up SQLite database
DB = "stocks.db"

# Create stocks table if it doesn't exist
with sqlite3.connect(DB) as conn:
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stocks (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        price REAL,
        change_percent REAL
    )
    """)
    conn.commit()

# Function to store stock data in the database
def store_stock_data(stock_data):
    print(f"Storing stock data: {stock_data}", flush=True)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        for stock in stock_data:
            cursor.execute("""
            INSERT OR REPLACE INTO stocks (symbol, name, price, change_percent)
            VALUES (?, ?, ?, ?)
            """, (stock['symbol'], stock['name'], stock['price'], stock['change_percent']))
        conn.commit()

#SYSTEM MESSAGE
# Again this is typical Experimental mindset - I'm changing the global variable we used above:

system_message = """
You are a helpful assistant that analyzes the contents of a stock related website,
and provides a short, snarky, humorous summary of the website and the  performance of the available stocks ,
 ignoring text that might be navigation related.
Respond in markdown. Do not wrap the markdown in a code block - respond just with the markdown.
"""

# Function to query stock data from the database
def query_stocks_db(stocks):
    print(f"Querying database for stocks: {stocks}", flush=True)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        placeholders = ','.join('?' for _ in stocks)
        query = f"SELECT symbol, name, price, change_percent FROM stocks WHERE symbol IN ({placeholders})"
        cursor.execute(query, stocks)
        results = cursor.fetchall()
        stock_info = {row[0]: {"name": row[1], "price": row[2], "change_percent": row[3]} for row in results}
        return stock_info

query_stocks_db(['AAPL', 'GOOGL', 'MSFT'])    
#Message GPT
def message_gpt(prompt):
    messages = [{"role": "system", "content": system_message}, {"role": "user", "content": prompt}]
    response = openai.chat.completions.create(model=MODEL, messages=messages)
    return response.choices[0].message.content

# Gradio Interface
def chat_interface(user_input, chat_history):
    print(f"User input: {user_input}", flush=True)
    response = message_gpt(user_input)
    chat_history.append(("User", user_input))
    chat_history.append(("Assistant", response))
    return "", chat_history

with gr.Blocks() as demo:
    gr.Markdown("# Investment Chatbot v2")
    chat_history = gr.State([])
    with gr.Row():
        with gr.Column():
            user_input = gr.Textbox(label="Your Message")
            send_button = gr.Button("Send")
        with gr.Column():
            chat_display = gr.Chatbot(label="Chat History")
    send_button.click(chat_interface, inputs=[user_input, chat_history], outputs=[user_input, chat_display])

demo.launch(inbrowser=True)
#Investment Chatbot version 2
#Credit: Edwar Donner LLM Engineering   
#for web scraper
#for database storage and retrieval
#for gradio interface
#for OpenAI GPT-4.1-mini interaction
#for environment variable management
#for SQLite database management
