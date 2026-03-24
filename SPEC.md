# SPEC.md: Cyber-Cosmos 第二轮自主进化

## 1. 项目概述

### 1.1 项目名称
**Cyber-Cosmos v2.0: Galactic Echoes (银河回响)**

### 1.2 项目目标
在现有的叙事引擎与外交系统基础上，通过引入**动态经济系统**、**环境不确定性**与**历史沉淀机制**，将宇宙模拟从“静态事件触发”升级为“复杂系统涌现”。目标是创造一个具有内生经济循环、历史厚度和可视化深度的赛博宇宙。

### 1.3 核心技术栈
*   **后端**: Node.js + TypeScript + NestJS (模块化架构)
*   **数据库**: PostgreSQL (关系数据) + Redis (实时行情/天气缓存) + TimescaleDB (时序数据)
*   **前端**: React + TypeScript + TailwindCSS + ECharts (数据可视化)
*   **通信**: REST API + WebSocket (实时推送贸易/天气事件)
*   **测试**: Jest + Supertest

---

## 2. 功能列表

经过架构分析，本轮进化选择以下 4 个核心方向实施：

### 2.1 【核心】星际贸易系统
*   **资源定义**：矿石、能源、技术点，每种资源具有基础价值与波动范围。
*   **动态定价引擎**：基于供需关系算法，文明资源过剩则价格下跌，稀缺则上涨。
*   **贸易路线**：文明间建立贸易协定后生成“贸易路线”实体，路线受“宇宙天气”影响效率。
*   **商队事件**：贸易路线上随机触发海盗袭击、走私获利等叙事事件。

### 2.2 【环境】宇宙天气预报
*   **天气类型**：
    *   *资源风暴*：特定区域矿石产出翻倍，但消耗能源增加。
    *   *黑暗波动*：降低传感器范围，外交视野受限。
    *   *暗物质浪潮*：科研速度提升，但可能引发文明变异。
*   **影响机制**：天气作为全局/区域 Modifier，实时影响贸易效率、资源产出和事件触发概率。
*   **预警系统**：通过 WebSocket 向所有客户端推送天气预警和实时状态。

### 2.3 【历史】文明遗迹系统
*   **遗迹生成**：监听重大事件（如“文明毁灭”、“超新星爆发”、“科技突破”），自动生成遗迹实体。
*   **遗迹属性**：包含历史描述、遗留资源、可研究科技碎片。
*   **交互机制**：文明可派遣舰队“探索”、“争夺”或“研究”遗迹，触发专属叙事链。

### 2.4 【观测】观测台增强
*   **宇宙演化时间线**：基于 TimescaleDB 记录关键指标，前端展示可缩放的时间轴。
*   **文明发展对比图**：雷达图展示各文明的军事、经济、科技、文化维度对比。
*   **势力范围热力图**：在 2D/3D 星图上根据文明影响力渲染动态热力图。

---

## 3. 目录结构

```text
~/cyber-cosmos/
├── server/                      # 后端服务
│   ├── src/
│   │   ├── modules/
│   │   │   ├── trade/           # 新增：贸易模块
│   │   │   │   ├── trade.service.ts
│   │   │   │   ├── market.engine.ts    # 动态定价引擎
│   │   │   │   └── trade.route.entity.ts
│   │   │   ├── weather/         # 新增：天气模块
│   │   │   │   ├── weather.service.ts
│   │   │   │   └── weather.effects.ts
│   │   │   ├── relics/          # 新增：遗迹模块
│   │   │   │   ├── relic.service.ts
│   │   │   │   └── relic.generator.ts
│   │   │   ├── timeline/        # 新增：时序数据模块
│   │   │   └── civilization/    # 现有：文明模块 (需更新)
│   │   ├── events/              # 事件总线
│   │   └── main.ts
│   └── test/
├── client/                      # 前端应用
│   ├── src/
│   │   ├── components/
│   │   │   ├── TradeDashboard/  # 贸易看板
│   │   │   ├── WeatherOverlay/  # 天气特效层
│   │   │   ├── RelicViewer/     # 遗迹详情
│   │   │   └── Observatory/     # 增强版观测台
│   │   ├── hooks/
│   │   └── App.tsx
├── database/                    # 数据库迁移脚本
│   └── migrations/
│       └── v2.0_add_trade_relics.sql
├── docs/
│   └── API.md
└── SPEC.md
```

