# SPEC.md: Cyber-Cosmos 宇宙模拟系统优化与扩展

## 1. 项目概述

### 1.1 项目名称
**Cyber-Cosmos: AI 多文明宇宙模拟器**

### 1.2 项目目标
在现有的 AI 多文明宇宙模拟基础上，深化宇宙演化的叙事深度，增强多 Agent（智能体）之间的社交复杂性，并提供更直观、数据丰富的可视化观测界面。旨在打造一个能够自动演化、具备涌现式叙事能力的“数字宇宙沙盒”。

### 1.3 核心技术栈
*   **模拟核心**: Python 3.10+ (用于复杂逻辑运算、Agent 决策、事件演化)
*   **后端服务**: Node.js 18+ / Express 或 NestJS (用于 API 网关、WebSocket 通信、状态同步)
*   **前端界面**: React 18+ / TypeScript (用于宇宙可视化、用户交互)
*   **数据库**: PostgreSQL (持久化数据), Redis (实时状态缓存/消息队列)
*   **可视化库**: Three.js (3D 宇宙渲染), D3.js (数据图表/时间线)

---

## 2. 功能列表

### 2.1 宇宙事件系统与叙事引擎
*   **宇宙事件生成器**:
    *   支持宏观事件：超新星爆发、黑洞形成、星云碰撞、宇宙背景辐射波动。
    *   支持微观事件：星球资源枯竭、环境突变、科技奇点爆发。
*   **叙事引擎**:
    *   基于事件链的历史记录系统，自动生成编年史。
    *   事件影响系统：灾难事件对文明人口、科技值的即时影响计算。
    *   文明兴衰逻辑：判定文明从“部落”到“星际帝国”的晋升，以及文明毁灭机制。

### 2.2 多 Agent 社交系统扩展
*   **外交行为模型**:
    *   新增外交状态：宣战、停战、结盟、贸易协定、互不侵犯条约。
    *   Agent 决策权重引入“信任度”与“威胁评估”参数。
*   **联盟系统**:
    *   多 Agent 联盟形成逻辑（基于意识形态或地理位置）。
    *   联盟事件：联合探索、共同防御战争、联盟分裂。
*   **文明广播**:
    *   Agent 可向全宇宙广播信息（如“在此止步”或“欢迎贸易”），广播内容通过 LLM 生成。

### 2.3 宇宙观测台界面优化
*   **增强型 3D 可视化**:
    *   星球状态实时渲染（颜色代表阵营，光晕代表科技等级，粒子效果代表灾难）。
    *   宇宙航线可视化（展示贸易路径或舰队移动轨迹）。
*   **事件时间线**:
    *   底部时间轴组件，支持缩放、拖拽，标记重大历史事件点。
    *   点击事件节点可回放该时刻的宇宙状态。
*   **文明详情面板**:
    *   展示文明属性雷达图（军事、经济、科技、文化）。
    *   展示该文明的外交关系网络图。

### 2.4 Agent 决策系统交互体验
*   **决策日志可视化**:
    *   实时滚动日志流，展示 Agent 的思考过程（Input -> Reasoning -> Action）。
    *   支持按文明 ID、事件类型筛选日志。
*   **决策干预**:
    *   观测者模式下的“神迹”功能：用户可手动触发局部事件（如陨石撞击），观察 Agent 的应对决策。

---

## 3. 目录结构

项目采用 Monorepo 结构，便于统一管理。

```text
~/cyber-cosmos/
├── README.md
├── docker-compose.yml
├── SPEC.md
├── universe/                  # Python 模拟核心
│   ├── app/
│   │   ├── core/              # 宇宙物理引擎与时间轮
│   │   ├── agents/            # Agent 定义与决策模型
│   │   ├── events/            # 事件系统（灾难、叙事）
│   │   ├── social/            # 社交系统（外交、联盟）
│   │   └── llm/               # LLM 接口封装（叙事生成）
│   ├── tests/                 # Python 单元测试
│   ├── requirements.txt
│   └── main.py                # 模拟入口
├── universe_server/           # Node.js 后端服务
│   ├── src/
│   │   ├── modules/           # 业务模块
│   │   │   ├── universe/      # 宇宙状态管理
│   │   │   ├── history/       # 历史记录服务
│   │   │   └── gateway/       # WebSocket 网关
│   │   ├── common/            # 中间件、过滤器
│   │   └── main.ts
│   ├── package.json
│   └── tsconfig.json
├── web/                       # React 前端应用
│   ├── public/
│   ├── src/
│   │   ├── components/        # 通用组件
│   │   │   ├── Canvas/        # Three.js 宇宙画布
│   │   │   ├── Timeline/      # 时间线组件
│   │   │   └── DecisionLog/   # 决策日志面板
│   │   ├── pages/             # 页面视图
│   │   │   ├── Observatory/   # 观测台主页
│   │   │   └── Civilization/  # 文明详情页
│   │   ├── services/          # API 调用
│   │   └── store/             # 状态管理
│   ├── package.json
│   └── tsconfig.json
└── docs/                      # 文档与设计稿
```

