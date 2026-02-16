"""
LLM 服务模块

提供统一的大语言模型接口：
- LLMProvider 抽象类定义统一接口
- Anthropic Claude 提供者实现
- OpenAI GPT 提供者实现
- 对话上下文管理 (ConversationManager)
- API 密钥管理（从环境变量读取）
- 使用 tenacity 实现重试机制
"""

import os
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, AsyncIterator, Union
from enum import Enum
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMProviderType(Enum):
    """LLM 提供者类型枚举"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class Message:
    """对话消息"""
    role: str  # "system", "user", "assistant"
    content: str
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        return result


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    provider: LLMProviderType
    usage: Dict[str, int] = field(default_factory=dict)
    raw_response: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider.value,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
        }


@dataclass
class StreamChunk:
    """流式响应块"""
    content: str
    delta: str
    model: str
    provider: LLMProviderType
    finish_reason: Optional[str] = None


class LLMProvider(ABC):
    """LLM 提供者抽象基类"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "",
        max_retries: int = 3,
        timeout: int = 60,
    ):
        """
        初始化 LLM 提供者

        Args:
            api_key: API 密钥，如果为 None 则从环境变量读取
            model: 模型名称
            max_retries: 最大重试次数
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key or self._get_api_key_from_env()
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout

        if not self.api_key:
            raise ValueError(f"API key is required for {self.__class__.__name__}")

    @abstractmethod
    def _get_api_key_from_env(self) -> Optional[str]:
        """从环境变量获取 API 密钥"""
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        发送对话请求（非流式）

        Args:
            messages: 对话消息列表
            temperature: 温度参数 (0-2)
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数

        Returns:
            LLMResponse: 响应对象
        """
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """
        发送对话请求（流式）

        Args:
            messages: 对话消息列表
            temperature: 温度参数 (0-2)
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数

        Yields:
            StreamChunk: 流式响应块
        """
        pass

    @abstractmethod
    def get_provider_type(self) -> LLMProviderType:
        """获取提供者类型"""
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """列出可用模型"""
        pass

    def _retry_decorator(self, func: Callable) -> Callable:
        """创建重试装饰器"""
        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((Exception,)),
            reraise=True,
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper


class AnthropicProvider(LLMProvider):
    """Anthropic Claude 提供者"""

    DEFAULT_MODELS = [
        "claude-opus-4-5-20251114",
        "claude-sonnet-4-20250514",
        "claude-haiku-3-20240307",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_retries: int = 3,
        timeout: int = 60,
    ):
        """
        初始化 Anthropic 提供者

        Args:
            api_key: Anthropic API 密钥
            model: 模型名称
            max_retries: 最大重试次数
            timeout: 请求超时时间（秒）
        """
        super().__init__(api_key, model, max_retries, timeout)
        self._client = None

    def _get_api_key_from_env(self) -> Optional[str]:
        """从环境变量获取 API 密钥"""
        return os.getenv("ANTHROPIC_API_KEY")

    @property
    def client(self):
        """获取 Anthropic 客户端"""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=self.api_key,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                )
            except ImportError:
                raise ImportError("Please install anthropic package: pip install anthropic")
        return self._client

    def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """发送对话请求（非流式）"""
        if max_tokens is None:
            max_tokens = 4096

        # 转换消息格式
        system_message = ""
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                anthropic_messages.append(msg.to_dict())

        @self._retry_decorator
        def _call_api():
            return self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message if system_message else None,
                messages=anthropic_messages,
                **kwargs
            )

        try:
            response = _call_api()

            return LLMResponse(
                content=response.content[0].text if response.content else "",
                model=response.model,
                provider=LLMProviderType.ANTHROPIC,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
                finish_reason=response.stop_reason,
            )
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise

    async def chat_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """发送对话请求（流式）"""
        if max_tokens is None:
            max_tokens = 4096

        # 转换消息格式
        system_message = ""
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                anthropic_messages.append(msg.to_dict())

        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message if system_message else None,
                messages=anthropic_messages,
                **kwargs
            ) as stream:
                for event in stream:
                    if event.type == "content_block_delta":
                        yield StreamChunk(
                            content=event.delta.text,
                            delta=event.delta.text,
                            model=self.model,
                            provider=LLMProviderType.ANTHROPIC,
                        )
                    elif event.type == "message_stop":
                        yield StreamChunk(
                            content="",
                            delta="",
                            model=self.model,
                            provider=LLMProviderType.ANTHROPIC,
                            finish_reason="stop",
                        )
        except Exception as e:
            logger.error(f"Anthropic streaming API call failed: {e}")
            raise

    def get_provider_type(self) -> LLMProviderType:
        """获取提供者类型"""
        return LLMProviderType.ANTHROPIC

    def list_models(self) -> List[str]:
        """列出可用模型"""
        return self.DEFAULT_MODELS.copy()


