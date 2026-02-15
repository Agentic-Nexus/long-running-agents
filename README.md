# Long-Running Agent System

基于 [Anthropic 文章: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) 的思想构建的长时 AI 系统框架。

## 核心思想

### 问题背景

长时运行代理面临的核心挑战：
1. **离散会话工作**: 代理必须在离散会话中工作，每个新会话开始时没有之前的记忆
2. **上下文窗口限制**: 上下文窗口有限，复杂项目无法在单个窗口内完成
3. **两个主要失败模式**:
   - 代理试图一次完成太多（one-shot），导致在实现中途耗尽上下文
   - 后续代理看到已有进展就宣布任务完成

### 解决方案：双代理架构

1. **初始化代理 (Initializer Agent)**: 首次运行时设置环境
   - 创建详细的 Feature List（功能需求列表）
   - 创建 init.sh 脚本（运行开发服务器）
   - 创建 claude-progress.txt 进度文件
   - 创建初始 git commit

2. **编码代理 (Coding Agent)**: 每个会话做增量进展
   - 每次只做一个功能
   - 为下一个会话留下清晰的产物

## 项目结构

```
long-running-agents/
├── long_running_agent/        # 核心框架
│   ├── __init__.py
│   ├── harness.py              # 主框架类
│   ├── config.py               # 配置管理
│   ├── agents/                 # 代理模块
│   │   ├── __init__.py
│   │   ├── initializer.py      # 初始化代理
│   │   └── coding.py           # 编码代理
│   ├── storage/                # 存储管理
│   │   ├── __init__.py
│   │   ├── feature_list.py     # 功能列表管理
│   │   └── progress.py         # 进度管理
│   └── utils/                  # 工具模块
│       ├── __init__.py
│       └── git.py              # Git管理
├── examples/                   # 使用示例
│   └── basic_usage.py
├── tests/                      # 测试目录
├── requirements.txt            # 依赖
└── README.md                   # 本文档
```

## 安装

```bash
# 克隆或下载项目后
cd long-running-agents

# 安装依赖
pip install -r requirements.txt
```

## 快速开始

### 1. 基础使用

```python
from long_running_agent import create_harness
from pathlib import Path

# 1. 创建 Harness
harness = create_harness(
    project_path="./my-project",
    project_spec="Build a web application",
    model_name="claude-opus-4-5"
)

# 2. 初始化项目（首次运行）
results = harness.initialize()
print(f"Initialization results: {results}")

# 3. 开始开发会话
session_id = harness.start_development_session()

# 4. 获取下一个任务
task = harness.get_next_task()
if task:
    print(f"Next task: {task.get('description')}")

    # 5. 实现任务
    result = harness.implement_task(task, ["Step 1", "Step 2"])

    # 6. 完成任务
    if result.get("tests_passed"):
        harness.complete_task(task)

# 7. 结束会话
session_results = harness.end_development_session("Completed setup")
```

### 2. 使用上下文管理器

```python
from long_running_agent import create_harness

harness = create_harness("./my-project", "Build a todo app")

with harness.start_session() as session:
    task = harness.get_next_task()
    if task:
        result = session.do_task(task, ["Implementation steps"])
```

### 3. 查看项目状态

```python
status = harness.get_project_status()
print(f"Features: {status['features']}")
print(f"Git: {status['git']}")
print(f"Recent commits: {status['recent_commits']}")
```

## 核心组件

### InitializerAgent (初始化代理)

首次运行时设置环境：

```python
from long_running_agent import InitializerAgent
from pathlib import Path

initializer = InitializerAgent(
    project_path=Path("./new-project"),
    project_spec="Build a todo app",
    model_name="claude-opus-4-5"
)

results = initializer.initialize()
```

**创建的文件：**
- `features.json`: 详细的功能需求列表
- `init.sh`: 开发服务器启动脚本
- `claude-progress.txt`: 进度记录文件
- 初始化 Git 仓库并创建初始 commit

### CodingAgent (编码代理)

每个会话做增量进展：

