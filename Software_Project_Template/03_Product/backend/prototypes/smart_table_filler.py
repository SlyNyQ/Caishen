"""
Smart Table Filler
==================
Upload any CSV/Excel/TSV file, analyze filled vs. unfilled cells,
scrape a target website, and use an LLM to fill in the gaps.
"""

import os
import re
import json
import time
import warnings
import pandas as pd
import gradio as gr
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from anthropic import Anthropic
import openai

warnings.filterwarnings("ignore")
load_dotenv()

# ── LLM clients ──────────────────────────────────────────────────────────────

def get_anthropic_client():
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return Anthropic(api_key=key) if key else None

def get_openai_client():
    key = os.getenv("OPENAI_API_KEY", "")
    openai.api_key = key
    return openai if key else None

# ── File loading ──────────────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {
    ".csv": lambda f: pd.read_csv(f),
    ".tsv": lambda f: pd.read_csv(f, sep="\t"),
    ".xlsx": lambda f: pd.read_excel(f, header=None),
    ".xls":  lambda f: pd.read_excel(f, header=None),
    ".json": lambda f: pd.read_json(f),
    ".parquet": lambda f: pd.read_parquet(f),
}

def load_file(filepath: str) -> tuple[pd.DataFrame | None, str]:
    """Load any supported tabular file. Returns (df, message)."""
    ext = os.path.splitext(filepath)[1].lower()
    loader = SUPPORTED_EXTENSIONS.get(ext)
    if not loader:
        return None, f"❌ Unsupported file type: `{ext}`. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
    try:
        df = loader(filepath)
        # Auto-detect header row for Excel files (find first row with >50% non-null values)
        if ext in (".xlsx", ".xls"):
            for i, row in df.iterrows():
                if row.notna().mean() > 0.4:
                    df.columns = df.iloc[i]
                    df = df.iloc[i + 1:].reset_index(drop=True)
                    break
        df.columns = [str(c).strip() for c in df.columns]
        return df, f"✅ Loaded `{os.path.basename(filepath)}` — {len(df)} rows × {len(df.columns)} columns"
    except Exception as e:
        return None, f"❌ Error loading file: {e}"

# ── Gap analysis ──────────────────────────────────────────────────────────────

def analyze_gaps(df: pd.DataFrame) -> dict:
    """Return per-column and per-cell fill statistics."""
    total_cells = df.size
    null_mask = df.isnull() | (df.applymap(lambda x: str(x).strip() in ("", "nan", "NaN", "None") if pd.notna(x) else True))
    filled_cells = (~null_mask).sum().sum()
    
    col_stats = []
    # iterate by column index so we always work with a Series even if names repeat
    for idx, col in enumerate(df.columns):
        col_mask = null_mask.iloc[:, idx]
        n_null = int(col_mask.sum())
        n_filled = len(df) - n_null
        col_stats.append({
            "column": col,
            "filled": n_filled,
            "missing": n_null,
            "pct_filled": round(100 * n_filled / len(df), 1) if len(df) else 0,
        })
    
    return {
        "total_cells": int(total_cells),
        "filled_cells": int(filled_cells),
        "missing_cells": int(total_cells - filled_cells),
        "pct_complete": round(100 * filled_cells / total_cells, 1) if total_cells else 0,
        "col_stats": col_stats,
        "null_mask": null_mask,
    }

def format_gap_report(stats: dict) -> str:
    lines = [
        f"## 📊 Table Analysis",
        f"- **Total cells:** {stats['total_cells']}",
        f"- **Filled:** {stats['filled_cells']} ({stats['pct_complete']}%)",
        f"- **Missing:** {stats['missing_cells']} ({100 - stats['pct_complete']:.1f}%)",
        "",
        "### Per-Column Breakdown",
        "| Column | Filled | Missing | % Complete |",
        "|--------|--------|---------|------------|",
    ]
    for cs in stats["col_stats"]:
        bar = "█" * int(cs["pct_filled"] / 10) + "░" * (10 - int(cs["pct_filled"] / 10))
        lines.append(f"| {cs['column']} | {cs['filled']} | {cs['missing']} | {bar} {cs['pct_filled']}% |")
    return "\n".join(lines)

# ── Web scraper ───────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def scrape_url(url: str, max_chars: int = 12000) -> tuple[str, str]:
    """Scrape a URL and return (clean_text, status_message)."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text[:max_chars]
        return text, f"✅ Scraped {url} — {len(text):,} chars"
    except requests.exceptions.HTTPError as e:
        return "", f"❌ HTTP Error {e.response.status_code}: {e}"
    except Exception as e:
        return "", f"❌ Scrape failed: {e}"

# ── LLM filling ───────────────────────────────────────────────────────────────

def build_prompt(df: pd.DataFrame, null_mask: pd.DataFrame, scraped_text: str, row_idx: int) -> str:
    row = df.iloc[row_idx]
    known = {col: str(val) for col, val in row.items() if not null_mask.iloc[row_idx][col]}
    missing_cols = [col for col in df.columns if null_mask.iloc[row_idx][col]]
    
    return f"""You are a data analyst. Your task is to fill in missing values in a table row.