class OpenAIProvider(LLMProvider):
    """OpenAI GPT 提供者"""

    DEFAULT_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        max_retries: int = 3,
        timeout: int = 60,
        base_url: Optional[str] = None,
    ):
        """
        初始化 OpenAI 提供者

        Args:
            api_key: OpenAI API 密钥
            model: 模型名称
            max_retries: 最大重试次数
            timeout: 请求超时时间（秒）
            base_url: 自定义 API 端点（用于代理或兼容 API）
        """
        super().__init__(api_key, model, max_retries, timeout)
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self._client = None

    def _get_api_key_from_env(self) -> Optional[str]:
        """从环境变量获取 API 密钥"""
        return os.getenv("OPENAI_API_KEY")

    @property
    def client(self):
        """获取 OpenAI 客户端"""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                )
            except ImportError:
                raise ImportError("Please install openai package: pip install openai")
        return self._client

    def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """发送对话请求（非流式）"""
        # 转换消息格式
        openai_messages = [msg.to_dict() for msg in messages]

        @self._retry_decorator
        def _call_api():
            return self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

        try:
            response = _call_api()

            return LLMResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                provider=LLMProviderType.OPENAI,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
                finish_reason=response.choices[0].finish_reason,
            )
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

    async def chat_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """发送对话请求（流式）"""
        # 转换消息格式
        openai_messages = [msg.to_dict() for msg in messages]

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    delta_content = chunk.choices[0].delta.content
                    yield StreamChunk(
                        content=delta_content,
                        delta=delta_content,
                        model=chunk.model,
                        provider=LLMProviderType.OPENAI,
                        finish_reason=chunk.choices[0].finish_reason,
                    )
        except Exception as e:
            logger.error(f"OpenAI streaming API call failed: {e}")
            raise

    def get_provider_type(self) -> LLMProviderType:
        """获取提供者类型"""
        return LLMProviderType.OPENAI

    def list_models(self) -> List[str]:
        """列出可用模型"""
        return self.DEFAULT_MODELS.copy()


