from fastapi import FastAPI
from booking.router import router as booking_router

app = FastAPI(title="Booking System API - Python FastAPI")

app.include_router(booking_router)

@app.get("/")
def root():
    return {"message": "Backend API Booking System đang chạy thành công!"}