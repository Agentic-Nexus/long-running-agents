"""
认证服务测试用例

测试用户认证、API 密钥管理和权限验证功能。
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    hash_api_key,
    verify_api_key,
    AuthService,
)


class TestPasswordHashing:
    """测试密码哈希功能"""

    def test_get_password_hash(self):
        """测试密码哈希"""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """测试验证正确密码"""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试验证错误密码"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False


class TestTokenGeneration:
    """测试令牌生成功能"""

    def test_create_access_token(self):
        """测试创建访问令牌"""
        data = {"sub": "123", "username": "testuser"}
        token = create_access_token(data, timedelta(minutes=30))

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        data = {"sub": "123", "username": "testuser"}
        token = create_refresh_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_token(self):
        """测试解码令牌"""
        data = {"sub": "123", "username": "testuser"}
        token = create_access_token(data, timedelta(minutes=30))

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["username"] == "testuser"

    def test_decode_invalid_token(self):
        """测试解码无效令牌"""
        payload = decode_token("invalid_token_string")

        assert payload is None

    def test_decode_expired_token(self):
        """测试解码过期令牌"""
        # 创建一个已经过期的令牌
        from jose import jwt as jose_jwt
        import time
        data = {"sub": "123", "username": "testuser"}
        # 创建一个过去时间的令牌
        expired_time = int(time.time()) - 10  # 10 秒前过期
        token = jose_jwt.encode(
            {**data, "exp": expired_time, "iat": expired_time - 1},
            "dev-secret-key-change-in-production",
            algorithm="HS256"
        )

        payload = decode_token(token)

        assert payload is None


class TestAPIKey:
    """测试 API 密钥功能"""

    def test_generate_api_key(self):
        """测试生成 API 密钥"""
        key, prefix = generate_api_key()

        assert key is not None
        assert key.startswith("sk_")
        assert len(key) > 12
        assert prefix is not None
        assert prefix.endswith("...")

    def test_hash_and_verify_api_key(self):
        """测试哈希和验证 API 密钥"""
        api_key = "sk_" + "a" * 32
        hashed = hash_api_key(api_key)

        assert hashed is not None
        assert hashed != api_key
        assert verify_api_key(api_key, hashed) is True

    def test_verify_invalid_api_key(self):
        """测试验证无效 API 密钥"""
        api_key = "sk_" + "a" * 32
        wrong_key = "sk_" + "b" * 32
        hashed = hash_api_key(api_key)

        assert verify_api_key(wrong_key, hashed) is False


class TestAuthService:
    """测试认证服务"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟数据库会话"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        session.delete = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_register_user(self, mock_session):
        """测试用户注册"""
        # Mock 查询结果为空（用户名和邮箱可用）
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        auth_service = AuthService(mock_session)

        user = await auth_service.register_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            display_name="Test User"
        )

        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_duplicate_username(self, mock_session):
        """测试用户名已存在的注册"""
        # Mock 用户名已存在
        from app.models.user import User
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = User(
            username="testuser",
            email="other@example.com",
            password_hash="hash"
        )
        mock_session.execute.return_value = mock_result

        auth_service = AuthService(mock_session)

        with pytest.raises(ValueError, match="用户名已存在"):
            await auth_service.register_user(
                username="testuser",
                email="test@example.com",
                password="password123"
            )

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, mock_session):
        """测试邮箱已被注册的注册"""
        from app.models.user import User
        # 第一次查询（用户名检查）返回 None
        # 第二次查询（邮箱检查）返回已存在的用户
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = None

        mock_result2 = MagicMock()
        existing_user = User(
            username="other",
            email="test@example.com",
            password_hash="hash"
        )
        mock_result2.scalar_one_or_none.return_value = existing_user

        mock_session.execute.side_effect = [mock_result1, mock_result2]

        auth_service = AuthService(mock_session)

        with pytest.raises(ValueError, match="邮箱已被注册"):
            await auth_service.register_user(
                username="testuser",
                email="test@example.com",
                password="password123"
            )

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, mock_session):
        """测试用户登录成功"""
        from app.models.user import User
        mock_result = MagicMock()
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            password_hash=get_password_hash("password123"),
            is_active=True,
            role="basic"
        )
        user.last_login_at = None
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        auth_service = AuthService(mock_session)

        result = await auth_service.authenticate_user("testuser", "password123")

        assert result is not None
        assert result.username == "testuser"

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, mock_session):
        """测试用户登录密码错误"""
        from app.models.user import User
        mock_result = MagicMock()
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            password_hash=get_password_hash("password123"),
            is_active=True
        )
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        auth_service = AuthService(mock_session)

        result = await auth_service.authenticate_user("testuser", "wrongpassword")

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, mock_session):
        """测试用户未激活"""
        from app.models.user import User
        mock_result = MagicMock()
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            password_hash=get_password_hash("password123"),
            is_active=False
        )
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        auth_service = AuthService(mock_session)

        result = await auth_service.authenticate_user("testuser", "password123")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, mock_session):
        """测试根据 ID 获取用户"""
        from app.models.user import User
        mock_result = MagicMock()
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            password_hash="hash",
            is_active=True
        )
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        auth_service = AuthService(mock_session)

        result = await auth_service.get_user_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, mock_session):
        """测试用户不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        auth_service = AuthService(mock_session)

        result = await auth_service.get_user_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_api_key(self, mock_session):
        """测试创建 API 密钥"""
        from app.models.user import User, APIKey

        # 先查询用户
        mock_result_user = MagicMock()
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            password_hash="hash",
            is_active=True
        )
        mock_result_user.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result_user

        auth_service = AuthService(mock_session)

        api_key_record, api_key = await auth_service.create_api_key(
            user_id=1,
            name="Test Key",
            expires_days=30
        )

        assert api_key is not None
        assert api_key.startswith("sk_")
        assert api_key_record.name == "Test Key"
        mock_session.add.assert_called()
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_list_api_keys(self, mock_session):
        """测试列出 API 密钥"""
        from app.models.user import APIKey

        mock_result = MagicMock()
        keys = [
            APIKey(id=1, user_id=1, name="Key 1", key_hash="hash1", key_prefix="sk_abc...", is_active=True),
            APIKey(id=2, user_id=1, name="Key 2", key_hash="hash2", key_prefix="sk_def...", is_active=True),
        ]
        mock_result.scalars.return_value.all.return_value = keys
        mock_session.execute.return_value = mock_result

        auth_service = AuthService(mock_session)

        result = await auth_service.list_api_keys(1)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_delete_api_key(self, mock_session):
        """测试删除 API 密钥"""
        from app.models.user import APIKey

        mock_result = MagicMock()
        key = APIKey(id=1, user_id=1, name="Key 1", key_hash="hash", key_prefix="sk_abc...")
        mock_result.scalar_one_or_none.return_value = key
        mock_session.execute.return_value = mock_result

        auth_service = AuthService(mock_session)

        result = await auth_service.delete_api_key(1, 1)

        assert result is True
        mock_session.delete.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_api_key_not_found(self, mock_session):
        """测试删除不存在的 API 密钥"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        auth_service = AuthService(mock_session)

        result = await auth_service.delete_api_key(1, 999)

        assert result is False


