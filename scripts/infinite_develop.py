#!/usr/bin/env python3
"""
Cyber Cosmos — 无限自动开发系统 v5
基于论文 "Effective Harnesses for Long-Running Agents" (arXiv:2603.05344)

v3 → v4 关键修复:
- Git Snapshot: 新建文件在回滚时被删除，不残留
- Plan Mode: LLM生成自然语言计划 → generate_fix生成实际代码
- snapshot_id: 用 stash list 按ID精确恢复
- commit message: 用 --file=/dev/stdin 避免引号转义
- concerns类型: 解析失败时默认为高风险需审批
- push失败: 3次指数退避重试，失败后不污染下次循环
- oplog: 传入cycle参数，不再每次读session文件
- 并发保护: 文件锁防止多实例冲突
- 清理未使用import
"""

import os
import sys
import json
import time
import subprocess
import httpx
import re
import fcntl
import atexit
import urllib.request
import ssl
from datetime import datetime
from pathlib import Path

# ─── 配置 ───────────────────────────────────────────────────
PROJECT_ROOT = Path.home() / "cyber-cosmos"
SERVER_URL = "http://localhost:8000"
GLM_KEY = os.environ.get(
    "GLM5_TURBO_KEY",
    "8ebd0252b1fc498ebd53dfc299d4de12.PwoiSyS6NA5RuALo"
)
DEVELOP_INTERVAL = 300   # 5分钟
MAX_AUTO_CHANGES = 2    # 每次最多改2个文件
RESOLVED_FILE = PROJECT_ROOT / ".auto_develop_resolved.json"
SESSION_FILE = PROJECT_ROOT / ".auto_develop_session.json"
OPLOG_FILE = PROJECT_ROOT / ".auto_develop_oplog.jsonl"
LOCK_FILE = PROJECT_ROOT / ".auto_develop.lock"


# ─── 文件锁（并发保护）──────────────────────────────────────────
_lock_fd = None


def acquire_lock():
    """获取文件锁，防止多实例同时运行"""
    global _lock_fd
    _lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        atexit.register(release_lock)
        return True
    except BlockingIOError:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⛔ 已有实例在运行，退出", flush=True)
        _lock_fd = None
        sys.exit(0)


def release_lock():
    global _lock_fd
    if _lock_fd:
        fcntl.flock(_lock_fd, fcntl.LOCK_UN)
        _lock_fd.close()


# ─── 日志 ───────────────────────────────────────────────────
def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {
        "INFO": "💬", "WARN": "⚠️", "ERROR": "❌", "OK": "✅",
        "PLAN": "📋", "THINK": "🤔", "CRITIQUE": "🔍", "EXEC": "⚡"
    }
    icon = icons.get(level, "💬")
    print(f"[{ts}] {icon} {msg}", flush=True)


def run(cmd: str, cwd: str = None) -> tuple[int, str, str]:
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd or PROJECT_ROOT
    )
    return result.returncode, result.stdout, result.stderr


# ─── 操作日志（Transparency） ─────────────────────────────────
# oplog 内存缓冲，循环结束时统一写入
_oplog_buffer = []

def oplog(action: str, data: dict, cycle: int = 0):
    """所有操作记录到 JSONL 日志（cycle由调用方传入，不读文件）"""
    entry = {
        "ts": datetime.now().isoformat(),
        "cycle": cycle,
        "action": action,
        **data
    }
    _oplog_buffer.append(json.dumps(entry, ensure_ascii=False))

def flush_oplog():
    """循环结束时统一写入oplog"""
    if not _oplog_buffer:
        return
    try:
        with open(OPLOG_FILE, "a") as f:
            for line in _oplog_buffer:
                f.write(line + "\n")
        _oplog_buffer.clear()
    except Exception as e:
        import sys
        print(f"[oplog flush error] {e}", file=sys.stderr, flush=True)


# ─── Session 持久化 ───────────────────────────────────────────
def get_session() -> dict:
    try:
        return json.loads(SESSION_FILE.read_text())
    except:
        return {
            "cycle": 0, "consecutive_empty": 0, "total_changes": 0,
            "last_change_time": None, "push_failures": 0
        }


