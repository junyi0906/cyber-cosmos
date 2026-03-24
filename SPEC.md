# SPEC.md - Cyber Cosmos 第二轮进化规格书

## 1. 项目概述

### 1.1 项目名称
**Cyber Cosmos v2.0: Echoes of Eternity (永恒回响)**

### 1.2 项目目标
在现有的叙事引擎与外交系统基础上，通过引入**经济流动**、**历史沉淀**与**宏观周期**机制，将宇宙模拟从"静态事件驱动"升级为"动态生态演化"。重点实现文明的长期经济博弈、历史痕迹的实体化以及宇宙宏观节奏的周期性变化。

### 1.3 核心技术栈
- **后端框架**: NestJS (TypeScript) - 模块化架构，依赖注入
- **前端框架**: Vue 3 + TypeScript + Pinia (状态管理)
- **可视化引擎**: PixiJS (星际地图) + ECharts (数据图表)
- **数据库**: PostgreSQL (关系数据) + Redis (实时状态/缓存)
- **通信协议**: REST API (CRUD) + WebSocket (实时推演广播)
- **测试框架**: Jest (单元/集成测试) + Supertest (API测试)

---

## 2. 功能列表

经过架构分析，本次进化选取以下四个核心方向实施：

### 2.1 【核心经济】星际贸易系统
*目标：建立文明间的资源流动机制，使资源不再仅是数值，而是可博弈的资产。*

- **F-1.1 贸易市场**: 
  - 文明可挂单出售/购买资源（矿石、能源、技术点）。
  - 支持限价单和市价单。
- **F-1.2 贸易路线**:
  - 基于星际距离计算物流时间与损耗。
  - 贸易路线可能遭遇"星际海盗"（随机事件）或被敌对文明截断。
- **F-1.3 经济制裁**:
  - 外交状态（战争/敌对）自动阻断贸易路线。
  - 联盟内部享受关税减免。

### 2.2 【历史沉淀】文明遗迹系统
*目标：将叙事引擎产生的"重大事件"实体化，影响后续地缘政治。*

- **F-2.1 遗迹生成**:
  - 监听叙事引擎的 `MajorEvent`（如：超新星爆发、泰坦陨落、星际大战）。
  - 在事件坐标生成"遗迹"实体，包含独特属性（如：高能辐射、古代科技残骸）。
- **F-2.2 遗迹探索与争夺**:
  - 文明可派遣舰队进行探索（消耗时间与燃料）。
  - 遗迹可能提供一次性科技加成、永久Buff或灾难性陷阱。
  - 多文明同时探索触发"争夺战"。

### 2.3 【宏观节奏】宇宙赛季机制
*目标：增加重玩价值与周期性目标，解决后期模拟枯燥问题。*

- **F-3.1 赛季周期**:
  - 每个赛季持续固定周期（如：模拟时间100年）。
  - 赛季末进行结算，评选"霸主"、"首富"、"科技巅峰"。
- **F-3.2 赛季规则变异**:
  - 每赛季随机生成"宇宙法则"（如：资源枯竭期-矿石产出-50%；狂暴星系-事件频率+200%）。
- **F-3.3 赛季传承**:
  - 赛季结算时，文明可保留部分"遗产"（如：核心科技蓝图）带入下一赛季（Roguelike元素）。

### 2.4 【数据感知】观测台增强
*目标：将复杂的模拟数据可视化，提供上帝视角的分析工具。*

- **F-4.1 宇宙演化时间线**:
  - 可拖动的时间轴，回放历史重大事件与疆域变迁。
- **F-4.2 势力范围热力图**:
  - 在星图上叠加半透明图层，实时显示各文明的影响力范围与军事密度。
- **F-4.3 文明发展雷达图**:
  - 多维度对比（军事、经济、科技、人口、疆域）不同文明的综合国力。

---

## 3. 目录结构

采用 Monorepo 结构，便于前后端代码复用与统一部署。

```text
cyber-cosmos/
├── apps/
│   ├── server/                # NestJS 后端
│   │   ├── src/
│   │   │   ├── modules/
│   │   │   │   ├── trade/     # 新增：贸易系统
│   │   │   │   ├── relic/     # 新增：遗迹系统
│   │   │   │   ├── season/    # 新增：赛季系统
│   │   │   │   ├── timeline/  # 新增：时间线服务
│   │   │   │   ├── event/     # 现有：事件系统
│   │   │   │   ├── narrative/ # 现有：叙事引擎
│   │   │   │   └── diplomacy/ # 现有：外交系统
│   │   │   ├── entities/      # TypeORM 实体
│   │   │   ├── common/        # 公共模块
│   │   │   └── main.ts
│   │   └── test/
│   ├── client/                # Vue 3 前端
│   │   ├── src/
│   │   │   ├── views/
│   │   │   │   ├── GalaxyMap/ # 星图组件（集成热力图）
│   │   │   │   ├── TradeHub/  # 新增：贸易中心页面
│   │   │   │   ├── RelicLab/  # 新增：遗迹探索页面
│   │   │   │   └── Observatory/ # 增强：观测台页面
│   │   │   ├── components/
│   │   │   ├── stores/        # Pinia 状态管理
│   │   │   └── utils/
├── packages/                  # 共享包
│   └── types/                 # 共享类型定义
├── docker-compose.yml
├── SPEC.md
└── README.md
```

