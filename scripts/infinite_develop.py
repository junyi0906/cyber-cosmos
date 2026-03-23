#!/usr/bin/env python3
"""
Cyber Cosmos — 无限自动开发系统
Infinite Automatic Development Daemon

每小时自动分析项目状态，决定需要改进的地方，实施改进，提交代码。

安全机制:
- [AUTO] 前缀的commit表示自动生成
- 高风险操作跳过
- AUTO_DEVELOP_PAUSE 文件存在时暂停
- 每次循环生成报告
"""

import os
import sys
import json
import time
import random
import subprocess
import httpx
from datetime import datetime
from pathlib import Path

# 配置
PROJECT_ROOT = Path.home() / "cyber-cosmos"
PYTHON_PATH = str(PROJECT_ROOT)
SERVER_URL = "http://localhost:8000"
GLM_KEY = os.environ.get(
    "GLM5_TURBO_KEY",
    "8ebd0252b1fc498ebd53dfc299d4de12.PwoiSyS6NA5RuALo"
)
DEVELOP_INTERVAL = 3600  # 每小时触发一次
MAX_AUTO_CHANGES_PER_CYCLE = 3  # 每次最多改3个文件


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run(cmd: str, cwd: str = None) -> tuple[int, str, str]:
    """运行shell命令"""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd or PROJECT_ROOT
    )
    return result.returncode, result.stdout, result.stderr


def check_pause() -> bool:
    """检查是否暂停"""
    pause_file = PROJECT_ROOT / "AUTO_DEVELOP_PAUSE"
    if pause_file.exists():
        log(f"⏸️  AUTO_DEVELOP_PAUSE 文件存在，无限开发已暂停")
        return True
    return False


def get_universe_status() -> dict:
    """获取宇宙运行状态"""
    try:
        r = httpx.get(f"{SERVER_URL}/universe", timeout=10)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}


def get_civilizations() -> list:
    """获取文明列表"""
    try:
        r = httpx.get(f"{SERVER_URL}/civilizations", timeout=10)
        return r.json() if r.status_code == 200 else []
    except:
        return []


def get_recent_events(limit: int = 20) -> list:
    """获取最近事件"""
    try:
        r = httpx.get(f"{SERVER_URL}/history", timeout=10)
        if r.status_code == 200:
            return r.json()[-limit:]
    except:
        pass
    return []


def get_git_status() -> dict:
    """获取Git状态"""
    code, out, err = run("git status --porcelain")
    changed = [l for l in out.strip().split("\n") if l]
    return {"changed_files": len(changed), "files": changed}


