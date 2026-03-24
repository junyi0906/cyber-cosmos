# SPEC.md: Cyber-Cosmos 第二轮进化规格文档

## 1. 项目概述

### 1.1 项目名称
**Cyber-Cosmos: Stellar Echoes (星际回响)**

### 1.2 项目目标
在现有的叙事引擎与外交系统基础上，通过引入经济循环（贸易）、历史沉淀（遗迹）与环境不确定性（天气），将宇宙模拟从"静态叙事"升级为"动态生态"。本次迭代旨在增强文明间的互动深度与观测台的数据可视化表现力。

### 1.3 核心技术栈
*   **后端**: Node.js + TypeScript + NestJS (模块化架构)
*   **数据库**: PostgreSQL (关系型数据) + Redis (缓存与实时队列)
*   **前端**: React + TypeScript + Three.js (3D可视化) + ECharts (图表)
*   **通信**: REST API + WebSocket (实时推送)
*   **测试**: Jest (单元/集成测试) + Supertest

---

## 2. 功能列表

本次迭代选定以下四个核心方向：

### 2.1 【星际贸易系统】
*   **资源定义**: 矿石、能源、技术点三种基础资源。
*   **贸易路线**: 文明间可建立贸易协定，路线距离与双方科技水平决定运输效率与损耗。
*   **动态市场**: 宇宙全局资源供需影响兑换汇率，每周期刷新市场状态。
*   **商船事件**: 贸易过程中有概率触发"海盗劫掠"或"走私暴利"随机事件。

### 2.2 【文明遗迹系统】
*   **遗迹生成**: 当发生"恒星坍缩"、"文明灭绝"或"神级科技突破"等重大事件时，在坐标点生成遗迹。
*   **交互机制**:
    *   **发现**: 探索队需消耗能源进行扫描。
    *   **争夺**: 遗迹所在星系可能引发外交争端或战争。
    *   **研究**: 占领遗迹可解锁远古科技蓝图或获得大量文化值。
*   **数据持久化**: 遗迹记录关联至历史事件ID，形成可追溯的历史档案。

### 2.3 【宇宙天气预报】
*   **天气类型**:
    *   *资源风暴*: 特定区域矿石产量翻倍，但增加舰船损耗。
    *   *黑暗波动*: 降低该区域视野范围，适合隐蔽军事行动。
    *   *暗物质浪潮*: 所有科技研究速度提升，但能源消耗加剧。
*   **影响范围**: 天气以"扇区"为单位播报，通过 WebSocket 实时推送给相关玩家。
*   **预警机制**: 观测台提前 3 个周期预报即将到来的天气。

### 2.4 【观测台增强】
*   **宇宙演化时间线**: 横轴为时间（Tick），纵轴为关键指标（总人口、科技等级），支持回放历史进程。
*   **文明发展对比图**: 雷达图展示各文明的军事、经济、科技、文化维度对比。
*   **势力范围热力图**: 在 3D 星图上叠加半透明热力层，直观展示各文明控制疆域的变化。

---

## 3. 目录结构

```text
cyber-cosmos/
├── src/
│   ├── modules/               # 业务模块
│   │   ├── trade/             # 新增：星际贸易模块
│   │   │   ├── dto/
│   │   │   ├── trade.service.ts
│   │   │   ├── trade.controller.ts
│   │   │   └── trade.gateway.ts (WebSocket)
│   │   ├── relics/            # 新增：遗迹系统模块
│   │   │   ├── relics.service.ts
│   │   │   └── relics.listener.ts (监听历史事件)
│   │   ├── weather/           # 新增：宇宙天气模块
│   │   │   ├── weather.scheduler.ts (定时任务)
│   │   │   └── effects.service.ts (效果计算)
│   │   ├── observatory/       # 更新：观测台模块
│   │   │   ├── timeline.service.ts
│   │   │   └── heatmap.service.ts
│   │   ├── civilization/      # 已有：文明核心
│   │   └── diplomacy/         # 已有：外交系统
│   ├── common/                # 公共组件
│   │   ├── events/            # 事件总线
│   │   └── utils/
│   └── database/              # 数据库配置
│       ├── migrations/
│       └── seeds/
├── client/                    # 前端项目
│   ├── src/
│   │   ├── components/
│   │   │   ├── TradePanel/    # 贸易界面
│   │   │   ├── WeatherHUD/    # 天气预警组件
│   │   │   └── Charts/        # 图表组件
│   │   └── three/             # Three.js 场景逻辑
├── tests/                     # 测试套件
│   ├── e2e/
│   └── unit/
├── SPEC.md
└── docker-compose.yml
```

