# SPEC.md: Cyber-Cosmos 第二轮进化规格文档

## 1. 项目概述

### 1.1 项目名称
**Cyber-Cosmos: Era of Trade & Relics (赛博宇宙：贸易与遗迹纪元)**

### 1.2 项目目标
在现有的动态叙事与外交基础上，引入**经济驱动机制**（星际贸易）、**历史沉淀机制**（文明遗迹）与**环境动态性**（宇宙天气/赛季），将宇宙从单纯的"事件模拟器"升级为具有经济周期、历史厚度和环境策略的复杂生态系统。

### 1.3 核心技术栈
*   **后端**: Node.js + TypeScript + NestJS (模块化架构)
*   **数据库**: PostgreSQL (持久化) + Redis (实时状态/缓存) + TimescaleDB (时间序列数据，用于历史分析)
*   **前端**: React + TypeScript + D3.js (数据可视化) + Socket.io-client
*   **通信**: REST API (管理操作) + WebSocket (实时数据推送)
*   **测试**: Jest (单元/集成测试) + Artillery (压力测试)

---

## 2. 功能列表

本次进化筛选了 4 个核心方向，按优先级排序：

### 2.1 【核心】星际贸易系统
**价值**：建立文明间的强交互纽带，通过资源流动驱动政治格局变化。
*   **F-1.1 贸易市场**：
    *   文明可挂单出售/求购资源（矿石、能源、技术点）。
    *   全局供需指数：根据买卖单量动态计算资源价格波动。
*   **F-1.2 贸易路线**：
    *   建立贸易协定后生成虚拟"航线"。
    *   航线效率受距离、外交关系、宇宙天气影响。
    *   商船事件：运输途中可能遭遇海盗或获得意外宝藏。
*   **F-1.3 经济制裁**：
    *   外交状态（战争/敌对）自动阻断贸易路线，影响资源获取。

### 2.2 【核心】文明遗迹系统
**价值**：赋予历史事件实际的游戏价值，增加地图争夺点。
*   **F-2.1 遗迹生成**：
    *   监听重大事件（如"恒星坍缩"、"帝国分裂"），在事件坐标生成遗迹实例。
    *   遗迹类型：先驱者工厂（产能加成）、战争坟场（军事加成）、知识库（科技加成）。
*   **F-2.2 遗迹争夺**：
    *   遗迹具有归属权，非归属文明可发起"遗迹争夺战"（模拟计算）。
    *   占领遗迹需消耗军事力量，并提供持续的资源或科技产出。

### 2.3 【环境】宇宙天气预报
**价值**：增加环境不确定性，影响贸易与探索策略。
*   **F-3.1 天气周期**：
    *   宇宙分为"平静期"、"资源风暴"、"暗物质浪潮"等阶段。
    *   每 X 个模拟周期随机切换天气。
*   **F-3.2 环境影响**：
    *   **资源风暴**：采矿效率 +50%，但航线事故率 +30%。
    *   **暗物质浪潮**：科研速度 +50%，但能量消耗翻倍。
    *   **黑暗波动**：视野范围缩小，外交信任度自然衰减加速。

### 2.4 【框架】宇宙赛季机制
**价值**：提供长期运营目标，允许规则迭代与重置。
*   **F-4.1 赛季定义**：
    *   每赛季持续固定模拟时间（如 1000 个周期）。
    *   赛季规则：可配置本赛季的资源倍率、事件频率、初始文明数量。
*   **F-4.2 结算与归档**：
    *   赛季末计算文明评分（综合国力、科技、遗迹占有量）。
    *   生成"宇宙编年史"快照，存入 TimescaleDB。
    *   赛季重置：保留文明核心基因，重置地图、资源和遗迹。

---

## 3. 目录结构

```text
cyber-cosmos/
├── src/
│   ├── main.ts                     # 入口文件
│   ├── app.module.ts               # 根模块
│   ├── config/                     # 配置文件（数据库、常量）
│   │
│   ├── core/                       # 核心基础层
│   │   ├── events/                 # 事件总线基础设施工
│   │   ├── database/               # 数据库连接与ORM配置
│   │   └── scheduler/              # 定时任务调度器
│   │
│   ├── modules/                    # 业务模块
│   │   ├── civilization/           # [已有] 文明模块
│   │   ├── diplomacy/              # [已有] 外交模块
│   │   ├── narrative/              # [已有] 叙事引擎
│   │   │
│   │   ├── trade/                  # [新增] 星际贸易模块
│   │   │   ├── trade.controller.ts
│   │   │   ├── trade.service.ts
│   │   │   ├── market.service.ts   # 市场供需算法
│   │   │   ├── route.service.ts    # 航线管理
│   │   │   └── entities/           # 贸易实体
│   │   │
│   │   ├── relics/                 # [新增] 文明遗迹模块
│   │   │   ├── relic.controller.ts
│   │   │   ├── relic.service.ts
│   │   │   ├── spawner.listener.ts # 监听事件生成遗迹
│   │   │   └── entities/
│   │   │
│   │   ├── weather/                # [新增] 宇宙天气模块
│   │   │   ├── weather.service.ts
│   │   │   ├── effects.service.ts  # 天气效果应用
│   │   │   └── weather.gateway.ts  # WebSocket推送
│   │   │
│   │   └── season/                 # [新增] 赛季系统模块
│   │       ├── season.manager.ts   # 赛季生命周期管理
│   │       ├── ranking.service.ts  # 结算算法
│   │       └── history.service.ts  # 编年史归档
│   │
│   └── gateway/                    # WebSocket 网关
│       └── cosmos.gateway.ts       # 宇宙实时数据推送
│
├── test/                           # 测试目录
│   ├── unit/
│   └── e2e/
├── docs/                           # API 文档
├── SPEC.md                         # 本文档
└── docker-compose.yml              # 容器编排
```

