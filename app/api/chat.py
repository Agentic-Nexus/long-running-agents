"""
智能问答 API

提供基于 LLM 的智能对话功能：
- 对话接口 /chat (POST)
- 流式响应支持
- 上下文管理
- 会话历史存储
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.services.llm_service import (
    get_conversation_manager,
    get_default_provider,
    LLMProviderType,
    Message,
)
from app.services.stock_service import get_stock_service, StockService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============ 请求/响应模型 ============

class ChatMessage(BaseModel):
    """单条聊天消息"""
    role: str = Field(..., description="消息角色: system, user, assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    conversation_id: Optional[str] = Field(None, description="对话ID，为空则创建新对话")
    stream: bool = Field(False, description="是否启用流式响应")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    temperature: float = Field(0.7, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(None, ge=1, description="最大生成token数")
    enable_stock_info: bool = Field(True, description="是否启用股票信息查询")


class ChatResponse(BaseModel):
    """聊天响应"""
    conversation_id: str = Field(..., description="对话ID")
    message: str = Field(..., description="AI 回复内容")
    timestamp: str = Field(..., description="响应时间戳")


class StreamChunkResponse(BaseModel):
    """流式响应块"""
    content: str = Field(..., description="增量内容")
    done: bool = Field(..., description="是否完成")


# ============ 系统提示词 ============

DEFAULT_SYSTEM_PROMPT = """你是一个智能股票助手，可以帮助用户：
1. 查询股票行情和基本信息
2. 分析股票K线数据
3. 解答股票相关问题

请用简洁、专业的中文回答用户问题。如果需要股票数据，请使用提供的工具查询。"""

STOCK_ASSISTANT_PROMPT = """你是一个专业的股票投资助手。你可以根据用户问题查询股票数据，并给出分析建议。

当用户询问具体股票时，你需要：
1. 先获取股票相关信息（行情、基本面等）
2. 根据数据分析股票情况
3. 给出投资建议（仅供参考，不构成投资建议）

