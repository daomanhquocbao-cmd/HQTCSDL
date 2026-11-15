from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


@pytest.mark.skipif(not FRONTEND.is_dir(), reason="không có thư mục frontend")
def test_web_serves_provider_login(client):
    assert client.get("/web/provider/provider-login.html").status_code == 200
