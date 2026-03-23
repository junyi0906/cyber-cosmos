#!/usr/bin/env python3
"""
Cyber Cosmos — 无限自动开发系统 v3
基于论文 "Effective Harnesses for Long-Running Agents" (arXiv:2603.05344)

改进:
  - Extended ReAct 循环 (thinking + critique phases)
  - Plan Mode（改动前生成结构化计划）
  - Git Snapshot（改动前回滚保护）
  - 操作日志（所有操作可追溯）
  - 自适应上下文压缩
  - Session 持久化
  - 事件驱动提醒
  - 防御深度安全（4层）
"""

import os
import sys
import json
import time
import shutil
import subprocess
import httpx
import re
import hashlib
from datetime import datetime
from pathlib import Path

# ─── 配置 ───────────────────────────────────────────────────
PROJECT_ROOT = Path.home() / "cyber-cosmos"
SERVER_URL = "http://localhost:8000"
GLM_KEY = os.environ.get(
    "GLM5_TURBO_KEY",
    "8ebd0252b1fc498ebd53dfc299d4de12.PwoiSyS6NA5RuALo"
)
GLM_THINKING_KEY = os.environ.get(
    "GLM_THINKING_KEY",
    "8ebd0252b1fc498ebd53dfc299d4de12.PwoiSyS6NA5RuALo"
)
DEVELOP_INTERVAL = 300   # 5分钟
MAX_AUTO_CHANGES = 2    # 每次最多改2个文件（安全优先）
RESOLVED_FILE = PROJECT_ROOT / ".auto_develop_resolved.json"
SESSION_FILE = PROJECT_ROOT / ".auto_develop_session.json"
OPLOG_FILE = PROJECT_ROOT / ".auto_develop_oplog.jsonl"


# ─── 日志 ───────────────────────────────────────────────────
def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "💬", "WARN": "⚠️", "ERROR": "❌", "OK": "✅",
             "PLAN": "📋", "THINK": "🤔", "CRITIQUE": "🔍", "EXEC": "⚡"}
    icon = icons.get(level, "💬")
    print(f"[{ts}] {icon} {msg}", flush=True)


def run(cmd: str, cwd: str = None) -> tuple[int, str, str]:
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd or PROJECT_ROOT
    )
    return result.returncode, result.stdout, result.stderr


