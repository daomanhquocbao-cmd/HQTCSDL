import json
from database import get_db_connection

class BookingModel:
    @staticmethod
    def create_booking_sp(user_id: int, room_id: int, start_time: str, end_time: str, equipment_ids: list):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            equipment_json = json.dumps(equipment_ids)
            cursor.execute(
                "{CALL sp_CreateBookingSecure (?, ?, ?, ?, ?)}",
                (user_id, room_id, start_time, end_time, equipment_json)
            )
            row = cursor.fetchone()
            conn.commit()
            if row:
                return {"status": row[0], "booking_id": row[1], "total_amount": float(row[2]) if row[2] else 0}
            return {"status": "FAILED", "booking_id": 0, "total_amount": 0}
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def get_all_bookings(status_filter: str = None, user_id: int = None):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT booking_id, user_id, room_id, start_time, end_time, total_amount, status FROM Bookings WHERE 1=1"
            params = []
            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            bookings = []
            for r in rows:
                bookings.append({
                    "booking_id": r[0], "user_id": r[1], "room_id": r[2],
                    "start_time": r[3], "end_time": r[4], "total_amount": float(r[5]), "status": r[6]
                })
            return bookings
        finally:
            conn.close()

    @staticmethod
    def get_booking_by_id(booking_id: int):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT booking_id, user_id, room_id, start_time, end_time, total_amount, status FROM Bookings WHERE booking_id = ?", (booking_id,))
            r = cursor.fetchone()
            if r:
                return {
                    "booking_id": r[0], "user_id": r[1], "room_id": r[2],
                    "start_time": r[3], "end_time": r[4], "total_amount": float(r[5]), "status": r[6]
                }
            return None
        finally:
            conn.close()

    @staticmethod
    def update_status(booking_id: int, new_status: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE Bookings SET status = ? WHERE booking_id = ?", (new_status, booking_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()