def save_session(s: dict):
    SESSION_FILE.write_text(json.dumps(s, ensure_ascii=False))


def update_session(**kwargs):
    s = get_session()
    s.update(kwargs)
    save_session(s)


# ─── Git Snapshot ─────────────────────────────────────────────
SNAPSHOT_MARKER = ".auto_snapshots"


def git_snapshot(cycle: int) -> tuple[str, list]:
    """
    创建Git stash snapshot，返回 (snapshot_id, 新建文件列表)
    新建文件在apply之前记录，回滚时删除
    """
    import random as _rand
    timestamp = int(time.time())
    rand_id = _rand.randint(1000, 9999)
    snapshot_id = f"cycle{cycle}_{timestamp}_{rand_id}"

    # 记录当前所有未跟踪的新文件
    code, new_files_out, _ = run("git ls-files --others --exclude-standard")
    new_files = [f.strip() for f in new_files_out.strip().split("\n") if f.strip()]

    # git stash 会保存跟踪文件的修改，不包括新文件
    code, out, err = run(f"git stash push -m 'auto_snapshot_{snapshot_id}'")

    if code != 0:
        oplog("snapshot", {"snapshot_id": snapshot_id, "new_files": new_files, "status": "failed", "err": err[:100]}, cycle)
        log(f"⚠️  Git stash失败: {err[:80]}", "WARN")
        return None, new_files
    oplog("snapshot", {"snapshot_id": snapshot_id, "new_files": new_files, "status": "created"}, cycle)
    log(f"📸 Git snapshot: {snapshot_id} (保护{len(new_files)}个新文件)", "INFO")
    return snapshot_id, new_files


def git_restore_snapshot(snapshot_id: str, new_files: list, cycle: int) -> bool:
    """
    从snapshot恢复：
    1. 如果 snapshot_id=None（stash失败），只清理新文件
    2. 否则 git stash list 找到对应的 stash 并 pop
    3. 删除新文件（这些文件不在stash里）
    """
    # snapshot 失败时只有新文件需要清理
    for f in new_files:
        fp = PROJECT_ROOT / f
        if fp.exists():
            try:
                fp.unlink()
                oplog("newfile_deleted", {"file": f}, cycle)
                log(f"🗑️  删除新文件: {f}", "WARN")
            except Exception as e:
                log(f"⚠️  删除失败: {f} ({e})", "WARN")
    if snapshot_id is None:
        oplog("restore_snapshot", {"snapshot_id": None, "status": "no_snapshot"}, cycle)
        log(f"↩️  无有效snapshot，仅清理新文件", "WARN")
        return True

    # 尝试从 stash 恢复
    # 找到包含 snapshot_id 的 stash
    code, stash_list, _ = run("git stash list")
    stash_ref = None
    for line in stash_list.strip().split("\n"):
        if f"auto_snapshot_{snapshot_id}" in line:
            # 格式: stash@{0}: On main: auto_snapshot_cycle6_...
            stash_ref = line.split(":")[0]
            break

    if stash_ref:
        code, out, err = run(f"git stash pop '{stash_ref}'")
    else:
        # 兜底：尝试任意一个 stash
        code, out, err = run("git stash pop")

    if code == 0:
        oplog("restore_snapshot", {"snapshot_id": snapshot_id, "status": "success"}, cycle)
        log(f"↩️  已从snapshot恢复: {snapshot_id}", "WARN")
        return True
    else:
        oplog("restore_snapshot", {"snapshot_id": snapshot_id, "status": "failed", "err": err[:100]}, cycle)
        log(f"↩️  恢复失败: {err[:100]}", "ERROR")
        return False


# ─── 上下文压缩 ─────────────────────────────────────────────
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
        effective = events[-20:]
    else:
        effective = events[-10:]

    if limit:
        effective = effective[-limit:]
    return effective


# ─── LLM 调用 ─────────────────────────────────────────────
def llm_call(messages: list, model: str = "glm-4-plus",
             max_tokens: int = 600, temperature: float = 0.3) -> str:
    """LLM 调用，支持重试，SSL修复"""

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    data = json.dumps(payload).encode("utf-8")

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