---

## 4. 技术方案

### 4.1 后端架构

采用**模块化单体**架构，利用 NestJS 的 Module 机制解耦。

#### 4.1.1 贸易系统
- **设计模式**: 发布订阅模式。
- **核心逻辑**:
  - `TradeService`: 处理订单撮合逻辑。
  - `LogisticsService`: 计算路线耗时，利用 `setTimeout` 或 BullMQ 队列延迟任务处理货物到达。
  - **数据库设计**:
    - `TradeOrder`: 订单表。
    - `TradeRoute`: 路线表。

#### 4.1.2 遗迹系统
- **事件驱动**: 监听 `NarrativeEngine` 抛出的 `narrative.major_event` 事件。
- **状态机**: 遗迹状态流转 `未发现 -> 探索中 -> 已占领 -> 枯竭`。
- **数据库设计**:
  - `Relic`: 遗迹实体。

#### 4.1.3 赛季系统
- **全局中间件**: 在请求层注入当前赛季上下文，所有资源计算需乘以赛季修正系数。
- **数据隔离**: 利用 PostgreSQL Schema 或 `season_id` 字段进行数据软隔离。

### 4.2 前端架构

#### 4.2.1 星图可视化
- **技术**: PixiJS。
- **实现**: 
  - 底层渲染星系背景与恒星。
  - 中层渲染文明疆域（使用 `Graphics` 绘制多边形或热力图 Shader）。
  - 顶层渲染遗迹图标、贸易路线动画（流动粒子效果）。

#### 4.2.2 数据图表
- **技术**: ECharts。
- **实现**: 
  - 封装 `<RadarChart />` 组件用于文明对比。
  - 封装 `<TimelineSlider />` 组件控制历史回放。

### 4.3 数据库设计

新增关键表结构：

```sql
-- 贸易订单表
CREATE TABLE trade_orders (
  id UUID PRIMARY KEY,
  seller_id UUID REFERENCES civilizations(id),
  resource_type VARCHAR(50), -- 'ORE', 'ENERGY', 'TECH'
  quantity INT,
  price_per_unit INT,
  status VARCHAR(20), -- 'OPEN', 'FILLED', 'CANCELLED'
  created_at TIMESTAMP
);

-- 遗迹表
CREATE TABLE relics (
  id UUID PRIMARY KEY,
  name VARCHAR(100),
  type VARCHAR(50), -- 'BATTLEFIELD', 'SUPERNOVA'
  coordinate JSONB, -- {x, y}
  bonus JSONB, -- { "tech": 0.1 }
  status VARCHAR(20),
  linked_event_id UUID
);

-- 赛季表
CREATE TABLE seasons (
  id UUID PRIMARY KEY,
  season_number INT,
  rules_modifiers JSONB, -- { "ore_rate": 0.8 }
  started_at TIMESTAMP,
  ended_at TIMESTAMP
);
```

### 4.4 接口设计

| 模块 | 方法 | 路径 | 描述 |
| :--- | :--- | :--- | :--- |
| **贸易** | POST | `/api/trade/orders` | 创建贸易订单 |
| | GET | `/api/trade/market` | 获取当前市场行情 |
| **遗迹** | GET | `/api/relics` | 获取所有已发现遗迹列表 |
| | POST | `/api/relics/:id/explore` | 派遣舰队探索遗迹 |
| **赛季** | GET | `/api/seasons/current` | 获取当前赛季信息与规则 |
| | POST | `/api/seasons/settle` | (Admin) 触发赛季结算 |
| **观测台**| GET | `/api/observatory/timeline` | 获取历史事件时间轴数据 |
| | GET | `/api/observatory/heatmap` | 获取势力范围热力图数据 |

---

## 5. 测试方案

### 5.1 单元测试
- **贸易逻辑**: 测试订单撮合算法，确保价格优先、时间优先。
- **遗迹生成**: Mock 叙事事件，验证遗迹是否正确生成及属性计算。
- **赛季修正**: 验证资源产出公式在不同赛季规则下的计算正确性。

### 5.2 集成测试
- **贸易闭环**: 模拟两个文明进行交易，验证资源扣除、增加及物流延迟。
- **遗迹争夺**: 模拟两个文明同时探索遗迹，验证冲突解决逻辑。

### 5.3 E2E 测试
- 使用 Cypress 或 Playwright 模拟用户操作：
  1. 登录观测台。
  2. 查看热力图。
  3. 发起一笔贸易。
  4. 查看赛季倒计时。

---

## 6. 运行与部署

### 6.1 环境要求
- Node.js >= 18
- PostgreSQL >= 14
- Redis >= 6
- Docker & Docker Compose (推荐)

### 6.2 本地开发启动

```bash
# 1. 安装依赖
npm install

# 2. 启动基础服务
docker-compose up -d postgres redis

# 3. 运行数据库迁移
npm run migration:run

# 4. 启动后端服务 (开发模式)
npm run dev:server

# 5. 启动前端服务 (开发模式)
npm run dev:client
```

### 6.3 生产部署

采用 Docker 容器