TABLE COLUMNS: {list(df.columns)}

EXISTING VALUES FOR THIS ROW:
{json.dumps(known, indent=2)}

MISSING COLUMNS TO FILL: {missing_cols}

REFERENCE INFORMATION (scraped from web):
---
{scraped_text[:8000]}
---

Instructions:
- Return ONLY a valid JSON object mapping each missing column name to its best value.
- Use "N/A" if no information is available for a field.
- Be concise and factual. Match the format/style of existing values.
- Do not add any explanation outside the JSON.

Example output format:
{{"Column A": "value", "Column B": "value"}}"""

def fill_with_llm(
    df: pd.DataFrame,
    null_mask: pd.DataFrame,
    scraped_text: str,
    model_choice: str,
    progress_fn=None,
) -> pd.DataFrame:
    """Fill missing cells row by row using the chosen LLM."""
    df_out = df.copy()
    rows_with_gaps = [i for i in range(len(df)) if null_mask.iloc[i].any()]

    for step, row_idx in enumerate(rows_with_gaps):
        if progress_fn:
            progress_fn(step / len(rows_with_gaps), desc=f"Filling row {row_idx + 1}...")

        prompt = build_prompt(df, null_mask, scraped_text, row_idx)

        try:
            if model_choice.startswith("claude"):
                client = get_anthropic_client()
                if not client:
                    raise ValueError("ANTHROPIC_API_KEY not set")
                resp = client.messages.create(
                    model=model_choice,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}]
                )
                raw = resp.content[0].text
            else:
                client = get_openai_client()
                if not client:
                    raise ValueError("OPENAI_API_KEY not set")
                resp = openai.chat.completions.create(
                    model=model_choice,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                )
                raw = resp.choices[0].message.content

            # Parse JSON from response
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                fills = json.loads(match.group())
                for col, val in fills.items():
                    if col in df_out.columns:
                        df_out.at[row_idx, col] = val
        except Exception as e:
            print(f"  Row {row_idx} error: {e}")
            time.sleep(1)

    if progress_fn:
        progress_fn(1.0, desc="Done!")
    return df_out

# ── Gradio UI ─────────────────────────────────────────────────────────────────

MODELS = [
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-3.5-turbo",
]

# State
state = {"df": None, "null_mask": None, "scraped_text": "", "df_filled": None}

with gr.Blocks(
    title="🧠 Smart Table Filler",
    theme=gr.themes.Soft(primary_hue="violet"),
    css="""
    .tab-selected { font-weight: bold !important; }
    footer { display: none !important; }
    """,
) as demo:

    gr.Markdown("# 🧠 Smart Table Filler\nUpload a tabular file, analyze gaps, scrape a reference site, and auto-fill missing data with an LLM.")

    with gr.Tabs():

        # ── Tab 1: Upload & Analyze ────────────────────────────────────────────
        with gr.Tab("📂 1. Upload & Analyze"):
            file_input = gr.File(
                label="Upload CSV, Excel, TSV, JSON, or Parquet",
                file_types=[".csv", ".xlsx", ".xls", ".tsv", ".json", ".parquet"],
            )
            load_btn = gr.Button("🔍 Load & Analyze", variant="primary")
            load_status = gr.Markdown()
            gap_report = gr.Markdown()
            preview_table = gr.Dataframe(label="Table Preview (first 20 rows)", interactive=False)

            def on_load(file):
                if file is None:
                    return "Please upload a file.", "", None
                df, msg = load_file(file.name)
                if df is None:
                    return msg, "", None
                state["df"] = df
                stats = analyze_gaps(df)
                state["null_mask"] = stats["null_mask"]
                report = format_gap_report(stats)
                return msg, report, df.head(20)

            load_btn.click(on_load, inputs=file_input, outputs=[load_status, gap_report, preview_table])

        # ── Tab 2: Web Scraper ─────────────────────────────────────────────────
        with gr.Tab("🌐 2. Web Scraper"):
            gr.Markdown("Scrape a reference site to give the LLM context for filling gaps.")
            url_input = gr.Textbox(
                label="Target URL",
                placeholder="e.g. https://artificialanalysis.ai or docs.anthropic.com/models",
            )
            scrape_btn = gr.Button("🕷️ Scrape Site", variant="primary")
            scrape_status = gr.Markdown()
            scraped_preview = gr.Textbox(
                label="Scraped Text Preview (first 3000 chars)",
                lines=15,
                interactive=False,
            )

            def on_scrape(url):
                if not url.strip():
                    return "Please enter a URL.", ""
                text, msg = scrape_url(url.strip())
                state["scraped_text"] = text
                return msg, text[:3000] if text else ""

            scrape_btn.click(on_scrape, inputs=url_input, outputs=[scrape_status, scraped_preview])

        # ── Tab 3: LLM Fill ────────────────────────────────────────────────────
        with gr.Tab("🤖 3. LLM Auto-Fill"):
            gr.Markdown("Select a model and fill all missing cells using scraped context.")
            
            with gr.Row():
                model_dropdown = gr.Dropdown(
                    choices=MODELS,
                    value="claude-sonnet-4-6",
                    label="LLM Model",
                )
                api_key_input = gr.Textbox(
                    label="API Key (or set in .env)",
                    placeholder="sk-... or anthropic key",
                    type="password",
                )

            fill_btn = gr.Button("✨ Fill Missing Cells", variant="primary", size="lg")
            fill_status = gr.Markdown()
            filled_preview = gr.Dataframe(label="Filled Table", interactive=False)
            download_btn = gr.File(label="⬇️ Download Filled File", visible=False)

            def on_fill(model, api_key, progress=gr.Progress()):
                if state["df"] is None:
                    return "⚠️ Please load a file first (Tab 1).", None, gr.update(visible=False)
                if not state["scraped_text"]:
                    return "⚠️ No scraped text found. Please run the scraper first (Tab 2).", None, gr.update(visible=False)

                # Override API key if provided
                if api_key.strip():
                    if model.startswith("claude"):
                        os.environ["ANTHROPIC_API_KEY"] = api_key.strip()
                    else:
                        os.environ["OPENAI_API_KEY"] = api_key.strip()

                df = state["df"]
                null_mask = state["null_mask"]
                rows_with_gaps = null_mask.any(axis=1).sum()

                if rows_with_gaps == 0:
                    return "✅ No missing cells found! Your table is complete.", df, gr.update(visible=False)

                try:
                    df_filled = fill_with_llm(df, null_mask, state["scraped_text"], model, progress_fn=progress)
                    state["df_filled"] = df_filled

                    # Save output
                    out_path = "/tmp/filled_table.xlsx"
                    df_filled.to_excel(out_path, index=False)

                    stats_before = analyze_gaps(df)
                    stats_after = analyze_gaps(df_filled)
                    msg = (
                        f"✅ **Filling complete!**\n\n"
                        f"- Before: {stats_before['pct_complete']}% complete\n"
                        f"- After: {stats_after['pct_complete']}% complete\n"
                        f"- Cells filled: {stats_before['missing_cells'] - stats_after['missing_cells']}"
                    )
                    return msg, df_filled, gr.update(value=out_path, visible=True)

                except Exception as e:
                    return f"❌ Error during filling: {e}", None, gr.update(visible=False)

            fill_btn.click(
                on_fill,
                inputs=[model_dropdown, api_key_input],
                outputs=[fill_status, filled_preview, download_btn],
            )

        # ── Tab 4: Manual Edit ─────────────────────────────────────────────────
        with gr.Tab("✏️ 4. Manual Edit & Export"):
            gr.Markdown("Review and manually edit the filled table, then export.")
            edit_table = gr.Dataframe(label="Edit Table", interactive=True)
            
            with gr.Row():
                refresh_btn = gr.Button("🔄 Load Filled Table")
                export_csv_btn = gr.Button("📥 Export as CSV")
                export_xlsx_btn = gr.Button("📥 Export as Excel")

            export_status = gr.Markdown()
            export_file = gr.File(label="Download", visible=False)

            def on_refresh():
                df = state.get("df_filled") or state.get("df")
                if df is None:
                    return None
                return df

            def on_export_csv(data):
                if data is None:
                    return "⚠️ No data to export.", gr.update(visible=False)
                df = pd.DataFrame(data)
                path = "/tmp/export.csv"
                df.to_csv(path, index=False)
                return "✅ CSV ready!", gr.update(value=path, visible=True)

            def on_export_xlsx(data):
                if data is None:
                    return "⚠️ No data to export.", gr.update(visible=False)
                df = pd.DataFrame(data)
                path = "/tmp/export.xlsx"
                df.to_excel(path, index=False)
                return "✅ Excel ready!", gr.update(value=path, visible=True)

            refresh_btn.click(on_refresh, outputs=edit_table)
            export_csv_btn.click(on_export_csv, inputs=edit_table, outputs=[export_status, export_file])
            export_xlsx_btn.click(on_export_xlsx, inputs=edit_table, outputs=[export_status, export_file])

    gr.Markdown("---\n*Built with Gradio · Anthropic Claude · OpenAI · BeautifulSoup*")

if __name__ == "__main__":
    demo.launch(share=False, server_name="0.0.0.0", server_port=7860)