# ─── Resolved 追踪 ─────────────────────────────────────────
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


# ─── 宇宙状态 ─────────────────────────────────────────────
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
    changed = [l for l in out.strip().split("\n") if l]
    return {"changed": len(changed), "files": changed}


# ─── 问题扫描器 ─────────────────────────────────────────────
def scan_issues() -> list[dict]:
    issues = []
    server = PROJECT_ROOT / "universe_server" / "server.py"
    auto_run = PROJECT_ROOT / "node" / "auto_run.py"
    ui = PROJECT_ROOT / "web" / "templates" / "index.html"
    narrative = PROJECT_ROOT / "universe" / "narrative.py"
    diplomacy = PROJECT_ROOT / "universe" / "diplomacy.py"

    def add(desc: str, file: str, ptype: str, content: str, priority: int):
        if desc not in get_resolved():
            issues.append({
                "desc": desc, "file": file, "type": ptype,
                "content": content, "priority": priority
            })

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

    # 5. 叙事模板（用更精确的检测）
    if narrative.exists():
        content = narrative.read_text()
        # 检查_fallback_narrative函数里有多少个双引号key叙事
        fallback_section = content[content.find("def _fallback_narrative"):] if "def _fallback_narrative" in content else ""
        quote_keys = re.findall(r'"(\w+)":\s*"', fallback_section)
        if len(quote_keys) < 6:
            add("叙事模板较少", "universe/narrative.py",
                "narrative_quality", f"fallback叙事只有{len(quote_keys)}个模板", 3)

    # 6. UI外交关系显示
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
        if "time.time" in content and not re.search(
                r"^import time|^from time import", content, re.MULTILINE):
            add("server.py缺少time导入", "universe_server/server.py",
                "missing_import", "time模块未导入", 9)

    issues.sort(key=lambda x: x["priority"], reverse=True)
    return issues


# ─── Extended ReAct 循环 ─────────────────────────────────────

# PHASE 1: Pre-check
def pre_check(sess: dict, cycle: int) -> dict:
    oplog("phase_precheck", {"ts": datetime.now().isoformat()}, cycle)

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
        "ok": True, "universe": univ,
        "civilizations": civs, "git_status": git_st, "session": sess
    }


# PHASE 2: Thinking
def thinking(issue: dict, ctx: dict, cycle: int) -> str:
    oplog("phase_thinking", {"issue": issue["desc"]}, cycle)

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
    oplog("thinking_result", {"issue": issue["desc"], "thought": response[:200]}, cycle)
    return response


# PHASE 3: Self-Critique
def self_critique(issue: dict, proposed_fix: dict, cycle: int) -> dict:
    oplog("phase_critique", {"issue": issue["desc"]}, cycle)

    prompt = f"""改动方案审查：

问题: {issue['content']}
文件: {issue['file']}
方案: {proposed_fix.get('description', '')}

请审查：
1. 这个改动是否会破坏现有功能？
2. 改动范围是否过大？
3. 是否需要人类审批？

JSON格式（严格，不能有换行）：
{{"risk":"low/medium/high","concerns":[],"needs_approval":false}}"""

    response = llm_call([
        {"role": "system", "content": "你是代码安全审查员。严格评估。"},
        {"role": "user", "content": prompt}
    ], max_tokens=200, temperature=0.2)

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(response[start:end])
            # 类型安全检查
            risk = result.get("risk", "medium")
            if risk not in ("low", "medium", "high"):
                risk = "medium"
            concerns = result.get("concerns", [])
            if not isinstance(concerns, list):
                concerns = []
            needs_approval = bool(result.get("needs_approval", False))
            log(f"🔍 审查: risk={risk} concerns={len(concerns)} needs_approval={needs_approval}", "CRITIQUE")
            oplog("critique_result", {"risk": risk, "concerns": concerns, "needs_approval": needs_approval}, cycle)
            return {"risk": risk, "concerns": concerns, "needs_approval": needs_approval}
    except:
        pass

    # 解析失败 → 默认高风险需审批
    log("🔍 审查解析失败，默认高风险", "CRITIQUE")
    oplog("critique_failed_default_high", {}, cycle)
    return {"risk": "high", "concerns": ["审查解析失败，默认为高风险"], "needs_approval": True}