请用简洁、专业、易懂的中文回答。"""


# ============ 对话管理 ============

class ChatManager:
    """聊天管理器"""

    def __init__(self):
        self.conversation_manager = get_conversation_manager(max_history=20)
        self.stock_service: Optional[StockService] = None

    def get_stock_service(self) -> StockService:
        """获取股票服务"""
        if self.stock_service is None:
            self.stock_service = get_stock_service()
        return self.stock_service

    async def build_context(self, message: str, enable_stock_info: bool) -> str:
        """构建上下文信息"""
        context_parts = []

        # 尝试提取股票代码
        import re
        stock_codes = re.findall(r'\b\d{6}\b', message)

        if enable_stock_info and stock_codes:
            try:
                stock_svc = self.get_stock_service()
                for code in stock_codes[:3]:  # 最多查询3只股票
                    try:
                        # 获取股票基本信息
                        info = stock_svc.get_stock_info(code)
                        if info:
                            context_parts.append(f"股票 {info.get('name', code)} ({code}):")
                            context_parts.append(f"  市场: {info.get('market', 'N/A')}")
                            context_parts.append(f"  行业: {info.get('industry', 'N/A')}")
                            context_parts.append(f"  总股本: {info.get('total_shares', 'N/A')} 万股")

                        # 获取实时行情
                        quote = stock_svc.get_stock_quote(code)
                        if quote:
                            context_parts.append(f"  最新价: {quote.get('price', 'N/A')} 元")
                            context_parts.append(f"  涨跌幅: {quote.get('change_percent', 'N/A')}%")
                            context_parts.append(f"  成交量: {quote.get('volume', 'N/A')}")
                            context_parts.append(f"  成交额: {quote.get('amount', 'N/A')} 元")

                        context_parts.append("")
                    except Exception as e:
                        logger.warning(f"获取股票 {code} 信息失败: {e}")

            except Exception as e:
                logger.warning(f"构建股票上下文失败: {e}")

        return "\n".join(context_parts) if context_parts else ""


# 全局聊天管理器
_chat_manager: Optional[ChatManager] = None


def get_chat_manager() -> ChatManager:
    """获取聊天管理器"""
    global _chat_manager
    if _chat_manager is None:
        _chat_manager = ChatManager()
    return _chat_manager


# ============ API 端点 ============

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    智能问答接口（非流式）

    Args:
        request: 聊天请求

    Returns:
        聊天响应
    """
    try:
        chat_mgr = get_chat_manager()

        # 创建或获取对话ID
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # 如果是新对话，设置系统提示
        if request.system_prompt:
            system_prompt = request.system_prompt
        else:
            system_prompt = STOCK_ASSISTANT_PROMPT

        # 构建增强的上下文消息
        enhanced_message = request.message

        if request.enable_stock_info:
            context = await chat_mgr.build_context(request.message, request.enable_stock_info)
            if context:
                enhanced_message = f"""用户问题: {request.message}

相关股票数据:
{context}

请根据以上数据回答用户问题。"""

        # 获取对话管理器
        conv_mgr = chat_mgr.conversation_manager

        # 创建对话（如果不存在）
        if conversation_id not in conv_mgr.conversations:
            conv_mgr.create_conversation(conversation_id, system_prompt)

        # 发送消息并获取响应
        response = conv_mgr.chat(
            conversation_id=conversation_id,
            user_message=enhanced_message,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        logger.info(f"Chat request processed: conversation_id={conversation_id}")

        return ChatResponse(
            conversation_id=conversation_id,
            message=response.content,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Chat request failed: {e}")
        raise HTTPException(status_code=500, detail=f"处理请求失败: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    智能问答接口（流式响应）

    使用 Server-Sent Events (SSE) 进行流式输出

    Args:
        request: 聊天请求

    Returns:
        流式响应
    """
    try:
        chat_mgr = get_chat_manager()

        # 创建或获取对话ID
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # 系统提示
        if request.system_prompt:
            system_prompt = request.system_prompt
        else:
            system_prompt = STOCK_ASSISTANT_PROMPT

        # 构建增强的上下文消息
        enhanced_message = request.message

        if request.enable_stock_info:
            context = await chat_mgr.build_context(request.message, request.enable_stock_info)
            if context:
                enhanced_message = f"""用户问题: {request.message}

相关股票数据:
{context}

请根据以上数据回答用户问题。"""

        # 获取对话管理器
        conv_mgr = chat_mgr.conversation_manager

        # 创建对话（如果不存在）
        if conversation_id not in conv_mgr.conversations:
            conv_mgr.create_conversation(conversation_id, system_prompt)

        # 构建消息列表
        messages = conv_mgr.get_messages(conversation_id)
        if conversation_id in conv_mgr.system_prompts:
            has_system = any(m.role == "system" for m in messages)
            if not has_system:
                messages.insert(
                    0,
                    Message(role="system", content=conv_mgr.system_prompts[conversation_id])
                )

        # 添加用户消息
        messages.append(Message(role="user", content=enhanced_message))

        # 流式生成响应
        async def generate():
            full_content = ""
            provider = get_default_provider()

            try:
                async for chunk in provider.chat_stream(
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                ):
                    if chunk.delta:
                        full_content += chunk.delta
                        # 发送 SSE 格式的数据
                        yield f"data: {chunk.delta}\n\n"

                # 添加助手响应到历史
                conv_mgr.add_message(conversation_id, "assistant", full_content)

                # 发送完成信号
                yield f"data: [DONE]\n\n"

                logger.info(f"Stream chat completed: conversation_id={conversation_id}")

            except Exception as e:
                logger.error(f"Stream chat error: {e}")
                yield f"data: [ERROR] {str(e)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error(f"Chat stream request failed: {e}")
        raise HTTPException(status_code=500, detail=f"处理请求失败: {str(e)}")


@router.get("/chat/history/{conversation_id}")
async def get_chat_history(conversation_id: str) -> Dict[str, Any]:
    """
    获取对话历史

    Args:
        conversation_id: 对话ID

    Returns:
        对话历史
    """
    try:
        chat_mgr = get_chat_manager()
        conv_mgr = chat_mgr.conversation_manager

        messages = conv_mgr.get_messages(conversation_id)

        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "name": msg.name,
                }
                for msg in messages
            ],
            "message_count": len(messages),
        }

    except Exception as e:
        logger.error(f"Get chat history failed: {e}")
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.delete("/chat/history/{conversation_id}")
async def clear_chat_history(conversation_id: str) -> Dict[str, Any]:
    """
    清空对话历史

    Args:
        conversation_id: 对话ID

    Returns:
        操作结果
    """
    try:
        chat_mgr = get_chat_manager()
        conv_mgr = chat_mgr.conversation_manager

        conv_mgr.clear_conversation(conversation_id)

        return {
            "conversation_id": conversation_id,
            "status": "cleared",
            "message": "对话历史已清空",
        }

    except Exception as e:
        logger.error(f"Clear chat history failed: {e}")
        raise HTTPException(status_code=500, detail=f"清空历史失败: {str(e)}")


@router.get("/chat/conversations")
async def list_conversations() -> Dict[str, Any]:
    """
    列出所有对话

    Returns:
        对话列表
    """
    try:
        chat_mgr = get_chat_manager()
        conv_mgr = chat_mgr.conversation_manager

        conversations = conv_mgr.list_conversations()

        return {
            "conversations": conversations,
            "total": len(conversations),
        }

    except Exception as e:
        logger.error(f"List conversations failed: {e}")
        raise HTTPException(status_code=500, detail=f"列出对话失败: {str(e)}")
