"""Xử lý lỗi không lường trước: trả JSON thay vì lộ stack trace."""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.error")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Lỗi chưa xử lý tại %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Lỗi máy chủ nội bộ"})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Exception, unhandled_exception_handler)
