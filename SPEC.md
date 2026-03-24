# SPEC.md - Cyber-Cosmos 第二轮进化规格书

## 1. 项目概述

### 1.1 项目名称
**Cyber-Cosmos: Echoes of Eternity (赛博宇宙：永恒回响)**

### 1.2 项目目标
在现有的事件系统、叙事引擎及外交联盟基础上，引入动态经济系统、历史沉淀机制与宏观时间维度，构建一个具有自我演化能力、历史厚重感与周期性规则变化的深度宇宙模拟器。本轮进化旨在解决宇宙静态化、资源单一化及长期目标缺失的问题。

### 1.3 核心技术栈
- **后端**: Node.js + TypeScript + NestJS (模块化架构)
- **数据库**: PostgreSQL (关系型数据) + MongoDB (事件/日志存储) + Redis (缓存/实时状态)
- **前端**: React + TypeScript + D3.js (数据可视化) + Socket.IO-client
- **通信**: REST API + WebSocket (实时推送)
- **测试**: Jest + Supertest

---

## 2. 功能列表

本轮进化经分析选定以下三个核心方向：

### 2.1 【核心】星际贸易系统
**目标**：建立文明间资源流动机制，激活外交博弈，增加资源获取维度。

*   **F-2.1.1 贸易市场与汇率引擎**
    *   实现基于供需关系的动态汇率算法（矿石、能源、技术点）。
    *   文明可发布“出售单”或“购买单”，支持限价单与市价单。
*   **F-2.1.2 贸易路线与物流**
    *   基于星图坐标计算贸易路线距离，距离越远，运输时间越长，风险（损耗）越高。
    *   贸易路线经过敌对势力范围时征收“过路费”或触发拦截事件。
*   **F-2.1.3 贸易制裁与禁运**
    *   外交状态为“战争”或“禁运”时，自动阻断双边贸易。
    *   贸易顺差/逆差影响文明间的外交好感度。

### 2.2 【核心】文明遗迹系统
**目标**：将短暂的历史事件转化为永久的世界资产，增加探索与争夺动机。

*   **F-2.2.1 遗迹生成机制**
    *   监听重大事件（如：恒星坍缩、文明毁灭、奇点科技研发），在原坐标生成“遗迹节点”。
    *   遗迹类型：数据废墟（提供技术点）、矿脉残渣（提供矿石）、虚空裂隙（提供能源但伴随风险）。
*   **F-2.2.2 遗迹探索与争夺**
    *   文明派遣舰队进行“遗迹考古”，需消耗时间与能源。
    *   遗迹具有“耐久度/研究进度”，多文明可同时争夺同一遗迹，触发PVP事件。
*   **F-2.2.3 遗迹叙事关联**
    *   遗迹携带“历史回响”属性，研究遗迹可解锁该遗迹生成时的历史日志片段。

### 2.3 【核心】宇宙赛季机制
**目标**：引入宏观时间维度，解决后期玩法固化问题，提供周期性重置/结算激励。

*   **F-2.3.1 赛季周期管理**
    *   宇宙时间分为：开拓期（资源丰度高）、扩张期（外交限制少）、终焉期（资源枯竭，灾害频发）。
    *   赛季时长设定为现实时间 30 天（可配置）。
*   **F-2.3.2 动态宇宙法则**
    *   每个赛季随机生成“赛季特质”（Trait），例如：
        *   *黑暗森林法则*：外交视野范围缩小 50%。
        *   *技术爆炸*：科技研发速度翻倍，但能源消耗翻倍。
*   **F-2.3.3 赛季结算与传承**
    *   赛季末根据文明积分（科技、军事、经济）进行排名。
    *   排名前列的文明获得“传承点数”，可在下个赛季解锁特殊初始天赋。

---

## 3. 目录结构

