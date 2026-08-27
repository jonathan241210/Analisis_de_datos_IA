from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_health_and_home():
    assert client.get("/health").json()["status"] == "ok"
    page = client.get("/")
    assert page.status_code == 200
    assert "analisis_ia" in page.text
    assert 'id="hist-col"' in page.text
    assert 'id="toast"' in page.text
    assert "select multiple" not in page.text
    assert 'id="splitter"' in page.text
    assert "multiagente" not in page.text.lower()
    assert "Especialista:" not in page.text
    assert 'id="chat-model"' in page.text
    assert settings.gemini_model in page.text
    assert "app.js?v=" in page.text
    assert "app.css?v=" in page.text
    assert 'id="btn-undo-all"' in page.text
    assert "Deshacer último cambio" in page.text
    assert 'data-tip="Formatos' not in page.text


def test_upload_and_cast():
    files = {"file": ("demo.csv", b"alumno,nota\nalumno,10.5\n", "text/csv")}
    up = client.post("/api/v1/datasets/upload", files=files)
    assert up.status_code == 200
    wr = client.post(
        "/api/v1/wrangling/apply",
        json={"op": "cast", "columns": ["nota"], "target_type": "numeric"},
    )
    assert wr.status_code == 200
    assert wr.json()["preview"]["rows"][0]["nota"] == 10.5
    dropped = client.post(
        "/api/v1/wrangling/apply",
        json={"op": "drop_columns", "columns": ["nota"]},
    )
    assert dropped.status_code == 200
    assert "nota" not in dropped.json()["columns"]
    reset = client.post("/api/v1/wrangling/reset")
    assert reset.status_code == 200
    body = reset.json()
    assert body["reset"] is True
    assert body["undo_depth"] == 0
    assert "nota" in body["columns"]


def test_histogram_and_execute_payload():
    files = {"file": ("demo.csv", b"a,b\n1,2\n3,4\n5,6\n", "text/csv")}
    assert client.post("/api/v1/datasets/upload", files=files).status_code == 200
    hist = client.get("/api/v1/eda/histogram", params={"columns": "a"})
    assert hist.status_code == 200
    assert hist.json()["figure"]["data"]
    empty = client.get("/api/v1/eda/histogram", params={"columns": ""})
    assert empty.status_code == 400
    exe = client.post("/api/v1/chat/execute", json={"code": "print(int(df.shape[0]))"})
    assert exe.status_code == 200
    body = exe.json()
    assert body["success"] is True
    assert "3" in (body.get("stdout") or "")
    assert "fig" in body
    assert "display" in body
    boom = client.post("/api/v1/chat/execute", json={"code": "1/0"})
    assert boom.status_code == 200
    fail = boom.json()
    assert fail["success"] is False
    assert fail["error"] == "No se pudo ejecutar el código."
    assert "ZeroDivision" not in (fail["error"] or "")


def test_histogram_survey_header():
    raw = "  4. ¿Asistes regularmente a clases?  ,b\n1,2\n3,4\n5,6\n".encode("utf-8")
    files = {"file": ("encuesta.csv", raw, "text/csv")}
    assert client.post("/api/v1/datasets/upload", files=files).status_code == 200
    name = "4. ¿Asistes regularmente a clases?"
    hist = client.get("/api/v1/eda/histogram", params=[("columns", name)])
    assert hist.status_code == 200
    assert hist.json()["figure"]["data"]
    padded = client.get("/api/v1/eda/histogram", params=[("columns", f"  {name}  ")])
    assert padded.status_code == 200
    preview = client.get("/api/v1/datasets/preview")
    assert preview.status_code == 200


def test_eda_report_after_upload():
    files = {"file": ("demo.csv", b"a,b\n1,x\n2,y\n3,x\n", "text/csv")}
    assert client.post("/api/v1/datasets/upload", files=files).status_code == 200
    report = client.get("/api/v1/eda/report")
    assert report.status_code == 200
    body = report.json()
    assert body["metrics"]["rows"] == 3
    assert body["metrics"]["columns"] == 2
    assert body["quality"]["columns"]
    assert "a" in body["numeric_columns"]
    assert "b" in body["categorical_columns"]
