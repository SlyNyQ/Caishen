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

# Some imports for handling images

import base64
from io import BytesIO
from PIL import Image

# Initialization

load_dotenv(override=True)

openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key:
    print(f"OpenAI API Key exists and begins {openai_api_key[:8]}")
else:
    print("OpenAI API Key not set")
    
MODEL = "gpt-4.1-mini"
openai = OpenAI()

DB = "stocks.db"

with sqlite3.connect(DB) as conn:
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS prices (stock TEXT PRIMARY KEY, price REAL)')
    conn.commit()

#SYSTEM MESSAGE
system_message = """
You are a helpful assistant for a stock broker called CaishenAI.
Give short, courteous answers, no more than 1 sentence.
Always be accurate. If you don't know the answer, say so.
"""

# TOOL: Get Stock Price from Database
def get_stock_price(stock):
    print(f"DATABASE TOOL CALLED: Getting price for {stock}", flush=True)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT price FROM prices WHERE stock = ?', (stock.lower(),))
        result = cursor.fetchone()
        return f"Price of {stock} is ${result[0]}" if result else "No price data available for this stock"

# TOOL: Set Stock Price in Database    
def set_stock_price(stock, price):
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO prices (stock, price) VALUES (?, ?) ON CONFLICT(stock) DO UPDATE SET price = ?', (stock.lower(), price, price))
        conn.commit()

# Example usage of set_stock_price to populate the database
stock_prices = {"Aluminum":0.79, "silver": 0.89, "gold": 1.42, "bronze": 2.99}
for stock, price in stock_prices.items():
    set_stock_price(stock, price)

# Define the function schema for the price tool
price_function = {
    "name": "get_stock_price",
    "description": "Get the price of a desired_stock.",
    "parameters": {
        "type": "object",
        "properties": {
            "desired_stock": {
                "type": "string",
                "description": "The stock that the customer wants to know the price of",
            },
        },
        "required": ["desired_stock"],
        "additionalProperties": False
    }
}
tools = [{"type": "function", "function": price_function}]
tools

# Chat Interface
def chat(message, history):
    history = [{"role": h["role"], "content": h["content"]} for h in history]
    messages = [{"role": "system", "content": system_message}] + history + [{"role": "user", "content": message}]
    response = openai.chat.completions.create(model=MODEL, messages=messages)
    return response.choices[0].message.content

#gr.ChatInterface(fn=chat, type="messages").launch()

# Handle Tool Calls
def handle_tool_calls(message):
    responses = []
    for tool_call in message.tool_calls:
        if tool_call.function.name == "get_stock_price":
            arguments = json.loads(tool_call.function.arguments)
            stock = arguments.get('desired_stock')
            price_details = get_stock_price(stock)
            responses.append({
                "role": "tool",
                "content": price_details,
                "tool_call_id": tool_call.id
            })
    return responses

# Chat Interface with Tools
def chat(message, history):
    history = [{"role":h["role"], "content":h["content"]} for h in history]
    messages = [{"role": "system", "content": system_message}] + history + [{"role": "user", "content": message}]
    response = openai.chat.completions.create(model=MODEL, messages=messages, tools=tools)

    while response.choices[0].finish_reason=="tool_calls":
        message = response.choices[0].message
        responses = handle_tool_calls(message)
        messages.append(message)
        messages.extend(responses)
        response = openai.chat.completions.create(model=MODEL, messages=messages, tools=tools)
    
    return response.choices[0].message.content
#gr.ChatInterface(fn=chat, type="messages").launch()

# Image Generation Function
def artist(stock):
    image_response = openai.images.generate(
            model="dall-e-3",
            prompt=f"An image representing the splendour of {stock}, showing the history and unique aspects about {stock}, in a vibrant pop-art style",
            size="1024x1024",
            n=1,
            response_format="b64_json",
        )
    image_base64 = image_response.data[0].b64_json
    image_data = base64.b64decode(image_base64)
    return Image.open(BytesIO(image_data))

# Text-to-Speech Function
def talker(message):
    response = openai.audio.speech.create(
      model="gpt-4o-mini-tts",
      voice="onyx",    # Also, try replacing onyx with alloy or coral
      input=message
    )
    return response.content

# Handle Tool Calls and Return Stocks
def handle_tool_calls_and_return_stocks(message):
    responses = []
    stocks = []
    for tool_call in message.tool_calls:
        if tool_call.function.name == "get_stock_price":
            arguments = json.loads(tool_call.function.arguments)
            stock = arguments.get('desired_stock')
            stocks.append(stock)
            price_details = get_stock_price(stock)
            responses.append({
                "role": "tool",
                "content": price_details,
                "tool_call_id": tool_call.id
            })
    return responses, stocks

# Chat Interface with Tools, Image Generation, and TTS
def chat(history):
    history = [{"role":h["role"], "content":h["content"]} for h in history]
    messages = [{"role": "system", "content": system_message}] + history
    response = openai.chat.completions.create(model=MODEL, messages=messages, tools=tools)
    stocks = []
    image = None

    while response.choices[0].finish_reason=="tool_calls":
        message = response.choices[0].message
        responses, stocks = handle_tool_calls_and_return_stocks(message)
        messages.append(message)
        messages.extend(responses)
        response = openai.chat.completions.create(model=MODEL, messages=messages, tools=tools)

    reply = response.choices[0].message.content
    history += [{"role":"assistant", "content":reply}]

    voice = talker(reply)

    if stocks:
        image = artist(stocks[0])
    
    return history, voice, image

# Callbacks (along with the chat() function above)

def put_message_in_chatbot(message, history):
        return "", history + [{"role":"user", "content":message}]

# UI definition

with gr.Blocks() as ui:
    with gr.Row():
        chatbot = gr.Chatbot(height=500, type="messages")
        image_output = gr.Image(height=500, interactive=False)
    with gr.Row():
        audio_output = gr.Audio(autoplay=True)
    with gr.Row():
        message = gr.Textbox(label="Chat with our AI Assistant:")

# Hooking up events to callbacks

    message.submit(put_message_in_chatbot, inputs=[message, chatbot], outputs=[message, chatbot]).then(
        chat, inputs=chatbot, outputs=[chatbot, audio_output, image_output]
    )

ui.launch(inbrowser=True, auth=("ed", "bananas"))