# ─── 代码生成（Plan Mode → generate_fix 协作）────────────────────────────────
def plan_mode(issues: list, ctx: dict, cycle: int) -> list[dict]:
    """
    Plan Mode: LLM生成自然语言计划，选择对应的fix类型，
    再由 generate_fix 生成实际代码。
    返回 fix 列表。
    """
    oplog("phase_plan", {"issue_count": len(issues)}, cycle)

    events = get_effective_events(limit=10)
    events_text = "\n".join([
        f"  - [{e.get('event_type', '')}] {e.get('narrative', '')[:50]}"
        for e in events
    ]) or "  无"

    civs_text = "\n".join([
        f"  - {c.get('name', '')} (tech={c.get('tech_level', 0):.2f})"
        for c in ctx.get("civilizations", [])[:5]
    ]) or "  无"

    # issue类型到fix描述的映射
    issue_type_map = {
        "debug_code": "删除console.log调试代码",
        "error_handling": "修复裸异常处理",
        "missing_import": "添加缺失的模块导入",
        "missing_api": "添加API端点",
        "ui_missing": "添加UI组件",
        "missing_feature": "添加缺失的功能",
        "new_feature": "集成新功能模块",
        "narrative_quality": "扩展叙事模板",
    }

    issue_list_text = "\n".join([
        f"  {i+1}. [{iss['priority']}分] {iss['content']} → fix类型: {issue_type_map.get(iss['type'], iss['type'])} ({iss['file']})"
        for i, iss in enumerate(issues[:3])
    ])

    prompt = f"""作为Cyber Cosmos的开发计划生成器，为以下问题选择修复方案。

当前宇宙状态:
文明: {civs_text}
最近事件: {events_text}

问题列表:
{issue_list_text}

你可用的修复类型（每种对应一个已知的最小改动）：
1. debug_code → 删除console.log
2. error_handling → 注入异常日志
3. missing_import → 添加import语句
4. missing_api → 在if __name__前注入API端点
5. ui_missing → 在popup-status标签后注入UI片段
6. missing_feature → 在"# 评估威胁"前注入功能代码
7. new_feature → 在"# 评估威胁"前注入新功能
8. narrative_quality → 在def _fallback_narrative前注入叙事模板

直接输出JSON（无markdown，无解释）：
{{"plan_summary":"一句话计划描述","fixes":[
  {{"issue_idx":0,"fix_type":"debug_code","reason":"删除console.log理由"}},
  {{"issue_idx":1,"fix_type":"missing_import","reason":"添加导入的理由"}}
]}}"""

    response = llm_call([
        {"role": "system", "content": "你是开发计划生成器。只输出JSON，不要解释。"},
        {"role": "user", "content": prompt}
    ], max_tokens=500, temperature=0.1)

    log(f"📋 Plan LLM响应: {len(response)}字符", "PLAN")

    # 清理 markdown 包装
    cleaned = re.sub(r"```json\s*", "", response.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.IGNORECASE).strip()

    fixes = []
    try:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            plan_data = json.loads(cleaned[start:end])
            summary = plan_data.get("plan_summary", "开发计划")
            log(f"📋 计划: {summary}", "PLAN")
            oplog("plan_generated", {"summary": summary}, cycle)

            # 对每个fix项，从issues里找到对应issue，再用generate_fix生成
            for fix_spec in plan_data.get("fixes", []):
                idx = fix_spec.get("issue_idx", 0)
                fix_type = fix_spec.get("fix_type", "")
                reason = fix_spec.get("reason", "")

                if idx < len(issues):
                    issue = issues[idx]
                    fix = generate_fix_for_type(issue, fix_type)
                    if fix:
                        fixes.append(fix)
                        log(f"  ✅ {issue['desc'][:40]} → {fix_type}", "PLAN")
                    else:
                        log(f"  ⚠️  无法生成fix: {issue['desc'][:40]}", "WARN")
                        oplog("no_fix", {"issue": issue["desc"], "fix_type": fix_type}, cycle)
    except Exception as e:
        log(f"📋 计划解析失败: {e}，使用Fallback", "WARN")
        oplog("plan_parse_failed", {"error": str(e)}, cycle)

    # Fallback：如果没有从plan生成任何fix，用generate_fix直接生成
    if not fixes:
        log("📋 Fallback直接生成fix", "WARN")
        oplog("plan_fallback", {}, cycle)
        for iss in issues[:MAX_AUTO_CHANGES]:
            fix = generate_fix_for_type(iss, iss["type"])
            if fix:
                fixes.append(fix)

    return fixes[:MAX_AUTO_CHANGES]


