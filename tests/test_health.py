import json
from curllm_core.server import app

def test_health_endpoint():
    client = app.test_client()
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('status') == 'healthy'
    assert 'model' in data
    assert 'ollama_host' in data
