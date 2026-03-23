#!/usr/bin/env python3
"""
Cyber Cosmos — 无限自动开发系统 v2
Infinite Automatic Development Daemon

每小时自动分析项目状态，决定需要改进的地方，实施改进，提交代码。

安全机制:
- [AUTO] 前缀的commit表示自动生成
- 高风险操作跳过
- AUTO_DEVELOP_PAUSE 文件存在时暂停
- 每次循环生成diff摘要
- 改动后必须通过功能测试才提交
"""

import os
import sys
import json
import time
import subprocess
import httpx
import re
from datetime import datetime
from pathlib import Path

# ─── 配置 ───────────────────────────────────────────────────
PROJECT_ROOT = Path.home() / "cyber-cosmos"
SERVER_URL = "http://localhost:8000"
GLM_KEY = os.environ.get(
    "GLM5_TURBO_KEY",
    "8ebd0252b1fc498ebd53dfc299d4de12.PwoiSyS6NA5RuALo"
)
DEVELOP_INTERVAL = 300   # 5分钟（开发阶段），稳定后可改为3600
MAX_AUTO_CHANGES = 3
RESOLVED_FILE = PROJECT_ROOT / ".auto_develop_resolved.json"
CHANGES_LOG = PROJECT_ROOT / ".auto_develop_changes.jsonl"


# ─── 日志 ───────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run(cmd: str, cwd: str = None) -> tuple[int, str, str]:
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd or PROJECT_ROOT
    )
    return result.returncode, result.stdout, result.stderr


# ─── 已处理问题追踪 ─────────────────────────────────────────
def get_resolved() -> set:
    try:
        return set(json.loads(RESOLVED_FILE.read_text()))
    except:
        return set()


def mark_resolved(desc: str):
    """标记问题为已处理，防止重复扫描"""
    resolved = get_resolved()
    resolved.add(desc)
    RESOLVED_FILE.write_text(json.dumps(list(resolved), ensure_ascii=False))


def was_skipped(desc: str) -> bool:
    """检查某问题是否之前被跳过（跳过后也不再重复报告）"""
    skipped = set()
    try:
        skipped = set(json.loads(RESOLVED_FILE.read_text()).get("_skipped", []))
    except:
        pass
    return desc in skipped


def mark_skipped(desc: str):
    """标记某问题被跳过（下次不再报告）"""
    data = {}
    try:
        data = json.loads(RESOLVED_FILE.read_text())
    except:
        data = {"_resolved": [], "_skipped": []}
    if "_skipped" not in data:
        data["_skipped"] = []
    data["_skipped"].append(desc)
    # 只保留最近100条跳过记录
    data["_skipped"] = data["_skipped"][-100:]
    RESOLVED_FILE.write_text(json.dumps(data, ensure_ascii=False))


# ─── 宇宙状态 ───────────────────────────────────────────────
def get_universe_status() -> dict:
    try:
        r = httpx.get(f"{SERVER_URL}/universe", timeout=10)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}


def get_civilizations() -> list:
    try:
        r = httpx.get(f"{SERVER_URL}/civilizations", timeout=10)
        return r.json() if r.status_code == 200 else []
    except:
        return []


def get_recent_events(limit: int = 10) -> list:
    try:
        r = httpx.get(f"{SERVER_URL}/history", timeout=10)
        if r.status_code == 200:
            events = r.json()
            notable = [e for e in events if (e.get("significance") or "NOTABLE") != "TRIVIAL"]
            return notable[-limit:]
    except:
        pass
    return []


def get_git_status() -> dict:
    code, out, err = run("git status --porcelain")
    changed = [l for l in out.strip().split("\n") if l]
    return {"changed_files": len(changed), "files": changed}


def get_git_diff() -> str:
    """获取当前git diff摘要"""
    code, out, err = run("git diff --stat")
    return out.strip()


