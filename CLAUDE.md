# 大模型驱动的股票分析系统

## 项目概述

基于大模型（LLM）驱动的智能股票分析系统，能够自动分析股票数据、生成投资建议、回答用户关于股票市场的相关问题。

## 技术栈

- **后端**: Python, FastAPI
- **数据库**: PostgreSQL, Redis
- **LLM 集成**: Anthropic Claude / OpenAI
- **数据源**: 股票行情 API (Tushare / AkShare)
- **前端**: React + TypeScript

## 开发环境

```bash
# 启动开发服务器
./init.sh

# 访问地址
http://localhost:8000
```

## 核心功能模块

详见 `features.json`

## 当前状态

详见 `claude-progress.txt`

## 会话开始步骤

1. 运行 `pwd` 确认工作目录
2. 读取 `claude-progress.txt` 了解项目进度
3. 读取 `git log --oneline -10` 查看最近工作
4. 读取 `features.json` 选择下一个功能
5. 运行 `./init.sh` 启动开发服务器
6. 验证基本功能是否正常
