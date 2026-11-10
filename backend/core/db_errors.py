"""Tách nội dung RAISERROR của SQL Server ra khỏi chuỗi lỗi của pyodbc."""
import re


def extract_message(exc: Exception) -> str:
    text = str(exc)
    match = re.search(r"\[SQL Server\](.*?)(?: \(\d+\))", text, re.S)
    return (match.group(1) if match else text).strip()
