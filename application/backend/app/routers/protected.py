from fastapi import APIRouter, Depends
from app.schemas import RoleEnum, UserResponse
from app.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/protected", tags=["Protected"])

# Lấy thông tin cá nhân hiện tại
@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user

# Dashboard dành cho Khách hàng & Admin
@router.get("/customer-dashboard")
def customer_only(user: UserResponse = Depends(require_roles([RoleEnum.CUSTOMER, RoleEnum.ADMIN]))):
    return {"message": f"Welcome Customer/Admin {user.username}!"}

# Dashboard dành cho Nhà cung cấp & Admin
@router.get("/provider-dashboard")
def provider_only(user: UserResponse = Depends(require_roles([RoleEnum.PROVIDER, RoleEnum.ADMIN]))):
    return {"message": f"Welcome Provider/Admin {user.username}!"}

# Dashboard dành cho Chuyên gia & Admin
@router.get("/expert-dashboard")
def expert_only(user: UserResponse = Depends(require_roles([RoleEnum.EXPERT, RoleEnum.ADMIN]))):
    return {"message": f"Welcome Expert/Admin {user.username}!"}

# Dashboard chỉ dành riêng cho Admin
@router.get("/admin-dashboard")
def admin_only(user: UserResponse = Depends(require_roles([RoleEnum.ADMIN]))):
    return {"message": f"Welcome System Admin {user.username}!"}
