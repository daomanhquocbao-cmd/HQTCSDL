from fastapi import APIRouter, Depends, HTTPException, status
from core.config import settings
from core.security import create_access_token, get_current_user
from users import service
from users.schemas import TokenOut, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister):
    try:
        return service.register_user(
            username=data.username,
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            phone=data.phone,
            role=data.role
        )
    except service.DuplicateUserError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

@router.post("/login", response_model=TokenOut)
def login(data: UserLogin):
    try:
        user = service.authenticate(data.username, data.password)
    except service.InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except service.AccountLockedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
        
    token = create_access_token(user["user_id"], user["role"], settings.access_token_minutes)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserOut)
def me(current: dict = Depends(get_current_user)):
    try:
        return service.get_user(current["user_id"])
    except service.UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
