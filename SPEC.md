# SPEC.md: Cyber-Cosmos 第二轮进化规格文档

## 1. 项目概述

### 1.1 项目名称
**Cyber-Cosmos: Void Echoes (赛博宇宙：虚空回响)**

### 1.2 项目目标
在现有的事件系统、叙事引擎和外交联盟基础上，通过引入经济循环、历史沉淀和环境动态性，将宇宙模拟从"静态交互"推向"动态演化"。本轮核心目标是构建一个具有经济深度、历史厚度和环境多变性的持久化宇宙模拟器。

### 1.3 核心技术栈
*   **后端**: Node.js + TypeScript + NestJS (模块化架构)
*   **前端**: React + TypeScript + Three.js (3D 可视化) + ECharts (数据分析)
*   **数据库**: PostgreSQL (关系数据) + TimescaleDB (时序数据/天气历史) + Redis (缓存/实时行情)
*   **通信**: REST API (CRUD) + WebSocket (实时推送/天气预警)
*   **测试**: Jest (单元/集成) + Supertest (API)

---

## 2. 功能列表

基于现有架构分析，选择以下 4 个方向进行实施，以形成"经济-环境-历史-观测"的闭环：

### 2.1 【核心】星际贸易系统
*   **贸易路线机制**: 文明间可建立贸易协定，根据距离和外交关系计算运输成本。
*   **动态市场**: 引入供需模型，资源（矿石、能源、技术点）价格根据全服存量动态波动。
*   **商队事件**: 贸易路线上的商队有概率遭遇海盗或宇宙天气，需护航或承担损失。

### 2.2 【环境】宇宙天气预报
*   **全局天气系统**: 引入"资源风暴"（增产）、"黑暗波动"（视野受限）、"暗物质浪潮"（科技加速）。
*   **周期性预报**: 系统每周期生成天气预测，文明需提前调整生产和防御策略。
*   **环境影响**: 天气直接影响星区资源产出率、舰队移动速度和事件触发概率。

### 2.3 【历史】文明遗迹系统
*   **遗迹生成**: 重大历史事件（如文明毁灭、超新星爆发、史诗战役）在原址生成"遗迹"数据节点。
*   **探索与争夺**: 文明可派遣考察队探索遗迹，解锁失落科技或获得资源；遗迹周围可能引发新的外交冲突。
*   **历史回响**: 遗迹会周期性触发"回响事件"，重演历史片段，影响周边文明。

### 2.4 【观测】观测台增强
*   **宇宙演化时间线**: 可视化展示宇宙关键节点事件（文明兴衰、天气大变）。
*   **势力范围热力图**: 基于文明控制的星区坐标，渲染动态势力热力图。
*   **资源流动图**: 展示全宇宙贸易路线的流向和流量大小。

---

## 3. 目录结构

```text
cyber-cosmos/
├── apps/
│   ├── server/                # 后端服务
│   │   ├── src/
│   │   │   ├── modules/
│   │   │   │   ├── trade/     # 新增：贸易系统
│   │   │   │   │   ├── dto/
│   │   │   │   │   ├── trade.service.ts
│   │   │   │   │   └── market.controller.ts
│   │   │   │   ├── weather/   # 新增：宇宙天气
│   │   │   │   │   ├── weather.scheduler.ts
│   │   │   │   │   └── effects.service.ts
│   │   │   │   ├── relic/     # 新增：遗迹系统
│   │   │   │   │   ├── relic.generator.ts
│   │   │   │   │   └── exploration.service.ts
│   │   │   │   ├── timeline/  # 新增：时间线/观测
│   │   │   │   └── ...        # 现有模块
│   │   │   ├── entities/
│   │   │   └── app.module.ts
│   │   └── test/
│   └── client/                # 前端应用
│       ├── src/
│       │   ├── components/
│       │   │   ├── TradeView/ # 贸易界面
│       │   │   ├── WeatherHUD/# 天气预警组件
│       │   │   ├── RelicCard/ # 遗迹卡片
│       │   │   └── Observatory/ # 增强版观测台
│       │   ├── services/
│       │   └── hooks/
│       └── public/
├── packages/
│   └── shared-types/          # 共享类型定义
├── docker-compose.yml
├── SPEC.md
└── README.md
```

---

## 4. 技术方案

### 4.1 后端架构设计

#### 4.1.1 星际贸易系统
*   **数据模型**:
    *   `TradeRoute`: { id, sourceCivId, targetCivId, resourceType, amount, status, expiresAt }
    *   `MarketOrder`: { id, civId, type: 'BUY'|'SELL', resource, price, quantity }
*   **核心逻辑**:
    *   使用 Redis 存储实时行情 (`market:prices`)。
    *   贸易结算采用异步队列处理，防止阻塞主线程。
    *   引入 `Transaction` 锁机制，防止并发交易导致的数据不一致。

