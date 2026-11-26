"""Entry point đầy đủ tính năng. Chạy: uvicorn app_full:app --reload
(app_full.py chỉ import lại `app` từ file này)."""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # phải chạy TRƯỚC khi import core.config / database (chúng đọc biến môi trường lúc import)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from admin.router import router as admin_router  # noqa: E402
from ai.router import router as ai_router  # noqa: E402
from booking.router import router as booking_router  # noqa: E402
from customer.router import router as customer_router  # noqa: E402
from community.router import router as community_router  # noqa: E402
from integrations.router import router as integrations_router  # noqa: E402
from photos.router import router as photos_router  # noqa: E402
from photos.service import UPLOAD_DIR  # noqa: E402
from pricing.router import router as pricing_router  # noqa: E402
from core.config import settings  # noqa: E402
from core.exceptions import register_exception_handlers  # noqa: E402
from core.logging_config import setup_logging  # noqa: E402
from core.middleware import ProcessTimeMiddleware  # noqa: E402
from provider.router import profile_router, router as provider_router  # noqa: E402
from rooms.router import router as rooms_router  # noqa: E402
from stats.router import router as stats_router  # noqa: E402
from studios.router import router as studios_router  # noqa: E402
from users.router import router as users_router  # noqa: E402
from workshops.router import router as workshops_router  # noqa: E402

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


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
    app.include_router(profile_router)
    app.include_router(provider_router)
    app.include_router(studios_router)
    app.include_router(rooms_router)
    app.include_router(booking_router)
    app.include_router(workshops_router)
    app.include_router(stats_router)
    app.include_router(admin_router)
    app.include_router(community_router)
    app.include_router(ai_router)
    app.include_router(pricing_router)
    app.include_router(customer_router)
    app.include_router(photos_router)
    app.include_router(integrations_router)

    @app.get("/")
    def root():
        return {"message": "Backend API Booking System đang chạy thành công!"}

    @app.get("/health", tags=["Health"])
    def health():
        return {"status": "ok", "version": settings.app_version}

    # Ảnh khách tải lên / ảnh đã phục hồi (đường dẫn khó đoán: <user_id>/<uuid>.jpg)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

    # Phục vụ giao diện tại /web (chỉ khi thư mục frontend tồn tại, vd. không có trong Docker)
    if FRONTEND_DIR.is_dir():
        app.mount("/web", StaticFiles(directory=FRONTEND_DIR, html=True), name="web")

    return app


app = create_app()
