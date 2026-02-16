"""
智能问答 API 测试

测试智能问答功能的各个端点：
- POST /api/v1/chat - 非流式对话
- POST /api/v1/chat/stream - 流式对话
- GET /api/v1/chat/history/{conversation_id} - 获取对话历史
- DELETE /api/v1/chat/history/{conversation_id} - 清空对话历史
- GET /api/v1/chat/conversations - 列出所有对话
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

# 在导入 app 之前设置测试环境变量
import os
os.environ["OPENAI_API_KEY"] = "test-api-key"


# 模拟 LLM 提供者
class MockLLMProvider:
    """模拟 LLM 提供者"""

    def __init__(self):
        self.provider_type = "openai"
        self.model = "gpt-4o-mini"

    def chat(self, messages, temperature=0.7, max_tokens=None, **kwargs):
        """模拟非流式对话"""
        return Mock(
            content="这是测试回复：股票代码 000001 是平安银行，属于金融行业。",
            model=self.model,
            provider=Mock(value="openai"),
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )

    async def chat_stream(self, messages, temperature=0.7, max_tokens=None, **kwargs):
        """模拟流式对话"""
        response_text = "这是测试回复：股票代码 000001 是平安银行。"
        for char in response_text:
            yield Mock(
                content=char,
                delta=char,
                model=self.model,
                provider=Mock(value="openai"),
                finish_reason=None,
            )
        yield Mock(
            content="",
            delta="",
            model=self.model,
            provider=Mock(value="openai"),
            finish_reason="stop",
        )

    def get_provider_type(self):
        return Mock(value="openai")

    def list_models(self):
        return ["gpt-4o-mini", "gpt-4o"]


# 模拟股票服务
class MockStockService:
    """模拟股票服务"""

    def get_stock_info(self, symbol):
        """模拟获取股票信息"""
        return {
            "code": symbol,
            "name": "平安银行",
            "market": "深圳证券交易所",
            "industry": "银行",
            "total_shares": "1940591",
            "circulating_shares": "1940591",
        }

    def get_stock_quote(self, symbol):
        """模拟获取股票行情"""
        return {
            "code": symbol,
            "name": "平安银行",
            "price": 12.50,
            "change": 0.15,
            "change_percent": 1.22,
            "volume": 50000000,
            "amount": 625000000,
            "timestamp": "2024-01-15 10:30:00",
        }


# 重置模块状态
def reset_modules():
    """重置所有模块的全局状态"""
    import app.services.llm_service as llm_module
    if hasattr(llm_module, '_default_provider'):
        llm_module._default_provider = None
    if hasattr(llm_module, '_default_conversation_manager'):
        llm_module._default_conversation_manager = None


@pytest.fixture(autouse=True)
def setup_mocks():
    """设置 mock"""
    reset_modules()

    # Mock LLM 提供者
    with patch('app.services.llm_service.get_default_provider') as mock_provider:
        mock_provider.return_value = MockLLMProvider()

        # Mock 股票服务
        with patch('app.api.chat.get_stock_service') as mock_stock:
            mock_stock.return_value = MockStockService()

            yield {
                "provider": mock_provider,
                "stock": mock_stock,
            }


@pytest.fixture
def client():
    """创建测试客户端"""
    from main import app
    return TestClient(app)


class TestChatAPI:
    """智能问答 API 测试"""

    def test_chat_endpoint(self, client):
        """测试非流式对话接口"""
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "请介绍一下股票 000001",
                "stream": False,
                "enable_stock_info": True,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "message" in data
        assert "timestamp" in data

    def test_chat_with_conversation_id(self, client):
        """测试指定对话ID的对话"""
        conversation_id = "test-conversation-123"

        response = client.post(
            "/api/v1/chat",
            json={
                "message": "请介绍一下股票 000001",
                "conversation_id": conversation_id,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conversation_id

    def test_chat_with_custom_system_prompt(self, client):
        """测试自定义系统提示词"""
        custom_prompt = "你是一个专业的金融分析师。"

        response = client.post(
            "/api/v1/chat",
            json={
                "message": "你好",
                "system_prompt": custom_prompt,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data

    def test_chat_with_temperature(self, client):
        """测试自定义温度参数"""
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "你好",
                "temperature": 0.5,
            }
        )

        assert response.status_code == 200

    def test_chat_with_max_tokens(self, client):
        """测试自定义最大token数"""
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "你好",
                "max_tokens": 100,
            }
        )

        assert response.status_code == 200

    def test_chat_stream_endpoint(self, client):
        """测试流式对话接口"""
        # 测试流式端点 /chat/stream
        with client.stream(
            "POST",
            "/api/v1/chat/stream",
            json={
                "message": "请介绍一下股票 000001",
            },
        ) as response:
            assert response.status_code == 200

    def test_get_chat_history(self, client):
        """测试获取对话历史"""
        # 先创建对话
        conversation_id = "test-history-123"

        # 发送消息
        client.post(
            "/api/v1/chat",
            json={
                "message": "你好",
                "conversation_id": conversation_id,
            }
        )

        # 获取历史
        response = client.get(f"/api/v1/chat/history/{conversation_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conversation_id
        assert "messages" in data

    def test_clear_chat_history(self, client):
        """测试清空对话历史"""
        conversation_id = "test-clear-123"

        # 先创建对话
        client.post(
            "/api/v1/chat",
            json={
                "message": "你好",
                "conversation_id": conversation_id,
            }
        )

        # 清空历史
        response = client.delete(f"/api/v1/chat/history/{conversation_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"

    def test_list_conversations(self, client):
        """测试列出所有对话"""
        # 创建几个对话
        for i in range(3):
            client.post(
                "/api/v1/chat",
                json={
                    "message": f"你好 {i}",
                    "conversation_id": f"conv-{i}",
                }
            )

        response = client.get("/api/v1/chat/conversations")

        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert "total" in data

    def test_chat_missing_message(self, client):
        """测试缺少消息内容"""
        response = client.post(
            "/api/v1/chat",
            json={}
        )

        assert response.status_code == 422  # Validation error

    def test_chat_invalid_temperature(self, client):
        """测试无效的温度参数"""
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "你好",
                "temperature": 3.0,  # 超过最大值 2
            }
        )

        assert response.status_code == 422  # Validation error


class TestChatRequest:
    """聊天请求模型测试"""

    def test_valid_request(self):
        """测试有效请求"""
        from app.api.chat import ChatRequest

        request = ChatRequest(
            message="你好",
            conversation_id="test-123",
            stream=False,
        )

        assert request.message == "你好"
        assert request.conversation_id == "test-123"
        assert request.stream is False
        assert request.temperature == 0.7  # 默认值

    def test_default_values(self):
        """测试默认值"""
        from app.api.chat import ChatRequest

        request = ChatRequest(message="你好")

        assert request.stream is False
        assert request.temperature == 0.7
        assert request.enable_stock_info is True


class TestChatResponse:
    """聊天响应模型测试"""

    def test_valid_response(self):
        """测试有效响应"""
        from app.api.chat import ChatResponse

        response = ChatResponse(
            conversation_id="test-123",
            message="你好，我是AI助手",
            timestamp="2024-01-15T10:30:00",
        )

        assert response.conversation_id == "test-123"
        assert response.message == "你好，我是AI助手"
        assert response.timestamp == "2024-01-15T10:30:00"
