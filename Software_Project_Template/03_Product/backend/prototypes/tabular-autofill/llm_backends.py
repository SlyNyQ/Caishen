from __future__ import annotations
import json
import os
from typing import Dict, List, Optional

# Frontier
from openai import OpenAI
import anthropic
import google.generativeai as genai

# Open-source/local
import requests as pyrequests

SYSTEM_RULES = """You extract structured fields from web page text.
Return ONLY valid JSON. No markdown. No commentary.
Keys MUST match the requested column names exactly.
If a value is not found, use null.
"""

def _json_load_safe(s: str) -> dict:
    # Some models may wrap JSON in text; try to recover
    s = s.strip()
    # Find first { ... last }
    if "{" in s and "}" in s:
        s = s[s.find("{"): s.rfind("}") + 1]
    return json.loads(s)

def openai_extract(model: str, page_text: str, columns: List[str], row_context: Dict) -> Dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = {
        "columns_to_fill": columns,
        "row_context": row_context,
        "page_text": page_text
    }
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_RULES},
            {"role": "user", "content": json.dumps(prompt)}
        ],
        temperature=0.0,
    )
    return _json_load_safe(resp.choices[0].message.content)

def anthropic_extract(model: str, page_text: str, columns: List[str], row_context: Dict) -> Dict:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    prompt = {
        "columns_to_fill": columns,
        "row_context": row_context,
        "page_text": page_text
    }
    msg = client.messages.create(
        model=model,
        max_tokens=1200,
        temperature=0.0,
        system=SYSTEM_RULES,
        messages=[{"role": "user", "content": json.dumps(prompt)}],
    )
    return _json_load_safe(msg.content[0].text)

def gemini_extract(model: str, page_text: str, columns: List[str], row_context: Dict) -> Dict:
    api_key = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)
    m = genai.GenerativeModel(model)
    prompt = {
        "columns_to_fill": columns,
        "row_context": row_context,
        "page_text": page_text
    }
    out = m.generate_content(
        [SYSTEM_RULES, json.dumps(prompt)],
        generation_config={"temperature": 0.0}
    )
    return _json_load_safe(out.text)

def ollama_extract(model: str, page_text: str, columns: List[str], row_context: Dict, host: Optional[str] = None) -> Dict:
    """
    Uses Ollama's local HTTP API.
    Default host: http://localhost:11434
    """
    host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    prompt = {
        "columns_to_fill": columns,
        "row_context": row_context,
        "page_text": page_text
    }
    payload = {
        "model": model,
        "prompt": SYSTEM_RULES + "\n\n" + json.dumps(prompt),
        "stream": False,
        "options": {"temperature": 0.0}
    }
    r = pyrequests.post(f"{host}/api/generate", json=payload, timeout=120)
    r.raise_for_status()
    return _json_load_safe(r.json()["response"])

def extract(
    backend: str,
    model: str,
    page_text: str,
    columns: List[str],
    row_context: Dict
) -> Dict:
    backend = backend.lower().strip()
    if backend == "openai":
        return openai_extract(model, page_text, columns, row_context)
    if backend == "anthropic":
        return anthropic_extract(model, page_text, columns, row_context)
    if backend == "gemini":
        return gemini_extract(model, page_text, columns, row_context)
    if backend == "ollama":
        return ollama_extract(model, page_text, columns, row_context)
    raise ValueError("backend must be one of: openai, anthropic, gemini, ollama")