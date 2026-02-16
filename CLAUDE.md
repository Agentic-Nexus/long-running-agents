# 大模型驱动的股票分析系统 (LLM Stock Analyzer)

## 项目概述

基于大模型（LLM）驱动的智能股票分析系统，能够自动分析股票数据、生成投资建议、回答用户关于股票市场的相关问题。

## 技术栈

- **后端**: Python, FastAPI, SQLAlchemy
- **数据库**: PostgreSQL (异步), Redis
- **LLM 集成**: Anthropic Claude / OpenAI GPT
- **数据源**: AkShare (开源股票数据API)
- **前端**: React, TypeScript, Vite, Recharts
- **状态管理**: Zustand

## 项目结构

```
.
├── main.py                    # FastAPI 应用入口
├── app/
│   ├── api/                  # API 路由
│   │   ├── health.py         # 健康检查
│   │   ├── stocks.py         # 股票查询 API
│   │   ├── chat.py           # 智能问答 API
│   │   └── analysis.py       # 分析报告 API
│   ├── services/              # 业务服务
│   │   ├── stock_service.py   # 股票数据服务
│   │   ├── llm_service.py    # LLM 集成服务
│   │   ├── prompt_templates.py    # Prompt 模板
│   │   ├── technical_analysis.py   # 技术指标
│   │   ├── pattern_recognition.py # K线形态识别
│   │   └── data_storage.py   # 数据存储
│   ├── db/                   # 数据库
│   │   └── database.py       # 数据库连接管理
│   ├── models/               # 数据模型
│   │   └── stock.py
│   └── utils/                # 工具
│       └── logger.py         # 日志配置
├── frontend/                  # React 前端
│   ├── src/
│   │   ├── components/       # 组件
│   │   ├── pages/            # 页面
│   │   ├── layouts/          # 布局
│   │   ├── router/           # 路由
│   │   ├── services/         # API 服务
│   │   └── store/            # 状态管理
│   └── package.json
├── tests/                    # 测试
├── features.json              # 功能清单
├── claude-progress.txt        # 进度记录
└── requirements.txt          # Python 依赖
```

## 开发环境

### 后端启动

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python main.py
# 或
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

### 访问地址

- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 前端: http://localhost:5173

## 环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
# LLM 配置
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key

# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/stock_db
REDIS_URL=redis://localhost:6379/0

# 股票数据
TUSHARE_TOKEN=your_tushare_token
```

## 核心功能

### 后端 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/stocks/search` | GET | 股票搜索 |
| `/api/v1/stocks/quote/{code}` | GET | 实时行情 |
| `/api/v1/stocks/kline/{code}` | GET | 历史K线 |
| `/api/v1/stocks/{code}` | GET | 股票详情 |
| `/api/v1/chat` | POST | 智能问答 |
| `/api/v1/analysis/technical/{code}` | GET | 技术分析 |
| `/api/v1/analysis/fundamental/{code}` | GET | 基本面分析 |
| `/api/v1/analysis/advice/{code}` | GET | 投资建议 |
| `/health` | GET | 健康检查 |

### 技术指标

- 移动平均线 (MA5, MA10, MA20, MA60)
- MACD (DIF, DEA, MACD柱)
- RSI (RSI-6, RSI-12, RSI-24)
- 布林带 (Upper, Middle, Lower)
- KDJ (K, D, J)

### K线形态

- 基本形态: 锤子线、吊颈线、十字星、倒锤线
- 组合形态: 头肩顶/底、双顶/底、三角形整理
- 趋势判断: 上升、下降、横盘

## 会话开发流程 (Agent Teams 模式)

### 每次会话开始

1. 运行 `pwd` 确认工作目录
2. 读取 `claude-progress.txt` 了解项目进度
3. 运行 `git log --oneline -10` 查看最近工作
4. 读取 `features.json` 选择下一个 `passes: false` 的功能

### 开发步骤

1. **选择任务**: 从 `features.json` 选择高优先级未完成功能
2. **实现功能**: 按 `steps` 列表逐步实现
3. **编写测试**: 在 `tests/` 目录添加测试用例
4. **更新进度**: 修改 `features.json` 中对应功能的 `passes: true`
5. **记录进度**: 更新 `claude-progress.txt`
6. **提交代码**: `git commit` 并推送到远程

### 功能清单格式 (features.json)

```json
{
  "id": "api-001",
  "category": "api",
  "description": "股票查询 API",
  "steps": [
    "实现股票搜索接口",
    "实现实时行情接口"
  ],
  "passes": true,
  "priority": "high",
  "completed_at": "2026-02-16T12:00:00"
}
```

### 进度记录格式 (claude-progress.txt)

```
## Session History
-----------------
[20260216_001] 2026-02-16 12:00 - Completed: infra-002 (FastAPI 后端基础框架)
  - 创建日志配置模块
  - 创建健康检查路由

## Current Status
-----------------
- Phase: DEVELOPMENT
- Features completed: 8
- Features remaining: 7
```

## 测试

```bash
# 运行后端测试
pytest tests/ -v

# 运行前端测试
cd frontend && npm test
```

## 贡献指南

1. 从 `features.json` 选择未完成的功能
2. 按照上述流程开发
3. 确保所有测试通过
4. 提交时更新 `features.json` 和 `claude-progress.txt`

## 当前进度

详见 `claude-progress.txt`

## 许可

MIT License
