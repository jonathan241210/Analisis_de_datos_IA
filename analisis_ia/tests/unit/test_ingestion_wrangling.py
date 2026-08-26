import pandas as pd

from app.services.ingestion import ingest_upload
from app.services.wrangling import apply_wrangling


def test_csv_ingest():
    raw = b"alumno,nota\nana,10.5\n"
    df, meta = ingest_upload("demo.csv", raw)
    assert list(df.columns) == ["alumno", "nota"]
    assert meta["formato"] == "CSV"


def test_ingest_strips_padded_headers():
    raw = "  nota  ,alumno\n10,ana\n".encode("utf-8")
    df, _ = ingest_upload("demo.csv", raw)
    assert list(df.columns) == ["nota", "alumno"]


def test_impute_constant():
    df = pd.DataFrame({"alumno": ["ana", None]})
    out = apply_wrangling(df, "impute", columns=["alumno"], strategy="Constante", value="NA")
    assert out["alumno"].iloc[1] == "NA"


def test_cast_multiple_numeric():
    df = pd.DataFrame({"nota": ["10.5", "8"], "extra": ["1", "2"]})
    out = apply_wrangling(df, "cast", columns=["nota", "extra"], target_type="numeric")
    assert float(out["nota"].iloc[0]) == 10.5
    assert float(out["extra"].iloc[1]) == 2.0