---

## 4. 技术方案

### 4.1 后端架构
采用 **NestJS** 模块化架构，利用其依赖注入和模块解耦特性。

*   **贸易引擎**: 使用"观察者模式"监听贸易完成事件，触发资源结算。利用 Redis 锁处理并发交易请求，防止超卖。
*   **遗迹生成**: 监听 `GameEvent` 总线。当事件严重等级 > 8 时，触发 `RelicGenerator` 生成实体。
*   **天气系统**: 基于 `Cron` 任务调度器，每 24 小时（游戏内时间）触发一次全局天气计算，结果存入 Redis 并广播。

### 4.2 数据库设计

新增表结构如下：

**Table: trade_routes**
| 字段 | 类型 | 描述 |
| :--- | :--- | :--- |
| id | UUID | 路由唯一标识 |
| source_civ_id | UUID | 发起方文明ID |
| target_civ_id | UUID | 接收方文明ID |
| resource_type | ENUM | (ORE, ENERGY, TECH) |
| status | ENUM | (ACTIVE, PAUSED, DESTROYED) |

**Table: relics**
| 字段 | 类型 | 描述 |
| :--- | :--- | :--- |
| id | UUID | 遗迹ID |
| location_x | float | 坐标 X |
| location_y | float | 坐标 Y |
| origin_event_id | UUID | 关联的历史事件 |
| bonus_type | VARCHAR | 加成类型 |

**Table: cosmic_weather**
| 字段 | 类型 | 描述 |
| :--- | :--- | :--- |
| id | UUID | 天气ID |
| sector_id | UUID | 影响扇区 |
| weather_type | ENUM | (STORM, DARKNESS, DARK_MATTER) |
| start_tick | int | 开始时间 |
| end_tick | int | 结束时间 |

### 4.3 前端架构

*   **状态管理**: 使用 Redux Toolkit 管理全局状态（如当前天气、贸易订单）。
*   **3D 渲染**: Three.js 场景中新增 `RelicMesh` 对象，使用发光材质高亮显示遗迹。
*   **数据可视化**:
    *   使用 ECharts 实现时间线视图，支持缩放和拖拽。
    *   使用 Three.js Shader 实现势力范围热力图，根据文明颜色动态渲染。

### 4.4 接口设计

*   `POST /api/trade/create`: 创建贸易订单
*   `GET /api/relics/nearby`: 获取附近坐标的遗迹列表
*   `POST /api/relics/{id}/excavate`: 派遣舰队挖掘遗迹
*   `GET /api/weather/forecast`: 获取未来 N 个周期的天气预报
*   `WS /observatory`: WebSocket 连接，实时推送天气变化、贸易完成通知

---

## 5. 测试方案

### 5.1 单元测试
*   **贸易逻辑**: 测试资源扣除与增加的原子性，测试距离损耗计算公式。
*   **遗迹生成**: Mock 一个高等级事件，验证遗迹是否正确生成及坐标是否在合理范围内。
*   **天气效果**: 验证不同天气对文明属性修正系数是否正确。

### 5.2 集成测试
*   **贸易流程**: 模拟两个文明建立连接 -> 发起贸易 -> 遭遇海盗事件 -> 处理结果。
*   **数据一致性**: 验证遗迹被挖掘后，数据库状态变更与前端查询结果一致。

### 5.3 性能测试
*   使用 Artillery 模拟 1000 个并发贸易请求，检测 Redis 锁机制是否有效防止资源竞争。

---

## 6. 运行/部署方式

### 6.1 开发环境
```bash
# 安装依赖
npm install

# 启动数据库
docker-compose up -d db redis

# 运行迁移
npm run migration:run

# 启动后端服务 (热重载)
npm run start:dev

# 启动前端
cd client && npm run dev
```

### 6.2 生产部署
采用 Docker 容器化部署。

```yaml
# docker-compose.yml 核心配置片段
services:
  api:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DB_HOST=postgres
      - REDIS_HOST=redis
  frontend:
    build: ./client
    ports:
      - "80:80"
  postgres:
    image: postgres:14
    volumes:
      - pgdata:/var/lib/postgresql/data
  redis:
    image: redis:alpine
```

### 6.3 监控与日志
*   使用 Winston 进行日志记录，输出 JSON 格式便于 ELK 采集。
*   关键业务（贸易额、遗迹发现数）通过 Prometheus 客户端暴露 Metrics 接口。