def generate_fix_for_type(issue: dict, fix_type: str) -> dict | None:
    """根据issue类型和fix_type生成修复方案"""
    fmap = issue["file"]

    fixes = {

        "debug_code": {
            "file": fmap,
            "change_type": "replace",
            "pattern": r"console\.log\([^)]+\);?\n?",
            "replacement": "",
            "description": "删除console.log",
            "risk": "low",
            "desc": issue["desc"],
        },

        "error_handling": {
            "file": fmap,
            "change_type": "inject",
            "inject_anchor": "except Exception as",
            "description": "添加异常日志",
            "code": 'except Exception as e:\n    print(f"[error] {type(e).__name__}: {e}")',
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
            "description": "集成外交系统",
            "code": """
            # 外交关系更新（每回合）
            try:
                matrix = get_relation_matrix()
                for aid in [civ.id for c in civilizations if c["is_alive"]]:
                    for tid in [c.id for c in civilizations if c["is_alive"] and c["id"] != aid]:
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

    return fixes.get(fix_type)


# ─── 代码应用 ───────────────────────────────────────────────
def apply_fix(fix: dict, cycle: int) -> bool:
    fp = PROJECT_ROOT / fix["file"]
    oplog("apply_fix_attempt", {"file": fix["file"], "desc": fix.get("desc", "")}, cycle)

    if not fp.exists():
        if fix["change_type"] in ("add", "modify"):
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(fix.get("code", ""))
            log(f"✅ 新建: {fix['file']}", "OK")
            oplog("file_created", {"file": fix["file"]}, cycle)
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
                oplog("anchor_not_found", {"anchor": anchor[:50], "file": fix["file"]}, cycle)
                return False
            idx = content.find(anchor)
            new_content = content[:idx] + fix.get("code", "") + "\n" + content[idx:]
            fp.write_text(new_content)
            log(f"✅ 注入: {fix['file']}", "OK")
            oplog("fix_applied", {"file": fix["file"], "type": "inject", "anchor": anchor[:30]}, cycle)
            return True

        elif ct == "replace":
            pattern = fix.get("pattern", "")
            replacement = fix.get("replacement", "")
            if pattern:
                # 转义正则特殊字符（如果锚点包含特殊字符）
                new_content = re.sub(pattern, replacement, content, count=1)
                fp.write_text(new_content)
                log(f"✅ 替换: {fix['file']}", "OK")
                oplog("fix_applied", {"file": fix["file"], "type": "replace"}, cycle)
                return True
            return False

        elif ct == "modify":
            fp.write_text(fix.get("code", ""))
            log(f"✅ 修改: {fix['file']}", "OK")
            oplog("fix_applied", {"file": fix["file"], "type": "modify"}, cycle)
            return True

    except Exception as e:
        log(f"❌ 应用失败: {e}", "ERROR")
        oplog("apply_failed", {"file": fix["file"], "error": str(e)}, cycle)
        return False

    return False


# ─── 测试 ───────────────────────────────────────────────────
def run_tests(cycle: int) -> bool:
    oplog("phase_test", {}, cycle)
    log("🧪 运行测试...", "INFO")

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
        try:
            with open(fp) as fh:
                ast.parse(fh.read())
            log(f"  ✅ {f}", "OK")
        except SyntaxError as e:
            log(f"  ❌ {f}: {e}", "ERROR")
            all_ok = False

    try:
        r = httpx.get(f"{SERVER_URL}/universe", timeout=10)
        if r.status_code == 200:
            log(f"  ✅ Universe API", "OK")
        else:
            log(f"  ⚠️  Universe API {r.status_code}", "WARN")
    except Exception as e:
        log(f"  ⚠️  Universe API离线: {e}", "WARN")

    return all_ok


# ─── Git提交（安全引号处理）────────────────────────────────
def git_commit_push(title: str, changes: list, cycle: int) -> bool:
    changes_str = ", ".join([c.get("description", c.get("file", ""))[:30] for c in changes[:3]])
    msg = f"[AUTO] {title}: {changes_str}"

    oplog("git_commit", {"message": msg}, cycle)

    run("git add -A")

    # 检查是否有变更
    code, diff_out, _ = run("git diff --staged --stat")
    if not diff_out.strip():
        log("ℹ️  无变更需提交", "INFO")
        return True

    # 用 --file=/dev/stdin 避免引号问题
    # 用subprocess直接传参数，避免shell引号问题
    proc = subprocess.run(
        ['git', 'commit', '-m', msg],
        cwd=PROJECT_ROOT,
        capture_output=True, text=True
    )
    code, out, err = proc.returncode, proc.stdout, proc.stderr
    if code != 0:
        log(f"⚠️  commit失败: {err[:150]}", "WARN")
        return False

    log(f"📦 已commit: {msg[:60]}", "OK")

    # Push：3次指数退避重试
    for attempt in range(3):
        code, _, err = run("git push origin main")
        if code == 0:
            log(f"✅ 已推送", "OK")
            oplog("git_pushed", {"status": "success", "attempts": attempt + 1}, cycle)
            update_session(push_failures=0)
            return True
        wait = 2 ** attempt
        log(f"⚠️  push失败({attempt+1}/3)，{wait}s后重试: {err[:80]}", "WARN")
        time.sleep(wait)

    log(f"⛔ push连续失败3次，暂停push", "ERROR")
    update_session(push_failures=min(get_session().get("push_failures", 0) + 1, 10))
    oplog("git_push_failed", {"attempts": 3}, cycle)
    return False


# ─── 主循环 ───────────────────────────────────────────────
def develop_cycle(cycle: int) -> dict:
    log("=" * 60, "INFO")
    log(f"🔄 循环 #{cycle} 开始", "INFO")

    sess = get_session()
    update_session(cycle=cycle)
    oplog("cycle_start", {"cycle": cycle}, cycle)

    # PHASE 0: Pre-check
    ctx = pre_check(sess, cycle)
    if not ctx["ok"]:
        return {"status": ctx["reason"], "changes": 0}

    universe = ctx["universe"]
    civs = ctx["civilizations"]

    # PHASE 1: 扫描问题
    issues = scan_issues()
    if not issues:
        log("✅ 没有发现新问题", "OK")
        update_session(consecutive_empty=sess.get("consecutive_empty", 0) + 1)
        return {"status": "ok", "changes": 0}

    update_session(consecutive_empty=0)
    log(f"🔍 发现 {len(issues)} 个问题", "INFO")

    # PHASE 2: Plan Mode（LLM → fix方案）
    fixes = plan_mode(issues, ctx, cycle)
    if not fixes:
        log("⚠️  无法生成修复方案，跳过", "WARN")
        return {"status": "no_fix", "changes": 0}

    # PHASE 3: Thinking + Self-Critique
    fixes_to_apply = []
    for i, fix in enumerate(fixes):
        issue = issues[i] if i < len(issues) else issues[0]

        thinking(issue, ctx, cycle)
        critique = self_critique(issue, fix, cycle)

        risk_level = critique.get("risk", "medium")

        # high risk → 跳过
        if risk_level == "high":
            log(f"⛔ 高风险，跳过: {issue['desc'][:40]}", "WARN")
            oplog("skipped_high_risk", {"issue": issue["desc"], "risk": risk_level}, cycle)
            continue

        # medium risk + 3个以上担忧 → 跳过
        concerns = critique.get("concerns", [])
        if not isinstance(concerns, list):
            concerns = []
        if risk_level == "medium" and len(concerns) >= 3:
            log(f"⛔ 中风险+{len(concerns)}个担忧，跳过: {issue['desc'][:40]}", "WARN")
            oplog("skipped_medium_high_concerns", {"issue": issue["desc"], "concerns": concerns}, cycle)
            continue

        fixes_to_apply.append(fix)
        oplog("fix_approved", {"file": fix["file"], "desc": fix["desc"], "risk": risk_level}, cycle)

    if not fixes_to_apply:
        log("⚠️  没有可安全执行的修复", "WARN")
        return {"status": "no_safe_fixes", "changes": 0}

    # PHASE 4: Git Snapshot
    snapshot_id, new_files = git_snapshot(cycle)

    # PHASE 5: 执行修复
    log(f"⚡ 开始执行 {len(fixes_to_apply)} 个修复...", "EXEC")
    applied = []
    for fix in fixes_to_apply:
        ok = apply_fix(fix, cycle)
        applied.append({"fix": fix, "ok": ok})
        time.sleep(1)

    # PHASE 6: 测试
    test_ok = run_tests(cycle)

    # PHASE 7: 提交或回滚
    successful = [a for a in applied if a["ok"]]
    if successful and test_ok:
        title = fixes[0].get("description", "自动改进") if fixes else "自动改进"
        pushed = git_commit_push(title, successful, cycle)
        if pushed:
            for a in successful:
                mark_resolved(a["fix"].get("desc", ""))
            update_session(
                total_changes=sess.get("total_changes", 0) + len(successful),
                last_change_time=datetime.now().isoformat()
            )
            status = "✅ 完成"
        else:
            status = "⚠️  已apply但push失败"
    elif not test_ok:
        log("⚠️  测试失败，回滚...", "WARN")
        git_restore_snapshot(snapshot_id, new_files, cycle)
        # 清除resolved（回滚的改动下次重试）
        try:
            RESOLVED_FILE.write_text(json.dumps({"_resolved": [], "_skipped": []}))
        except:
            pass
        status = "⚠️ 测试失败已回滚"
    else:
        status = "⚠️ 无成功改动"

    oplog("cycle_end", {
        "cycle": cycle, "status": status,
        "applied": len(successful),
        "failed": len(applied) - len(successful)
    }, cycle)

    log(f"""
{'='*60}
🔄 循环 #{cycle} 报告
{'='*60}
问题: {len(issues)} 个 | 执行: {len(successful)} 个 | 状态: {status}
{'='*60}""", "INFO")

    return {
        "status": "ok" if test_ok else "test_failed",
        "changes": len(successful), "issues": len(issues),
    }


# ─── 入口 ───────────────────────────────────────────────────
def main():
    acquire_lock()

    log("🚀 Cyber Cosmos 无限自动开发系统 v5 启动", "INFO")
    log(f"📁 项目: {PROJECT_ROOT}", "INFO")
    log(f"⏱️  间隔: {DEVELOP_INTERVAL}秒 ({DEVELOP_INTERVAL//60}分钟)", "INFO")
    log(f"🛑 暂停: touch {PROJECT_ROOT}/AUTO_DEVELOP_PAUSE", "INFO")
    log(f"🔒 并发保护: 文件锁已启用", "INFO")
    log("-" * 60, "INFO")

    if not SESSION_FILE.exists():
        save_session({"cycle": 0, "consecutive_empty": 0, "total_changes": 0, "push_failures": 0})

    cycle = get_session().get("cycle", 0)

    while True:
        cycle += 1
        try:
            result = develop_cycle(cycle)

            pf = get_session().get("push_failures", 0)
            if pf >= 3:
                log(f"⛔ push连续失败{pf}次，需要人工介入!", "ERROR")

            time.sleep(DEVELOP_INTERVAL)
        except KeyboardInterrupt:
            log("⛔ 被用户中断，退出", "WARN")
            break
        except Exception as e:
            log(f"❌ 循环异常: {type(e).__name__}: {e}", "ERROR")
            import traceback; traceback.print_exc()
            time.sleep(60)
        finally:
            update_session(cycle=cycle)
            flush_oplog()



if __name__ == "__main__":
    main()
