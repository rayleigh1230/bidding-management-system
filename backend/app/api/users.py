from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user, get_password_hash
from ..models.user import User
from ..schemas.user import UserCreate, UserUpdate, UserResponse
from ..services.logger import log_operation

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all users."""
    users = db.query(User).order_by(User.id.asc()).all()
    return users


@router.post("", response_model=UserResponse)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new user with hashed password."""
    # Only admins can create users
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可创建用户")

    # Check if username already exists
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        display_name=data.display_name,
        role=data.role,
        phone=data.phone,
        is_active=True,
    )
    db.add(user)
    db.flush()
    log_operation(db, current_user.id, "create", "user", user.id, f"创建用户: {user.username}")
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a user. If password is provided, hash it before saving."""
    # Only admins can update users
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可更新用户")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    # Handle password separately: hash it before storing
    plain_password = update_data.pop("password", None)

    for field, value in update_data.items():
        setattr(user, field, value)

    if plain_password is not None:
        user.password_hash = get_password_hash(plain_password)

    log_operation(db, current_user.id, "update", "user", user.id, f"更新用户: {user.username}")
    db.commit()
    db.refresh(user)
    return user
