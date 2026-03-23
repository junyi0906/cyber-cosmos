# 🛠️ 维护者手册

## 维护规则

### PR Review 流程

1. **检查 PR** — 每次检查自动执行以下步骤
2. **自动检查** — 代码格式、测试、是否破坏现有功能
3. **给出判断** — Accept / Request Changes / Need Discussion
4. **争议上报** — 有争议的 PR 汇报给项目 owner
5. **Merge** — 需要 owner 手动确认，或 owner 授权后执行

### Merge 标准

| 条件 | 说明 |
|------|------|
| 格式正确 | 代码符合 PEP8 或对应语言规范 |
| 有测试 | 新功能有对应的单元测试 |
| 不破坏现有功能 | 现有测试全部通过 |
| 无严重警告 | linter / type checker 无 ERROR |

### 需要上报的情况

遇到以下情况，立即汇报给 owner：
- PR 涉及 License 变更
- PR 涉及安全相关改动
- 贡献者与维护者意见严重不一致
- 大量文件或核心模块改动
- 多人争议同一个 PR

### 可自行处理的情况

以下情况可直接 Merge 或 Close：
- 明显 spam / 无意义改动 → 直接 Close
- typo 修复 / 文档更新 → 可直接 Merge
- 测试通过、无争议的 bugfix → 可直接 Merge

---

## 当前状态

- **Repo**: junyi0906/cyber-cosmos
- **Owner**: junyi0906
- **维护者**: 阿爪（AI Agent）
- **最后检查**: 2026-03-23

---

## 下一步计划

- [ ] 接入 LLM（让 Agent 真正能自主决策）
- [ ] 完善 AI↔AI 通信协议实现
- [ ] 补充测试覆盖
- [ ] 添加 Docker 支持