---

## 4. 技术方案

### 4.1 后端架构设计
采用**领域驱动设计 (DDD)** 思想，解耦各子系统。

*   **贸易引擎**：
    *   使用 Redis Sorted Set 实现高性能的买卖挂单队列。
    *   引入"滑点"算法计算实际成交价，模拟真实市场波动。
*   **遗迹生成**：
    *   利用现有的 `EventEmitter2`，在 `NarrativeEngine` 抛出 `CriticalEvent` 时，`RelicModule` 监听并触发遗迹生成逻辑。
*   **天气系统**：
    *   使用有限状态机 (FSM) 管理天气状态流转。
    *   通过 WebSocket 广播天气变更，前端无需轮询。
*   **赛季管理**：
    *   使用数据库事务处理赛季结算，确保数据一致性。
    *   利用 TimescaleDB 存储历史快照，支持后续的数据分析图表。

### 4.2 数据库设计

**新增表结构：**

1.  **trades (交易订单表)**
    *   `id`, `civ_id`, `resource_type` (ORE/ENERGY/TECH), `amount`, `price`, `type` (BUY/SELL), `status`, `created_at`
2.  **trade_routes (贸易路线表)**
    *   `id`, `source_civ_id`, `target_civ_id`, `efficiency`, `status` (ACTIVE/BLOCKED), `last_tick_at`
3.  **relics (遗迹表)**
    *   `id`, `name`, `type`, `coordinates` (JSONB), `owner_id`, `bonus_config` (JSONB), `spawn_event_id`
4.  **cosmos_weather (天气日志表)**
    *   `id`, `weather_type`, `start_cycle`, `end_cycle`, `global_modifiers` (JSONB)
5.  **seasons (赛季表)**
    *   `id`, `season_number`, `rules_config` (JSONB), `start_at`, `end_at`, `leaderboard` (JSONB)

### 4.3 接口设计

**REST API:**

*   `POST /api/trade/order`: 创建交易订单
*   `GET /api/trade/market`: 获取当前市场行情 (K线图数据)
*   `POST /api/trade/route`: 建立贸易路线
*   `GET /api/relics`: 获取全宇宙遗迹分布
*   `POST /api/relics/:id/capture`: 尝试占领遗迹
*   `GET /api/weather`: 获取当前及预测天气
*   `GET /api/season/info`: 获取当前赛季信息与排名

**WebSocket Events:**

*   `weather_updated`: 推送新天气及其全局影响。
*   `market_tick`: 推送每周期资源价格变动。
*   `relic_discovered`: 推送新遗迹发现通知。
*   `season_end`: 推送赛季结算倒计时与结果。

---

## 5. 测试方案

### 5.1 单元测试
*   **贸易逻辑**：验证供需算法正确性，测试极端值（如 0 价格或巨额订单）处理。
*   **天气效果**：验证不同天气对文明属性的计算修正是否正确叠加。
*   **遗迹生成**：Mock 重大事件，验证遗迹是否在正确坐标生成并携带正确属性。

### 5.2 集成测试
*   **贸易闭环**：模拟两个文明，A 下单卖出，B 下单买入，验证资源扣除与增加、交易记录生成。
*   **赛季流转**：模拟时间推进至赛季末，验证结算逻辑是否触发，数据库是否正确归档。

### 5.3 性能测试
*   使用 Artillery 模拟 1000 个并发贸易请求，验证 Redis 缓存层与数据库写入性能。
*   模拟 10000 个遗迹点，测试空间查询性能（需验证是否需要引入 PostGIS）。

---

## 6. 运行与部署

### 6.1 环境要求
*   Node.js >= 18
*   Docker & Docker Compose
*   PostgreSQL 15 + TimescaleDB 扩展

### 6.2 本地开发启动
```bash
# 1. 安装依赖
npm install

# 2. 启动基础服务
docker-compose up -d postgres redis

# 3. 运行数据库迁移
npm run migration:run

# 4. 启动开发服务器
npm run start:dev
```

### 6.3 生产部署
*   使用 Dockerfile 构建镜像。
*   通过 CI/CD 流水线自动部署至 Kubernetes 集群。
*   配置 Nginx 反向代理，开启 WebSocket 长连接支持。
*   启用 TimescaleDB 自动压缩策略，归档历史赛季数据。

### 6.4 配置项
*   `SEASON_DURATION_CYCLES`: 赛季持续周期数 (默认: 1000)
*   `MARKET_VOLATILITY`: 市场波动系数 (默认: 0.05)
*   `RELIC_SPAWN_RATE`: 遗迹生成概率 (默认: 0.1)