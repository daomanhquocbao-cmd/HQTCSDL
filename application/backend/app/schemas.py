from pydantic import BaseModel, EmailStr
from enum import Enum

# Enum chứa 4 vai trò của dự án
class RoleEnum(str, Enum):
    CUSTOMER = "CUSTOMER"
    PROVIDER = "PROVIDER"
    EXPERT = "EXPERT"
    ADMIN = "ADMIN"

# Cấu trúc dữ liệu gửi lên khi Đăng ký
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: RoleEnum = RoleEnum.CUSTOMER

# Cấu trúc Token trả về khi Đăng nhập
class Token(BaseModel):
    access_token: str
    token_type: str

# Cấu trúc thông tin User trả về cho Frontend (ẩn password)
class UserResponse(BaseModel):
    username: str
    email: str
    role: RoleEnum
