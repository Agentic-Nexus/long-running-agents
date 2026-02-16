"""
LLM 服务模块测试

测试大语言模型集成功能：
- Message 数据类
- LLMResponse 数据类
- LLMProvider 抽象基类
- AnthropicProvider 提供者
- OpenAIProvider 提供者
- ConversationManager 对话管理器
- 工厂函数和单例
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import List

from app.services.llm_service import (
    Message,
    LLMResponse,
    StreamChunk,
    LLMProvider,
    LLMProviderType,
    AnthropicProvider,
    OpenAIProvider,
    ConversationManager,
    create_provider,
    get_default_provider,
    get_conversation_manager,
    reset_default_provider,
)


class TestMessage:
    """Message 数据类测试"""

    def test_message_creation(self):
        """测试消息创建"""
        msg = Message(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None

    def test_message_with_name(self):
        """测试带名称的消息"""
        msg = Message(role="user", content="Hello", name="test_user")

        assert msg.name == "test_user"

    def test_message_to_dict(self):
        """测试消息转换为字典"""
        msg = Message(role="user", content="Hello", name="test_user")

        result = msg.to_dict()

        assert result["role"] == "user"
        assert result["content"] == "Hello"
        assert result["name"] == "test_user"

    def test_message_to_dict_without_name(self):
        """测试不带名称的消息转换为字典"""
        msg = Message(role="user", content="Hello")

        result = msg.to_dict()

        assert "name" not in result


class TestLLMResponse:
    """LLMResponse 数据类测试"""

    def test_llm_response_creation(self):
        """测试响应创建"""
        response = LLMResponse(
            content="Test response",
            model="gpt-4",
            provider=LLMProviderType.OPENAI,
            usage={"prompt_tokens": 10, "completion_tokens": 20}
        )

        assert response.content == "Test response"
        assert response.model == "gpt-4"
        assert response.provider == LLMProviderType.OPENAI
        assert response.usage["prompt_tokens"] == 10

    def test_llm_response_to_dict(self):
        """测试响应转换为字典"""
        response = LLMResponse(
            content="Test response",
            model="gpt-4",
            provider=LLMProviderType.OPENAI,
            finish_reason="stop"
        )

        result = response.to_dict()

        assert result["content"] == "Test response"
        assert result["model"] == "gpt-4"
        assert result["provider"] == "openai"
        assert result["finish_reason"] == "stop"


class TestStreamChunk:
    """StreamChunk 数据类测试"""

    def test_stream_chunk_creation(self):
        """测试流式响应块创建"""
        chunk = StreamChunk(
            content="Hello",
            delta="Hello",
            model="gpt-4",
            provider=LLMProviderType.OPENAI,
            finish_reason="stop"
        )

        assert chunk.content == "Hello"
        assert chunk.delta == "Hello"
        assert chunk.model == "gpt-4"
        assert chunk.finish_reason == "stop"


class TestAnthropicProvider:
    """Anthropic 提供者测试"""

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    def test_anthropic_provider_init(self):
        """测试 Anthropic 提供者初始化"""
        provider = AnthropicProvider(model="claude-sonnet-4-20250514")

        assert provider.api_key == "test-api-key"
        assert provider.model == "claude-sonnet-4-20250514"
        assert provider.max_retries == 3

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    def test_anthropic_provider_init_with_custom_key(self):
        """测试使用自定义 API 密钥初始化"""
        provider = AnthropicProvider(api_key="custom-key")

        assert provider.api_key == "custom-key"

    @patch.dict("os.environ", {})
    def test_anthropic_provider_no_api_key(self):
        """测试无 API 密钥时抛出异常"""
        with pytest.raises(ValueError):
            AnthropicProvider()

    def test_anthropic_get_provider_type(self):
        """测试获取提供者类型"""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"}):
            provider = AnthropicProvider()

            assert provider.get_provider_type() == LLMProviderType.ANTHROPIC

    def test_anthropic_list_models(self):
        """测试列出可用模型"""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"}):
            provider = AnthropicProvider()
            models = provider.list_models()

            assert isinstance(models, list)
            assert len(models) > 0
            assert "claude-sonnet-4-20250514" in models


class TestOpenAIProvider:
    """OpenAI 提供者测试"""

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"})
    def test_openai_provider_init(self):
        """测试 OpenAI 提供者初始化"""
        provider = OpenAIProvider(model="gpt-4o")

        assert provider.api_key == "test-api-key"
        assert provider.model == "gpt-4o"
        assert provider.max_retries == 3

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"})
    def test_openai_provider_init_with_custom_key(self):
        """测试使用自定义 API 密钥初始化"""
        provider = OpenAIProvider(api_key="custom-key")

        assert provider.api_key == "custom-key"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key", "OPENAI_BASE_URL": "https://custom.endpoint.com/v1"})
    def test_openai_provider_custom_base_url(self):
        """测试自定义 API 端点"""
        provider = OpenAIProvider()

        assert provider.base_url == "https://custom.endpoint.com/v1"

    @patch.dict("os.environ", {})
    def test_openai_provider_no_api_key(self):
        """测试无 API 密钥时抛出异常"""
        with pytest.raises(ValueError):
            OpenAIProvider()

    def test_openai_get_provider_type(self):
        """测试获取提供者类型"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            provider = OpenAIProvider()

            assert provider.get_provider_type() == LLMProviderType.OPENAI

    def test_openai_list_models(self):
        """测试列出可用模型"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            provider = OpenAIProvider()
            models = provider.list_models()

            assert isinstance(models, list)
            assert len(models) > 0
            assert "gpt-4o" in models


class TestConversationManager:
    """对话管理器测试"""

    def test_conversation_manager_init(self):
        """测试对话管理器初始化"""
        mock_provider = Mock()
        manager = ConversationManager(mock_provider, max_history=5)

        assert manager.provider == mock_provider
        assert manager.max_history == 5
        assert manager.conversations == {}

    def test_create_conversation(self):
        """测试创建对话"""
        mock_provider = Mock()
        manager = ConversationManager(mock_provider)

        manager.create_conversation("test-id", system_prompt="You are a helpful assistant")

        assert "test-id" in manager.conversations
        assert manager.system_prompts["test-id"] == "You are a helpful assistant"

    def test_add_message(self):
        """测试添加消息"""
        mock_provider = Mock()
        manager = ConversationManager(mock_provider)

        manager.add_message("test-id", "user", "Hello")

        messages = manager.get_messages("test-id")
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"

    def test_add_message_auto_create_conversation(self):
        """测试添加消息时自动创建对话"""
        mock_provider = Mock()
        manager = ConversationManager(mock_provider)

        manager.add_message("test-id", "user", "Hello")

        assert "test-id" in manager.conversations

    def test_get_messages_empty(self):
        """测试获取不存在的对话消息"""
        mock_provider = Mock()
        manager = ConversationManager(mock_provider)

        messages = manager.get_messages("non-existent")

        assert messages == []

    def test_clear_conversation(self):
        """测试清空对话"""
        mock_provider = Mock()
        manager = ConversationManager(mock_provider)

        manager.create_conversation("test-id", system_prompt="Test")
        manager.add_message("test-id", "user", "Hello")
        manager.add_message("test-id", "assistant", "Hi there")

        manager.clear_conversation("test-id")

        messages = manager.get_messages("test-id")
        # 系统提示被重新添加
        assert len(messages) >= 1

    def test_delete_conversation(self):
        """测试删除对话"""
        mock_provider = Mock()
        manager = ConversationManager(mock_provider)

        manager.create_conversation("test-id", system_prompt="Test")
        manager.add_message("test-id", "user", "Hello")

        manager.delete_conversation("test-id")

        assert "test-id" not in manager.conversations
        assert "test-id" not in manager.system_prompts

    def test_max_history_limit(self):
        """测试历史消息数量限制"""
        mock_provider = Mock()
        manager = ConversationManager(mock_provider, max_history=3)

        manager.create_conversation("test-id")
        for i in range(5):
            manager.add_message("test-id", "user", f"Message {i}")

        messages = manager.get_messages("test-id")
        # 最多保留 max_history 条消息
        assert len(messages) <= manager.max_history

    def test_list_conversations(self):
        """测试列出所有对话"""
        mock_provider = Mock()
        manager = ConversationManager(mock_provider)

        manager.create_conversation("id1")
        manager.create_conversation("id2")

        conversations = manager.list_conversations()

        assert len(conversations) == 2
        assert "id1" in conversations
        assert "id2" in conversations


class TestConversationManagerWithMockProvider:
    """使用模拟提供者的对话管理器测试"""

    @pytest.mark.asyncio
    async def test_chat_with_mock_provider(self):
        """测试使用模拟提供者进行对话"""
        mock_provider = Mock()
        mock_response = LLMResponse(
            content="Hello, I am Claude",
            model="claude-sonnet-4-20250514",
            provider=LLMProviderType.ANTHROPIC,
            usage={"input_tokens": 10, "output_tokens": 20}
        )
        mock_provider.chat.return_value = mock_response

        manager = ConversationManager(mock_provider)
        manager.create_conversation("test-id")

        response = manager.chat("test-id", "Hi")

        assert response.content == "Hello, I am Claude"
        mock_provider.chat.assert_called_once()

        # 验证消息被添加
        messages = manager.get_messages("test-id")
        assert len(messages) == 2  # user message + assistant response


class TestProviderFactory:
    """提供者工厂函数测试"""

    def test_create_anthropic_provider(self):
        """测试创建 Anthropic 提供者"""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            provider = create_provider(
                LLMProviderType.ANTHROPIC,
                model="claude-haiku-3-20240307"
            )

            assert isinstance(provider, AnthropicProvider)
            assert provider.model == "claude-haiku-3-20240307"

    def test_create_openai_provider(self):
        """测试创建 OpenAI 提供者"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            provider = create_provider(
                LLMProviderType.OPENAI,
                model="gpt-4o-mini"
            )

            assert isinstance(provider, OpenAIProvider)
            assert provider.model == "gpt-4o-mini"

    def test_get_default_provider_creates_new(self):
        """测试获取默认提供者（新建）"""
        reset_default_provider()

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            provider = get_default_provider(LLMProviderType.OPENAI)

            assert isinstance(provider, OpenAIProvider)

    def test_get_default_provider_reuses_existing(self):
        """测试获取默认提供者（重用已有）"""
        reset_default_provider()

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            provider1 = get_default_provider(LLMProviderType.OPENAI)
            provider2 = get_default_provider(LLMProviderType.OPENAI)

            assert provider1 is provider2

    def test_get_default_provider_different_type(self):
        """测试不同类型的提供者会创建新实例"""
        reset_default_provider()

        with patch.dict("os.environ", {
            "OPENAI_API_KEY": "test-key",
            "ANTHROPIC_API_KEY": "test-key"
        }):
            openai_provider = get_default_provider(LLMProviderType.OPENAI)
            anthropic_provider = get_default_provider(LLMProviderType.ANTHROPIC)

            assert openai_provider is not anthropic_provider

    def test_get_conversation_manager(self):
        """测试获取对话管理器"""
        reset_default_provider()

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            manager1 = get_conversation_manager(max_history=5)
            manager2 = get_conversation_manager()

            # 应该返回同一个实例
            assert manager1 is manager2
            assert manager1.max_history == 5


class TestLLMProviderType:
    """LLMProviderType 枚举测试"""

    def test_provider_type_values(self):
        """测试提供者类型枚举值"""
        assert LLMProviderType.ANTHROPIC.value == "anthropic"
        assert LLMProviderType.OPENAI.value == "openai"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
