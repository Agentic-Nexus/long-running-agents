"""
WebSocket 实时行情 API

提供 WebSocket 连接用于实时股票行情推送。
"""
import asyncio
import json
import time
import uuid
from typing import Dict, Set, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from pydantic import BaseModel, Field
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================
# 连接管理
# ============================================

class ConnectionManager:
    """
    WebSocket 连接管理器

    管理所有活跃的 WebSocket 连接，支持：
    - 多客户端同时连接
    - 按股票代码订阅/取消订阅
    - 心跳保活
    - 广播推送
    """

    def __init__(self):
        # 所有活跃连接: {client_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}

        # 客户端订阅的股票: {client_id: Set[stock_code]}
        self.client_subscriptions: Dict[str, Set[str]] = {}

        # 股票订阅者: {stock_code: Set[client_id]}
        self.stock_subscribers: Dict[str, Set[str]] = {}

        # 客户端心跳: {client_id: last_ping_time}
        self.client_heartbeat: Dict[str, float] = {}

        # 心跳间隔（秒）
        self.heartbeat_interval = 30

        # 清理任务
        self._cleanup_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> str:
        """
        处理新的 WebSocket 连接

        Args:
            websocket: WebSocket 连接
            client_id: 客户端 ID，如果为 None 则自动生成

        Returns:
            客户端 ID
        """
        await websocket.accept()

        # 生成客户端 ID
        if client_id is None:
            client_id = str(uuid.uuid4())

        # 注册连接
        self.active_connections[client_id] = websocket
        self.client_subscriptions[client_id] = set()
        self.client_heartbeat[client_id] = time.time()

        logger.info(f"WebSocket client connected: {client_id}, total: {len(self.active_connections)}")

        # 发送连接成功消息
        await self._send_personal_message({
            "type": "connected",
            "client_id": client_id,
            "message": "WebSocket 连接已建立"
        }, client_id)

        # 启动清理任务（如果尚未启动）
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        return client_id

    async def disconnect(self, client_id: str):
        """
        处理连接断开

        Args:
            client_id: 客户端 ID
        """
        # 从所有股票订阅中移除
        if client_id in self.client_subscriptions:
            for stock_code in self.client_subscriptions[client_id]:
                if stock_code in self.stock_subscribers:
                    self.stock_subscribers[stock_code].discard(client_id)
                    # 如果没有订阅者了，清理空集合
                    if not self.stock_subscribers[stock_code]:
                        del self.stock_subscribers[stock_code]

        # 移除连接
        self.active_connections.pop(client_id, None)
        self.client_subscriptions.pop(client_id, None)
        self.client_heartbeat.pop(client_id, None)

        logger.info(f"WebSocket client disconnected: {client_id}, remaining: {len(self.active_connections)}")

    async def subscribe(self, client_id: str, stock_codes: list[str]):
        """
        订阅股票行情

        Args:
            client_id: 客户端 ID
            stock_codes: 股票代码列表
        """
        if client_id not in self.client_subscriptions:
            self.client_subscriptions[client_id] = set()

        for code in stock_codes:
            # 添加到客户端订阅
            self.client_subscriptions[client_id].add(code)

            # 添加到股票订阅者
            if code not in self.stock_subscribers:
                self.stock_subscribers[code] = set()
            self.stock_subscribers[code].add(client_id)

        logger.info(f"Client {client_id} subscribed to: {stock_codes}")

        # 发送订阅确认
        await self._send_personal_message({
            "type": "subscribed",
            "stocks": stock_codes
        }, client_id)

    async def unsubscribe(self, client_id: str, stock_codes: list[str]):
        """
        取消订阅股票行情

        Args:
            client_id: 客户端 ID
            stock_codes: 股票代码列表
        """
        if client_id not in self.client_subscriptions:
            return

        for code in stock_codes:
            # 从客户端订阅中移除
            self.client_subscriptions[client_id].discard(code)

            # 从股票订阅者中移除
            if code in self.stock_subscribers:
                self.stock_subscribers[code].discard(client_id)
                if not self.stock_subscribers[code]:
                    del self.stock_subscribers[code]

        logger.info(f"Client {client_id} unsubscribed from: {stock_codes}")

        # 发送取消订阅确认
        await self._send_personal_message({
            "type": "unsubscribed",
            "stocks": stock_codes
        }, client_id)

    async def broadcast_to_subscribers(self, stock_code: str, data: dict):
        """
        向订阅某股票的的所有客户端广播数据

        Args:
            stock_code: 股票代码
            data: 要发送的数据
        """
        if stock_code not in self.stock_subscribers:
            return

        subscribers = self.stock_subscribers[stock_code].copy()
        message = {
            "type": "quote",
            "stock_code": stock_code,
            "data": data
        }

        for client_id in subscribers:
            await self._send_personal_message(message, client_id)

    async def broadcast_to_all(self, data: dict):
        """
        向所有客户端广播数据

        Args:
            data: 要发送的数据
        """
        message = {
            "type": "broadcast",
            "data": data
        }

        for client_id in list(self.active_connections.keys()):
            await self._send_personal_message(message, client_id)

    async def _send_personal_message(self, message: dict, client_id: str):
        """
        向指定客户端发送消息

        Args:
            message: 消息内容
            client_id: 客户端 ID
        """
        if client_id not in self.active_connections:
            return

        websocket = self.active_connections[client_id]

        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message to {client_id}: {e}")
            # 连接可能已断开，标记待清理
            await self.disconnect(client_id)

    async def handle_ping(self, client_id: str):
        """
        处理客户端心跳

        Args:
            client_id: 客户端 ID
        """
        self.client_heartbeat[client_id] = time.time()

    async def _cleanup_loop(self):
        """
        定期清理超时连接
        """
        while True:
            await asyncio.sleep(10)
            await self._cleanup_stale_connections()

    async def _cleanup_stale_connections(self):
        """
        清理超时未发送心跳的连接
        """
        current_time = time.time()
        stale_clients = []

        for client_id, last_ping in self.client_heartbeat.items():
            if current_time - last_ping > self.heartbeat_interval * 2:  # 60秒超时
                stale_clients.append(client_id)

        for client_id in stale_clients:
            logger.warning(f"Client {client_id} heartbeat timeout, disconnecting")
            await self.disconnect(client_id)

    def get_stats(self) -> dict:
        """
        获取连接统计信息

        Returns:
            统计信息字典
        """
        return {
            "total_connections": len(self.active_connections),
            "total_subscriptions": sum(len(s) for s in self.client_subscriptions.values()),
            "tracked_stocks": len(self.stock_subscribers),
            "subscribers_per_stock": {
                stock: len(subscribers)
                for stock, subscribers in self.stock_subscribers.items()
            }
        }