---

## 4. 技术方案

### 4.1 后端架构
采用 NestJS 模块化设计，利用其依赖注入和生命周期钩子。

*   **贸易引擎**:
    *   使用 Redis 存储实时行情 (`market:prices`)。
    *   实现简单的线性回归模型：`Price = BasePrice * (1 + DemandFactor - SupplyFactor)`。
    *   贸易路线使用有向图结构存储，节点为文明，边为路线。

*   **天气系统**:
    *   基于 Cron Job 每 30 分钟进行一次全局天气结算。
    *   使用策略模式 处理不同天气对游戏逻辑的影响。

*   **遗迹生成**:
    *   监听 `GameEvent` 总线。
    *   当事件严重程度 > 阈值时，触发 `RelicGenerator`，将事件元数据转化为遗迹实体。

### 4.2 前端架构
*   **状态管理**: 使用 Zustand 管理全局状态（当前天气、选中文明）。
*   **可视化**:
    *   引入 ECharts 实现雷达图和时间轴。
    *   使用 HTML5 Canvas 绘制势力范围热力图，叠加在星图之上。
*   **实时通信**: 封装 WebSocket Hook，监听 `weather_update` 和 `trade_alert` 频道。

### 4.3 数据库设计
新增以下核心表：

1.  **trade_routes**
    *   `id`, `source_civ_id`, `target_civ_id`, `resource_type`, `volume`, `status`, `created_at`.
2.  **market_history** (TimescaleDB 超级表)
    *   `time`, `resource_type`, `price`, `volume`.
3.  **relics**
    *   `id`, `name`, `description`, `location_x`, `location_y`, `type`, `bonus_data` (JSONB), `discovered_by`.
4.  **cosmic_weather**
    *   `id`, `type`, `intensity`, `start_time`, `end_time`, `affected_regions` (JSONB).

### 4.4 接口设计
*   `GET /api/market/prices`: 获取当前全市场行情。
*   `POST /api/trade/routes`: 建立新贸易路线。
*   `GET /api/weather/current`: 获取当前宇宙天气。
*   `GET /api/relics`: 获取已发现的遗迹列表。
*   `POST /api/relics/:id/explore`: 探索遗迹。
*   `GET /api/timeline?range=7d`: 获取演化时间线数据。

---

## 5. 测试方案

### 5.1 单元测试
*   **定价算法测试**: 模拟极端供需情况，验证价格波动在合理区间。
*   **天气效果测试**: 验证不同天气对资源产出的 Modifier 计算是否正确。
*   **遗迹生成逻辑**: Mock 重大事件，验证遗迹是否正确生成并包含正确的 Lore。

### 5.2 集成测试
*   **贸易全流程**: 文明 A 发起贸易 -> 扣除资源 -> 文明 B 增加资源 -> 市场价格波动。
*   **天气影响链**: 天气变更 -> WebSocket 推送 -> 前端状态更新 -> 贸易效率计算变更。

### 5.3 性能测试
*   使用 k6 模拟 1000 个文明同时请求市场数据，验证 Redis 缓存命中率及响应时间 (目标 < 100ms)。

---

## 6. 运行与部署

### 6.1 环境要求
*   Node.js >= 18
*   Docker & Docker Compose
*   PostgreSQL 15 + TimescaleDB 扩展

### 6.2 本地开发启动
```bash
# 1. 启动基础设施
docker-compose up -d db redis

# 2. 安装依赖
npm install

# 3. 运行数据库迁移
npm run db:migrate

# 4. 启动后端服务 (热重载)
npm run dev:server

# 5. 启动前端服务
npm run dev:client
```

### 6.3 生产部署
*   使用 GitHub Actions 构建 CI/CD 流水线。
*   后端打包为 Docker 镜像，部署至 K8s 集群。
*   前端构建静态资源，上传至 CDN/OSS。
*   配置 Nginx 反向代理，开启 WebSocket 长连接支持。

### 6.4 监控与日志
*   集成 Prometheus + Grafana 监控贸易交易量和 API 延迟。
*   使用 ELK 栈收集叙事引擎生成的日志，用于后续分析叙事逻辑的合理性。