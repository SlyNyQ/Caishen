from __future__ import annotations
import io
import os
from typing import Union

import pandas as pd

SUPPORTED_EXTS = (".csv", ".tsv", ".xlsx", ".xls")

def load_table(file_input: Union[bytes, str], filename: str | None = None) -> pd.DataFrame:
    """
    file_input can be:
      - bytes (raw file content)
      - str (a filesystem path)
    filename is required only when file_input is bytes.
    """
    if isinstance(file_input, str):
        path = file_input
        name = os.path.basename(path).lower()

        if name.endswith(".csv"):
            return pd.read_csv(path)
        if name.endswith(".tsv"):
            return pd.read_csv(path, sep="\t")
        if name.endswith((".xlsx", ".xls")):
            return pd.read_excel(path)

        raise ValueError(f"Unsupported file type: {name}. Supported: {SUPPORTED_EXTS}")

    # bytes path
    if filename is None:
        raise ValueError("filename must be provided when file_input is bytes.")

    name = filename.lower()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(file_input))
    if name.endswith(".tsv"):
        return pd.read_csv(io.BytesIO(file_input), sep="\t")
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(file_input))

    raise ValueError(f"Unsupported file type: {filename}. Supported: {SUPPORTED_EXTS}")


def save_table(df: pd.DataFrame, out_format: str) -> bytes:
    out_format = out_format.lower().strip()
    buf = io.BytesIO()
    if out_format == "csv":
        df.to_csv(buf, index=False)
        return buf.getvalue()
    if out_format == "xlsx":
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="Filled")
        return buf.getvalue()
    raise ValueError("out_format must be 'csv' or 'xlsx'")


def is_missing(x) -> bool:
    if x is None:
        return True
    if isinstance(x, float) and pd.isna(x):
        return True
    if isinstance(x, str) and x.strip() == "":
        return True
    return False