```python
from long_running_agent import CodingAgent

coding = CodingAgent(
    project_path=Path("./my-project"),
    model_name="claude-opus-4-5"
)

# 开始会话
session = coding.start_session()

# 了解当前状态
coding._get_bearings()

# 选择下一个功能
feature = coding.select_next_feature()

# 实现并完成
if feature:
    result = coding.implement_feature(feature, steps)
    if result.get("tests_passed"):
        coding.complete_feature(feature)

# 结束会话
coding.end_session("Summary")
```

### FeatureListManager (功能列表管理)

```python
from long_running_agent import FeatureListManager

manager = FeatureListManager(Path("./project/features.json"))

# 读取所有功能
features = manager.read_all()

# 获取统计
stats = manager.get_statistics()
# {'total': 10, 'passed': 3, 'pending': 7, ...}

# 获取待办
pending = manager.get_pending()

# 标记完成
manager.mark_passed("feat-001")
```

### ProgressManager (进度管理)

```python
from long_running_agent import ProgressManager

manager = ProgressManager(Path("./project/claude-progress.txt"))

# 读取进度
progress = manager.read()

# 添加会话记录
manager.add_session_entry(
    session_id="20240215_143000",
    completed_features=["feat-001", "feat-002"],
    errors=[],
    summary="Implemented two features"
)

# 获取最近会话
recent = manager.get_recent_sessions(5)
```

### GitManager (Git管理)

```python
from long_running_agent import GitManager

git = GitManager(Path("./project"))

# 获取状态
status = git.get_status()
# {'branch': 'main', 'modified': [], 'staged': [], ...}

# 获取提交历史
commits = git.get_recent_commits(10)

# 创建提交
git.commit("Implement feature X")
```

## 会话流程

每个开发会话遵循以下流程：

```
1. 读取 pwd 确认工作目录
2. 读取 claude-progress.txt 了解进度
3. 读取 git log 查看最近工作
4. 读取 features.json 选择下一个功能
5. 运行 init.sh 启动开发服务器
6. 验证基本功能是否正常工作
7. 实现新功能
8. 进行端到端测试
9. 提交 git commit
10. 更新 claude-progress.txt
```

## features.json 格式

```json
{
  "version": "1.0",
  "project": "My Project",
  "features": [
    {
      "id": "ui-001",
      "category": "ui",
      "description": "用户界面布局",
      "steps": [
        "创建基本HTML结构",
        "添加CSS样式",
        "验证布局"
      ],
      "passes": false,
      "priority": "high"
    }
  ]
}
```

## claude-progress.txt 格式

```
# Claude Progress Log
# =================
# Project: My Project
# Initialized: 2024-02-15T10:00:00
# Model: claude-opus-4-5

## Session History
-----------------
[20240215_143000] 2024-02-15 14:30:00 - Completed: feat-001, feat-002

## Current Status
-----------------
- Phase: DEVELOPMENT
- Features completed: 2
- Features remaining: (see features.json)
```

## 最佳实践

1. **始终使用 Git**: 每次会话结束都提交，便于回滚
2. **增量开发**: 每次只实现一个功能，不要试图一次完成太多
3. **详细的功能列表**: 使用 JSON 格式，记录每个功能的测试步骤
4. **端到端测试**: 使用 Puppeteer 等工具进行真实的端到端测试
5. **清晰的进度记录**: 每次会话结束更新进度文件

## 扩展使用

### 添加新的测试框架

```python
class CustomTestingAgent:
    def __init__(self, project_path):
        self.project_path = project_path

    def run_tests(self, feature):
        # 实现自定义测试逻辑
        pass
```

### 自定义初始化逻辑

```python
from long_running_agent import InitializerAgent

class CustomInitializer(InitializerAgent):
    def _create_feature_list(self):
        # 自定义功能列表生成逻辑
        super()._create_feature_list()
```

## 常见问题

### Q: 如何处理会话中断？

A: 下次会话开始时，代理会自动读取 `claude-progress.txt` 和 git 历史来了解当前状态。

### Q: 如何回滚错误的更改？

A: 使用 `git.revert(commit_hash)` 方法可以回滚到任意提交。

### Q: 如何添加更多功能到 features.json？

A: 使用 `FeatureListManager.add()` 方法添加新功能。

## 参考资料

- [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Claude Agent SDK](https://docs.anthropic.com/en/docs/claude-code/overview)

## License

MIT License