def analyze_with_llm(
    prompt: str, system: str = "你是Cyber Cosmos的开发顾问，分析代码并给出具体改进建议。"
) -> str:
    """用LLM分析并生成建议"""
    import urllib.request

    payload = {
        "model": "glm-4-plus",
        "messages": [
            {"role": "system", "content": system},
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
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[LLM Error: {e}]"


def scan_code_issues() -> list[dict]:
    """扫描代码，识别需要改进的地方"""
    issues = []

    # 1. 检查 server.py 的事件处理
    server_path = PROJECT_ROOT / "universe_server" / "server.py"
    if server_path.exists():
        content = server_path.read_text()

        # 检查是否有TODO注释
        for i, line in enumerate(content.split("\n"), 1):
            if "TODO" in line or "FIXME" in line or "XXX" in line:
                issues.append(
                    {
                        "file": "universe_server/server.py",
                        "line": i,
                        "type": "todo",
                        "content": line.strip(),
                        "priority": 5,
                    }
                )

        # 检查是否有重复代码模式
        lines = content.split("\n")
        for i in range(len(lines) - 5):
            chunk = "\n".join(lines[i : i + 5])
            if chunk.count("\n\n\n") >= 2:
                issues.append(
                    {
                        "file": "universe_server/server.py",
                        "line": i + 1,
                        "type": "code_smell",
                        "content": "可能存在重复的空行或格式问题",
                        "priority": 3,
                    }
                )

    # 2. 检查 Web UI 是否有待改进
    ui_path = PROJECT_ROOT / "web" / "templates" / "index.html"
    if ui_path.exists():
        content = ui_path.read_text()
        if "console.log" in content:
            issues.append(
                {
                    "file": "web/templates/index.html",
                    "line": 0,
                    "type": "debug_code",
                    "content": "Web UI中存在console.log调试代码",
                    "priority": 4,
                }
            )

    # 3. 检查 auto_run.py 是否有问题
    auto_run_path = PROJECT_ROOT / "node" / "auto_run.py"
    if auto_run_path.exists():
        content = auto_run_path.read_text()
        if "except Exception as e:" in content and "print(f\"[error]" not in content:
            issues.append(
                {
                    "file": "node/auto_run.py",
                    "line": 0,
                    "type": "error_handling",
                    "content": "存在裸异常处理，可能吞掉错误",
                    "priority": 6,
                }
            )

    # 4. 检查 diplomatic 系统的完整度
    diplomacy_path = PROJECT_ROOT / "universe" / "diplomacy.py"
    if diplomacy_path.exists():
        issues.append(
            {
                "file": "universe/diplomacy.py",
                "line": 0,
                "type": "new_feature",
                "content": "外交系统已创建，需要集成到 server.py 和 agent 决策中",
                "priority": 8,
            }
        )

    # 5. 检查 node/auto_run.py 的决策循环是否有更智能的外交选项
    auto_run = PROJECT_ROOT / "node" / "auto_run.py"
    if auto_run.exists():
        content = auto_run.read_text()
        # 检查是否缺少外交行动
        if "PROPOSE_ALLIANCE" not in content or "SEND_SIGNAL" not in content:
            issues.append(
                {
                    "file": "node/auto_run.py",
                    "line": 0,
                    "type": "missing_feature",
                    "content": "Agent决策引擎缺少外交行动支持（SEND_SIGNAL/PROPOSE_ALLIANCE等）",
                    "priority": 7,
                }
            )

    # 6. 检查 Web UI 是否缺少外交/关系可视化
    ui_path = PROJECT_ROOT / "web" / "templates" / "index.html"
    if ui_path.exists():
        content = ui_path.read_text()
        if "relation" not in content.lower() and "diplomacy" not in content.lower():
            issues.append(
                {
                    "file": "web/templates/index.html",
                    "line": 0,
                    "type": "ui_missing",
                    "content": "Web UI缺少文明关系/外交状态的可视化展示",
                    "priority": 5,
                }
            )

    # 7. 检查 server.py 是否缺少 /relations API端点
    server_path = PROJECT_ROOT / "universe_server" / "server.py"
    if server_path.exists():
        content = server_path.read_text()
        if "/relations" not in content:
            issues.append(
                {
                    "file": "universe_server/server.py",
                    "line": 0,
                    "type": "missing_api",
                    "content": "缺少 /relations API（查看文明间关系）",
                    "priority": 6,
                }
            )

    # 8. 检查 narative.py 的fallback叙事是否够丰富
    narrative_path = PROJECT_ROOT / "universe" / "narrative.py"
    if narrative_path.exists():
        content = narrative_path.read_text()
        if content.count("f\"") < 10:
            issues.append(
                {
                    "file": "universe/narrative.py",
                    "line": 0,
                    "type": "narrative_quality",
                    "content": "叙事fallback模板较少，可以扩展更多事件类型的叙事",
                    "priority": 4,
                }
            )

    return issues


def generate_improvement(
    issue: dict,
    universe_status: dict,
    civs: list,
    recent_events: list,
) -> dict | None:
    """为某个问题生成具体的改进方案"""

    # ─── 模式1：直接生成简单改进（不需要LLM）──────────────────────
    if issue["type"] == "missing_api":
        # 添加 /relations API 端点
        code = '''
@app.get("/relations/{civ_id}")
async def get_relations(civ_id: str):
    """获取某个文明与其他文明的全部关系"""
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


@app.post("/relations/send_signal")
async def send_diplomatic_signal(req: dict):
    """发送外交信号"""
    from universe.diplomacy import get_relation_matrix
    civ = universe.get_civilization(req.get("civilization_id"))
    target = universe.get_civilization(req.get("target_id"))
    if not civ or not target:
        return {"error": "文明不存在"}
    matrix = get_relation_matrix()
    result = matrix.send_signal(
        civ.id, target.id,
        req.get("content", ""),
        encrypted=req.get("encrypted", False)
    )
    if result["success"]:
        # 记录外交事件
        event = UniverseEvent(
            event_id=f"{civ.id}_signal_{int(time.time())}",
            event_type=EventType.DIPLOMATIC_SIGNAL,
            timestamp=civ.last_active,
            actor_id=civ.id,
            target_id=target.id,
            narrative=f"{civ.name} 向 {target.name} 发送了外交信号",
            significance="NOTABLE"
        )
        event_history.record(event)
        event_history.flush()
        await manager.broadcast({
            "type": "event",
            "event": event.model_dump(mode="json"),
            "universe": universe.get_universe_summary()
        })
    return result
'''
        return {
            "file": "universe_server/server.py",
            "change_type": "inject",
            "inject_anchor": "if __name__ == '__main__'",
            "description": "添加 /relations 和 /relations/send_signal API",
            "code": code.strip(),
            "risk": "low"
        }

    if issue["type"] == "missing_feature":
        # 添加外交行动到 auto_run.py
        return {
            "file": "node/auto_run.py",
            "change_type": "inject",
            "inject_anchor": "# 评估威胁",
            "description": "Agent决策增加外交行动选项（SEND_SIGNAL/PROPOSE_ALLIANCE等）",
            "code": '''
            # 外交行动选项（如果关系允许）
            diplomacy_actions = []
            for other_civ in civilizations:
                if other_civ["id"] == civ_id or not other_civ["is_alive"]:
                    continue
                rel = get_relation_between(civ_id, other_civ["id"])
                if rel and rel["relation"] > 20 and rel["status"] != "alliance":
                    diplomacy_actions.append({
                        "action": "PROPOSE_ALLIANCE",
                        "target_id": other_civ["id"],
                        "reason": f"与{other_civ['name']}关系良好，可提议结盟"
                    })
                if rel and rel["relation"] < -30:
                    diplomacy_actions.append({
                        "action": "DECLARE_WAR",
                        "target_id": other_civ["id"],
                        "reason": f"{other_civ['name']}关系恶劣，威胁极大"
                    })
''',
            "risk": "low"
        }

    if issue["type"] == "ui_missing":
        # Web UI添加关系标签
        return {
            "file": "web/templates/index.html",
            "change_type": "inject",
            "inject_anchor": "popup-status",
            "description": "文明详情弹窗显示外交关系状态",
            "code": '''
                    <div id="popup-relation" style="margin-top:4px;color:#74b9ff;font-size:0.7rem;"></div>
''',
            "risk": "low"
        }

    # ─── 模式2：LLM生成复杂改进 ─────────────────────────────────
    prompt = f"""你是Cyber Cosmos的开发者。当前需要改进：

文件: {issue['file']}
问题类型: {issue['type']}
问题描述: {issue['content']}

请给出:
1. 要修改的具体位置（精确到文件和行号）
2. 改动后的完整代码

要求:
- 改动必须小而精确（少于50行新增/修改）
- 不能修改其他地方的逻辑
- 只输出该文件的增量代码（不是完整文件）

直接输出JSON格式：
{{
  "file": "文件路径",
  "change_type": "modify",
  "description": "简短说明",
  "code": "完整的修改后文件内容（不是增量）",
  "risk": "low/medium/high"
}}

如果改动超过50行或风险高，返回null。"""

    response = analyze_with_llm(prompt)
    try:
        if "null" in response or "NULL" in response:
            return None
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except:
        pass
    return None


def apply_change(change: dict) -> bool:
    """应用代码改进"""
    file_path = PROJECT_ROOT / change["file"]
    if not file_path.exists() and change["change_type"] == "add":
        file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if change["change_type"] == "add":
            file_path.write_text(change["code"])
            log(f"  ✅ 创建新文件: {change['file']}")
            return True

        elif change["change_type"] == "inject":
            # 锚点注入：在指定锚点前插入代码
            content = file_path.read_text()
            anchor = change.get("inject_anchor", "")
            if anchor and anchor in content:
                idx = content.find(anchor)
                new_content = content[:idx] + change["code"] + "\n" + content[idx:]
                file_path.write_text(new_content)
                log(f"  ✅ 注入代码到: {change['file']} (anchor: {anchor[:30]})")
                return True
            else:
                log(f"  ⚠️  未找到注入锚点: {anchor[:30] if anchor else 'none'}")
                return False

        elif change["change_type"] == "modify":
            content = file_path.read_text()
            if len(change["code"]) > len(content) * 0.5:
                file_path.write_text(change["code"])
                log(f"  ✅ 修改文件: {change['file']} (完整替换)")
            else:
                log(f"  ⚠️  部分修改需要人工处理: {change['file']}")
                return False
            return True

        return True
    except Exception as e:
        log(f"  ❌ 应用失败: {e}")
        return False


def run_tests() -> bool:
    """运行基本测试"""
    log("  🧪 运行测试...")
    # 检查Python语法
    code, out, err = run("python3 -c 'import ast; ast.parse(open(\"universe/diplomacy.py\").read())'")
    if code == 0:
        log("  ✅ diplomacy.py 语法正确")
    else:
        log(f"  ❌ diplomacy.py 语法错误: {err}")
        return False

    # 检查server.py
    code, out, err = run("python3 -c 'import ast; ast.parse(open(\"universe_server/server.py\").read())'")
    if code == 0:
        log("  ✅ server.py 语法正确")
    else:
        log(f"  ❌ server.py 语法错误: {err}")
        return False
    return True


def git_commit_push(message: str) -> bool:
    """提交并推送"""
    log(f"  📦 Git提交: {message[:60]}")
    code, out, err = run(f'git add -A && git commit -m "{message}"')
    if code != 0:
        log(f"  ⚠️  Git commit失败: {err[:200]}")
        return False
    code, out, err = run("git push origin main")
    if code != 0:
        log(f"  ⚠️  Git push失败 (可能无需推送)")
        return False
    else:
        log(f"  ✅ 已推送")
    return True


def generate_develop_report(
    cycle: int,
    issues_found: int,
    changes_made: int,
    status: str,
) -> str:
    """生成开发报告"""
    return f"""
═══════════════════════════════════════
🔄 Cyber Cosmos 无限自动开发报告
#{cycle:03d}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
═══════════════════════════════════════
发现待改进: {issues_found} 项
实际改动:   {changes_made} 项
状态:       {status}
═══════════════════════════════════════
"""


# ══════════════════════════════════════
# 主循环
# ══════════════════════════════════════

def develop_cycle(cycle: int) -> dict:
    """执行一次开发循环"""
    log("═" * 50)
    log(f"🔄 开始开发循环 #{cycle}")

    # 1. 检查暂停
    if check_pause():
        return {"status": "paused", "changes": 0}

    # 2. 获取宇宙状态
    universe = get_universe_status()
    civs = get_civilizations()
    events = get_recent_events(10)
    git_status = get_git_status()

    log(f"📊 宇宙: {universe.get('alive_civilizations', '?')}文明 "
        f"| 事件: {universe.get('event_count', '?')} "
        f"| Git变更: {git_status['changed_files']}个文件")

    # 3. 扫描问题
    issues = scan_code_issues()
    issues.sort(key=lambda x: x["priority"], reverse=True)
    log(f"🔍 发现 {len(issues)} 个待改进项")

    if not issues:
        log("  ✅ 没有发现需要改进的地方")
        return {"status": "ok", "changes": 0, "issues": 0}

    # 4. 最多处理TOP3
    changes_made = 0
    for issue in issues[:MAX_AUTO_CHANGES_PER_CYCLE]:
        if changes_made >= MAX_AUTO_CHANGES_PER_CYCLE:
            break

        # 高风险跳过
        improvement = generate_improvement(issue, universe, civs, events)
        if not improvement:
            log(f"  ⏭️  跳过: {issue['content'][:50]}")
            continue

        if improvement.get("risk") == "high":
            log(f"  ⛔ 高风险操作，跳过: {improvement['description'][:50]}")
            continue

        # 应用改动
        if apply_change(improvement):
            changes_made += 1
            time.sleep(2)  # 给LLM喘息时间

    # 5. 测试
    test_ok = run_tests() if changes_made > 0 else True

    # 6. 提交
    if changes_made > 0 and test_ok:
        git_commit_push(
            f"[AUTO] 自动改进 #{cycle}: {changes_made}项优化 "
            f"({datetime.now().strftime('%m/%d %H:%M')})"
        )
    elif changes_made > 0 and not test_ok:
        log("  ⚠️  测试失败，代码未提交")
        run("git checkout -- .")  # 还原

    report = generate_develop_report(
        cycle, len(issues), changes_made,
        "✅ 完成" if test_ok else "⚠️ 测试失败"
    )
    log(report)

    return {
        "status": "ok" if test_ok else "test_failed",
        "changes": changes_made,
        "issues": len(issues),
        "report": report,
    }


def main():
    log("🚀 Cyber Cosmos 无限自动开发系统启动")
    log(f"📁 项目目录: {PROJECT_ROOT}")
    log(f"⏱️  触发间隔: {DEVELOP_INTERVAL}秒 (1小时)")
    log("🛑 暂停: touch AUTO_DEVELOP_PAUSE")
    log("-" * 50)

    cycle = 0
    while True:
        cycle += 1
        try:
            result = develop_cycle(cycle)
            if result["status"] == "paused":
                # 暂停状态，等待
                time.sleep(300)
            else:
                time.sleep(DEVELOP_INTERVAL)
        except KeyboardInterrupt:
            log("⛔ 被用户中断，退出")
            break
        except Exception as e:
            log(f"❌ 循环出错: {e}")
            time.sleep(300)  # 出错后等5分钟重试


if __name__ == "__main__":
    main()
