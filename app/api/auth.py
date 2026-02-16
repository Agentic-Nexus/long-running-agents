"""
认证 API 路由

提供用户注册、登录、令牌刷新、API 密钥管理等接口。
"""
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.services.auth_service import (
    AuthService,
    create_access_token,
    create_refresh_token,
    decode_token,
)

# 路由和安全
router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


# ============ Pydantic 模型 ============

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: str
    display_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    api_quota: int
    api_used: int

    class Config:
        from_attributes = True


class CreateAPIKeyRequest(BaseModel):
    """创建 API 密钥请求"""
    name: str = Field(..., min_length=1, max_length=100, description="密钥名称")
    expires_days: Optional[int] = Field(None, ge=1, le=365, description="过期天数")


class APIKeyResponse(BaseModel):
    """API 密钥响应"""
    id: int
    name: str
    key_prefix: str
    is_active: bool
    expires_at: Optional[str]
    created_at: str
    last_used_at: Optional[str]

    class Config:
        from_attributes = True


class APIKeyWithSecretResponse(BaseModel):
    """带密钥的 API 密钥响应"""
    id: int
    name: str
    api_key: str
    key_prefix: str
    is_active: bool
    expires_at: Optional[str]
    created_at: str


# ============ 依赖项 ============

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    获取当前用户

    从 Bearer token 或 API Key 中提取用户信息。
    支持两种认证方式：
    1. Bearer token (JWT)
    2. API Key (以 sk_ 开头)
    """
    auth_service = AuthService(session)

    # 方式1: 使用 Bearer Token
    if credentials:
        token = credentials.credentials
        payload = decode_token(token)

        if payload:
            user_id = payload.get("sub")
            if user_id:
                user = await auth_service.get_user_by_id(int(user_id))
                if user and user.is_active:
                    return UserResponse.model_validate(user)

    # 方式2: 使用 API Key (从 Authorization header 获取)
    # 需要从请求中获取原始 Authorization header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未提供有效的认证凭据",
        headers={"WWW-Authenticate": "Bearer, APIKey"},
    )


async def get_current_user_optional(
    session: AsyncSession = Depends(get_session),
) -> Optional[UserResponse]:
    """
    获取当前用户（可选）

    返回当前用户，如果未认证则返回 None。
    """
    return None  # 可以扩展为支持可选认证


async def get_current_admin(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """
    获取当前管理员用户
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


# ============ 路由 ============

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    用户注册

    创建新用户账户。
    """
    auth_service = AuthService(session)

    try:
        user = await auth_service.register_user(
            username=request.username,
            email=request.email,
            password=request.password,
            display_name=request.display_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    用户登录

    返回访问令牌和刷新令牌。
    """
    auth_service = AuthService(session)
    user = await auth_service.authenticate_user(
        username=request.username,
        password=request.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建令牌
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "username": user.username}
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=30 * 60,  # 30 分钟
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    刷新令牌

    使用刷新令牌获取新的访问令牌。
    """
    payload = decode_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌载荷",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(session)
    user = await auth_service.get_user_by_id(int(user_id))

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建新令牌
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id), "username": user.username}
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=30 * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user),
):
    """
    获取当前用户信息

    返回当前登录用户的详细信息。
    """
    return current_user


@router.post("/api-keys", response_model=APIKeyWithSecretResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    创建 API 密钥

    为当前用户创建一个新的 API 密钥。
    注意：密钥只会在创建时显示一次，请妥善保存。
    """
    auth_service = AuthService(session)

    try:
        api_key_record, api_key = await auth_service.create_api_key(
            user_id=current_user.id,
            name=request.name,
            expires_days=request.expires_days,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return APIKeyWithSecretResponse(
        id=api_key_record.id,
        name=api_key_record.name,
        api_key=api_key,
        key_prefix=api_key_record.key_prefix,
        is_active=api_key_record.is_active,
        expires_at=api_key_record.expires_at.isoformat() if api_key_record.expires_at else None,
        created_at=api_key_record.created_at.isoformat(),
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    列出 API 密钥

    返回当前用户的所有 API 密钥。
    """
    auth_service = AuthService(session)
    keys = await auth_service.list_api_keys(current_user.id)

    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            is_active=key.is_active,
            expires_at=key.expires_at.isoformat() if key.expires_at else None,
            created_at=key.created_at.isoformat(),
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        )
        for key in keys
    ]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: int,
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    删除 API 密钥

    删除指定的 API 密钥。
    """
    auth_service = AuthService(session)
    success = await auth_service.delete_api_key(current_user.id, key_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API 密钥不存在",
        )


@router.get("/quota", response_model=dict)
async def get_quota(
    current_user: UserResponse = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    获取 API 配额

    返回当前用户的 API 配额使用情况。
    """
    auth_service = AuthService(session)
    has_quota, used, total = await auth_service.check_quota(current_user.id)

    return {
        "has_quota": has_quota,
        "used": used,
        "total": total,
        "remaining": total - used,
    }
