"""test_clone_kill_script: scripts/clone_kill.py(clone 域残留定点清理)守阵。

背景(2026-11-22): `dev.run --dry-run` 是守护循环(cli.py:305), 停后台任务只杀
bash/uv 包装链, venv python 子进程孤儿化继续持 state 锁、周期落盘 —— port_kill
的端口定位管不到非监听残留, clone_kill 按 cmdline 归属定点(判别见
pitfalls/ops/dev-run-dry-run-daemon-orphan.md)。拍板面: 判据/实杀 import 复用
port_kill 单点(不复制); 默认只列, 杀必须 --match + --yes 双闸; 自身 + 祖先链
硬排除; 目标后代连坐但逐个过闸(后代先杀); nt/posix 双支。

全部 monkeypatched/纯内存构造: taskkill/SIGKILL 从不真执行, 杀路径只测决策与
接线; POSIX 查询单元在环境层打桩(假 /proc 树 + os.name 钉 posix), 与
test_legacy_review4_scripts.py 的 port_kill 守阵同范式。用例纯内存构造, 不真跑
git 写操作、不连 qB、不写仓库外文件。

## 测试计划(每个测试函数一条, 后续批次往里追加)
- test_clone_kill_judgement_imports_port_kill_single_point: 静态钉 -- in_clone_domain/_kill_pid/REPO_ROOT 是 port_kill 同一对象(import 复用), clone_kill 源里不得再现归属判定/实杀定义/taskkill 字面量(复制一分就有了第二个判据演化点)
- test_clone_kill_select_candidates_matrix: 候选矩阵 -- 本 clone venv python 探针/uv shim(解释器在 clone 外但 cmdline 指回 clone 根)命中; 其它 clone/前缀同串变体/空 cmdline/相对 uv 包装(fail-closed)不命中; --match 小写子串过滤; 排除集剔除
- test_clone_kill_self_and_ancestors_excluded: 假自身 + 祖先链(bash/uv/python)全剔除(祖先不管归属与否); 祖先 raced exit(不在表)即停(尾 ppid 仍入排除集, 无害); ppid=0 与 PPID 成环不死循环
- test_clone_kill_descendant_closure_and_gate: 后代闭包按深度降序(后代先杀)再 pid 升序; clone 域外后代(explorer 形态)REFUSED(outside-repo)不杀, 其 clone 域后代仍过自己那道闸; 排除集内后代不进杀面
- test_clone_kill_main_list_only_default: 无参列全部候选、仅 --match 列命中子集, 两者零 _kill_pid 调用且 rc=0; 仅 --match 带「补 --yes」提示行
- test_clone_kill_main_kill_requires_match_and_yes: --yes 无 --match / --match 缺值 / --match --yes(旗标占值) / --match 空白值(空子串恒真 = 变相杀全部, 双闸拒收)一律 rc=2 且零扫描零杀
- test_clone_kill_main_self_exclusion_production_path: 自杀排除生产路径 -- 自身 pid(os.getpid 钉 10**9)以工具形态在表内、cmdline 含 clone 根与 match 词, 断言不出现于候选/杀行(此前全部用例注入 self_pid, 生产默认支零守卫)
- test_clone_kill_main_kill_flow_gates: 双闸齐备 -- 命中目标 + 过闸后代逐个杀(后代先杀), outside-repo 后代 WARNING+REFUSED 行且零实杀, rc=1; 无候选 rc=0; 扫描空表 fail-safe rc=1
- test_clone_kill_main_kill_failed_rc: _kill_pid 失败行透传 rc=1(与 port_kill 实杀失败面对称)
- test_clone_kill_scan_posix_reads_proc: 假 /proc 树 -- comm/cmdline/stat 全读出, comm 含括号空格时 ppid 用 rpartition 解析不歪, cmdline NUL 拼回空格, cmdline 缺失(raced exit)与 comm 空串的 pid 缺席, 非数字目录跳过
- test_clone_kill_scan_nt_parses_json: nt 支 -- 数组/单字典两形态归一, CommandLine null -> 空串, ParentProcessId 缺失 -> 0, 行缺 ProcessId/Name 整行跳过不炸, JSON 解析不动/非零 rc -> 空表(fail-safe)
- test_clone_kill_show_truncation: _show 边界 -- 160 内原样, 超长截 157+「...」(归属行展示单点)
- test_clone_kill_scan_edges_fail_safe: 扫描边角 -- nt stdout 空(rc=0)也空表; posix stat ppid 非数字落 0 不炸
- test_clone_kill_main_list_no_candidates_without_match: 只列模式无候选 -> rc=0 无 match 后缀(与 kill 模式带 match 后缀的分支对称)
- test_clone_kill_plan_defensive_gates: 杀面防御 -- 目标已从进程表消失(procs.get 兜底形态)REFUSED(outside-repo); 目标落排除集 REFUSED(self-or-ancestor)
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    """scripts/ 不是包, 按路径加载(与 test_legacy_review4_scripts.py 同款做法); 经
    sys.modules 去重, 同一 pytest 进程里其它测试文件先加载过的模块直接复用。"""
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def _probe_cmd(root, tail="scripts/dev_run.py config.yml --dry-run"):
    """本 clone 探针的真实 cmdline 形态: 绝对 venv python(仓库根)+ 相对脚本路径。"""
    return f'"{root}\\.venv\\Scripts\\python.exe" {tail}'


# --------------------------------------------------------------------------- 判据单点与纯函数


def test_clone_kill_judgement_imports_port_kill_single_point():
    """判据/实杀 import 复用 port_kill 单点: 同一对象 + 源里不得再现定义与 taskkill 字面量。"""
    mod_ck = _load_script("clone_kill")
    mod_pk = _load_script("port_kill")
    assert mod_ck.in_clone_domain is mod_pk.in_clone_domain, "归属判据必须与 port_kill 同一对象, 不得复制"
    assert mod_ck._kill_pid is mod_pk._kill_pid, "实杀单点必须与 port_kill 同一对象, 不得复制"
    assert mod_ck.REPO_ROOT == mod_pk.REPO_ROOT, "仓库根锚必须一致"
    src = (ROOT / "scripts" / "clone_kill.py").read_text(encoding="utf-8")
    assert "def in_clone_domain" not in src, "归属判定不得在 clone_kill 里再现"
    assert "def _kill_pid" not in src, "实杀不得在 clone_kill 里再现"
    assert '"taskkill"' not in src and "taskkill /F" not in src, "taskkill 调用字面量不得再现(实杀单点在 port_kill)"


def test_clone_kill_select_candidates_matrix():
    """候选矩阵: 命中/不命中两态 + --match 小写子串 + 排除集。"""
    mod_ck = _load_script("clone_kill")
    root = str(mod_ck.REPO_ROOT)
    procs = {
        # 命中: 本 clone venv python 探针(绝对解释器 + 相对脚本)
        10: ("python.exe", _probe_cmd(root), 1),
        # 命中: uv shim -- 解释器在 clone 外(Roaming\\uv), cmdline 指回 clone 根
        11:
            (
                "python.exe",
                f'"C:\\Users\\x\\AppData\\Roaming\\uv\\python\\python.exe" "{root}\\.venv\\Scripts\\auto-qb.exe"', 1
            ),
        # 命中(归一面): 正斜杠形态
        30: ("python.exe", f'"{root}/.venv/Scripts/python.exe" {"" }scripts/dev_run.py --dry-run', 1),
        # 不命中: 其它 clone 的进程
        20: ("python.exe", '"D:\\Projects\\auto-qb\\.venv\\Scripts\\python.exe" -m gtm run', 1),
        # 不命中: 前缀同串变体(clone2-old)
        21: ("python.exe", f'"{root}-old\\.venv\\Scripts\\python.exe" x', 1),
        # 不命中: 空 cmdline(fail-closed)
        22: ("python.exe", "", 1),
        # 不命中: 相对 cmdline 的 uv 包装(已接受盲区: 子死后自退)
        23: ("uv.exe", "uv run python scripts/dev_run.py", 1),
    }
    all_c = mod_ck.select_candidates(procs)
    assert [p for p, *_ in all_c] == [10, 11, 30], f"clone 域候选 = 探针/uv shim/正斜杠形态: {[p for p, *_ in all_c]}"
    matched = mod_ck.select_candidates(procs, match="dev_run")
    assert [p for p, *_ in matched] == [10, 30], "--match 子串命中探针两态"
    assert [p for p, *_ in mod_ck.select_candidates(procs, match="DEV_RUN")] == [10, 30], "match 大小写不敏感"
    assert [p for p, *_ in mod_ck.select_candidates(procs, match="auto-qb.exe")] == [
        11
    ], ("裸 'auto-qb' 会撞 REPO_ROOT(auto-qb-zcode-clone2)的子串 -- 收窄到带后缀形态")
    assert mod_ck.select_candidates(procs, match="no-such-thing") == []
    assert [p for p, *_ in mod_ck.select_candidates(procs, excluded={10, 30})] == [11], "排除集剔除候选"


def test_clone_kill_self_and_ancestors_excluded():
    """自身 + 祖先链硬排除: 上溯到根; raced exit 即停; ppid=0 / 成环不死循环。"""
    mod_ck = _load_script("clone_kill")
    root = str(mod_ck.REPO_ROOT)
    procs = {
        1: ("init", "", 0),
        10: ("bash.exe", "bash -c commands run dev.clone-kill", 1),
        20: ("uv.exe", "uv run python scripts/clone_kill.py --match dev_run", 10),
        30: ("python.exe", f'"{root}\\.venv\\Scripts\\python.exe" scripts/clone_kill.py', 20),
        99: ("python.exe", '"D:\\other\\python.exe"', 20),  # 同父兄弟, 非祖先
    }
    assert mod_ck.self_and_ancestors(procs, self_pid=30) == {30, 20, 10, 1}, "自身 + 整条祖先链(不管归属)全剔除"
    # 祖先 raced exit(20 不在表): 走链即停, 尾 ppid 仍入排除集(排除不存在的 pid 无害)
    assert mod_ck.self_and_ancestors({30: procs[30]}, self_pid=30) == {30, 20}
    # ppid=0 即根: 只排自身
    assert mod_ck.self_and_ancestors({5: ("a", "", 0)}, self_pid=5) == {5}
    # PPID 成环: visited 兜底不死循环
    assert mod_ck.self_and_ancestors({50: ("a", "", 60), 60: ("b", "", 50)}, self_pid=50) == {50, 60}


def test_clone_kill_descendant_closure_and_gate():
    """后代闭包: 深度降序(后代先杀)再 pid 升序; outside-repo 后代 REFUSED; 排除集内不进杀面。"""
    mod_ck = _load_script("clone_kill")
    root = str(mod_ck.REPO_ROOT)
    procs = {
        1: ("init", "", 0),
        10: ("python.exe", _probe_cmd(root), 1),  # 目标(探针)
        11: ("python.exe", f'"{root}\\.venv\\Scripts\\python.exe" scripts/dev_webui.py', 10),  # 后代 d1(clone 域)
        12: ("node.exe", f'"{root}\\.commands\\x\\node.exe" server.js', 10),  # 后代 d1(clone 域 node)
        13: ("explorer.exe", "C:\\Windows\\explorer.exe", 10),  # 后代 d1(clone 域外: 产品拉起的 explorer)
        20: ("python.exe", f'"{root}\\.venv\\Scripts\\python.exe" scripts/child.py', 11),  # 孙代 d2
        40: ("python.exe", f'"{root}\\.venv\\Scripts\\python.exe" scripts/x.py', 13),  # clone 域外后代的孩子
        30: ("python.exe", _probe_cmd(root), 1),  # 兄弟(非后代)
    }
    plan = mod_ck.build_kill_plan([10], procs, excluded={999})
    assert [(row[0], row[3])
            for row in plan] == [(20, 2), (40, 2), (11, 1), (12, 1), (13, 1),
                                 (10, 0)], (f"闭包 = 目标 + 全代后代, 深度降序再 pid 升序: {[(row[0], row[3]) for row in plan]}")
    by_pid = {row[0]: row for row in plan}
    assert by_pid[13][4] is False and by_pid[13][5] == "outside-repo", "clone 域外后代 REFUSED(outside-repo)"
    assert all(by_pid[p][4] for p in (10, 11, 12, 20, 40)), "clone 域成员全过闸"
    assert 30 not in by_pid, "非后代不进杀面"
    # 后代过自己那道闸: clone 域外后代(explorer)的孩子(40)按自身 cmdline 判, 照杀
    assert by_pid[40][4] is True
    # 排除集内的后代不进杀面(也不沿它继续走)
    plan2 = mod_ck.build_kill_plan([10], procs, excluded={20})
    assert 20 not in [row[0] for row in plan2], "排除集内后代不进杀面"
    assert 40 in [row[0] for row in plan2], "其余后代不受影响"


# --------------------------------------------------------------------------- main 接线(全打桩, 杀路径不真执行)


def _patch_kill_env(monkeypatch, mod_ck, table, kill_results=None):
    """打桩 scan_processes + _kill_pid(记调用); 返回 (scan_log, kill_log)。"""
    scan_log = []
    kill_log = []

    def fake_scan():
        scan_log.append(1)
        return table

    def fake_kill(pid):
        kill_log.append(pid)
        if kill_results and pid in kill_results:
            return kill_results[pid]
        return (True, "killed")

    monkeypatch.setattr(mod_ck, "scan_processes", fake_scan)
    monkeypatch.setattr(mod_ck, "_kill_pid", fake_kill)
    # 自身 pid 钉到表外常量: 生产 main 走 os.getpid() 默认支, 不钉会与假表小号 pid
    # 撞车(Linux testbed 容器 pid 可低至两位数)造成偶发翻红; 也让「自身在表内」
    # 形态(test_clone_kill_main_self_exclusion_production_path)可控注入。
    monkeypatch.setattr(mod_ck.os, "getpid", lambda: 10**9)
    return scan_log, kill_log


def test_clone_kill_main_list_only_default(monkeypatch, capsys):
    """默认/仅 --match 都只列: 归属行齐全、零杀、rc=0; 仅 --match 带「补 --yes」提示。"""
    mod_ck = _load_script("clone_kill")
    root = str(mod_ck.REPO_ROOT)
    table = {
        10: ("python.exe", _probe_cmd(root), 1),
        11: ("python.exe", f'"{root}\\.venv\\Scripts\\python.exe" scripts/dev_webui.py', 1),
        20: ("python.exe", '"D:\\Projects\\auto-qb\\.venv\\Scripts\\python.exe" -m gtm run', 1),
    }
    scan_log, kill_log = _patch_kill_env(monkeypatch, mod_ck, table)
    assert mod_ck.main([]) == 0
    out = capsys.readouterr().out
    assert "pid 10" in out and "pid 11" in out and "dev_run.py config.yml --dry-run" in out, "归属行带 pid 与 cmdline"
    assert "pid 20" not in out, "clone 域外进程不出现在候选行"
    assert kill_log == [] and len(scan_log) == 1, "只列模式零杀"
    assert mod_ck.main(["--match", "dev_run"]) == 0
    out2 = capsys.readouterr().out
    assert "pid 10" in out2 and "pid 11" not in out2, "--match 收窄子集"
    assert "listing only" in out2 and "--yes" in out2, "缺 --yes 时给「补 --yes」提示"
    assert kill_log == []


def test_clone_kill_main_kill_requires_match_and_yes(monkeypatch, capsys):
    """双闸缺一即拒: --yes 无 --match / --match 缺值 / --match --yes 占值 / --match 空白值 -> rc=2 零扫描零杀。"""
    mod_ck = _load_script("clone_kill")
    root = str(mod_ck.REPO_ROOT)
    table = {10: ("python.exe", _probe_cmd(root), 1)}
    scan_log, kill_log = _patch_kill_env(monkeypatch, mod_ck, table)
    for argv in (["--yes"], ["--match"], ["--match", "--yes"], ["--match", ""], ["--match", "   "]):
        rc = mod_ck.main(argv)
        assert rc == 2, f"{argv} -> rc=2"
        out = capsys.readouterr().out
        assert "usage:" in out, f"{argv} 给用法行"
    assert scan_log == [] and kill_log == [], "拒跑发生在扫描/杀之前, 零副作用"


def test_clone_kill_main_self_exclusion_production_path(monkeypatch, capsys):
    """自杀排除生产路径: 自身 pid 在表内、cmdline 含 clone 根与 match 词 -> 不进候选/杀面。

    _patch_kill_env 把 os.getpid 钉到 10**9, 本用例把 10**9 以工具自身形态放进假表
    (cmdline 同时含仓库根与 --match dev_run 关键词 -- 若排除支回归, 它会被 --yes
    实杀); 断言零出现, 生产 os.getpid() 默认支由此获得守卫(此前全部用例注入 self_pid)。
    """
    mod_ck = _load_script("clone_kill")
    root = str(mod_ck.REPO_ROOT)
    table = {
        1: ("init", "", 0),
        10: ("python.exe", _probe_cmd(root), 1),  # 真候选
        # 工具自身形态: ppid 指向不在表的 5 -> 祖先链即停, 排除集 = {10**9, 5}, 不牵连真候选
        10**9: ("python.exe", f'"{root}\\.venv\\Scripts\\python.exe" scripts/clone_kill.py --match dev_run --yes', 5),
    }
    scan_log, kill_log = _patch_kill_env(monkeypatch, mod_ck, table)
    assert mod_ck.main(["--match", "dev_run", "--yes"]) == 0
    assert kill_log == [10], "只杀真候选, 自身形态零杀"
    out = capsys.readouterr().out
    assert "clone_kill.py --match dev_run" not in out, "自身形态不出现于候选/杀行"


def test_clone_kill_main_kill_flow_gates(monkeypatch, capsys):
    """双闸齐备: 目标 + 过闸后代逐个杀(后代先杀); outside-repo 后代 WARNING+REFUSED 零实杀; rc=1。

    边界面: 无候选 rc=0; 扫描空表 fail-safe rc=1。
    """
    mod_ck = _load_script("clone_kill")
    root = str(mod_ck.REPO_ROOT)
    table = {
        1: ("init", "", 0),
        10: ("python.exe", _probe_cmd(root), 1),  # 目标 1
        11: ("python.exe", _probe_cmd(root, "scripts/dev_run.py --hr-status"), 10),  # 目标 2(10 的孩子)
        13: ("explorer.exe", "C:\\Windows\\explorer.exe", 10),  # 10 的 clone 域外后代
        20: ("python.exe", f'"{root}\\.venv\\Scripts\\python.exe" scripts/dev_webui.py', 11),  # 11 的后代(不含 dev_run)
        30: ("python.exe", '"D:\\Projects\\auto-qb\\.venv\\Scripts\\python.exe" -m gtm run', 1),  # clone 域外
    }
    scan_log, kill_log = _patch_kill_env(monkeypatch, mod_ck, table)
    rc = mod_ck.main(["--match", "dev_run", "--yes"])
    assert kill_log == [20, 10, 11], f"实杀序 = 后代先杀(20 为孙代)再目标: {kill_log}"
    assert 13 not in kill_log, "outside-repo 后代零实杀"
    assert 30 not in kill_log, "clone 域外进程永不进杀面"
    assert rc == 1, "有 REFUSED -> rc=1"
    out = capsys.readouterr().out
    assert (
        "OUTSIDE-REPO" in out and "REFUSED(outside-repo)" in out and "explorer.exe" in out and
        str(mod_ck.REPO_ROOT) in out
    ), "拒绝行显眼且带归属(含仓库根要点, port_kill 同款守阵口径)"
    assert kill_log != [] and 20 in kill_log, "不含 match 的后代经杀树闭包仍然被杀"
    # 无候选: rc=0
    scan_log, kill_log = _patch_kill_env(monkeypatch, mod_ck, {30: table[30]})
    assert mod_ck.main(["--match", "dev_run", "--yes"]) == 0 and kill_log == []
    assert "no candidates" in capsys.readouterr().out
    # 扫描空表 = verify-failed 形态: fail-safe rc=1
    _patch_kill_env(monkeypatch, mod_ck, {})
    assert mod_ck.main(["--match", "dev_run", "--yes"]) == 1
    assert "refusing to act" in capsys.readouterr().out


def test_clone_kill_main_kill_failed_rc(monkeypatch, capsys):
    """实杀失败面: _kill_pid 失败行透传 rc=1, 不崩栈不静默(port_kill 失败面对称)。"""
    mod_ck = _load_script("clone_kill")
    root = str(mod_ck.REPO_ROOT)
    table = {10: ("python.exe", _probe_cmd(root), 1)}
    scan_log, kill_log = _patch_kill_env(
        monkeypatch, mod_ck, table, kill_results={10: (False, "kill-failed: access denied")}
    )
    rc = mod_ck.main(["--match", "dev_run", "--yes"])
    assert rc == 1 and kill_log == [10], "失败行 rc=1"
    assert "kill-failed: access denied" in capsys.readouterr().out


# --------------------------------------------------------------------------- 查询单元(POSIX 环境层打桩 / nt JSON 解析)


def test_clone_kill_scan_posix_reads_proc(monkeypatch, tmp_path):
    """POSIX 查询单元: 假 /proc 树全链 -- comm/cmdline/stat, rpartition ppid, NUL 拼回, 缺件缺席。"""
    mod_ck = _load_script("clone_kill")
    monkeypatch.setattr(mod_ck.os, "name", "posix")  # 钉 POSIX 分派
    proc = tmp_path / "proc"
    (proc / "100").mkdir(parents=True)
    (proc / "100" / "comm").write_text("python3\n", encoding="utf-8")
    (proc / "100" / "cmdline").write_bytes(b"/venv/bin/python\0scripts/dev_run.py\0--dry-run\0")
    (proc / "100" / "stat").write_text("100 (python3) S 10 0 0 0 0 0\n", encoding="utf-8")
    # comm 含括号与空格: ppid 必须用 rpartition(")") 解析, 裸 split 会错位
    (proc / "101").mkdir()
    (proc / "101" / "comm").write_text("py (th)on\n", encoding="utf-8")
    (proc / "101" / "cmdline").write_bytes(b"uv\0run\0")
    (proc / "101" / "stat").write_text("101 (py (th)on) R 20 0 0\n", encoding="utf-8")
    # raced exit 形态: 只有 comm, cmdline/stat 缺 -> 整个 pid 缺席
    (proc / "102").mkdir()
    (proc / "102" / "comm").write_text("python3\n", encoding="utf-8")
    # comm 空串: 整行缺席(if not name 分支, 查询层不吞但归属无从谈起)
    (proc / "104").mkdir()
    (proc / "104" / "comm").write_text("", encoding="utf-8")
    (proc / "104" / "cmdline").write_bytes(b"whatever\0")
    (proc / "104" / "stat").write_text("104 (x) S 9 0 0\n", encoding="utf-8")
    # 空文件: cmdline 空、stat 空 -> ppid 0, 仍在表(cmdline 空由归属闸出局, 查询层不吞)
    (proc / "103").mkdir()
    (proc / "103" / "comm").write_text("kthreadd\n", encoding="utf-8")
    (proc / "103" / "cmdline").write_bytes(b"")
    (proc / "103" / "stat").write_text("", encoding="utf-8")
    (proc / "net").mkdir()
    (proc / "net" / "tcp").write_text("garbage\n", encoding="utf-8")  # 非数字目录跳过
    monkeypatch.setattr(mod_ck, "PROC_ROOT", str(proc))
    procs = mod_ck.scan_processes()
    assert set(procs) == {100, 101, 103}, f"raced exit(102)/comm 空串(104)缺席, 非数字目录(net)跳过: {sorted(procs)}"
    assert procs[100] == ("python3", "/venv/bin/python scripts/dev_run.py --dry-run", 10)
    assert procs[101][0] == "py (th)on" and procs[101][2] == 20, "comm 含括号空格时 ppid=rpartition 解析"
    assert procs[103][2] == 0, "空 stat -> ppid 0"


class _FakeRun:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def test_clone_kill_scan_nt_parses_json(monkeypatch):
    """nt 查询单元: 数组/单字典两形态归一; null CommandLine -> 空串; 坏 JSON / 非零 rc -> 空表。"""
    mod_ck = _load_script("clone_kill")
    monkeypatch.setattr(mod_ck.os, "name", "nt")  # 钉 nt 分派
    rows = [
        {
            "ProcessId": 10,
            "Name": "python.exe",
            "CommandLine": "D:\\x\\.venv\\Scripts\\python.exe scripts/dev_run.py --dry-run",
            "ParentProcessId": 5
        },
        {
            "ProcessId": 11,
            "Name": "python.exe",
            "CommandLine": None,
            "ParentProcessId": 10
        },
        {
            "ProcessId": 12,
            "Name": "powershell.exe"
        },  # ParentProcessId 缺失 -> 0
        {
            "Name": "ghost.exe",
            "CommandLine": "x",
            "ParentProcessId": 1
        },  # 缺 ProcessId -> 整行跳过
        {
            "ProcessId": 13,
            "CommandLine": "y",
            "ParentProcessId": 1
        },  # 缺 Name -> 整行跳过
    ]
    monkeypatch.setattr(mod_ck.subprocess, "run", lambda *a, **k: _FakeRun(stdout=json.dumps(rows)))
    procs = mod_ck.scan_processes()
    assert set(procs) == {10, 11, 12}, f"缺 ProcessId/Name 的行整行跳过(fail-safe, 不炸): {sorted(procs)}"
    assert procs[10] == ("python.exe", "D:\\x\\.venv\\Scripts\\python.exe scripts/dev_run.py --dry-run", 5)
    assert procs[11][1] == "" and procs[11][2] == 10, "null CommandLine -> 空串(归属闸对空串恒 False)"
    assert procs[12][2] == 0
    # 单字典形态(部分 PS host 拆包)
    monkeypatch.setattr(mod_ck.subprocess, "run", lambda *a, **k: _FakeRun(stdout=json.dumps(rows[0])))
    assert set(mod_ck.scan_processes()) == {10}
    # 坏 JSON / 非零 rc -> 空表(main 视空表为 verify-failed 形态, fail-safe)
    monkeypatch.setattr(mod_ck.subprocess, "run", lambda *a, **k: _FakeRun(stdout="not-json"))
    assert mod_ck.scan_processes() == {}
    monkeypatch.setattr(mod_ck.subprocess, "run", lambda *a, **k: _FakeRun(stdout="[]", returncode=1))
    assert mod_ck.scan_processes() == {}


# --------------------------------------------------------------------------- 角落加固(coverage 补面)


def test_clone_kill_show_truncation():
    """_show 边界: 160 内原样, 超长截 157 + 「...」(与 port_kill 同口径)。"""
    mod_ck = _load_script("clone_kill")
    assert mod_ck._show("x" * 160) == "x" * 160
    assert mod_ck._show("x" * 161) == "x" * 157 + "..."


def test_clone_kill_scan_edges_fail_safe(monkeypatch, tmp_path):
    """扫描边角: nt stdout 空(rc=0)空表; posix stat ppid 非数字落 0。"""
    mod_ck = _load_script("clone_kill")
    monkeypatch.setattr(mod_ck.os, "name", "nt")
    monkeypatch.setattr(mod_ck.subprocess, "run", lambda *a, **k: _FakeRun(stdout=""))
    assert mod_ck.scan_processes() == {}, "stdout 空(哪怕 rc=0) -> 空表"
    monkeypatch.setattr(mod_ck.os, "name", "posix")
    proc = tmp_path / "proc"
    (proc / "70").mkdir(parents=True)
    (proc / "70" / "comm").write_text("python3\n", encoding="utf-8")
    (proc / "70" / "cmdline").write_bytes(b"x\0")
    (proc / "70" / "stat").write_text("70 (python3) S junk 0 0\n", encoding="utf-8")  # ppid 非数字
    monkeypatch.setattr(mod_ck, "PROC_ROOT", str(proc))
    assert mod_ck.scan_processes()[70] == ("python3", "x", 0), "ppid 非数字落 0 不炸"


def test_clone_kill_main_list_no_candidates_without_match(monkeypatch, capsys):
    """只列模式无候选 -> rc=0, 输出无 match 后缀(kill 模式带 match 后缀的分支对称面)。"""
    mod_ck = _load_script("clone_kill")
    table = {30: ("python.exe", '"D:\\Projects\\auto-qb\\.venv\\Scripts\\python.exe" -m gtm run', 1)}
    _patch_kill_env(monkeypatch, mod_ck, table)
    assert mod_ck.main([]) == 0
    out = capsys.readouterr().out
    assert "no candidates" in out and "match:" not in out, "无 match 时不带 match 后缀"


def test_clone_kill_plan_defensive_gates():
    """杀面防御: 目标消失(procs.get 兜底)与目标落排除集都 REFUSED, 不杀。"""
    mod_ck = _load_script("clone_kill")
    procs = {1: ("init", "", 0)}
    plan = mod_ck.build_kill_plan([999], procs, excluded=set())  # 999 不在表
    assert plan == [(999, "", "", 0, False, "outside-repo")], "消失目标 -> 空 cmdline -> outside-repo 拒杀"
    plan2 = mod_ck.build_kill_plan([10], {10: ("python.exe", "x", 1)}, excluded={10})
    assert plan2 == [(10, "python.exe", "x", 0, False, "self-or-ancestor")], "目标落排除集 -> 防御拒杀"