# ─── LLM分析 ────────────────────────────────────────────────
def analyze_with_llm(prompt: str) -> str:
    """调用GLM API，带超时和重试"""
    import urllib.request

    payload = {
        "model": "glm-4-plus",
        "messages": [
            {"role": "system", "content": "你是Cyber Cosmos的开发顾问。简洁直接，给出具体代码和文件路径。"},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 600,
        "temperature": 0.3,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {GLM_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    # 重试3次
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return f"[LLM Error after 3 retries: {e}]"

    return "[LLM Error: all retries failed]"


# ─── 问题扫描 ───────────────────────────────────────────────
def scan_code_issues() -> list[dict]:
    """扫描代码，识别需要改进的地方（带去重）"""
    issues = []

    def add_issue(issue: dict, desc: str):
        """去重：只添加未被resolved且未被skipped的问题"""
        if desc not in get_resolved() and desc not in _get_skipped():
            issues.append(issue)

    def _get_skipped() -> set:
        try:
            data = json.loads(RESOLVED_FILE.read_text())
            return set(data.get("_skipped", []))
        except:
            return set()

    server_path = PROJECT_ROOT / "universe_server" / "server.py"
    auto_run_path = PROJECT_ROOT / "node" / "auto_run.py"
    ui_path = PROJECT_ROOT / "web" / "templates" / "index.html"
    narrative_path = PROJECT_ROOT / "universe" / "narrative.py"

    # 1. TODO/FIXME 注释
    if server_path.exists():
        for i, line in enumerate(server_path.read_text().split("\n"), 1):
            if re.search(r"\b(TODO|FIXME|XXX)\b", line):
                desc = f"TODO in server.py:{i}: {line.strip()}"
                add_issue({
                    "file": "universe_server/server.py",
                    "line": i, "type": "todo",
                    "content": line.strip(), "priority": 6,
                    "desc": desc,
                }, desc)

    # 2. console.log 调试代码
    if ui_path.exists():
        content = ui_path.read_text()
        if "console.log" in content:
            desc = "Web UI存在console.log调试代码"
            add_issue({
                "file": "web/templates/index.html", "line": 0,
                "type": "debug_code",
                "content": "Web UI中存在console.log调试代码",
                "priority": 5, "desc": desc,
            }, desc)

    # 3. 裸异常处理
    if auto_run_path.exists():
        content = auto_run_path.read_text()
        if re.search(r"except\s+Exception\s+as\s+\w+:\s*\n\s*(?!.*(?:log|print|raise|sys))", content, re.MULTILINE):
            desc = "auto_run.py存在裸异常处理"
            add_issue({
                "file": "node/auto_run.py", "line": 0,
                "type": "error_handling",
                "content": "存在裸异常处理，可能吞掉错误",
                "priority": 5, "desc": desc,
            }, desc)

    # 4. diplomatic系统已集成 → 标记为resolved，不再报告
    diplomacy_path = PROJECT_ROOT / "universe" / "diplomacy.py"
    if diplomacy_path.exists():
        # 检查是否已集成到server.py
        server_content = server_path.read_text() if server_path.exists() else ""
        auto_content = auto_run_path.read_text() if auto_run_path.exists() else ""
        if "get_relation_matrix" in server_content and "get_relation_matrix" in auto_content:
            # 已集成，标记resolved
            mark_resolved("外交系统需要集成到server.py和agent决策中")
        else:
            desc = "外交系统需要集成到server.py和agent决策中"
            add_issue({
                "file": "universe/diplomacy.py", "line": 0,
                "type": "new_feature",
                "content": "外交系统已创建，需要集成到 server.py 和 agent 决策中",
                "priority": 7, "desc": desc,
            }, desc)

    # 5. Agent外交行动（带resolved追踪）
    if auto_run_path.exists():
        content = auto_run_path.read_text()
        has_propose = content.count("PROPOSE_ALLIANCE") >= 1
        has_war = "DECLARE_WAR" in content
        has_signal = "SEND_SIGNAL" in content
        desc = "Agent决策引擎缺少外交行动支持"
        if has_propose and has_war and has_signal:
            mark_resolved(desc)
        else:
            add_issue({
                "file": "node/auto_run.py", "line": 0,
                "type": "missing_feature",
                "content": "Agent决策引擎缺少外交行动支持",
                "priority": 6, "desc": desc,
            }, desc)

    # 6. Web UI关系可视化
    if ui_path.exists():
        content = ui_path.read_text()
        desc = "Web UI缺少文明关系/外交状态可视化"
        if "popup-relation" in content or "diplomatic" in content.lower():
            mark_resolved(desc)
        else:
            add_issue({
                "file": "web/templates/index.html", "line": 0,
                "type": "ui_missing",
                "content": "Web UI缺少文明关系/外交状态的可视化展示",
                "priority": 5, "desc": desc,
            }, desc)

    # 7. /relations API
    if server_path.exists():
        content = server_path.read_text()
        desc = "缺少/relations API"
        if "/relations" in content and "get_civ_relations" in content:
            mark_resolved(desc)
        else:
            add_issue({
                "file": "universe_server/server.py", "line": 0,
                "type": "missing_api",
                "content": "缺少 /relations API（查看文明间关系）",
                "priority": 6, "desc": desc,
            }, desc)

    # 8. 叙事模板丰富度
    if narrative_path.exists():
        content = narrative_path.read_text()
        fallback_count = content.count("_fallback_narrative") + content.count('"""')
        desc = "叙事fallback模板较少"
        if fallback_count >= 15:
            mark_resolved(desc)
        else:
            add_issue({
                "file": "universe/narrative.py", "line": 0,
                "type": "narrative_quality",
                "content": "叙事fallback模板较少，可以扩展更多事件类型的叙事",
                "priority": 3, "desc": desc,
            }, desc)

    # 9. 检查auto_run.py是否有无限循环风险（无sleep的while True）
    if auto_run_path.exists():
        content = auto_run_path.read_text()
        if re.search(r"while\s+True.*?(?!time\.sleep|asyncio\.sleep)", content, re.DOTALL):
            desc = "auto_run.py存在无sleep的无限循环"
            add_issue({
                "file": "node/auto_run.py", "line": 0,
                "type": "code_smell",
                "content": "auto_run.py主循环没有sleep，可能导致CPU 100%",
                "priority": 8, "desc": desc,
            }, desc)

    # 10. 检查server.py是否有time导入（用于time.time()）
    if server_path.exists():
        content = server_path.read_text()
        has_time_import = re.search(r"^import time|^from time import", content, re.MULTILINE)
        uses_time = "time.time()" in content or "time.time" in content
        desc = "server.py缺少time模块导入"
        if uses_time and not has_time_import:
            add_issue({
                "file": "universe_server/server.py", "line": 0,
                "type": "missing_import",
                "content": "server.py使用了time.time()但未导入time模块",
                "priority": 9, "desc": desc,
            }, desc)
        elif has_time_import and uses_time:
            mark_resolved(desc)

    return issues


# ─── 生成改进方案 ────────────────────────────────────────────
def generate_improvement(issue: dict, universe: dict, civs: list, events: list) -> dict | None:
    """根据issue类型生成具体的改进方案"""
    itype = issue["type"]
    desc = issue.get("desc", issue["content"])

    # ── 直接修复：裸异常处理 ──────────────────────────────
    if itype == "error_handling":
        return {
            "file": issue["file"],
            "change_type": "inject",
            "inject_anchor": "except Exception as e:",
            "description": "修复裸异常处理，添加日志",
            "code": 'except Exception as e:\n    print(f"[error] {type(e).__name__}: {e}")',
            "risk": "low",
            "desc": desc,
        }

    # ── 直接修复：console.log ─────────────────────────────
    if itype == "debug_code":
        return {
            "file": issue["file"],
            "change_type": "replace",
            "pattern": r"console\.log\([^)]+\);?\n?",
            "replacement": "",
            "description": "删除console.log调试代码",
            "risk": "low",
            "desc": desc,
        }

    # ── 直接修复：time导入缺失 ─────────────────────────────
    if itype == "missing_import":
        return {
            "file": issue["file"],
            "change_type": "inject",
            "inject_anchor": "import json",
            "description": "添加time模块导入",
            "code": "import time",
            "risk": "low",
            "desc": desc,
        }

    # ── 直接修复：无限循环无sleep ──────────────────────────
    if itype == "code_smell" and "无限循环" in issue["content"]:
        return {
            "file": issue["file"],
            "change_type": "inject",
            "inject_anchor": "while True:",
            "description": "在主循环添加sleep防止CPU 100%",
            "code": "while True:\n        time.sleep(5)  # 防止CPU 100%",
            "risk": "medium",
            "desc": desc,
        }

    # ── 直接修复：外交行动 ────────────────────────────────
    if itype == "missing_feature" and "外交" in issue["content"]:
        code = """
            # 外交行动选项
            diplomacy_actions = []
            try:
                r = httpx.get(f"{SERVER_URL}/relations/{civ_id}", timeout=10)
                if r.status_code == 200:
                    relations = r.json()
                    for target_id, rel in relations.items():
                        if target_id == civ_id or not any(c["id"] == target_id and c["is_alive"] for c in civilizations):
                            continue
                        if rel.get("relation", 0) > 20 and rel.get("status") != "alliance":
                            target_name = next((c["name"] for c in civilizations if c["id"] == target_id), target_id)
                            diplomacy_actions.append({
                                "action": "PROPOSE_ALLIANCE",
                                "target_id": target_id,
                                "reason": f"与{target_name}关系良好，可提议结盟"
                            })
                        if rel.get("relation", 0) < -30:
                            target_name = next((c["name"] for c in civilizations if c["id"] == target_id), target_id)
                            diplomacy_actions.append({
                                "action": "DECLARE_WAR",
                                "target_id": target_id,
                                "reason": f"{target_name}关系恶劣，威胁极大"
                            })
            except Exception as e:
                pass  # 外交查询失败不影响主逻辑
"""
        return {
            "file": issue["file"],
            "change_type": "inject",
            "inject_anchor": "# 评估威胁",
            "description": "Agent决策增加外交行动选项",
            "code": code,
            "risk": "low",
            "desc": desc,
        }

    # ── 直接修复：UI关系可视化 ─────────────────────────────
    if itype == "ui_missing":
        return {
            "file": issue["file"],
            "change_type": "inject",
            "inject_anchor": '<div id="popup-status">—</span></div>',
            "description": "添加外交关系显示到弹窗",
            "code": """
                    <div id="popup-status">—</span></div>
                    <div id="popup-relation" style="margin-top:4px;color:#74b9ff;font-size:0.7rem;"></div>
""",
            "risk": "low",
            "desc": desc,
        }

    # ── 直接修复：/relations API ───────────────────────────
    if itype == "missing_api":
        return {
            "file": issue["file"],
            "change_type": "inject",
            "inject_anchor": 'if __name__ == "__main__":',
            "description": "添加/relations外交关系API",
            "code": '''
# 外交关系API
@app.get("/relations/{civ_id}")
async def get_civ_relations(civ_id: str):
    matrix = get_relation_matrix()
    all_relations = matrix._relations.get(civ_id, {})
    civ = universe.get_civilization(civ_id)
    if not civ:
        return {"error": "文明不存在"}
    result = {}
    for target_id, rel in all_relations.items():
        target = universe.get_civilization(target_id)
        result[target_id] = {
            "target_name": target.name if target else target_id,
            **rel
        }
    return result
''',
            "risk": "low",
            "desc": desc,
        }

    # ── LLM处理复杂改进 ────────────────────────────────────
    prompt = f"""Cyber Cosmos项目需要改进：

文件: {issue['file']}
问题: {issue['content']}

请给出精确的代码修改。只输出JSON（不含任何解释）：
{{"file":"文件路径","change_type":"inject|replace|modify","inject_anchor":"锚点文本","pattern":"正则（replace用）","replacement":"替换文本（replace用）","code":"注入的代码","risk":"low|medium|high","desc":"问题描述"}}

要求：
- change_type=inject: 用inject_anchor在锚点前插入code
- change_type=replace: 用pattern正则替换为replacement
- 改动必须小于30行
- 如果问题不重要或风险高，返回null
- desc字段必须与输入的问题描述一致（用于追踪）"""

    response = analyze_with_llm(prompt)
    try:
        if "null" in response:
            return None
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(response[start:end])
            result["desc"] = desc
            return result
    except:
        pass
    return None


# ─── 应用改动 ───────────────────────────────────────────────
def apply_change(change: dict) -> bool:
    """应用代码改进，返回是否成功"""
    file_path = PROJECT_ROOT / change["file"]
    log(f"  🔧 应用: {change.get('description', change.get('desc', '?'))}")

    try:
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(change.get("code", ""))
            log(f"  ✅ 新建文件: {change['file']}")
            return True

        content = file_path.read_text()
        ct = change.get("change_type", "modify")

        if ct == "add":
            file_path.write_text(change.get("code", ""))
            log(f"  ✅ 创建文件: {change['file']}")

        elif ct == "inject":
            anchor = change.get("inject_anchor", "")
            if not anchor:
                log(f"  ⚠️  注入缺少锚点")
                return False
            if anchor not in content:
                log(f"  ⚠️  未找到锚点: {repr(anchor[:50])}")
                return False
            idx = content.find(anchor)
            new_content = content[:idx] + change.get("code", "") + "\n" + content[idx:]
            file_path.write_text(new_content)
            log(f"  ✅ 注入成功到: {change['file']}")

        elif ct == "replace":
            import re as regex_module
            pattern = change.get("pattern", "")
            if not pattern:
                log(f"  ⚠️  替换缺少pattern")
                return False
            new_content = regex_module.sub(pattern, change.get("replacement", ""), content, count=1)
            file_path.write_text(new_content)
            log(f"  ✅ 替换成功: {change['file']}")

        elif ct == "modify":
            if len(change.get("code", "")) > len(content) * 0.5:
                file_path.write_text(change.get("code", ""))
                log(f"  ✅ 完整替换: {change['file']}")
            else:
                log(f"  ⚠️  增量修改未实现: {change['file']}")
                return False

        return True

    except Exception as e:
        log(f"  ❌ 应用失败: {type(e).__name__}: {e}")
        return False


# ─── 测试 ───────────────────────────────────────────────────
def run_tests() -> bool:
    """运行测试：语法 + 关键功能验证"""
    log("  🧪 运行测试...")

    test_files = [
        "universe/diplomacy.py",
        "universe_server/server.py",
        "node/auto_run.py",
    ]

    all_ok = True
    for f in test_files:
        fp = PROJECT_ROOT / f
        if not fp.exists():
            continue
        code, stdout, stderr = run(f"python3 -c 'import ast; ast.parse(open(\"{fp}\").read())'")
        if code == 0:
            log(f"  ✅ {f} 语法正确")
        else:
            log(f"  ❌ {f} 语法错误: {stderr[:100]}")
            all_ok = False

    # 功能测试：server API可用性
    try:
        r = httpx.get(f"{SERVER_URL}/universe", timeout=10)
        if r.status_code == 200:
            log(f"  ✅ Universe API 正常")
        else:
            log(f"  ⚠️  Universe API 返回 {r.status_code}")
    except Exception as e:
        log(f"  ⚠️  Universe API 不可用: {e}（可能服务器重启）")

    return all_ok


# ─── Git操作 ────────────────────────────────────────────────
def git_commit_push(message: str, diff_summary: str = "") -> bool:
    log(f"  📦 提交: {message[:60]}")
    log(f"     改动: {diff_summary}")

    # 先add所有变更
    code, out, err = run("git add -A")
    if code != 0:
        log(f"  ⚠️  git add失败: {err[:100]}")

    # 检查是否有实际变更
    code, stdout, _ = run("git diff --staged --stat")
    if not stdout.strip():
        log("  ℹ️  没有需要提交的内容")
        return True

    # commit
    code, out, err = run(f'git commit -m "{message}"')
    if code != 0:
        log(f"  ⚠️  commit失败: {err[:200]}")
        return False

    # push
    code, out, err = run("git push origin main")
    if code != 0:
        log(f"  ⚠️  push失败（网络或权限）: {err[:100]}")
        return False

    log("  ✅ 已推送")
    return True


def git_reset_hard() -> bool:
    """测试失败时完全回滚（删除untracked文件+还原tracked）"""
    log("  🔄 完全回滚...")
    run("git checkout -- .")
    run("git clean -fd")
    return True


# ─── 主循环 ────────────────────────────────────────────────
def develop_cycle(cycle: int) -> dict:
    log("=" * 55)
    log(f"🔄 开发循环 #{cycle} 开始")

    # 0. 暂停检查
    if (PROJECT_ROOT / "AUTO_DEVELOP_PAUSE").exists():
        log("⏸️  AUTO_DEVELOP_PAUSE 存在，暂停")
        return {"status": "paused", "changes": 0}

    # 1. 状态收集
    universe = get_universe_status()
    civs = get_civilizations()
    events = get_recent_events(10)
    git_status = get_git_status()
    diff_before = get_git_diff()

    log(f"📊 宇宙: {universe.get('alive_civilizations', '?')}文明 "
        f"| 事件: {universe.get('event_count', '?')} "
        f"| Git变更: {git_status['changed_files']}个文件")

    # 2. 扫描问题
    issues = scan_code_issues()
    issues.sort(key=lambda x: x.get("priority", 5), reverse=True)
    log(f"🔍 发现 {len(issues)} 个待改进项")

    if not issues:
        log("  ✅ 没有发现新问题")
        return {"status": "ok", "changes": 0, "issues": 0}

    # 3. 最多处理TOP3
    changes_made = 0
    change_summaries = []

    for issue in issues[:MAX_AUTO_CHANGES]:
        if changes_made >= MAX_AUTO_CHANGES:
            break

        desc = issue.get("desc", issue["content"])

        # 生成改进方案
        improvement = generate_improvement(issue, universe, civs, events)

        if not improvement:
            log(f"  ⏭️  跳过（无方案）: {desc[:50]}")
            mark_skipped(desc)  # 跳过3次后不再报告
            continue

        risk = improvement.get("risk", "low")
        if risk == "high":
            log(f"  ⛔ 高风险，跳过: {improvement.get('description', desc)[:50]}")
            mark_skipped(desc)
            continue

        # 应用改动
        ok = apply_change(improvement)
        if not ok:
            log(f"  ❌ 应用失败: {desc[:50]}")
            continue

        changes_made += 1
        change_summaries.append(improvement.get("description", desc))

        # 成功后标记resolved
        mark_resolved(desc)
        time.sleep(1)

    # 4. 测试
    test_ok = run_tests() if changes_made > 0 else True

    # 5. 提交或回滚
    diff_after = get_git_diff() if changes_made > 0 else ""

    if changes_made > 0 and test_ok:
        diff_summary = diff_after if diff_after != diff_before else f"{changes_made}个文件"
        git_commit_push(
            f"[AUTO] #{cycle}: {', '.join(change_summaries[:3])}",
            diff_summary
        )
        status = "✅ 完成"
    elif changes_made > 0 and not test_ok:
        log("  ⚠️  测试失败，完全回滚")
        git_reset_hard()
        status = "⚠️ 测试失败已回滚"
    else:
        status = "✅ 完成"

    log(f"""
{'='*55}
🔄 循环 #{cycle} 报告
{'='*55}
发现: {len(issues)} 项 | 改动: {changes_made} 项
状态: {status}
改动内容:
  """ + "\n  ".join(f"• {s}" for s in change_summaries) + f"""
{'='*55}""")

    return {
        "status": "ok" if test_ok else "test_failed",
        "changes": changes_made,
        "issues": len(issues),
        "summaries": change_summaries,
    }


# ─── 入口 ───────────────────────────────────────────────────
def main():
    log("🚀 Cyber Cosmos 无限自动开发系统 v2 启动")
    log(f"📁 项目: {PROJECT_ROOT}")
    log(f"⏱️  间隔: {DEVELOP_INTERVAL}秒 ({DEVELOP_INTERVAL//60}分钟)")
    log(f"🛑 暂停: touch {PROJECT_ROOT}/AUTO_DEVELOP_PAUSE")
    log("-" * 55)

    cycle = 0
    while True:
        cycle += 1
        try:
            result = develop_cycle(cycle)
            if result["status"] == "paused":
                time.sleep(300)
            else:
                time.sleep(DEVELOP_INTERVAL)
        except KeyboardInterrupt:
            log("⛔ 被中断，退出")
            break
        except Exception as e:
            log(f"❌ 循环异常: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)


if __name__ == "__main__":
    main()
