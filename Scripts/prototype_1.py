#Investment Chatbot
#Credit: Edwar Donner LLM Engineering
#for web scraper

# imports

import os
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
from scraper import fetch_website_contents

# Load environment variables in a file called .env
# Print the key prefixes to help with any debugging

load_dotenv(override=True)
openai_api_key = os.getenv('OPENAI_API_KEY')
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
google_api_key = os.getenv('GOOGLE_API_KEY')

if openai_api_key:
    print(f"OpenAI API Key exists and begins {openai_api_key[:8]}")
else:
    print("OpenAI API Key not set")
    
if anthropic_api_key:
    print(f"Anthropic API Key exists and begins {anthropic_api_key[:7]}")
else:
    print("Anthropic API Key not set")

if google_api_key:
    print(f"Google API Key exists and begins {google_api_key[:8]}")
else:
    print("Google API Key not set")

# Initialize

openai = OpenAI()
MODEL = 'gpt-4.1-mini'

# Connect to OpenAI, Anthropic and Google; comment out the Claude or Google lines if you're not using them

#openai = OpenAI()

anthropic_url = "https://api.anthropic.com/v1/"
gemini_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

anthropic = OpenAI(api_key=anthropic_api_key, base_url=anthropic_url)
gemini = OpenAI(api_key=google_api_key, base_url=gemini_url)

#SYSTEM MESSAGE
# Again this is typical Experimental mindset - I'm changing the global variable we used above:

system_message = """
You are a helpful assistant that analyzes the contents of a stock related websites,
and provides a short, snarky, humorous summary of the website and the  performance of the available stocks ,
 ignoring text that might be navigation related.
Respond in markdown. Do not wrap the markdown in a code block - respond just with the markdown.
"""
# user_prompt = """
# Here are the contents of a website.
# Provide a short summary of this website.
# Create a table outlining the performance of the stocks 3 columns: stock name, performance(good,bad,neutral), volatiity (High,Mid,Low)
# If it includes news or announcements, then summarize these too.
# """


#Message GPT
#system_message = "You are a helpful assistant"
def message_gpt(prompt):
    messages = [{"role": "system", "content": system_message}, {"role": "user", "content": prompt}]
    response = openai.chat.completions.create(model="gpt-4.1-mini", messages=messages)
    return response.choices[0].message.content

#Authentication method
#gr.Interface(fn=shout, inputs="textbox", outputs="textbox", flagging_mode="never").launch(inbrowser=True, auth=("ed", "bananas"))

#Stream GPT

def stream_gpt(prompt):
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
      ]
    stream = openai.chat.completions.create(
        model='gpt-4.1-mini',
        messages=messages,
        stream=True
    )
    result = ""
    for chunk in stream:
        result += chunk.choices[0].delta.content or ""
        yield result

#Stream Claude

def stream_claude(prompt):
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
      ]
    stream = anthropic.chat.completions.create(
        model='claude-sonnet-4-5-20250929',
        messages=messages,
        stream=True
    )
    result = ""
    for chunk in stream:
        result += chunk.choices[0].delta.content or ""
        yield result

#Stream Model

def stream_model(prompt, model):
    if model=="GPT":
        result = stream_gpt(prompt)
    elif model=="Claude":
        result = stream_claude(prompt)
    else:
        raise ValueError("Unknown model")
    yield from result

#Stream Investment
def stream_invest(company_name, url, model):
    yield ""
    user_prompt = f""" Here are the contents of a website.Provide a short summary of this website.
    Create a table outlining the performance of the stocks 3 columns: stock name, performance(good,bad,neutral), volatiity (High,Mid,Low)
    If it includes news or announcements, then summarize these too. {company_name}. Here is their landing page:\n"""
    prompt = user_prompt
    prompt += fetch_website_contents(url)
    if model=="GPT":
        result = stream_gpt(prompt)
    elif model=="Claude":
        result = stream_claude(prompt)
    else:
        raise ValueError("Unknown model")
    yield from result

name_input = gr.Textbox(label="Company name:")
url_input = gr.Textbox(label="Landing page URL including http:// or https://")
model_selector = gr.Dropdown(["GPT", "Claude"], label="Select model", value="GPT")
message_output = gr.Markdown(label="Response:")

view = gr.Interface(
    fn=stream_invest,
    title="Stock Input", 
    inputs=[name_input, url_input, model_selector], 
    outputs=[message_output], 
    examples=[
            ["Yahoo Finance", "https://finance.yahoo.com/?guccounter=1", "GPT"],
            ["Investing", "https://www.investing.com/", "Claude"]
        ], 
    flagging_mode="never"
    )
view.launch()