---

## 4. 技术方案

### 4.1 架构设计
采用 **分层异步架构**。Python 负责重计算逻辑，Node.js 负责高并发连接与数据聚合，React 负责渲染。

1.  **模拟层**: 运行主循环。每个 Tick 计算星球状态、Agent 决策、事件触发。计算结果推送到 Redis。
2.  **服务层**: 订阅 Redis 频道或轮询获取最新状态，通过 WebSocket 广播给前端。提供 REST API 查询历史数据。
3.  **表现层**: 订阅 WebSocket 更新 3D 场景，发送用户干预指令。

### 4.2 数据库设计

**PostgreSQL (持久化存储)**
*   `civilizations`: id, name, attributes (JSONB), tech_level, status, created_at.
*   `universe_events`: id, event_type, description, impact_data (JSONB), tick, timestamp.
*   `diplomacy_logs`: id, from_civ_id, to_civ_id, action_type, result, timestamp.
*   `decision_logs`: id, civ_id, context, reasoning (Text), action, tick.

**Redis (实时缓存)**
*   `universe:state`: 当前时刻所有星球坐标、状态（Hash）。
*   `universe:tick`: 当前时间刻度。
*   `event_queue`: 待处理事件队列。

### 4.3 接口设计

**WebSocket 事件**
*   `universe:tick` -> Payload: `{ tick: number, changes: Array<Object> }`
*   `decision:new` -> Payload: `{ civ_id: string, log: string }`
*   `event:triggered` -> Payload: `{ type: string, details: Object }`

**REST API**
*   `GET /api/universe/history?range=100`: 获取过去 100 tick 的历史事件。
*   `GET /api/civilization/:id`: 获取文明详情及外交关系。
*   `POST /api/intervention`: 用户干预接口。

### 4.4 关键算法
*   **叙事生成**: 结合规则引擎与 LLM。规则引擎判定事件触发条件（如：人口 > 1B 触发“分裂危机”），LLM 负责生成事件的文本描述和 Agent 的对话内容。
*   **Agent 决策**: 采用 BDI (Belief-Desire-Intention) 架构简化版。Agent 根据当前环境更新 Belief，结合自身 Desire（如生存、扩张）生成 Intention，最后执行 Action。

---

## 5. 测试方案

### 5.1 单元测试
*   **Python**: 使用 `pytest`。重点测试事件触发逻辑、Agent 决策树的输出是否符合预期、属性计算公式。
*   **Node.js**: 使用 `Jest`。测试 API 接口响应、数据聚合逻辑、WebSocket 消息格式校验。

### 5.2 集成测试
*   搭建本地 Docker 环境，测试 Python 模拟核心与 Node.js 服务的数据同步。
*   验证前端 WebSocket 断线重连机制及状态恢复。

### 5.3 压力测试
*   使用 `Locust` 模拟高并发 Agent 决策场景，测试 Python 核心在 1000+ Agent 同时决策时的 Tick 延迟。
*   测试 Node.js WebSocket 在 500+ 连接下的广播延迟。

### 5.4 E2E 测试
*   使用 `Cypress` 或 `Playwright`。
*   场景：启动模拟 -> 等待事件触发 -> 前端时间线出现节点 -> 点击节点 -> 详情面板更新。

---

## 6. 运行与部署方式

### 6.1 开发环境运行
依赖 Docker 和 Docker Compose。

```bash
# 克隆项目
cd ~/cyber-cosmos

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f universe_app

# 访问前端
open http://localhost:3000
```

### 6.2 配置文件
*   `universe/.env`: 配置 LLM API Key (OpenAI/Claude)、模拟速度。
*   `universe_server/.env`: 配置数据库连接串、Redis 地址、跨域策略。

### 6.3 生产环境部署
*   **容器化**: 使用 Docker 构建三个独立的镜像。
*   **编排**: 推荐使用 Kubernetes (K8s)。
    *   `universe-simulator`: Deployment，单实例（有状态计算），需持久化存储日志。
    *   `universe-server`: Deployment，多实例，通过 Service 负载均衡。
    *   `web-client`: Nginx 托管静态资源。
*   **监控**: 集成 Prometheus + Grafana 监控 Tick 速率和系统资源。

### 6.4 初始化数据
项目提供 `seed.sql` 或初始化脚本，用于创建初始的 3-5 个母文明和基础星球数据，避免空宇宙启动。