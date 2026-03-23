# 🤝 Contributing to Cyber Cosmos

感谢你感兴趣！以下是你参与贡献的方式。

---

## 贡献流程

### 1. Fork & Clone

```bash
# Fork 后克隆你的 Fork
git clone https://github.com/YOUR_USERNAME/cyber-cosmos.git
cd cyber-cosmos
```

### 2. 创建功能分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

### 3. 开发 & 提交

```bash
git add .
git commit -m "feat: add new feature"
```

提交信息格式：
- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更新
- `refactor:` 重构
- `test:` 测试相关

### 4. Push & 创建 Pull Request

```bash
git push origin feature/your-feature-name
```

然后在 GitHub 上创建 PR 到 `junyi0906/cyber-cosmos` 的 `main` 分支。

---

## PR 审查规则

### 自动检查（通过才受理）
- ✅ 代码格式正确
- ✅ 无明显语法错误
- ✅ 不破坏现有功能
- ✅ 有必要的测试（如涉及新功能）

### Merge 条件
- 至少通过自动检查
- 维护者（junyi0906）确认
- 无未解决的争议

### 争议处理
如果 PR 有争议，我会介入：
1. 分析争议焦点
2. 给出技术判断
3. 汇报给项目 owner，等待最终决定

---

## 当前优先方向

如果你想贡献，可以从这些方向入手：

### 🔴 高优先
- **LLM 接入** — 接入实际的 LLM API，让 Agent 能真正做决策
- **协议完善** — AI↔AI 通信协议的实现

### 🟡 中优先
- **Web 界面优化** — 更丰富的观测台 UI
- **子世界系统** — 创建和管理子世界的完整逻辑
- **测试覆盖** — `tests/` 目录下的单元测试

### 🟢 低优先
- **文档完善** — README 补充更多说明
- **Docker 支持** — 一键部署

---

## 项目架构

```
cyber-cosmos/
├── universe/          # 宇宙核心规则和状态
│   ├── rules.py       # 宇宙宪法（黑暗森林法则）
│   ├── state.py       # 宇宙状态管理
│   ├── events.py     # 事件系统
│   └── protocol.py   # AI↔AI 通信协议
├── node/              # AI Agent 节点
│   └── agent.py      # Agent 核心（性格+记忆+决策）
├── universe_server/   # 共享宇宙服务器
│   └── server.py      # FastAPI + WebSocket 服务器
└── web/              # Web 观测台
    └── templates/
        └── index.html # 实时事件流界面
```

---

## 问题 & Discussion

有想法先提 Issue，不用担心"这个想法够不够好"——先讨论再开发，避免白写。

---

*维护者规则：PR 由 AI 自动 Review，有争议时由项目 owner 最终决定。*
