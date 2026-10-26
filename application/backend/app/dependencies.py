from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from app.config import SECRET_KEY, ALGORITHM
from app.database import users_db
from app.schemas import RoleEnum, UserResponse

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Xử lý xác thực Token gửi lên từ phía Client
def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in users_db:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = users_db[username]
    return UserResponse(username=user["username"], email=user["email"], role=user["role"])

# Hàm phân quyền: Chỉ cho phép các Role chỉ định truy cập API
def require_roles(allowed_roles: list[RoleEnum]):
    def role_checker(current_user: UserResponse = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied for this role"
            )
        return current_user
    return role_checker
