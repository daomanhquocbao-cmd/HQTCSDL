from fastapi import HTTPException
from booking.models import BookingModel
from booking.schemas import CreateBookingSchema

class BookingService:
    @staticmethod
    def create_new_booking(user_id: int, data: CreateBookingSchema):
        start_str = data.start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_str = data.end_time.strftime('%Y-%m-%d %H:%M:%S')

        res = BookingModel.create_booking_sp(
            user_id=user_id,
            room_id=data.room_id,
            start_time=start_str,
            end_time=end_str,
            equipment_ids=data.equipment_ids
        )

        if res["status"] == "CONFLICT":
            raise HTTPException(status_code=409, detail="ROOM_CONFLICT: Phòng đã được đặt trong khoảng thời gian này.")
        if res["status"] != "SUCCESS":
            raise HTTPException(status_code=500, detail="DATABASE_ERROR: Lỗi xử lý đặt lịch từ CSDL.")

        return res

    @staticmethod
    def cancel_booking(booking_id: int, user_info: dict):
        booking = BookingModel.get_booking_by_id(booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="NOT_FOUND: Không tìm thấy lịch đặt.")

        if booking["user_id"] != user_info["user_id"] and user_info["role"] != "admin":
            raise HTTPException(status_code=403, detail="FORBIDDEN: Bạn không có quyền hủy lịch này.")

        BookingModel.update_status(booking_id, "CANCELLED")
        return {"message": "Đã hủy lịch đặt thành công."}