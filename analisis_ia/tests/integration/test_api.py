from fastapi.testclient import TestClient

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
