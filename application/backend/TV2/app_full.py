"""Entry point đầy đủ tính năng. Chạy: uvicorn app_full:app --reload
(main.py gốc được giữ nguyên, file này không sửa gì main.py)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from booking.router import router as booking_router
from core.config import settings
from core.exceptions import register_exception_handlers
from core.logging_config import setup_logging
from core.middleware import ProcessTimeMiddleware
from rooms.router import router as rooms_router
from stats.router import router as stats_router
from users.router import router as users_router


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ProcessTimeMiddleware)
    register_exception_handlers(app)

    app.include_router(users_router)
    app.include_router(rooms_router)
    app.include_router(booking_router)
    app.include_router(stats_router)

    @app.get("/")
    def root():
        return {"message": "Backend API Booking System đang chạy thành công!"}

    @app.get("/health", tags=["Health"])
    def health():
        return {"status": "ok", "version": settings.app_version}

    return app


app = create_app()
