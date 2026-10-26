from fastapi import FastAPI
from app.routers import auth, protected

app = FastAPI(title="HQTCSDL Backend Authentication & RBAC API")

# Đăng ký danh sách các Router
app.include_router(auth.router)
app.include_router(protected.router)

@app.get("/")
def root():
    return {"message": "Backend Authentication & RBAC API is running!"}
