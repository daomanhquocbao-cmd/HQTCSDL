from typing import Optional
from pydantic import BaseModel, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
USERNAME_PATTERN = r"^[A-Za-z0-9_.]+$"

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=USERNAME_PATTERN)
    email: str = Field(..., pattern=EMAIL_PATTERN, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=100, description="Họ và tên người dùng")
    phone: Optional[str] = Field(default=None, max_length=20)
    role: Optional[str] = Field(default="CUSTOMER", description="CUSTOMER, PROVIDER, EXPERT")

class UserLogin(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

class UserOut(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    status: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
