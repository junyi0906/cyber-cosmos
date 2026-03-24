# SPEC.md - Cyber-Cosmos 项目优化与扩展规格书

## 1. 项目概述

### 1.1 项目名称
**Cyber-Cosmos: AI Multi-Civilization Universe Simulator**

### 1.2 项目目标
在现有的 AI 多文明宇宙模拟基础上，深化宇宙模拟的真实性与复杂度，构建一个具备自发叙事能力、复杂多 Agent 社交网络以及高可观测性的智能宇宙系统。通过引入事件引擎、外交系统和可视化增强，使用户能够从宏观（宇宙演化）到微观（Agent 决策）全方位观测和干预宇宙进程。

### 1.3 核心技术栈
*   **模拟核心**: Python 3.10+ (用于复杂逻辑运算、LLM 集成、物理模拟)
*   **后端服务**: Node.js (Express/NestJS) (用于 API 网关、WebSocket 通信、会话管理)
*   **前端界面**: React 18+ + TypeScript (可视化、交互界面)
*   **数据存储**: PostgreSQL (结构化数据), MongoDB (事件日志/叙事存档), Redis (实时状态/消息队列)
*   **通信协议**: REST API + WebSocket (实时推送)

---

## 2. 功能列表

### 2.1 宇宙事件系统与叙事引擎
*   **动态事件生成**：
    *   **天体事件**：超新星爆发、黑洞形成、星云坍缩、星球资源枯竭。
    *   **文明事件**：科技突破、文化复兴、内战分裂、文明灭绝。
    *   **随机灾难**：伽马射线暴、星际瘟疫、虚空入侵。
*   **叙事引擎**：
    *   基于事件链生成历史编年史。
    *   事件因果关联（例如：资源枯竭 -> 导致星际战争 -> 文明迁徙）。
    *   生成“宇宙纪元”总结报告。

### 2.2 多 Agent 社交系统扩展
*   **外交行为**：
    *   建立外交关系（和平、中立、敌对）。
    *   签订条约（互不侵犯、科技共享、贸易协定）。
*   **联盟机制**：
    *   文明联盟的组建与解散。
    *   联盟任务（联合防御、共同开发）。
    *   联盟内部投票决策。
*   **文明广播**：
    *   向全宇宙广播信息（技术广播、威胁警告、求救信号）。
    *   加密通讯与破译机制。

### 2.3 宇宙观测台界面优化
*   **高级可视化**：
    *   星系热力图（资源分布、人口密度）。
    *   文明影响力范围动态边界。
    *   事件特效渲染（爆炸、扩散波）。
*   **事件时间线**：
    *   可缩放的时间轴控件。
    *   关键事件标记与回放功能。
    *   按文明/星系筛选事件流。

### 2.4 Agent 决策系统交互增强
*   **决策日志可视化**：
    *   展示 Agent 思考链。
    *   决策权重分析（为何选择 A 而非 B）。
    *   决策后果追踪回路。
*   **交互式干预**：
    *   用户可对特定 Agent 施加“神谕”（修改决策参数）。
    *   触发特定测试场景。

---

## 3. 目录结构

项目根目录：`~/cyber-cosmos`

```text
cyber-cosmos/
├── universe/                  # Python 模拟核心
│   ├── core/                  # 基础物理与时间引擎
│   ├── agents/                # Agent 定义与行为树
│   │   ├── base_agent.py
│   │   └── decision_engine.py # 决策系统增强
│   ├── events/                # [新增] 宇宙事件系统
│   │   ├── generator.py       # 事件生成器
│   │   ├── types.py           # 事件类型定义
│   │   └── dispatcher.py      # 事件分发与处理
│   ├── narrative/             # [新增] 叙事引擎
│   │   ├── chronicler.py      # 历史记录与生成
│   │   └── llm_interface.py   # LLM 接口封装
│   ├── social/                # [新增] 社交与外交系统
│   │   ├── diplomacy.py       # 外交关系管理
│   │   ├── alliance.py        # 联盟逻辑
│   │   └── broadcast.py       # 广播系统
│   └── requirements.txt
├── universe_server/           # Node.js 后端服务
│   ├── src/
│   │   ├── api/               # REST API 接口
│   │   ├── websocket/         # WebSocket 处理器
│   │   ├── services/          # 业务逻辑层
│   │   │   ├── sync.service.ts # 与 Python 核心同步
│   │   │   └── event.proxy.ts # 事件代理
│   │   └── models/            # 数据库模型
│   ├── package.json
│   └── tsconfig.json
├── web/                       # React 前端应用
│   ├── src/
│   │   ├── components/
│   │   │   ├── Observatory/   # 宇宙观测台组件
│   │   │   │   ├── StarMap.tsx    # 星图核心
│   │   │   │   └── Timeline.tsx   # [新增] 时间线组件
│   │   │   ├── DecisionLog/   # [新增] 决策日志组件
│   │   │   └── Social/        # [新增] 社交/外交面板
│   │   ├── hooks/             # 自定义 Hooks
│   │   ├── store/             # 状态管理
│   │   └── utils/             # 工具函数
│   └── package.json
├── docker-compose.yml         # 容器编排
├── Makefile                   # 常用命令脚本
└── SPEC.md                    # 本文档
```

