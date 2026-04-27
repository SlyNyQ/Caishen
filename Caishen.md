# Cashien

**Cashien** is an AI-powered investment qualifier and analysis assistant that combines **historical and current market data**, **web-sourced context**, **agentic AI workflows**, and **Retrieval-Augmented Generation (RAG)** to help users **understand stocks and investment strategies in plain English**.

Cashien is designed to **analyze**, **interpret**, and **explain** — not to trade, execute orders, or give guaranteed financial advice.

---

## What Cashien Does

Cashien acts as a **decision-support layer** for investing by:

- Scraping and summarizing stock-related websites
- Interpreting stock performance and volatility
- Translating market signals into **layman-friendly explanations**
- Generating **strategy options** based on user intent (risk tolerance, horizon, goals)
- Supporting **multiple LLM providers** (OpenAI, Anthropic, Google)
- Laying the groundwork for **agentic AI + RAG-based reasoning**

The current prototype focuses on **web-based stock analysis**, with a clear path toward deeper market data ingestion and portfolio-level reasoning.

---

## What Cashien Is *Not*

- ❌ Not a brokerage  
- ❌ Not a trading bot  
- ❌ Not an execution engine  
- ❌ Not guaranteed to be correct  

Cashien **does not place trades** and **does not manage money**.  
It exists to **help humans think better**, not to replace professional judgment.

---

## Current Prototype Overview

The current prototype consists of:

- A **web scraper** that extracts readable stock-related content from public websites
- A **Gradio UI** for interactive analysis
- **Streaming LLM responses** from multiple providers
- Markdown-formatted analytical summaries with tables

### Key Files

- `prototype.py` — main application, UI, and LLM orchestration
- `scraper.py` — website scraping and content extraction logic
- `requirements.txt` — pip dependency list
- `pyproject.toml` — project metadata and dependency definition

---

## Supported LLM Providers

Cashien is **provider-agnostic by design**.

Currently supported:

- **OpenAI** (default in prototype)
- **Anthropic (Claude)**
- **Google Gemini**

The active model is selected dynamically at runtime.

---

## ⚠️ API Keys Required (Mandatory)

**Cashien will NOT run without your own API keys.**

This is intentional and non-negotiable.

You must supply your own keys for:

- LLM providers (OpenAI, Anthropic, Google)
- Future: market data providers, news APIs, vector databases

Cashien does **not**:
- ship with API keys
- bundle credentials
- hide usage costs
- proxy billing through the project

---

## Environment Setup

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/Cashien.git
cd Cashien