#### 4.1.2 宇宙天气系统
*   **数据模型**:
    *   `CosmicWeather`: { id, type: 'STORM'|'DARKNESS'|'MATTER', intensity, startTime, endTime, affectedSectors[] }
*   **核心逻辑**:
    *   使用 `@nestjs/schedule` 定时任务每小时生成新天气。
    *   天气效果通过 `EffectManager` 动态修改文明属性（如 `productionRate *= 1.5`）。
    *   WebSocket 广播天气预警：`event:weather_update`。

#### 4.1.3 文明遗迹系统
*   **数据模型**:
    *   `Relic`: { id, location, type, historicalEventId, lootTable, durability }
*   **核心逻辑**:
    *   监听现有 `EventSystem`，当事件严重等级 > 8 时，触发 `RelicGenerator`。
    *   遗迹探索逻辑类似随机数生成（RNG），结合文明科技等级计算成功率。

### 4.2 前端架构设计

#### 4.2.1 观测台增强
*   **时间线**: 使用 `vis-timeline` 或自定义 SVG 组件，拉取 `TimelineService` 数据。
*   **热力图**: 在 Three.js 场景中叠加 Canvas 图层，使用 `simpleheat` 库根据文明坐标渲染热力值。
*   **数据可视化**: 使用 ECharts 展示资源价格走势（K线图）和文明发展对比（雷达图）。

#### 4.2.2 实时交互
*   监听 WebSocket 频道：
    *   `trade_updates`: 实时刷新交易状态。
    *   `weather_alert`: 屏幕顶部显示天气预警横幅。
    *   `relic_discovered`: 弹出发现遗迹通知。

### 4.3 数据库设计

新增表结构概览：

```sql
-- 贸易路线
CREATE TABLE trade_routes (
    id UUID PRIMARY KEY,
    source_civ_id UUID REFERENCES civilizations(id),
    target_civ_id UUID REFERENCES civilizations(id),
    resource_type VARCHAR(50),
    rate_per_tick DECIMAL(10, 2),
    status VARCHAR(20), -- ACTIVE, SUSPENDED, ENDED
    created_at TIMESTAMP
);

-- 宇宙天气历史 (使用 TimescaleDB 扩展)
CREATE TABLE weather_history (
    time TIMESTAMPTZ NOT NULL,
    weather_type VARCHAR(50),
    intensity DECIMAL(3, 2),
    affected_sectors JSONB
);
SELECT create_hypertable('weather_history', 'time');

-- 遗迹
CREATE TABLE relics (
    id UUID PRIMARY KEY,
    name VARCHAR(100),
    description TEXT,
    location_x INT,
    location_y INT,
    source_event_id UUID,
    bonus_data JSONB,
    expires_at TIMESTAMP
);
```

### 4.4 接口设计

| 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| POST | `/api/trade/routes` | 建立新贸易路线 |
| GET | `/api/trade/market` | 获取当前市场行情 |
| GET | `/api/weather/forecast` | 获取未来 3 个周期的天气预报 |
| GET | `/api/relics` | 获取当前可见的遗迹列表 |
| POST | `/api/relics/:id/explore` | 派遣舰队探索遗迹 |
| GET | `/api/observatory/timeline` | 获取演化时间线数据 |
| GET | `/api/observatory/heatmap` | 获取势力范围热力数据 |

---

## 5. 测试方案

### 5.1 单元测试
*   **贸易逻辑**: 测试供需算法，确保价格波动符合预期（需求增 -> 价格涨）。
*   **天气效果**: 验证不同天气类型对资源产出的修正系数正确性。
*   **遗迹生成**: Mock 重大事件，验证遗迹是否正确生成及坐标是否正确。

### 5.2 集成测试
*   **贸易流程**: 模拟两个文明建立联盟 -> 开通路线 -> 资源扣除与增加 -> 天气影响路线中断的全流程。
*   **WebSocket 推送**: 验证天气变化时，客户端是否能收到广播消息。

### 5.3 压力测试
*   使用 Artillery 模拟 1000+ 并发贸易请求，验证 Redis 缓存击穿保护和数据库事务死锁处理。

---

## 6. 运行与部署

### 6.1 环境要求
*   Node.js >= 18
*   Docker & Docker Compose
*   PostgreSQL 14 + TimescaleDB 扩展

### 6.2 本地开发启动
```bash
# 1. 安装依赖
npm install

# 2. 启动基础服务
docker-compose up -d postgres redis

# 3. 运行数据库迁移
npm run migration:run

# 4. 启动后端开发服务
npm run start:dev

# 5. 启动前端
cd apps/client && npm run dev
```

### 6.3 生产部署
*   使用 Dockerfile 构建多阶段镜像。
*   后端服务水平扩展，通过 Nginx 负载均衡。
*   TimescaleDB 用于存储历史天气和贸易数据，便于后续大数据分析。
*   配置 Prometheus + Grafana 监控贸易吞吐量和天气事件延迟。