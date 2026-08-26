"""response_model 用例:/docs OpenAPI schema 里响应结构完整可读。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from instrumental_prompt.main import app

client = TestClient(app)


def test_openapi_documents_prompt_response_fields():
    """OpenAPI schema 必须声明 /prompt 响应的全部字段——后端在 /docs 看契约。"""
    spec = client.get("/openapi.json").json()
    resp = spec["paths"]["/prompt"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]

    # $ref 指向 components 里的 PromptResponse
    ref = resp.get("$ref", "")
    assert ref.endswith("PromptResponse"), f"响应未挂 PromptResponse 模型: {resp}"
    props = spec["components"]["schemas"]["PromptResponse"]["properties"]
    for field in ("ok", "scheme", "prompt"):
        assert field in props, f"缺字段 {field}"
    for optional in ("lyria_response", "audio", "generation_text"):
        assert optional in props, f"缺可选字段 {optional}"


def test_openapi_documents_health_response():
    spec = client.get("/openapi.json").json()
    resp = spec["paths"]["/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    ref = resp.get("$ref", "")
    assert ref.endswith("HealthResponse"), f"响应未挂 HealthResponse 模型: {resp}"
    props = spec["components"]["schemas"]["HealthResponse"]["properties"]
    for field in ("ok", "model", "gemini_key_present", "key_source"):
        assert field in props, f"缺字段 {field}"


def test_small_response_shape_unchanged():
    """挂模型后小响应字段值不变——行为兼容。"""
    r = client.post("/prompt", json={"user_input": "来一首粤语老情歌", "instrumental": True})
    body = r.json()
    assert body["ok"] is True and body["scheme"] == "B"
    assert "<user_input>" in body["prompt"]