```text
cyber-cosmos/
├── src/
│   ├── main.ts                     # 入口文件
│   ├── app.module.ts               # 根模块
│   ├── config/                     # 配置文件（数据库、环境变量）
│   │
│   ├── core/                       # 核心基础层
│   │   ├── events/                 # 事件总线与基础事件定义
│   │   ├── database/               # 数据库连接与ORM配置
│   │   └── scheduler/              # 定时任务服务（赛季结算、贸易更新）
│   │
│   ├── modules/
│   │   ├── civilization/           # 现有：文明模块
│   │   ├── diplomacy/              # 现有：外交模块
│   │   │
│   │   ├── trade/                  # 【新增】星际贸易模块
│   │   │   ├── trade.controller.ts
│   │   │   ├── trade.service.ts
│   │   │   ├── models/
│   │   │   │   ├── order.entity.ts     # 贸易订单
│   │   │   │   └── route.entity.ts     # 贸易路线
│   │   │   └── algorithms/
│   │   │       ├── pricing.engine.ts   # 定价算法
│   │   │       └── pathfinding.ts      # 路径计算
│   │   │
│   │   ├── relic/                  # 【新增】文明遗迹模块
│   │   │   ├── relic.controller.ts
│   │   │   ├── relic.service.ts
│   │   │   ├── models/
│   │   │   │   └── relic.entity.ts
│   │   │   └── listeners/
│   │   │       └── history.listener.ts # 监听事件生成遗迹
│   │   │
│   │   └── season/                 # 【新增】宇宙赛季模块
│   │       ├── season.controller.ts
│   │       ├── season.service.ts
│   │       ├── models/
│   │       │   └── season.entity.ts
│   │       └── rules/
│   │           └── rule-engine.ts      # 赛季规则引擎
│   │
│   ├── narrative/                  # 现有：叙事引擎（需适配遗迹叙事）
│   └── api/                        # API 网关与 WebSocket 网关
│
├── tests/                          # 测试目录
│   ├── unit/
│   └── e2e/
├── docs/                           # 文档
├── SPEC.md                         # 本文档
└── package.json
```

---

## 4. 技术方案

### 4.1 后端架构
采用 **NestJS** 模块化架构，利用其依赖注入和模块系统解耦各业务域。

*   **贸易系统**：使用 Redis 的 Sorted Set 实现高性能的订单簿，利用 Pub/Sub 机制实现交易撮合通知。
*   **遗迹系统**：基于观察者模式。现有的事件系统发射 `MajorEventOccurred`，遗迹模块监听并根据事件权重决定是否生成遗迹。
*   **赛季系统**：引入全局拦截器，在每次请求处理前注入当前赛季上下文，动态调整资源计算逻辑。

### 4.2 数据库设计

**PostgreSQL (关系型数据)**
*   `civilizations`: 现有表，新增 `legacy_points` (传承点)。
*   `trade_orders`: `id`, `seller_id`, `buyer_id`, `resource_type`, `price`, `amount`, `status`.
*   `trade_routes`: `id`, `start_pos`, `end_pos`, `owner_id`, `efficiency`.
*   `relics`: `id`, `location`, `type`, `source_event_id`, `remaining_resources`, `discovered_by`.
*   `seasons`: `id`, `start_time`, `end_time`, `traits (JSONB)`, `status`.

**MongoDB (日志与历史)**
*   `event_logs`: 存储所有事件，用于遗迹生成溯源。
*   `season_history`: 存储过往赛季的详细记录。

**Redis (缓存与实时状态)**
*   `market_prices`: 实时资源价格缓存。
*   `season_current`: 当前赛季配置缓存。

### 4.3 接口设计

#### REST API
*   `GET /api/trade/market`: 获取当前市场行情。
*   `POST /api/trade/orders`: 创建贸易订单。
*   `GET /api/relics`: 获取可见遗迹列表。
*   `POST /api/relics/{id}/excavate`: 派遣舰队探索遗迹。
*   `GET /api/season/info`: 获取当前赛季信息与剩余时间。

#### WebSocket Events
*   `trade_update`: 推送订单成交、价格波动。
*   `relic_discovered`: 推送新遗迹发现通知。
*   `season_phase_change`: 推送赛季阶段变更（如进入终焉期）。

---

## 5. 测试方案

### 5.1 单元测试
*   **贸易定价算法**：验证供需关系函数在极端值下的稳定性。
*   **遗迹生成逻辑**：Mock 事件数据，验证遗迹生成的概率与属性正确性。
*   **赛季规则引擎**：测试不同赛季特质对资源公式的修正是否生效。

### 5.2 集成测试
*   **贸易全流程**：模拟两个文明从发布订单到成交、物流运输、资源到账的全链路。
*   **遗迹争夺**：模拟多文明同时请求探索同一遗迹的并发处理与冲突判定。

### 5.3 压力测试
*   使用 Artillery 模拟高并发贸易请求，验证 Redis 订单簿的性能瓶颈。

---

## 6. 运行与部署

### 6.1 本地开发环境
```bash
# 安装依赖
npm install

# 启动数据库
docker-compose up -d db redis

# 运行迁移
npm run migration:run

# 启动开发服务
npm run start:dev
```

### 6.2 Docker 部署
项目根目录包含 `Dockerfile` 和 `docker-compose.yml`。
```yaml
# docker-compose.yml 核心配置示意
services:
  api:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DB_HOST=postgres
      - REDIS_HOST=redis
      - CURRENT_SEASON_ID=1
    depends_on:
      - postgres
      - redis
```

### 6.3 运维监控
*   **日志**：集成 Winston，输出 JSON 格式日志便于 ELK 采集。
*   **监控**：集成 Prometheus metrics，监控贸易吞吐量、事件处理延迟。