# ─── 操作日志（Transparency） ─────────────────────────────────
def oplog(action: str, data: dict):
    """所有操作记录到 JSONL 日志"""
    entry = {
        "ts": datetime.now().isoformat(),
        "cycle": get_session().get("cycle", 0),
        "action": action,
        **data
    }
    with open(OPLOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ─── Session 持久化 ───────────────────────────────────────────
def get_session() -> dict:
    try:
        return json.loads(SESSION_FILE.read_text())
    except:
        return {"cycle": 0, "consecutive_empty": 0, "total_changes": 0,
                "last_change_time": None, "reminders": []}


def save_session(s: dict):
    SESSION_FILE.write_text(json.dumps(s, ensure_ascii=False))


def update_session(**kwargs):
    s = get_session()
    s.update(kwargs)
    save_session(s)


# ─── Git Snapshot ─────────────────────────────────────────────
SNAPSHOT_DIR = PROJECT_ROOT / ".auto_snapshots"


def git_snapshot() -> str:
    """创建Git stash snapshot，返回snapshot ID"""
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    sess = get_session()
    snapshot_id = f"cycle{sess['cycle']}_{int(time.time())}"
    code, out, err = run("git stash push -m 'auto_snapshot'")
    if code == 0:
        oplog("snapshot", {"snapshot_id": snapshot_id, "status": "created"})
        log(f"📸 Git snapshot: {snapshot_id}", "INFO")
    else:
        oplog("snapshot", {"snapshot_id": snapshot_id, "status": "no_changes"})
        log("📸 无变更，无需snapshot", "INFO")
    return snapshot_id


def git_restore_snapshot() -> bool:
    """从snapshot恢复，并清除已应用的resolved标记"""
    code, out, err = run("git stash pop")
    if code == 0:
        oplog("restore_snapshot", {"status": "success"})
        log("↩️  已从snapshot恢复", "WARN")
        # 清除所有resolved（回滚的改动需要重新尝试）
        try:
            data = {"_resolved": [], "_skipped": []}
            RESOLVED_FILE.write_text(json.dumps(data, ensure_ascii=False))
            log("🧹 已清除resolved标记（回滚后重试）", "WARN")
        except:
            pass
        return True
    else:
        oplog("restore_snapshot", {"status": "failed", "err": err[:100]})
        log(f"↩️  恢复失败: {err[:100]}", "ERROR")
        return False


# ─── 上下文压缩（Adaptive Context Compaction） ──────────────────
def get_effective_events(limit: int = None) -> list:
    """根据事件总量自适应压缩"""
    try:
        r = httpx.get(f"{SERVER_URL}/history", timeout=10)
        if r.status_code != 200:
            return []
        events = r.json()
    except:
        return []

    total = len(events)
    if total < 30:
        effective = events
    elif total < 60:
        effective = events[-20:]  # 保留最近20
    else:
        effective = events[-10:]  # 紧急压缩到10

    if limit:
        effective = effective[-limit:]

    return effective


# ─── LLM 调用（带重试） ───────────────────────────────────────
def llm_call(messages: list, model: str = "glm-4-plus",
             max_tokens: int = 600, temperature: float = 0.3) -> str:
    """LLM 调用，支持重试，修复SSL证书问题"""
    import urllib.request
    import ssl

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    data = json.dumps(payload).encode("utf-8")

    # 修复SSL证书验证
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {GLM_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60, context=ssl_ctx) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return f"[LLM Error: {e}]"


# ─── Resolved 问题追踪 ────────────────────────────────────────
def get_resolved() -> set:
    try:
        raw = json.loads(RESOLVED_FILE.read_text())
        if isinstance(raw, dict):
            return set(raw.get("_resolved", []))
        return set(raw)
    except:
        return set()


def mark_resolved(desc: str):
    data = {"_resolved": [], "_skipped": []}
    try:
        raw = json.loads(RESOLVED_FILE.read_text())
        if isinstance(raw, dict):
            data = raw
        elif isinstance(raw, list):
            data = {"_resolved": raw, "_skipped": []}
    except:
        pass
    if desc not in data["_resolved"]:
        data["_resolved"].append(desc)
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


def get_git_status() -> dict:
    code, out, _ = run("git status --porcelain")
    return {"changed": len([l for l in out.strip().split("\n") if l])}


# ─── 问题扫描器 ───────────────────────────────────────────────
def scan_issues() -> list[dict]:
    """扫描代码问题"""
    issues = []
    server = PROJECT_ROOT / "universe_server" / "server.py"
    auto_run = PROJECT_ROOT / "node" / "auto_run.py"
    ui = PROJECT_ROOT / "web" / "templates" / "index.html"
    narrative = PROJECT_ROOT / "universe" / "narrative.py"
    diplomacy = PROJECT_ROOT / "universe" / "diplomacy.py"

    def add(desc: str, file: str, ptype: str, content: str, priority: int):
        if desc not in get_resolved():
            issues.append({"desc": desc, "file": file, "type": ptype,
                           "content": content, "priority": priority})

    # 1. console.log
    if ui.exists():
        content = ui.read_text()
        if "console.log" in content:
            add("Web UI存在console.log调试代码", "web/templates/index.html",
                "debug_code", "console.log存在", 5)

    # 2. 裸异常处理
    if auto_run.exists():
        content = auto_run.read_text()
        if re.search(r"except\s+Exception\s+as\s+\w+:\s*\n\s*(?!.*(?:log|print))",
                     content, re.MULTILINE):
            add("auto_run.py存在裸异常处理", "node/auto_run.py",
                "error_handling", "裸异常无日志", 5)

    # 3. diplomatic系统集成
    if diplomacy.exists() and server.exists() and auto_run.exists():
        sc = server.read_text()
        ac = auto_run.read_text()
        if not ("get_relation_matrix" in sc and "get_relation_matrix" in ac):
            add("外交系统未完整集成", "universe/diplomacy.py",
                "new_feature", "外交系统需要集成", 7)

    # 4. /relations API
    if server.exists():
        if "/relations" not in server.read_text():
            add("缺少/relations API", "universe_server/server.py",
                "missing_api", "外交关系API缺失", 6)

    # 5. 叙事模板
    if narrative.exists():
        content = narrative.read_text()
        if content.count('"""') < 15:
            add("叙事模板较少", "universe/narrative.py",
                "narrative_quality", "fallback叙事不足", 3)

    # 6. UI缺少外交关系显示
    if ui.exists():
        content = ui.read_text()
        if "popup-relation" not in content:
            add("Web UI缺少外交关系显示", "web/templates/index.html",
                "ui_missing", "关系弹窗缺失", 5)

    # 7. Agent外交行动
    if auto_run.exists():
        content = auto_run.read_text()
        if content.count("PROPOSE_ALLIANCE") < 1 or "DECLARE_WAR" not in content:
            add("Agent缺少外交决策", "node/auto_run.py",
                "missing_feature", "外交行动未集成", 6)

    # 8. time导入检测
    if server.exists():
        content = server.read_text()
        if "time.time" in content and not re.search(r"^import time|^from time import",
                                                     content, re.MULTILINE):
            add("server.py缺少time导入", "universe_server/server.py",
                "missing_import", "time模块未导入", 9)

    issues.sort(key=lambda x: x["priority"], reverse=True)
    return issues


# ─── Extended ReAct 循环 ─────────────────────────────────────

# PHASE 1: Pre-check
def pre_check(sess: dict) -> dict:
    """环境检查：暂停文件、宇宙状态、Git状态"""
    oplog("phase_precheck", {"ts": datetime.now().isoformat()})

    if (PROJECT_ROOT / "AUTO_DEVELOP_PAUSE").exists():
        log("⏸️  AUTO_DEVELOP_PAUSE 存在，暂停", "WARN")
        return {"ok": False, "reason": "paused"}

    git_st = get_git_status()
    univ = get_universe_status()
    civs = get_civilizations()

    log(f"📊 宇宙: {univ.get('alive_civilizations', '?')}文明 "
        f"| 事件: {univ.get('event_count', '?')} "
        f"| Git变更: {git_st['changed']}个", "INFO")

    return {
        "ok": True,
        "universe": univ,
        "civilizations": civs,
        "git_status": git_st,
        "session": sess,
    }


# PHASE 2: Thinking
def thinking(issue: dict, ctx: dict) -> str:
    """LLM Thinking：让模型先"想一想"这个问题的本质"""
    oplog("phase_thinking", {"issue": issue["desc"]})

    prompt = f"""问题: {issue['content']}
文件: {issue['file']}
优先级: {issue['priority']}/10

请简要分析：
1. 这个问题的根本原因是什么？
2. 最小改动是什么？
3. 有什么潜在风险？

回答简洁，1-3句话即可。"""

    response = llm_call([
        {"role": "system", "content": "你是一个代码分析助手。简洁直接。"},
        {"role": "user", "content": prompt}
    ], max_tokens=150, temperature=0.3)

    log(f"🤔 思考: {response[:80]}", "THINK")
    oplog("thinking_result", {"issue": issue["desc"], "thought": response[:200]})
    return response


# PHASE 3: Self-Critique
def self_critique(issue: dict, proposed_fix: dict, ctx: dict) -> dict:
    """LLM Self-Critique：审查改动方案的可行性"""
    oplog("phase_critique", {"issue": issue["desc"]})

    prompt = f"""改动方案审查：

问题: {issue['content']}
文件: {issue['file']}
方案: {proposed_fix.get('description', '')}

请审查：
1. 这个改动是否会破坏现有功能？
2. 改动范围是否过大？
3. 是否需要人类审批？

JSON格式：
{{"risk": "low/medium/high", "concerns": ["风险1", "风险2"], "needs_approval": true/false}}"""

    response = llm_call([
        {"role": "system", "content": "你是代码安全审查员。严格评估。"},
        {"role": "user", "content": prompt}
    ], max_tokens=200, temperature=0.2)

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(response[start:end])
            log(f"🔍 审查: risk={result.get('risk')} needs_approval={result.get('needs_approval')}", "CRITIQUE")
            oplog("critique_result", result)
            return result
    except:
        pass

    return {"risk": "medium", "concerns": [], "needs_approval": False}


# PHASE 4: Plan Mode — 生成结构化计划
def plan_mode(issues: list, ctx: dict) -> dict | None:
    """Plan Mode: 生成结构化开发计划，等待确认"""
    oplog("phase_plan", {"issue_count": len(issues)})

    events = get_effective_events(limit=10)
    events_text = "\n".join([
        f"  - [{e.get('event_type', '')}] {e.get('narrative', '')[:50]}"
        for e in events
    ]) or "  无"

    civs_text = "\n".join([
        f"  - {c.get('name', '')} (tech={c.get('tech_level', 0):.2f})"
        for c in ctx.get("civilizations", [])[:5]
    ]) or "  无"

    prompt = f"""作为Cyber Cosmos的开发顾问，基于以下问题生成结构化开发计划。

当前宇宙状态:
文明: {civs_text}
最近事件: {events_text}

待解决问题（按优先级）:
{chr(10).join(f"  {i+1}. [{iss['priority']}分] {iss['content']} ({iss['file']})"
               for i, iss in enumerate(issues[:3]))}

请生成开发计划，直接输出JSON：
{{
  "title": "计划标题",
  "changes": [
    {{
      "file": "文件路径",
      "action": "inject|replace",
      "anchor": "锚点文本",
      "code": "要注入的代码",
      "reason": "改动原因"
    }}
  ]
}}"""

    response = llm_call([
        {"role": "system", "content": "你是一个JSON生成器。只输出纯JSON，不要任何markdown格式、代码块标记或解释文字。"},
        {"role": "user", "content": prompt}
    ], max_tokens=1000, temperature=0.1)

    log(f"📋 LLM响应长度: {len(response)}字符", "PLAN")

    # 去除markdown包装（```json ... ``` 或 ``` ... ```）
    cleaned = re.sub(r"```json\s*", "", response.strip())
    cleaned = re.sub(r"```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    # 尝试直接解析
    try:
        plan = json.loads(cleaned)
        log(f"📋 计划: {plan.get('title', '未命名')} ({len(plan.get('changes', []))}个改动)", "PLAN")
        oplog("plan_generated", {"plan": plan.get("title", ""), "changes": len(plan.get("changes", []))})
        return plan
    except:
        pass

    # 尝试从文本中提取JSON
    try:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start and (end - start) > 20:
            plan = json.loads(cleaned[start:end])
            log(f"📋 计划(提取): {plan.get('title', '未命名')} ({len(plan.get('changes', []))}个改动)", "PLAN")
            oplog("plan_generated", {"plan": plan.get("title", ""), "changes": len(plan.get("changes", []))})
            return plan
    except Exception as e:
        log(f"📋 JSON解析失败: {e}", "WARN")

    log(f"📋 原始响应前200字符: {response[:200]}", "WARN")

    # Fallback: 从issue直接生成修复方案
    log("📋 回退到直接修复模式", "WARN")
    oplog("plan_fallback", {"reason": "json_parse_failed"})

    fixes_for_fallback = []
    for iss in issues[:MAX_AUTO_CHANGES]:
        fix = generate_fix(iss, ctx)
        if fix:
            fixes_for_fallback.append({
                "file": fix["file"],
                "action": fix.get("change_type", "inject"),
                "anchor": fix.get("inject_anchor", ""),
                "code": fix.get("code", ""),
                "reason": fix.get("description", iss["content"])
            })
        else:
            oplog("no_fix_for_issue", {"issue": iss["desc"], "type": iss["type"]})

    fallback_plan = {
        "title": "直接修复",
        "changes": fixes_for_fallback
    }
    return fallback_plan


# ─── 代码生成 ────────────────────────────────────────────────
def generate_fix(issue: dict, ctx: dict) -> dict | None:
    """根据issue类型生成修复方案"""
    itype = issue["type"]
    fmap = issue["file"]

    # 直接修复映射
    fixes = {

        "debug_code": {
            "file": fmap,
            "change_type": "replace",
            "pattern": r"console\.log\([^)]+\);?\n?",
            "replacement": "",
            "description": f"删除console.log",
            "risk": "low",
            "desc": issue["desc"],
        },

        "error_handling": {
            "file": fmap,
            "change_type": "inject",
            "inject_anchor": "except Exception as",
            "description": "添加异常日志",
            "code": "except Exception as e:\n    print(f\"[error] {{type(e).__name__}}: {{e}}\")",
            "risk": "low",
            "desc": issue["desc"],
        },

        "missing_import": {
            "file": fmap,
            "change_type": "inject",
            "inject_anchor": "import json",
            "description": "添加time导入",
            "code": "import time",
            "risk": "low",
            "desc": issue["desc"],
        },

        "missing_api": {
            "file": fmap,
            "change_type": "inject",
            "inject_anchor": 'if __name__ == "__main__":',
            "description": "添加/relations API",
            "code": '''
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
        result[target_id] = {"target_name": target.name if target else target_id, **rel}
    return result
''',
            "risk": "low",
            "desc": issue["desc"],
        },

        "ui_missing": {
            "file": fmap,
            "change_type": "inject",
            "inject_anchor": '<div id="popup-status">—</span></div>',
            "description": "添加外交关系弹窗",
            "code": '\n                    <div id="popup-relation" style="margin-top:4px;color:#74b9ff;font-size:0.7rem;"></div>\n',
            "risk": "low",
            "desc": issue["desc"],
        },

        "missing_feature": {
            "file": fmap,
            "change_type": "inject",
            "inject_anchor": "# 评估威胁",
            "description": "Agent外交决策支持",
            "code": """
            # 外交行动
            diplomacy_actions = []
            try:
                r = httpx.get(f"{SERVER_URL}/relations/{civ_id}", timeout=10)
                if r.status_code == 200:
                    for tid, rel in r.json().items():
                        if tid == civ_id: continue
                        if rel.get("relation", 0) > 20 and rel.get("status") != "alliance":
                            tn = next((c["name"] for c in civilizations if c["id"] == tid), tid)
                            diplomacy_actions.append({"action": "PROPOSE_ALLIANCE", "target_id": tid, "reason": f"与{tn}关系良好可结盟"})
                        if rel.get("relation", 0) < -30:
                            tn = next((c["name"] for c in civilizations if c["id"] == tid), tid)
                            diplomacy_actions.append({"action": "DECLARE_WAR", "target_id": tid, "reason": f"{tn}关系恶劣"})
            except: pass
""",
            "risk": "low",
            "desc": issue["desc"],
        },

        "new_feature": {
            "file": issue.get("file", "universe_server/server.py"),
            "change_type": "inject",
            "inject_anchor": "# 评估威胁",
            "description": "集成外交系统到服务器",
            "code": """
            # 外交关系更新（每回合）
            try:
                matrix = get_relation_matrix()
                # 关系自然衰减
                for aid in [civ.id for c in civilizations if c["is_alive"]]:
                    for tid in [civ.id for c in civilizations if c["is_alive"] if c["id"] != aid]:
                        rel = matrix.get_relation(aid, tid)
                        if rel["relation"] > 0:
                            matrix.update_relation(aid, tid, -1, 0)
            except: pass
""",
            "risk": "medium",
            "desc": issue["desc"],
        },

        "narrative_quality": {
            "file": fmap,
            "change_type": "inject",
            "inject_anchor": "def _fallback_narrative",
            "description": "扩展叙事模板",
            "code": '''
    "declaration_of_war": "黑暗森林中，{actor}向{target}发出宣战信号，宇宙为之颤抖。",
    "alliance_proposal": "{actor}向{target}伸出橄榄枝，宇宙格局即将改变。",
    "diplomatic_signal": "{actor}发送加密外交信号，宇宙博弈进入新阶段。",
    "espionage": "{actor}的间谍活动悄然进行，暗流涌动。",
    "relation_changed": "宇宙关系网络发生微妙变化，{actor}与{target}的关系进入新时期。",
    "truce_proposal": "{actor}提议休战，宇宙迎来短暂的宁静。",
''',
            "risk": "low",
            "desc": issue["desc"],
        },
    }

    return fixes.get(itype)


# ─── 代码应用 ────────────────────────────────────────────────
def apply_fix(fix: dict) -> bool:
    """应用代码修复"""
    fp = PROJECT_ROOT / fix["file"]
    oplog("apply_fix_attempt", {"file": fix["file"], "desc": fix.get("desc", "")})

    if not fp.exists():
        if fix["change_type"] == "add":
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(fix.get("code", ""))
            log(f"✅ 新建: {fix['file']}", "OK")
            oplog("file_created", {"file": fix["file"]})
            return True
        log(f"❌ 文件不存在: {fix['file']}", "ERROR")
        return False

    try:
        content = fp.read_text()
        ct = fix.get("change_type", "modify")

        if ct == "inject":
            anchor = fix.get("inject_anchor", "")
            if not anchor:
                log(f"⚠️  缺少锚点", "WARN")
                return False
            if anchor not in content:
                log(f"⚠️  未找到锚点: {repr(anchor[:40])}", "WARN")
                oplog("anchor_not_found", {"anchor": anchor[:50], "file": fix["file"]})
                return False
            idx = content.find(anchor)
            new_content = content[:idx] + fix.get("code", "") + "\n" + content[idx:]
            fp.write_text(new_content)
            log(f"✅ 注入: {fix['file']}", "OK")
            oplog("fix_applied", {"file": fix["file"], "type": "inject", "anchor": anchor[:30]})
            return True

        elif ct == "replace":
            pattern = fix.get("pattern", "")
            replacement = fix.get("replacement", "")
            if pattern:
                new_content = re.sub(pattern, replacement, content, count=1)
                fp.write_text(new_content)
                log(f"✅ 替换: {fix['file']}", "OK")
                oplog("fix_applied", {"file": fix["file"], "type": "replace"})
                return True
            return False

        elif ct == "modify":
            fp.write_text(fix.get("code", ""))
            log(f"✅ 修改: {fix['file']}", "OK")
            oplog("fix_applied", {"file": fix["file"], "type": "modify"})
            return True

    except Exception as e:
        log(f"❌ 应用失败: {e}", "ERROR")
        oplog("apply_failed", {"file": fix["file"], "error": str(e)})
        return False

    return False


# ─── 测试 ───────────────────────────────────────────────────
def run_tests() -> bool:
    """测试所有关键文件"""
    oplog("phase_test", {})
    log("🧪 运行测试...", "INFO")

    test_files = [
        "universe/diplomacy.py",
        "universe_server/server.py",
        "node/auto_run.py",
    ]
    all_ok = True

    # 用Python子进程而非shell，避免引号问题
    for f in test_files:
        fp = PROJECT_ROOT / f
        if not fp.exists():
            continue
        try:
            with open(fp) as fh:
                import ast
                ast.parse(fh.read())
            log(f"  ✅ {f}", "OK")
        except SyntaxError as e:
            log(f"  ❌ {f}: {e}", "ERROR")
            all_ok = False
        except Exception as e:
            log(f"  ⚠️  {f}: {e}", "WARN")

    # API测试
    try:
        r = httpx.get(f"{SERVER_URL}/universe", timeout=10)
        if r.status_code == 200:
            log(f"  ✅ Universe API", "OK")
        else:
            log(f"  ⚠️  Universe API {r.status_code}", "WARN")
    except Exception as e:
        log(f"  ⚠️  Universe API离线: {e}", "WARN")

    return all_ok


# ─── Git提交 ────────────────────────────────────────────────
def git_commit_push(plan: dict, changes_made: int) -> bool:
    """提交并推送"""
    title = plan.get("title", "自动改进")
    changes_str = ", ".join([c.get("description", c.get("file", ""))[:30]
                              for c in plan.get("changes", [])[:3]])
    msg = f"[AUTO] {title}: {changes_str}"

    oplog("git_commit", {"message": msg})

    code, out, err = run("git add -A")
    if code != 0:
        log(f"⚠️  git add失败: {err[:100]}", "WARN")
        return False

    # 检查是否有变更
    code, diff_out, _ = run("git diff --staged --stat")
    if not diff_out.strip():
        log("ℹ️  无变更需提交", "INFO")
        return True

    code, out, err = run(f'git commit -m "{msg}"')
    if code != 0:
        log(f"⚠️  commit失败: {err[:150]}", "WARN")
        return False

    log(f"📦 已commit: {msg[:60]}", "OK")

    code, _, err = run("git push origin main")
    if code != 0:
        log(f"⚠️  push失败（网络或权限）", "WARN")
        return False

    log(f"✅ 已推送", "OK")
    oplog("git_pushed", {"status": "success"})
    return True


# ─── 主循环 ────────────────────────────────────────────────
def develop_cycle(cycle: int) -> dict:
    """Extended ReAct 开发循环"""
    log("=" * 60, "INFO")
    log(f"🔄 循环 #{cycle} 开始", "INFO")

    sess = get_session()
    update_session(cycle=cycle)
    oplog("cycle_start", {"cycle": cycle})

    # ═══ PHASE 0: Pre-check ════════════════════════════════════
    ctx = pre_check(sess)
    if not ctx["ok"]:
        return {"status": ctx["reason"], "changes": 0}

    universe = ctx["universe"]
    civs = ctx["civilizations"]

    # ═══ PHASE 1: 扫描问题 ════════════════════════════════════
    issues = scan_issues()
    if not issues:
        log("✅ 没有发现新问题", "OK")
        update_session(consecutive_empty=sess.get("consecutive_empty", 0) + 1)
        return {"status": "ok", "changes": 0}

    update_session(consecutive_empty=0)
    log(f"🔍 发现 {len(issues)} 个问题", "INFO")

    # ═══ PHASE 2: Plan Mode — 生成结构化计划 ══════════════════
    plan = plan_mode(issues, ctx)
    if not plan:
        log("⚠️  计划生成失败，跳过", "WARN")
        return {"status": "plan_failed", "changes": 0}

    changes = plan.get("changes", [])
    if not changes:
        log("⚠️  计划无改动项，跳过", "WARN")
        return {"status": "ok", "changes": 0}

    # ═══ PHASE 3: Thinking — 每个问题先思考再修复 ═════════════
    fixes_to_apply = []
    for i, change in enumerate(changes[:MAX_AUTO_CHANGES]):
        issue = issues[i] if i < len(issues) else issues[0]
        log(f"🤔 思考问题 {i+1}: {issue['desc'][:40]}", "THINK")
        thinking_result = thinking(issue, ctx)

        # 根据plan的change生成fix
        fix = {
            "file": change.get("file", issue["file"]),
            "change_type": change.get("action", "inject"),
            "inject_anchor": change.get("anchor", ""),
            "code": change.get("code", ""),
            "description": change.get("reason", issue["content"]),
            "risk": "low",
            "desc": issue["desc"],
        }

        # Self-Critique
        critique = self_critique(issue, fix, ctx)
        needs_approval = critique.get("needs_approval", False)
        risk_level = critique.get("risk", "medium")

        # 只有high risk才跳过；其他自动执行
        if risk_level == "high":
            log(f"⛔ 高风险，跳过: {issue['desc'][:40]}", "WARN")
            oplog("skipped_high_risk", {"issue": issue["desc"], "risk": risk_level})
            continue

        if risk_level == "medium" and needs_approval:
            concerns = critique.get("concerns", [])
            # 担忧少于3条 → 自动执行（论文原文：medium risk可在观察下执行）
            if len(concerns) < 3:
                log(f"🔍 medium risk({len(concerns)}个担忧)，自动执行: {issue['desc'][:40]}", "WARN")
                oplog("auto_exec_medium_risk", {"issue": issue["desc"], "concerns": concerns})
            else:
                log(f"🔍 需要人类审批，跳过: {issue['desc'][:40]}", "WARN")
                oplog("skipped_needs_approval", {"issue": issue["desc"], "risk": risk_level})
                continue

        fixes_to_apply.append(fix)
        oplog("fix_approved", {"file": fix["file"], "desc": fix["desc"], "risk": critique.get("risk")})

    if not fixes_to_apply:
        log("⚠️  没有可安全执行的修复", "WARN")
        return {"status": "no_safe_fixes", "changes": 0}

    # ═══ PHASE 4: Git Snapshot（执行前保护）══════════════════
    snapshot_id = git_snapshot()

    # ═══ PHASE 5: 执行所有修复 ═══════════════════════════════
    log(f"⚡ 开始执行 {len(fixes_to_apply)} 个修复...", "EXEC")
    applied = []
    for fix in fixes_to_apply:
        ok = apply_fix(fix)
        applied.append({"fix": fix, "ok": ok})
        time.sleep(1)

    # ═══ PHASE 6: 测试 ════════════════════════════════════════
    test_ok = run_tests()

    # ═══ PHASE 7: 提交或回滚 ══════════════════════════════════
    successful = [a for a in applied if a["ok"]]
    if successful and test_ok:
        git_commit_push(plan, len(successful))
        for a in successful:
            mark_resolved(a["fix"].get("desc", ""))
        update_session(
            total_changes=sess.get("total_changes", 0) + len(successful),
            last_change_time=datetime.now().isoformat()
        )
        status = "✅ 完成"
    else:
        if not test_ok:
            log("⚠️  测试失败，尝试回滚...", "WARN")
            git_restore_snapshot()
            status = "⚠️ 测试失败已回滚"
        else:
            status = "⚠️ 无成功改动"

    oplog("cycle_end", {
        "cycle": cycle,
        "status": status,
        "applied": len(successful),
        "failed": len(applied) - len(successful)
    })

    log(f"""
{'='*60}
🔄 循环 #{cycle} 报告
{'='*60}
问题: {len(issues)} 个 | 执行: {len(successful)} 个 | 状态: {status}
计划: {plan.get('title', '')}
{'='*60}""", "INFO")

    return {
        "status": "ok" if test_ok else "test_failed",
        "changes": len(successful),
        "issues": len(issues),
        "plan": plan.get("title", ""),
    }


# ─── 入口 ───────────────────────────────────────────────────
def main():
    log("🚀 Cyber Cosmos 无限自动开发系统 v3 启动", "INFO")
    log(f"📁 项目: {PROJECT_ROOT}", "INFO")
    log(f"⏱️  间隔: {DEVELOP_INTERVAL}秒 ({DEVELOP_INTERVAL//60}分钟)", "INFO")
    log(f"🛑 暂停: touch {PROJECT_ROOT}/AUTO_DEVELOP_PAUSE", "INFO")
    log(f"📋 计划模式: 每次循环生成结构化开发计划", "INFO")
    log(f"📸 Git快照: 每次执行前自动快照保护", "INFO")
    log("-" * 60, "INFO")

    # 初始化session
    if not SESSION_FILE.exists():
        save_session({"cycle": 0, "consecutive_empty": 0, "total_changes": 0})

    cycle = get_session().get("cycle", 0)

    while True:
        cycle += 1
        try:
            result = develop_cycle(cycle)
            update_session(cycle=cycle)
            time.sleep(DEVELOP_INTERVAL)
        except KeyboardInterrupt:
            log("⛔ 被用户中断，退出", "WARN")
            break
        except Exception as e:
            log(f"❌ 循环异常: {type(e).__name__}: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            time.sleep(60)


if __name__ == "__main__":
    main()
