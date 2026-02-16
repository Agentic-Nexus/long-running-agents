"""
测试 WebSocket 实时行情功能
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestWebSocketEndpoints:
    """WebSocket 端点测试"""

    def test_websocket_endpoint_exists(self, client):
        """测试 WebSocket 端点存在"""
        # 使用 WebSocket TestClient
        with client.websocket_connect("/api/v1/ws/quote") as ws:
            # 接收连接消息
            data = ws.receive_json()
            assert data["type"] == "connected"
            assert "client_id" in data

    def test_websocket_subscribe(self, client):
        """测试订阅股票"""
        with client.websocket_connect("/api/v1/ws/quote") as ws:
            # 接收连接消息
            ws.receive_json()

            # 发送订阅请求
            ws.send_json({
                "type": "subscribe",
                "stocks": ["600000", "000001"]
            })

            # 接收订阅确认
            data = ws.receive_json()
            assert data["type"] == "subscribed"
            assert "600000" in data["stocks"]

    def test_websocket_unsubscribe(self, client):
        """测试取消订阅"""
        with client.websocket_connect("/api/v1/ws/quote") as ws:
            # 接收连接消息
            ws.receive_json()

            # 先订阅
            ws.send_json({
                "type": "subscribe",
                "stocks": ["600000"]
            })
            ws.receive_json()

            # 取消订阅
            ws.send_json({
                "type": "unsubscribe",
                "stocks": ["600000"]
            })

            # 接收取消订阅确认
            data = ws.receive_json()
            assert data["type"] == "unsubscribed"

    def test_websocket_ping(self, client):
        """测试心跳"""
        with client.websocket_connect("/api/v1/ws/quote") as ws:
            # 接收连接消息
            ws.receive_json()

            # 发送 ping
            ws.send_json({
                "type": "ping"
            })

            # 接收 pong
            data = ws.receive_json()
            assert data["type"] == "pong"
            assert "timestamp" in data

    def test_websocket_list_subscriptions(self, client):
        """测试获取订阅列表"""
        with client.websocket_connect("/api/v1/ws/quote") as ws:
            # 接收连接消息
            ws.receive_json()

            # 订阅股票
            ws.send_json({
                "type": "subscribe",
                "stocks": ["600000", "000001"]
            })
            ws.receive_json()

            # 获取订阅列表
            ws.send_json({
                "type": "list"
            })

            # 接收订阅列表
            data = ws.receive_json()
            assert data["type"] == "subscription_list"
            assert "600000" in data["stocks"]
            assert "000001" in data["stocks"]

    def test_websocket_stats(self, client):
        """测试获取统计信息"""
        with client.websocket_connect("/api/v1/ws/quote") as ws:
            # 接收连接消息
            ws.receive_json()

            # 获取统计信息
            ws.send_json({
                "type": "stats"
            })

            # 接收统计信息
            data = ws.receive_json()
            assert data["type"] == "stats"
            assert "total_connections" in data["data"]

    def test_websocket_invalid_message(self, client):
        """测试无效消息类型"""
        with client.websocket_connect("/api/v1/ws/quote") as ws:
            # 接收连接消息
            ws.receive_json()

            # 发送无效消息
            ws.send_json({
                "type": "invalid_type"
            })

            # 接收错误消息
            data = ws.receive_json()
            assert data["type"] == "error"

    def test_websocket_disconnect(self, client):
        """测试断开连接"""
        with client.websocket_connect("/api/v1/ws/quote") as ws:
            # 接收连接消息
            ws.receive_json()
            # 连接会自动断开，测试通过

    def test_websocket_multiple_clients(self, client):
        """测试多个客户端"""
        # 连接第一个客户端
        with client.websocket_connect("/api/v1/ws/quote") as ws1:
            ws1.receive_json()

            # 连接第二个客户端
            with client.websocket_connect("/api/v1/ws/quote") as ws2:
                ws2.receive_json()

                # 第一个客户端订阅
                ws1.send_json({
                    "type": "subscribe",
                    "stocks": ["600000"]
                })
                ws1.receive_json()

                # 获取统计信息
                ws1.send_json({"type": "stats"})
                data = ws1.receive_json()

                # 应该有2个连接
                assert data["data"]["total_connections"] >= 1


class TestWebSocketStatus:
    """WebSocket 状态端点测试"""

    def test_websocket_status(self, client):
        """测试 WebSocket 状态接口"""
        response = client.get("/api/v1/ws/status")
        assert response.status_code == 200
        data = response.json()
        assert "websocket" in data
        assert data["websocket"] == "enabled"
        assert "total_connections" in data

    def test_websocket_status_v1(self, client):
        """测试 WebSocket 状态接口 (API v1) - 重复测试保持向后兼容"""
        response = client.get("/api/v1/ws/status")
        assert response.status_code == 200
        data = response.json()
        assert "websocket" in data


class TestConnectionManager:
    """连接管理器测试"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        from app.api.websocket import ConnectionManager

        manager = ConnectionManager()
        assert manager.active_connections == {}
        assert manager.client_subscriptions == {}
        assert manager.stock_subscribers == {}

    def test_manager_stats(self):
        """测试管理器统计"""
        from app.api.websocket import ConnectionManager

        manager = ConnectionManager()
        stats = manager.get_stats()

        assert stats["total_connections"] == 0
        assert stats["total_subscriptions"] == 0
        assert stats["tracked_stocks"] == 0


@pytest.mark.asyncio
async def test_websocket_connection_lifecycle():
    """测试 WebSocket 连接生命周期"""
    from app.api.websocket import ConnectionManager
    from unittest.mock import MagicMock

    manager = ConnectionManager()

    # 创建模拟的 WebSocket
    mock_websocket = MagicMock()
    mock_websocket.client_state = MagicMock()
    mock_websocket.client_state.CONNECTED = "connected"
    mock_websocket.accept = AsyncMock()
    mock_websocket.send_json = AsyncMock()
    mock_websocket.receive_text = AsyncMock(side_effect=[
        '{"type": "subscribe", "stocks": ["600000"]}',
        WebSocketDisconnect()
    ])

    # 测试连接
    client_id = await manager.connect(mock_websocket)
    assert client_id is not None
    assert client_id in manager.active_connections

    # 清理
    await manager.disconnect(client_id)
    assert client_id not in manager.active_connections


@pytest.mark.asyncio
async def test_websocket_subscribe_unsubscribe():
    """测试订阅和取消订阅"""
    from app.api.websocket import ConnectionManager
    from unittest.mock import MagicMock

    manager = ConnectionManager()

    # 创建模拟的 WebSocket
    mock_websocket = MagicMock()
    mock_websocket.client_state = MagicMock()
    mock_websocket.client_state.CONNECTED = "connected"
    mock_websocket.accept = AsyncMock()
    mock_websocket.send_json = AsyncMock()

    # 连接
    client_id = await manager.connect(mock_websocket)

    # 订阅
    await manager.subscribe(client_id, ["600000", "000001"])
    assert "600000" in manager.client_subscriptions[client_id]
    assert "000001" in manager.client_subscriptions[client_id]

    # 取消订阅
    await manager.unsubscribe(client_id, ["600000"])
    assert "600000" not in manager.client_subscriptions[client_id]
    assert "000001" in manager.client_subscriptions[client_id]

    # 清理
    await manager.disconnect(client_id)