class ConversationManager:
    """对话上下文管理器"""

    def __init__(self, provider: LLMProvider, max_history: int = 10):
        """
        初始化对话管理器

        Args:
            provider: LLM 提供者实例
            max_history: 最大历史消息数量
        """
        self.provider = provider
        self.max_history = max_history
        self.conversations: Dict[str, List[Message]] = {}
        self.system_prompts: Dict[str, str] = {}

    def create_conversation(
        self,
        conversation_id: str,
        system_prompt: Optional[str] = None,
    ) -> None:
        """
        创建新对话

        Args:
            conversation_id: 对话 ID
            system_prompt: 系统提示词
        """
        self.conversations[conversation_id] = []
        if system_prompt:
            self.system_prompts[conversation_id] = system_prompt
        logger.info(f"Created conversation: {conversation_id}")

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        name: Optional[str] = None,
    ) -> None:
        """
        添加消息到对话

        Args:
            conversation_id: 对话 ID
            role: 角色 ("system", "user", "assistant")
            content: 消息内容
            name: 名称（可选）
        """
        if conversation_id not in self.conversations:
            self.create_conversation(conversation_id)

        message = Message(role=role, content=content, name=name)
        self.conversations[conversation_id].append(message)

        # 限制历史消息数量
        if len(self.conversations[conversation_id]) > self.max_history:
            # 保留系统消息
            messages = self.conversations[conversation_id]
            system_msg = None
            if messages and messages[0].role == "system":
                system_msg = messages[0]
                messages = messages[1:]

            # 保留最近的消息
            messages = messages[-self.max_history + 1:]

            if system_msg:
                messages.insert(0, system_msg)

            self.conversations[conversation_id] = messages

    def get_messages(self, conversation_id: str) -> List[Message]:
        """
        获取对话历史消息

        Args:
            conversation_id: 对话 ID

        Returns:
            消息列表
        """
        return self.conversations.get(conversation_id, [])

    def clear_conversation(self, conversation_id: str) -> None:
        """
        清空对话历史

        Args:
            conversation_id: 对话 ID
        """
        if conversation_id in self.conversations:
            system_prompt = self.system_prompts.get(conversation_id)
            self.conversations[conversation_id] = []
            if system_prompt:
                self.add_message(conversation_id, "system", system_prompt)
            logger.info(f"Cleared conversation: {conversation_id}")

    def delete_conversation(self, conversation_id: str) -> None:
        """
        删除对话

        Args:
            conversation_id: 对话 ID
        """
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
        if conversation_id in self.system_prompts:
            del self.system_prompts[conversation_id]
        logger.info(f"Deleted conversation: {conversation_id}")

    def chat(
        self,
        conversation_id: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        发送消息并获取响应

        Args:
            conversation_id: 对话 ID
            user_message: 用户消息
            temperature: 温度参数
            max_tokens: 最大 token 数
            **kwargs: 其他参数

        Returns:
            LLMResponse: 响应对象
        """
        # 添加用户消息
        self.add_message(conversation_id, "user", user_message)

        # 获取完整消息列表
        messages = self.get_messages(conversation_id)

        # 添加系统提示词（如果存在）
        if conversation_id in self.system_prompts:
            # 检查是否已有 system 消息
            has_system = any(m.role == "system" for m in messages)
            if not has_system:
                messages.insert(
                    0,
                    Message(role="system", content=self.system_prompts[conversation_id])
                )

        # 调用 LLM
        response = self.provider.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        # 添加助手响应
        self.add_message(conversation_id, "assistant", response.content)

        return response

    async def chat_stream(
        self,
        conversation_id: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """
        发送消息并获取流式响应

        Args:
            conversation_id: 对话 ID
            user_message: 用户消息
            temperature: 温度参数
            max_tokens: 最大 token 数
            **kwargs: 其他参数

        Yields:
            StreamChunk: 流式响应块
        """
        # 添加用户消息
        self.add_message(conversation_id, "user", user_message)

        # 获取完整消息列表
        messages = self.get_messages(conversation_id)

        # 添加系统提示词（如果存在）
        if conversation_id in self.system_prompts:
            has_system = any(m.role == "system" for m in messages)
            if not has_system:
                messages.insert(
                    0,
                    Message(role="system", content=self.system_prompts[conversation_id])
                )

        # 收集完整响应内容
        full_content = ""

        # 调用 LLM
        async for chunk in self.provider.chat_stream(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        ):
            full_content += chunk.delta
            yield chunk

        # 添加助手响应
        self.add_message(conversation_id, "assistant", full_content)

    def list_conversations(self) -> List[str]:
        """列出所有对话 ID"""
        return list(self.conversations.keys())


# 全局 LLM 提供者实例
_default_provider: Optional[LLMProvider] = None
_default_conversation_manager: Optional[ConversationManager] = None


def get_default_provider(
    provider_type: LLMProviderType = LLMProviderType.OPENAI,
    model: Optional[str] = None,
    **kwargs
) -> LLMProvider:
    """
    获取默认 LLM 提供者

    Args:
        provider_type: 提供者类型
        model: 模型名称
        **kwargs: 其他参数

    Returns:
        LLMProvider: LLM 提供者实例
    """
    global _default_provider

    if _default_provider is None or (
        _default_provider.get_provider_type() != provider_type
    ):
        if provider_type == LLMProviderType.ANTHROPIC:
            _default_provider = AnthropicProvider(model=model or "claude-sonnet-4-20250514", **kwargs)
        elif provider_type == LLMProviderType.OPENAI:
            _default_provider = OpenAIProvider(model=model or "gpt-4o", **kwargs)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    return _default_provider


def get_conversation_manager(
    provider: Optional[LLMProvider] = None,
    max_history: int = 10,
) -> ConversationManager:
    """
    获取对话管理器

    Args:
        provider: LLM 提供者，如果为 None 则使用默认提供者
        max_history: 最大历史消息数量

    Returns:
        ConversationManager: 对话管理器实例
    """
    global _default_conversation_manager, _default_provider

    if provider is None:
        provider = get_default_provider()

    if _default_conversation_manager is None:
        _default_conversation_manager = ConversationManager(
            provider=provider,
            max_history=max_history,
        )

    return _default_conversation_manager


def create_provider(
    provider_type: LLMProviderType,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> LLMProvider:
    """
    创建 LLM 提供者

    Args:
        provider_type: 提供者类型
        api_key: API 密钥
        model: 模型名称
        **kwargs: 其他参数

    Returns:
        LLMProvider: LLM 提供者实例
    """
    if provider_type == LLMProviderType.ANTHROPIC:
        return AnthropicProvider(api_key=api_key, model=model, **kwargs)
    elif provider_type == LLMProviderType.OPENAI:
        return OpenAIProvider(api_key=api_key, model=model, **kwargs)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


def reset_default_provider() -> None:
    """重置默认 LLM 提供者"""
    global _default_provider, _default_conversation_manager
    _default_provider = None
    _default_conversation_manager = None
    logger.info("Reset default LLM provider")