---

## 4. 技术方案

### 4.1 架构设计
采用 **微内核 + 网关** 架构。
*   **Python Core**: 作为计算密集型的“内核”，负责模拟循环、Agent 决策计算、事件判定。通过 Redis Pub/Sub 发布状态变更。
*   **Node.js Server**: 作为“网关”与“控制器”，负责客户端连接管理、数据持久化、API 聚合。订阅 Redis 消息并推送给前端。
*   **React Web**: 作为“视图层”，负责数据可视化和用户交互。

### 4.2 前端方案
*   **可视化库**: 使用 **Three.js** 或 **PixiJS** 实现高性能 2D/3D 星图渲染。
*   **状态管理**: 使用 **Zustand** 或 **Redux Toolkit** 管理全局宇宙状态。
*   **时间线组件**: 自定义开发基于 D3.js 的时间轴，支持大规模事件数据的缩放渲染。
*   **决策日志**: 使用树形图或流程图组件展示 Agent 的思维链。

### 4.3 后端方案
*   **通信机制**:
    *   前端 <-> Node.js: WebSocket (Socket.io)，保证实时性。
    *   Node.js <-> Python: Redis 消息队列。Python 计算完一帧后推送 `universe:tick` 事件。
*   **数据存储**:
    *   **PostgreSQL**: 存储文明基础属性、外交关系表、用户配置。
    *   **MongoDB**: 存储“事件日志”和“叙事历史”，利用其 Schema-free 特性适应多变的事件结构。
    *   **Redis**: 缓存当前帧的宇宙快照，用于前端快速重连恢复现场。

### 4.4 接口设计

#### 4.4.1 REST API
*   `GET /api/universe/snapshot`: 获取当前宇宙快照。
*   `GET /api/events/timeline?range=1000-2000`: 获取指定时间段的事件。
*   `GET /api/agents/:id/decisions`: 获取指定 Agent 的决策历史。
*   `POST /api/intervention/god`: 用户干预接口（修改参数）。

#### 4.4.2 WebSocket Events
*   **Server -> Client**:
    *   `tick`: 推送每帧更新数据（坐标、状态）。
    *   `major_event`: 推送重大事件（如星球爆炸）。
    *   `alert`: 推送文明广播或警报。
*   **Client -> Server**:
    *   `subscribe_agent`: 订阅特定 Agent 的详细日志。
    *   `pause_simulation`: 暂停/继续模拟。

---

## 5. 测试方案

### 5.1 单元测试
*   **Python**: 使用 `pytest` 测试事件生成逻辑、Agent 决策权重计算、外交状态机转换。
*   **Node.js**: 使用 `Jest` 测试 API 接口、数据转换层、WebSocket 消息解析。

### 5.2 集成测试
*   模拟完整的模拟循环：初始化宇宙 -> 运行 1000 tick -> 验证数据库中的事件记录是否完整。
*   测试 Node.js 与 Python 的消息队列连通性。

### 5.3 压力测试
*   使用 `Locust` 模拟 1000+ Agent 同时决策，观察 CPU/内存占用及帧率（FPS）下降情况。
*   前端渲染压力测试：模拟 5000+ 星体同时移动时的帧率。

### 5.4 E2E 测试
*   使用 `Cypress` 测试用户关键路径：打开观测台 -> 查看时间线 -> 点击文明 -> 查看决策日志。

---

## 6. 运行与部署方式

### 6.1 开发环境运行
依赖 Docker 和 Docker Compose。

```bash
# 克隆项目
cd ~/cyber-cosmos

# 启动所有服务
make dev

# 或者使用 docker-compose
docker-compose up --build
```
服务地址：
*   前端：`http://localhost:3000`
*   Node API：`http://localhost:4000`
*   Python Core：内部服务，无直接 HTTP 端口，通过 Redis 通信。

### 6.2 生产环境部署
采用容器化部署，建议使用 Kubernetes (K8s)。

*   **镜像构建**:
    *   `universe-core`: 基于 Python slim 镜像，包含所有依赖。
    *   `universe-server`: 基于 Node alpine 镜像。
    *   `web-client`: 使用 Nginx 托管静态资源。
*   **配置管理**: 使用环境变量注入数据库连接串、Redis 地址、LLM API Key。
*   **扩容策略**:
    *   Node.js 服务可水平扩展。
    *   Python 核心计算密集，建议垂直扩展或采用分片模拟（未来规划）。

### 6.3 环境变量说明
```env
# .env.example
POSTGRES_URI=postgresql://user:pass@db:5432/cybercosmos
MONGO_URI=mongodb://mongo:27017/cybercosmos
REDIS_URI=redis://redis:6379
OPENAI