class TestUserModel:
    """测试用户模型"""

    def test_user_model_creation(self):
        """测试用户模型创建"""
        from app.models.user import User, UserRole

        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            display_name="Test User",
            role=UserRole.BASIC.value,
            is_active=True,
            api_quota=1000,
            api_used=0,
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == UserRole.BASIC.value
        assert user.is_active is True

    def test_user_role_enum(self):
        """测试用户角色枚举"""
        from app.models.user import UserRole

        assert UserRole.ADMIN.value == "admin"
        assert UserRole.PREMIUM.value == "premium"
        assert UserRole.BASIC.value == "basic"
        assert UserRole.GUEST.value == "guest"

    def test_api_key_model_creation(self):
        """测试 API 密钥模型创建"""
        from app.models.user import APIKey

        api_key = APIKey(
            user_id=1,
            name="Test API Key",
            key_hash="hashed_key",
            key_prefix="sk_test...",
            is_active=True,
        )

        assert api_key.user_id == 1
        assert api_key.name == "Test API Key"
        assert api_key.is_active is True

    def test_user_session_model_creation(self):
        """测试用户会话模型创建"""
        from app.models.user import UserSession

        session = UserSession(
            user_id=1,
            jti="test_jti_123",
            device_info="Chrome/120.0",
            ip_address="127.0.0.1",
            is_valid=True,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )

        assert session.user_id == 1
        assert session.jti == "test_jti_123"
        assert session.is_valid is True
