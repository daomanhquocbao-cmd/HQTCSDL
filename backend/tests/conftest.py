import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_full import app  # noqa: E402
from booking.auth import create_access_token  # noqa: E402


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture
def user_headers():
    return {"Authorization": f"Bearer {create_access_token(1, 'customer')}"}


@pytest.fixture
def admin_headers():
    return {"Authorization": f"Bearer {create_access_token(99, 'admin')}"}
