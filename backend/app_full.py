"""Tên cũ của entry point: Dockerfile và tests/conftest.py vẫn import `app_full`.
Chạy được cả hai cách: `uvicorn main:app --reload` hoặc `uvicorn app_full:app --reload`."""
from main import app  # noqa: F401