# 全局连接管理器
manager = ConnectionManager()


# ============================================
# 请求/响应模型
# ============================================

class SubscribeRequest(BaseModel):
    """订阅请求"""
    stocks: list[str] = Field(..., min_length=1, max_length=50, description="股票代码列表")


class UnsubscribeRequest(BaseModel):
    """取消订阅请求"""
    stocks: list[str] = Field(..., min_length=1, max_length=50, description="股票代码列表")


class WebSocketMessage(BaseModel):
    """WebSocket 消息"""
    type: str
    client_id: Optional[str] = None
    message: Optional[str] = None
    stocks: Optional[list[str]] = None
    data: Optional[dict] = None
    stock_code: Optional[str] = None


# ============================================
# WebSocket 端点
# ============================================

@router.websocket("/ws/quote")
async def websocket_quote(websocket: WebSocket):
    """
    WebSocket 实时行情端点

    支持以下功能：
    - 连接建立后发送订阅消息订阅股票
    - 接收实时股票行情推送
    - 心跳保活（ping/pong）
    - 取消订阅

    客户端消息格式：
    ```json
    {
        "type": "subscribe",
        "stocks": ["600000", "000001"]
    }
    ```

    服务器消息格式：
    ```json
    {
        "type": "quote",
        "stock_code": "600000",
        "data": {
            "code": "600000",
            "name": "浦发银行",
            "price": 10.5,
            "change": 0.1,
            "change_percent": 0.96,
            ...
        }
    }
    ```
    """
    client_id = None

    try:
        # 接受连接
        client_id = await manager.connect(websocket)

        # 消息处理循环
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await manager._send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, client_id)
                continue

            msg_type = message.get("type")

            # 处理订阅请求
            if msg_type == "subscribe":
                stocks = message.get("stocks", [])
                if stocks:
                    await manager.subscribe(client_id, stocks)

            # 处理取消订阅请求
            elif msg_type == "unsubscribe":
                stocks = message.get("stocks", [])
                if stocks:
                    await manager.unsubscribe(client_id, stocks)

            # 处理心跳
            elif msg_type == "ping":
                await manager.handle_ping(client_id)
                await manager._send_personal_message({
                    "type": "pong",
                    "timestamp": time.time()
                }, client_id)

            # 处理获取订阅列表请求
            elif msg_type == "list":
                subscriptions = list(manager.client_subscriptions.get(client_id, set()))
                await manager._send_personal_message({
                    "type": "subscription_list",
                    "stocks": subscriptions
                }, client_id)

            # 处理获取统计信息请求
            elif msg_type == "stats":
                await manager._send_personal_message({
                    "type": "stats",
                    "data": manager.get_stats()
                }, client_id)

            else:
                await manager._send_personal_message({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                }, client_id)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if client_id:
            await manager.disconnect(client_id)


# ============================================
# 辅助端点
# ============================================

@router.get("/ws/status")
async def get_websocket_status():
    """
    获取 WebSocket 连接状态

    返回当前活跃连接数和订阅统计。
    """
    return {
        "websocket": "enabled",
        **manager.get_stats()
    }
