import pyodbc
import os

DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_NAME = os.getenv("DB_NAME", "FilmPhotographyPlatform")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YourStrongPassword123!")

CONN_STR = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
)

def get_db_connection():
    try:
        conn = pyodbc.connect(CONN_STR, autocommit=False)
        return conn
    except Exception as e:
        print(f"Lỗi kết nối SQL Server: {e}")
        raise e