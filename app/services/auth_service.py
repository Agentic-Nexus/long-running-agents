"""
认证服务模块

提供用户认证、授权和 API 密钥管理功能。
"""
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_config
from app.models.user import APIKey, User, UserSession, UserRole

# JWT 算法
ALGORITHM = "HS256"


def get_password_hash(password: str) -> str:
    """
    密码哈希

    Args:
        password: 原始密码

    Returns:
        哈希后的密码
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 原始密码
        hashed_password: 哈希后的密码

    Returns:
        是否匹配
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌

    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量

    Returns:
        JWT 令牌
    """
    config = get_config()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode, config.secret_key, algorithm=ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    创建刷新令牌

    Args:
        data: 要编码的数据

    Returns:
        JWT 刷新令牌
    """
    config = get_config()
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=config.refresh_token_expire_days)
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode, config.secret_key, algorithm=ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    解码令牌

    Args:
        token: JWT 令牌

    Returns:
        解码后的数据，失败返回 None
    """
    try:
        payload = jwt.decode(token, get_config().secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_api_key() -> tuple[str, str]:
    """
    生成 API 密钥

    Returns:
        (完整密钥, 密钥前缀)
    """
    # 生成 32 位随机密钥
    key = "sk_" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    # 密钥前缀用于显示
    prefix = key[:12] + "..."
    return key, prefix


def hash_api_key(api_key: str) -> str:
    """
    哈希 API 密钥

    Args:
        api_key: 原始 API 密钥

    Returns:
        哈希后的密钥
    """
    return bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    验证 API 密钥

    Args:
        plain_key: 原始密钥
        hashed_key: 哈希后的密钥

    Returns:
        是否匹配
    """
    return bcrypt.checkpw(plain_key.encode('utf-8'), hashed_key.encode('utf-8'))


class AuthService:
    """认证服务类"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        display_name: Optional[str] = None,
    ) -> User:
        """
        注册新用户

        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            display_name: 显示名称

        Returns:
            创建的用户

        Raises:
            ValueError: 用户名或邮箱已存在
        """
        # 检查用户名是否存在
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        if result.scalar_one_or_none():
            raise ValueError("用户名已存在")

        # 检查邮箱是否存在
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        if result.scalar_one_or_none():
            raise ValueError("邮箱已被注册")

        # 创建用户
        user = User(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            display_name=display_name or username,
            role=UserRole.BASIC.value,
            is_active=True,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        return user

    async def authenticate_user(
        self,
        username: str,
        password: str,
    ) -> Optional[User]:
        """
        验证用户登录

        Args:
            username: 用户名或邮箱
            password: 密码

        Returns:
            用户对象，认证失败返回 None
        """
        # 支持用户名或邮箱登录
        result = await self.session.execute(
            select(User).where(
                (User.username == username) | (User.email == username)
            )
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            return None

        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        await self.session.commit()

        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        根据 ID 获取用户

        Args:
            user_id: 用户 ID

        Returns:
            用户对象，不存在返回 None
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名获取用户

        Args:
            username: 用户名

        Returns:
            用户对象，不存在返回 None
        """
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        根据邮箱获取用户

        Args:
            email: 邮箱

        Returns:
            用户对象，不存在返回 None
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def update_user(
        self,
        user_id: int,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> Optional[User]:
        """
        更新用户信息

        Args:
            user_id: 用户 ID
            display_name: 显示名称
            avatar_url: 头像 URL

        Returns:
            更新后的用户，不存在返回 None
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        if display_name is not None:
            user.display_name = display_name
        if avatar_url is not None:
            user.avatar_url = avatar_url

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def create_api_key(
        self,
        user_id: int,
        name: str,
        expires_days: Optional[int] = None,
    ) -> tuple[APIKey, str]:
        """
        创建 API 密钥

        Args:
            user_id: 用户 ID
            name: 密钥名称
            expires_days: 过期天数，None 表示永不过期

        Returns:
            (APIKey 对象, 原始密钥)
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")

        # 生成密钥
        api_key, key_prefix = generate_api_key()

        # 计算过期时间
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        # 创建 API 密钥记录
        api_key_record = APIKey(
            user_id=user_id,
            name=name,
            key_hash=hash_api_key(api_key),
            key_prefix=key_prefix,
            is_active=True,
            expires_at=expires_at,
        )
        self.session.add(api_key_record)
        await self.session.commit()
        await self.session.refresh(api_key_record)

        return api_key_record, api_key

    async def verify_api_key(self, api_key: str) -> Optional[User]:
        """
        验证 API 密钥

        Args:
            api_key: 原始 API 密钥

        Returns:
            用户对象，验证失败返回 None
        """
        # 遍历所有活跃的 API 密钥进行验证
        result = await self.session.execute(
            select(APIKey).where(APIKey.is_active == True)
        )
        api_keys = result.scalars().all()

        for key_record in api_keys:
            if verify_api_key(api_key, key_record.key_hash):
                # 检查是否过期
                if key_record.expires_at and key_record.expires_at < datetime.utcnow():
                    return None

                # 更新最后使用时间
                key_record.last_used_at = datetime.utcnow()
                await self.session.commit()

                # 返回关联用户
                return await self.get_user_by_id(key_record.user_id)

        return None

    async def list_api_keys(self, user_id: int) -> list[APIKey]:
        """
        列出用户的 API 密钥

        Args:
            user_id: 用户 ID

        Returns:
            API 密钥列表
        """
        result = await self.session.execute(
            select(APIKey)
            .where(APIKey.user_id == user_id)
            .order_by(APIKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_api_key(self, user_id: int, key_id: int) -> bool:
        """
        删除 API 密钥

        Args:
            user_id: 用户 ID
            key_id: 密钥 ID

        Returns:
            是否删除成功
        """
        result = await self.session.execute(
            select(APIKey).where(
                APIKey.id == key_id,
                APIKey.user_id == user_id
            )
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            return False

        await self.session.delete(api_key)
        await self.session.commit()
        return True

    async def create_session(
        self,
        user_id: int,
        jti: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> UserSession:
        """
        创建用户会话

        Args:
            user_id: 用户 ID
            jti: JWT ID
            device_info: 设备信息
            ip_address: IP 地址
            expires_delta: 过期时间增量

        Returns:
            会话对象
        """
        config = get_config()
        if expires_delta:
            expires_at = datetime.utcnow() + expires_delta
        else:
            expires_at = datetime.utcnow() + timedelta(days=config.refresh_token_expire_days)

        session = UserSession(
            user_id=user_id,
            jti=jti,
            device_info=device_info,
            ip_address=ip_address,
            is_valid=True,
            expires_at=expires_at,
        )
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)

        return session

    async def invalidate_session(self, jti: str) -> bool:
        """
        使会话失效

        Args:
            jti: JWT ID

        Returns:
            是否成功
        """
        result = await self.session.execute(
            select(UserSession).where(UserSession.jti == jti)
        )
        session = result.scalar_one_or_none()
        if not session:
            return False

        session.is_valid = False
        await self.session.commit()
        return True

    async def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话

        Returns:
            清理的会话数量
        """
        result = await self.session.execute(
            select(UserSession).where(
                UserSession.expires_at < datetime.utcnow()
            )
        )
        sessions = result.scalars().all()

        count = len(sessions)
        for session in sessions:
            await self.session.delete(session)

        await self.session.commit()
        return count

    async def check_quota(self, user_id: int) -> tuple[bool, int, int]:
        """
        检查用户配额

        Args:
            user_id: 用户 ID

        Returns:
            (是否有配额, 当前已使用, 配额上限)
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False, 0, 0

        remaining = user.api_quota - user.api_used
        return remaining > 0, user.api_used, user.api_quota

    async def increment_usage(self, user_id: int, count: int = 1) -> bool:
        """
        增加 API 使用次数

        Args:
            user_id: 用户 ID
            count: 增加的数量

        Returns:
            是否成功
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.api_used += count
        await self.session.commit()
        return True
