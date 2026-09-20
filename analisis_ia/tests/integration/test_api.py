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
    assert 'id="chat-mode"' in page.text
    assert "Asistente" in page.text
    assert ">Agente<" in page.text or "data-chat-mode=\"agent\"" in page.text
    assert 'id="chat-settings-btn"' in page.text
    assert 'id="llm-settings"' in page.text
    assert 'id="db-connect"' in page.text
    assert 'id="ingest-tech-wrap"' in page.text


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


def test_chat_replace_last(monkeypatch):
    async def fake_reply(*_a, **_k):
        return "respuesta de prueba", None

    monkeypatch.setattr("app.services.copilot.orchestrator.generate_reply_routed", fake_reply)
    files = {"file": ("demo.csv", b"nota\n1\n2\n", "text/csv")}
    assert client.post("/api/v1/datasets/upload", files=files).status_code == 200
    first = client.post("/api/v1/chat/message", json={"message": "hola", "tab": "eda"})
    assert first.status_code == 200
    hist = client.get("/api/v1/chat/history").json()["history"]
    assert hist[-2]["content"] == "hola"
    second = client.post(
        "/api/v1/chat/message",
        json={"message": "hola editado", "tab": "eda", "replace_last": True},
    )
    assert second.status_code == 200
    hist = client.get("/api/v1/chat/history").json()["history"]
    user_msgs = [m["content"] for m in hist if m["role"] == "user"]
    assert user_msgs == ["hola editado"]


def test_chat_apply_drop_duplicates():
    files = {"file": ("demo.csv", b"a,b\n1,2\n1,2\n3,4\n", "text/csv")}
    assert client.post("/api/v1/datasets/upload", files=files).status_code == 200
    applied = client.post(
        "/api/v1/chat/apply",
        json={"op": "drop_duplicates", "label": "Quitar duplicados"},
    )
    assert applied.status_code == 200
    body = applied.json()
    assert body["success"] is True
    assert body["mutated"] is True
    assert body["preview"]["shape"][0] == 2


def test_agent_stream_scripted(monkeypatch):
    from app.services.copilot.gemini_client import ModelTurn

    n = {"i": 0}

    async def fake_tools(_session, _system, _contents):
        n["i"] += 1
        if n["i"] == 1:
            return ModelTurn(calls=[{"name": "inspect_dataset", "args": {"focus": "duplicates"}}]), None
        return ModelTurn(text="Hay duplicados. Quita filas repetidas antes de entrenar."), None

    monkeypatch.setattr("app.api.v1.chat.generate_with_tools_routed", fake_tools)
    files = {"file": ("demo.csv", b"a,b\n1,2\n1,2\n", "text/csv")}
    assert client.post("/api/v1/datasets/upload", files=files).status_code == 200
    with client.stream("POST", "/api/v1/chat/agent", json={"message": "analiza", "tab": "eda"}) as res:
        assert res.status_code == 200
        raw = b"".join(res.iter_bytes()).decode("utf-8")
    assert "duplicad" in raw.lower()
    assert '"type": "final"' in raw or '"type":"final"' in raw
    assert "Hay duplicados" in raw


def test_chat_token_error(monkeypatch):
    from app.services.copilot.errors import MSG_TOKENS
    from app.services.copilot.gemini_client import GeminiUnavailable

    async def boom(*_a, **_k):
        raise GeminiUnavailable(MSG_TOKENS)

    monkeypatch.setattr("app.services.copilot.orchestrator.generate_reply_routed", boom)
    files = {"file": ("demo.csv", b"nota\n1\n", "text/csv")}
    assert client.post("/api/v1/datasets/upload", files=files).status_code == 200
    res = client.post("/api/v1/chat/message", json={"message": "hola", "tab": "eda"})
    assert res.status_code == 503
    assert res.json()["detail"] == MSG_TOKENS


def test_correlation_ok_and_unexpected_is_clean(monkeypatch):
    from app.core.exceptions import MSG_PLOT_CLEAN

    files = {"file": ("demo.csv", b"a,b\n1,2\n3,4\n5,6\n", "text/csv")}
    assert client.post("/api/v1/datasets/upload", files=files).status_code == 200
    ok = client.get("/api/v1/eda/correlation")
    assert ok.status_code == 200
    assert ok.json()["figure"]["data"]

    def boom(_df):
        raise TypeError("imshow() got an unexpected keyword argument 'autosize'")

    monkeypatch.setattr("app.api.v1.eda.correlation_spec", boom)
    failed = client.get("/api/v1/eda/correlation")
    assert failed.status_code == 400
    detail = failed.json()["detail"]
    assert detail == MSG_PLOT_CLEAN
    assert "autosize" not in detail
    assert "TypeError" not in detail
    assert "Traceback" not in detail


def test_db_connect_is_stub():
    from app.core.exceptions import MSG_DB_CONNECT_SOON

    res = client.post(
        "/api/v1/datasets/db-connect",
        json={"engine": "postgresql", "host": "localhost", "password": "secret-pass"},
    )
    assert res.status_code == 501
    body = res.json()
    assert body["detail"] == MSG_DB_CONNECT_SOON
    dumped = str(body)
    assert "secret-pass" not in dumped


def test_llm_settings_hides_keys_and_fallback(monkeypatch):
    from app.services.copilot.errors import MSG_TOKENS
    from app.services.copilot.gemini_client import GeminiUnavailable, ModelTurn

    files = {"file": ("demo.csv", b"nota\n1\n2\n", "text/csv")}
    assert client.post("/api/v1/datasets/upload", files=files).status_code == 200

    saved = client.post(
        "/api/v1/settings/llm",
        json={
            "active_id": "gemini",
            "slots": [
                {"id": "gemini", "model": "gemini-2.0-flash", "key_mode": "user", "api_key": "gk-secret-test"},
                {"id": "openai", "model": "gpt-4o-mini", "key_mode": "user", "api_key": "sk-secret-test"},
                {"id": "anthropic", "model": "claude-sonnet-4-5", "key_mode": "user"},
            ],
        },
    )
    assert saved.status_code == 200
    public = saved.json()
    blob = str(public)
    assert "gk-secret-test" not in blob
    assert "sk-secret-test" not in blob
    assert "api_key" not in public
    assert public["active_id"] == "gemini"
    by_id = {row["id"]: row for row in public["slots"]}
    assert by_id["gemini"]["has_user_key"] is True
    assert by_id["openai"]["has_user_key"] is True
    assert by_id["anthropic"]["has_user_key"] is False

    got = client.get("/api/v1/settings/llm").json()
    assert "gk-secret-test" not in str(got)
    assert "api_key" not in got

    async def fake_call(slot, **_k):
        if slot["id"] == "gemini":
            raise GeminiUnavailable(MSG_TOKENS)
        return ModelTurn(text="respuesta de openai")

    monkeypatch.setattr("app.services.copilot.llm_router._call_slot", fake_call)
    res = client.post("/api/v1/chat/message", json={"message": "hola", "tab": "eda"})
    assert res.status_code == 200
    body = res.json()
    assert body["content"] == "respuesta de openai"
    assert body["fallback"]["from_id"] == "gemini"
    assert body["fallback"]["to_id"] == "openai"
    after = client.get("/api/v1/settings/llm").json()
    assert after["active_id"] == "openai"


def test_llm_settings_validation_redacts_key():
    res = client.post(
        "/api/v1/settings/llm",
        json={"active_id": "gemini", "slots": [{"id": "gemini", "api_key": 12345}]},
    )
    assert res.status_code == 422
    dumped = str(res.json())
    assert "12345" not in dumped
    assert "[redacted]" in dumped
