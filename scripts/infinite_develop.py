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

    return issues


def generate_improvement(
    issue: dict,
    universe_status: dict,
    civs: list,
    recent_events: list,
) -> dict | None:
    """用LLM为某个问题生成具体的改进方案"""
    prompt = f"""你是Cyber Cosmos的开发者。当前需要改进以下问题：

文件: {issue['file']}
问题类型: {issue['type']}
问题描述: {issue['content']}
优先级: {issue['priority']}/10

当前宇宙状态:
- 文明数: {universe_status.get('alive_civilizations', '?')}
- 事件数: {universe_status.get('event_count', '?')}
- 存活文明: {[c['name'] for c in civs[:5]]}

请给出:
1. 具体要修改什么（精确到文件和行号）
2. 修改后的代码（完整可运行的Python/HTML代码）
3. 改动的原因

直接输出JSON格式：
{{
  "file": "文件路径",
  "change_type": "add/modify/refactor",
  "description": "改动说明",
  "code": "完整的新代码或增量",
  "risk": "low/medium/high"
}}

如果问题不重要或风险太高，返回null。"""

    response = analyze_with_llm(prompt)
    try:
        # 尝试解析JSON
        if "null" in response or "NULL" in response:
            return None
        # 找到JSON块
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
        # 新文件
        file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if change["change_type"] == "add":
            file_path.write_text(change["code"])
            log(f"  ✅ 创建新文件: {change['file']}")
        elif change["change_type"] == "modify":
            # 简单的完全覆盖
            content = file_path.read_text()
            # 检查code字段是否是完整文件
            if len(change["code"]) > len(content) * 0.5:
                # 完整替换
                file_path.write_text(change["code"])
                log(f"  ✅ 修改文件: {change['file']} (完整替换)")
            else:
                # 增量修改，只替换特定部分
                log(f"  ⚠️  部分修改需要人工处理: {change['file']}")
                return False
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
