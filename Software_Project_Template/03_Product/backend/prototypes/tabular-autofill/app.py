from __future__ import annotations
import gradio as gr
import pandas as pd

from tabular_io import load_table, save_table, is_missing
from scrape import fetch_html, html_to_text, polite_delay
from llm_backends import extract

def build_url(row: dict, mode: str, url_col: str, url_template: str) -> str:
    if mode == "url_column":
        u = row.get(url_col, "")
        return str(u).strip()
    if mode == "template":
        # Example: https://site.com/item/{sku}
        return url_template.format(**{k: ("" if row.get(k) is None else row.get(k)) for k in row.keys()})
    raise ValueError("Unknown mode")

def autofill_file(
    file_obj,
    url_mode: str,
    url_column: str,
    url_template: str,
    key_columns: list[str],
    target_columns: list[str],
    fill_policy: str,
    backend: str,
    model: str,
    max_rows: int,
    out_format: str,
):
    if file_obj is None:
        raise gr.Error("Upload a file first.")

    df = load_table(file_obj.read(), file_obj.name)

    # Basic sanity
    if df.empty:
        raise gr.Error("Uploaded table is empty.")
    for c in key_columns + target_columns:
        if c not in df.columns:
            raise gr.Error(f"Missing column: {c}")

    # Work on a copy
    out = df.copy()
    n = min(max_rows, len(out))

    logs = []
    for i in range(n):
        row = out.iloc[i].to_dict()

        # Decide which columns to fill
        if fill_policy == "only_empty":
            cols_to_fill = [c for c in target_columns if is_missing(row.get(c))]
        else:
            cols_to_fill = list(target_columns)

        if not cols_to_fill:
            logs.append(f"Row {i}: nothing to fill.")
            continue

        url = build_url(row, url_mode, url_column, url_template)
        if not url or not url.startswith(("http://", "https://")):
            logs.append(f"Row {i}: invalid URL -> {url!r}")
            continue

        try:
            html = fetch_html(url)
            text = html_to_text(html)
            row_context = {k: row.get(k) for k in key_columns}
            result = extract(
                backend=backend,
                model=model,
                page_text=text,
                columns=cols_to_fill,
                row_context=row_context
            )

            # Apply results
            for c in cols_to_fill:
                if c in result and result[c] is not None:
                    out.at[i, c] = result[c]

            logs.append(f"Row {i}: filled {len([c for c in cols_to_fill if result.get(c) is not None])}/{len(cols_to_fill)} from {url}")
        except Exception as e:
            logs.append(f"Row {i}: error -> {type(e).__name__}: {e}")

        polite_delay()

    blob = save_table(out, out_format)
    out_name = f"filled.{out_format}"
    return out, (out_name, blob), "\n".join(logs)

def infer_columns(file_obj):
    if file_obj is None:
        return gr.update(choices=[]), gr.update(choices=[])
    df = load_table(file_obj.read(), file_obj.name)
    cols = list(df.columns)
    return gr.update(choices=cols, value=[]), gr.update(choices=cols, value=[])

with gr.Blocks(title="Tabular Autofill + Web Scrape + LLM") as demo:
    gr.Markdown("## Tabular Autofill (CSV/XLSX) → Scrape Website → LLM fills missing fields")

    with gr.Row():
        file_in = gr.File(label="Upload CSV/XLSX/TSV", file_types=[".csv", ".xlsx", ".xls", ".tsv"])
        preview = gr.Dataframe(label="Preview (after fill)", interactive=False)

    with gr.Row():
        url_mode = gr.Radio(
            choices=[("Use URL column", "url_column"), ("Use URL template", "template")],
            value="url_column",
            label="How to get the URL for each row"
        )
        url_column = gr.Textbox(value="url", label="URL column name (if using URL column)")
        url_template = gr.Textbox(value="https://example.com/item/{sku}", label="URL template (if using template)")

    with gr.Row():
        key_cols = gr.Dropdown(multiselect=True, label="Key columns (context to help matching)", choices=[])
        target_cols = gr.Dropdown(multiselect=True, label="Columns to autofill", choices=[])

    with gr.Row():
        fill_policy = gr.Radio(
            choices=[("Only fill empty cells", "only_empty"), ("Overwrite target columns", "overwrite")],
            value="only_empty",
            label="Fill policy"
        )
        max_rows = gr.Slider(1, 500, value=50, step=1, label="Max rows to process (limit for safety)")
        out_format = gr.Radio(choices=["csv", "xlsx"], value="xlsx", label="Output format")

    with gr.Row():
        backend = gr.Dropdown(
            choices=["openai", "anthropic", "gemini", "ollama"],
            value="ollama",
            label="LLM backend"
        )
        model = gr.Textbox(value="llama3.1:8b", label="Model name (depends on backend)")

    run_btn = gr.Button("Run Autofill")
    download = gr.File(label="Download filled file")
    logs = gr.Textbox(label="Logs", lines=12)

    file_in.change(fn=infer_columns, inputs=[file_in], outputs=[key_cols, target_cols])

    run_btn.click(
        fn=autofill_file,
        inputs=[file_in, url_mode, url_column, url_template, key_cols, target_cols, fill_policy, backend, model, max_rows, out_format],
        outputs=[preview, download, logs]
    )

demo.launch()