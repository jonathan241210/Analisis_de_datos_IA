from io import BytesIO

import chardet
import pandas as pd

from app.core.exceptions import AppError
from app.services.dataframe_ops import normalize_column_labels


def detect_encoding(raw_bytes: bytes) -> str:
    result = chardet.detect(raw_bytes[:200_000])
    return result.get("encoding") or "utf-8"


def sniff_separator(sample_text: str) -> str:
    candidates = [",", ";", "\t", "|"]
    counts = {c: sample_text.count(c) for c in candidates}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def read_tabular(filename: str, raw_bytes: bytes) -> tuple[pd.DataFrame, dict]:
    name = filename.lower()
    meta = {"file_name": filename}

    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(BytesIO(raw_bytes))
        meta.update({"formato": "Excel", "encoding": "N/A (binario)", "separador": "N/A"})
        return normalize_column_labels(df), meta

    encoding = detect_encoding(raw_bytes)
    text_sample = raw_bytes[:5000].decode(encoding, errors="replace")
    separator = "\t" if name.endswith(".tsv") else sniff_separator(text_sample)
    df = pd.read_csv(BytesIO(raw_bytes), sep=separator, encoding=encoding)
    meta.update({
        "formato": "TSV" if name.endswith(".tsv") else "CSV",
        "encoding": encoding,
        "separador": repr(separator),
    })
    return normalize_column_labels(df), meta


def ingest_upload(filename: str, raw_bytes: bytes) -> tuple[pd.DataFrame, dict]:
    allowed = (".csv", ".tsv", ".xlsx", ".xls")
    if not filename.lower().endswith(allowed):
        raise AppError("Formato no permitido. Usa CSV, TSV o Excel.", 400)
    try:
        return read_tabular(filename, raw_bytes)
    except Exception as exc:
        raise AppError(f"No se pudo leer el archivo: {exc}", 400) from exc
