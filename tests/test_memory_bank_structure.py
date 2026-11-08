"""test_memory_bank_structure 测试计划: Memory Bank 结构守卫测试 (TASK010; 2026-09-18 随任务档案改名同步更新)。

守什么: 知识库的"跨会话连续性"完全依赖 `memory-bank/tasks/` 与入口文件的**结构化约定** —
必备章节缺失、状态词漂移, 下次会话就无法从 `tasks/` 续作。这些判定都是纯静态的, 用测试守住成本极低。
(2026-11-08 重构: tasks 索引/归档清单、顶层墓碑与存根机制已退役 —— 索引登记/归档全量/存根合法性/
activeContext.md 流水账回流等以已删文件为宿主的用例随之收缩。)

2026-09-18 起档案命名由 `TASKnnn-<slug>.md` 改为 `YY-MM-DD-<slug>.md`(全局序号在 9 个并行
worktree 下必然撞号)。本文件在兼容期内同时接受两种命名, 主键一律取"去掉编号 / 日期前缀后的 slug"。

2026-09-30 **cap 债务制**改造 (计划 `memory-bank/plans/26-09-30-2112-plan-memory-bank-cap-debt.html`):
尺寸类 cap 从"提交前置条件"降级为**债务**(超限只是读起来更贵, 事实源完好) —— 除 `AGENTS.md`
(越过它发生的是 IDE 注入**截断**, 尾部对模型真不可见, 是硬规定, 超了仍拦)。所以本文件删掉了
对 KB 角色**现行文档尺寸**的断言, 换成「债务可发现性」断言: 造一个超限文件, 它必须被报成
warn 而不是 problem —— 守住"降级后的严重度仍然正确", 而不是"今天的文件恰好不超"。

## 测试计划

- test_session_protocol_is_exposed_in_always_on_entries: skill 载体存在且含阈值/DoD, `AGENTS.md` 声明阈值并指向 skill (copilot-instructions 2026-10-06 降级为指针后不再受查)

知识库目录化守卫 (检查器在 memory-bank skill 的 `scripts/check_kb_structure.py`, 进程内 import):

- test_kb_index_is_regenerated / test_kb_index_and_files_are_bijective: 索引 == 生成结果; 索引与目录双向一致
- test_kb_no_orphan_index_dirs: 顶层索引都被 README 引用
- test_kb_active_context_slices_are_valid: 切片命名定宽 / 三行头齐 (结构); 尺寸与条数是**债务**, 不判红
- test_kb_debt_count_excludes_min_size_hints: CLI 汇总行的「cap 债务 N 项」只数带 `DEBT_MARK` 的行, 「文件过小」提示不计入
- test_kb_trim_hint_is_fixed_action_not_compress: 触顶口径 = 刚好 ≤ cap + 固定动作(外迁/删死段/合并邻近件), 禁止「压文案」与 50% 收缩 (2026-11-05 计划 §07 P2)
- test_kb_active_render_respects_byte_budget: kb.active 默认字节预算截取(30KB 内联上限), 页脚留总数, --all / -n N 逃生

文档族注册表与 kb.new / kb.wrap (2026-10-17 P1, 计划 26-10-17-0527; 实现与检查器在
memory-bank skill 的 `scripts/new_doc.py` / `wrap_session.py` / `check_doc_templates.py`,
**进程内 import** —— 本项目测试禁止起子进程):


kb.status / kb.bump 与 D4 反向补链 (2026-10-17 P2, 计划 26-10-17-0527; 实现与检查器在
memory-bank skill 的 `scripts/flip_status.py` / `bump_doc.py`, **进程内 import**):


二期四族 pitfall/report/baseline/progress 与守卫扩面 (2026-10-17 P3, 计划 26-10-17-0527;
实现 = `_common.FAMILIES` 扩行 + `templates/` 四件 + new_doc 分派 + check_doc_templates
扩扫描面, 进程内 import; 验收: 计划 §07 P3 行):


时间守卫 (检查器 memory-bank skill 的 `scripts/timekit.py`, 2026-10-06 加):


回写措辞守卫 (检查器 memory-bank skill 的 `scripts/check_wording.py`, 2026-10-07 加):

- test_kb_scripts_import_cleanly: skill 的脚本都能 import

常驻锚防流水守卫 (检查器 memory-bank skill 的 `scripts/check_mutation_anchor.py`, 2026-10-31 加):


- test_gen_all_declares_exactly_all_indexes: gen_all.py 的产出集合 == 库内全部 `_index.md`(生成物全集单点)
- test_gen_all_check_is_green: gen_all.py `--check` 在当前库上绿 (磁盘 == 生成结果)
- test_gen_all_list_matches_outputs: `--list` 声明的路径集合 == collect() 实际产出 (白名单不得多/少)
- test_generated_indexes_are_lf_only: 生成物字节里无 CR —— 生成器 `write_text` 显式 `newline="
"`, 防 Windows 上按 os.linesep 落成 CRLF 的"纯行尾噪音"
- test_gen_cmd_hints_name_real_tasks: 生成物的"怎么重建"提示必须指向真能重建它的命令(`gen_cmd` 按脚本查表 + `kb.index` 覆盖面 ⊇ 闸门判红的生成物集合, 经 gen_all.py 单点收编后按声明核对; 2026-09-24 `_doc-map.md` 报错文案指错命令的机检)


状态漂移守卫 (检查器 memory-bank skill 的 `scripts/check_status_drift.py`, 2026-10-31 加, **进程内
import**, tmp 夹具不碰真实 memory-bank/; 四档: A 反链x Open / B issue badge vs meta / 异常
status-unreadable 三档硬拦 rc=1, C 反链x In Progress / D 完成断言两档清单只提示):


HTML 结构守卫 (检查器 memory-bank skill 的 `scripts/check_html.py`, 2026-11-01 加, **进程内
import**; L1 行级正则 + L2 stdlib 解析器残缺标签名校验双网, script/style 区遮蔽防 JS 字面量
误报; 全库存量基线 = 零命中, 命中即新增 —— 无存量豁免清单; 更广的规范级伤害归 `--vnu` 巡检):

"""

from __future__ import annotations

import re

import sys

from pathlib import Path

from kb_test_support import (
    EXTRA_GENERATED,
    MB,
    ROOT,
    SKILL,
    SKILL_SCRIPTS,
    _gen_all,
    _kb_checker,
)


def test_session_protocol_is_exposed_in_always_on_entries() -> None:
    assert SKILL.exists(), "缺少 skill 载体 .agents/skills/memory-bank/SKILL.md (会话协议将无法被触发)"
    skill_text = SKILL.read_text(encoding="utf-8")
    for token in ("立档阈值", "收尾 DoD", "会话开始"):
        assert token in skill_text, f"SKILL.md 缺少 {token}"

    # 2026-10-06 起只查 `AGENTS.md` —— `.github/copilot-instructions.md` 已降级为**纯指针**
    # (内容只有"以 ../AGENTS.md 为准")。原先"两个入口都得含阈值 / skill 路径"的断言实际是在
    # **替过期副本兜底**: 副本一改成不重复口径就判红, 逼得它要么留着旧说法、要么留一行机械 token。
    # 会话协议守单点足够 —— 指针自己不承载口径, 也就不需要被守。
    agents = ROOT / "AGENTS.md"
    text = agents.read_text(encoding="utf-8")
    assert "立档阈值" in text, f"{agents.name} 未声明立档阈值"
    assert ".agents/skills/memory-bank/SKILL.md" in text, f"{agents.name} 未指向 memory-bank skill"


def test_kb_index_is_regenerated() -> None:
    """每个索引目录的 `_index.md` == 生成结果 (索引是生成物, 冲突靠重跑, 不手改)。"""
    problems = _kb_checker().check_index_regenerated(ROOT, MB)
    assert not problems, ("请运行 `python .agents/skills/memory-bank/scripts/gen_kb_index.py` 重建:\n" + "\n".join(problems))


def test_kb_index_and_files_are_bijective() -> None:
    """索引 ↔ 目录内容双向一致: 有文件没登记、登记了没文件, 都红。"""
    problems = _kb_checker().check_bijection(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_no_orphan_index_dirs() -> None:
    """每个顶层 `_index.md` 都被 memory-bank/README.md 引用 (新增目录忘了登记就红)。"""
    problems = _kb_checker().check_orphan_indexes(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_active_context_slices_are_valid() -> None:
    """切片命名定宽 / 三行头齐 —— 这两个是**结构**, 坏了就解析不了, 判红。

    尺寸与条数不再在本用例里判红(2026-09-30, D2 拍板归债务通道): 切片是「每会话重写文件头
    同一段」的替代物, 冲突在结构上消掉了, 代价是文件数不再有界 —— 但"该蒸馏了"与"切片的
    命名坏了"性质不同: 前者只是读起来更贵, 后者是事实源残缺。旧口径把它俩都判红, 实测后果是
    阈值(按 ~5 片/日校准的估计值)打满时, 逼出"为了过守卫而违规归档"(切片 26-09-30-2112 记的实例)。
    """
    checker = _kb_checker()
    import gen_active_recent

    slice_dir = MB / "active-context"
    assert slice_dir.is_dir(), "缺少 memory-bank/active-context/ 切片目录"
    rows, problems, _warns = gen_active_recent.collect(slice_dir, ROOT)
    assert not problems, "\n".join(problems)
    assert checker.role_of("memory-bank/active-context/x.md") == "slice", "切片路径未被 _common.role_of 认成 slice 角色"
    assert rows, "切片目录是空的 —— 滚动状态没有归宿"


def test_kb_active_render_respects_byte_budget() -> None:
    """kb.active 默认按字节预算截取 —— AI 工具壳内联上限 30,000 字节 (pitfalls/ops/console-encoding.md)。

    切片 90+ 条后全量输出 ~51KB → 落盘 + 截断点切进多字节字符时预览整段乱码, 「全量」反而不可读。
    守四点: 预算内必停(按编码后字节计) / 收紧到只够一行也不许输出空表 / 页脚保留总数与省略数
    (截的是展示不是事实) / 不传预算(--all)仍全量。行内容是合成行, 不与现行切片数耦合。
    """
    from datetime import datetime, timedelta

    # 不能依赖别的用例先插过 sys.path —— xdist 分组随测试集变化(2026-10-13 W7 加了
    # 一个 dom_panel 用例就翻出本潜伏依赖), 自带插入才是确定性口径。
    import sys

    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import gen_active_recent

    now = datetime(2026, 10, 2, 12, 0)

    def row(i: int) -> dict:
        when = datetime(2026, 1, 1) + timedelta(days=i)
        return {
            "rel": f"memory-bank/active-context/s{i}.md",
            "slug": f"topic-{i:02d}",
            "created": when,
            "last": when,
            "summary": "摘要" * 150
        }

    rows = [row(i) for i in range(60)]
    out = gen_active_recent.render(rows, 14, now, byte_budget=gen_active_recent.DEFAULT_BYTE_BUDGET)
    assert len(out.encode("utf-8")) < 30_000, "默认预算输出仍可能超 AI 工具壳内联上限"
    assert "共 60 个切片" in out and "省略" in out, "页脚必须保留总数与省略数"

    tiny = gen_active_recent.render(rows, 14, now, byte_budget=100)
    assert "省略 59 条" in tiny, "预算只够一行时至少显示 1 行, 不得输出空表"

    full = gen_active_recent.render(rows, 14, now)
    assert "省略" not in full and "topic-59" in full, "不传预算(--all)必须仍是全量"

    five = gen_active_recent.render(rows, 14, now, limit=5)
    assert "省略 55 条" in five and "topic-59" not in five, "-n N 按条数截取"


def test_kb_debt_count_excludes_min_size_hints(tmp_path: Path, monkeypatch, capsys) -> None:
    """CLI 汇总行的「cap 债务 N 项」**只数带 `DEBT_MARK` 的行**, 「文件过小」提示不进这个数。

    判据出自 `pitfalls/kb/cap-debt.md` 第 1 条: **债务数必须能清零** —— 一件债务对应一个动作
    (精简 / 外迁), 而「文件过小」没有这样的动作(把它往外迁是错的动作)。旧实现直接 `len(warns)`,
    于是这行恒报常数(2026-10-06 实测 ~40 项)而真实债务 0 ⇒ 清理会话按它收口必然徒劳。
    """
    checker = _kb_checker()
    evergreen = tmp_path / "memory-bank" / "evergreen"
    evergreen.mkdir(parents=True)
    (evergreen / "_about.md").write_text("# t\n> 摘要: x\n> 触发: y\n", encoding="utf-8")
    (evergreen / "small.md").write_text("# 小\n> 摘要: x\n> 触发: y\n", encoding="utf-8")

    def run() -> str:
        monkeypatch.setattr(sys, "argv", ["check_kb_structure.py", "--root", str(tmp_path)])
        checker.main()
        return capsys.readouterr().out

    only_hint = run()
    assert "cap 债务 0 项" in only_hint, f"「文件过小」不得计入债务数: {only_hint}"
    assert "cap 债务 1 项" not in only_hint, f"债务数被「过小」提示撑大了: {only_hint}"
    assert "过小" in only_hint, "提示本身仍要打印(只是不计入债务数)"

    (evergreen / "big.md").write_text("# 大\n> 摘要: x\n> 触发: y\n" + "x" * 30_000, encoding="utf-8")
    with_debt = run()
    assert "cap 债务 1 项" in with_debt, f"真实超限必须计成 1 项债务: {with_debt}"


def test_kb_trim_hint_is_fixed_action_not_compress() -> None:
    """触顶处置口径 (2026-11-05 计划 26-11-05-1049 §07 P2): 严禁「压文案」, 只做三件固定动作。

    旧口径「精简/外迁到 50%」会诱导 agent 删事实换字数; 新口径清债目标=刚好 ≤ cap,
    动作=外迁 attachments/ → 删除死段 → 合并邻近件。`log` 仍按 append-only 轮转。
    """
    checker = _kb_checker()
    hint = checker.trim_hint("pitfall", 8_000)
    assert "外迁 `attachments/`" in hint
    assert "删除死段" in hint and "合并邻近件" in hint
    assert "禁止压文案" in hint
    assert "≤ 8,000" in hint, "目标必须写明刚好 ≤ 当前 cap, 不是比例"
    assert "50%" not in hint and "精简" not in hint, f"旧收缩口径不得回潮: {hint}"

    log_hint = checker.trim_hint("log", 8_000)
    assert "最老一端" in log_hint and "轮转" in log_hint
    assert "禁止压文案" in log_hint

    agents_hint = checker.trim_hint("agents", 8_000)
    assert "硬规定" in agents_hint and "≤ 8,000" in agents_hint


def test_kb_scripts_import_cleanly() -> None:
    """skill 的脚本都能被 import —— 模块级错误在这里当场红, 不必等闸门跑 `--help`。"""
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    for name in (
        "_common", "gen_kb_index", "gen_all", "check_kb_structure", "gen_active_recent", "gen_baseline_recent",
        "check_doc_links", "timekit", "check_wording", "new_doc", "wrap_session", "check_doc_templates", "flip_status",
        "bump_doc", "check_status_drift"
    ):
        path = SKILL_SCRIPTS / f"{name}.py"
        assert path.is_file(), f"缺少 {path.relative_to(ROOT)}"
        __import__(name)


def test_gen_all_declares_exactly_all_indexes() -> None:
    """生成物集合单点: gen_all 的产出 == 库内**全部**索引页面(`_index.md` + 分卷页 `_index-<n>.md`)
    + `EXTRA_GENERATED` —— 一个不多, 一个不少。

    这是 sync 自动化解白名单的安全底线: 白名单里多一个其实不是生成物的路径, sync 就会
    在冲突时静默丢弃手写内容(第 3 步自证也救不回来); 少一个则冲突化解不了。

    `EXTRA_GENERATED`(2026-10-11 加入): 不叫 `_index.md` 的**生成物**。issues 归档索引是第一个 ——
    它落在 `attachments/`(该目录不计 cap)才敢放全量清单, 而名字不叫 `_index.md` 正是为了
    **不**被 `index-auto` 角色套上 8,000 的 cap。新增同类生成物必须**显式登记在这里** ——
    否则本守阵会在它出现的那一刻红, 逼你确认它确实是生成物而不是手写件。
    """
    gen_all = _gen_all()
    outputs = gen_all.collect(ROOT, MB)
    on_disk = set(MB.rglob("_index*.md")) | {ROOT / rel for rel in EXTRA_GENERATED}
    assert set(outputs) == on_disk, (
        f"gen_all 产出与库内 _index.md 不一致: 多 {sorted(set(outputs) - on_disk)} / "
        f"少 {sorted(on_disk - set(outputs))}"
    )


def test_gen_all_check_is_green() -> None:
    """`--check` 在当前库上必须绿 —— 磁盘内容 == 生成结果(等价于 kb.check 的生成物部分)。"""
    gen_all = _gen_all()
    outputs = gen_all.collect(ROOT, MB)
    drifted = [p for p, want in outputs.items() if (p.read_text(encoding="utf-8") if p.exists() else "") != want]
    assert not drifted, "请运行 `commands run kb.index` 重建:\n" + "\n".join(
        f"  {p.relative_to(ROOT)}" for p in sorted(drifted)
    )


def test_gen_all_list_matches_outputs(capsys) -> None:
    """`--list` 声明的集合必须与 collect() 实际写出的集合**恒等** —— 白名单不得多/少。"""
    gen_all = _gen_all()
    assert gen_all.main(["--list"]) == 0
    listed = {ROOT / line for line in capsys.readouterr().out.splitlines() if line.strip()}
    assert listed == set(gen_all.collect(ROOT, MB))


def test_generated_indexes_are_lf_only() -> None:
    """生成物一律 LF 行尾 (2026-10-04) —— `Path.write_text` 的 `newline` 默认 `None` ⇒ 按 `os.linesep`
    翻换行, Windows 上把 `\n` 写成 CRLF, 于是 `kb.index` 顺带产出一批"纯行尾噪音"的 modified
    (坑档 pitfalls/git/editing-traps.md; 根因属该条记的"未决改造")。

    这里逐**字节**断言无 CR —— 用 `read_text` 会把 CRLF 折成 LF, 正好是这条缺陷能逃过既有
    `test_gen_all_check_is_green` / `kb.check` 的原因(它们对行尾不敏感)。文件集合取
    `gen_all.collect()` 的键(生成物单点), 不另抄一份清单。
    """
    gen_all = _gen_all()
    offenders = sorted(
        p.relative_to(ROOT).as_posix() for p in gen_all.collect(ROOT, MB) if p.exists() and b"\r" in p.read_bytes()
    )
    assert not offenders, (
        "这些生成物含 CR 字节(应为纯 LF), 请运行 `commands run kb.index` 重建:\n" + "\n".join(f"  {rel}" for rel in offenders)
    )


def test_gen_cmd_hints_name_real_tasks() -> None:
    """生成物的"怎么重建"提示必须指向**真的能重建它**的命令(2026-09-24 实测缺陷)

    原先 `_common.gen_cmd()` 忽略传入的脚本名, 一律返回 `commands run kb.index`, 而 `kb.index`
    当时的覆盖面与闸门判红的生成物集合不一致。于是 `_doc-map.md` / `plans|reports/_index.md` 的报错
    文案("请运行 commands run kb.index")**照做一遍仍然是红的** —— 而提交闸门早就把这两条的
    `--check` 挂上了, 形成"闸门能红、却没有一条能修的命令"。

    三条断言(前两条都拦不住这个缺陷, 只有 3. 判的是"跑那条命令真的会重建/校验它"):
      1. 每个 `gen_cmd(root, "<脚本>")` 调用点的脚本名都在表里(新生成脚本忘了登记 ⇒ 退回默认值);
      2. 表里每个 task id 在 `.commands/` 里真实存在(任务改名/删除后提示不能变成死指针);
      3. **提示说跑 `kb.index` 的脚本必须真的出现在 `kb.index` 的 run 列表里**(`kb.check` 同理)
         —— 这同时钉住了"`kb.index` 的覆盖面 ⊇ 提交闸门判红的生成物集合"这条设计口径。
    """
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import _common

    table = _common.GEN_CMD_BY_SCRIPT

    # 1. 调用点全覆盖
    call_sites: set[str] = set()
    for path in sorted(SKILL_SCRIPTS.glob("*.py")):
        call_sites |= set(
            re.findall(r'gen_cmd\(\s*root\s*,\s*["\']([^"\']+)["\']\s*\)', path.read_text(encoding="utf-8"))
        )
    assert call_sites, "一个 gen_cmd 调用点都没扫到(写法变了? 同步本守阵)"
    missing = sorted(call_sites - set(table))
    assert not missing, (f"这些脚本调了 gen_cmd 却不在 GEN_CMD_BY_SCRIPT 表里: {missing} —— "
                         "会退回默认值 `kb.index`, 而它未必能重建该脚本的产出")

    def task_body(task_id: str) -> str:
        pack, _, name = task_id.partition(".")
        cfg = ROOT / ".commands" / pack / "config.toml"
        assert cfg.is_file(), f"提示里的包不存在: {cfg.relative_to(ROOT)}"
        text = cfg.read_text(encoding="utf-8")
        m = re.search(rf'^\[tasks\."{re.escape(task_id)}"\]\n(.*?)(?=^\[|\Z)', text, re.S | re.M)
        assert m, f"{cfg.relative_to(ROOT)} 里找不到任务 `{task_id}` —— 表里的提示是死指针"
        return m.group(1)

    gen_scripts = {s for _skill, s in _gen_all().GENERATORS}

    for script, hint in sorted(table.items()):
        parts = hint.split()
        assert parts[:2] == ["commands", "run"] and len(parts) >= 3, f"{script} 的提示不是 `commands run <task>`: {hint!r}"
        task_id = parts[2]
        body = task_body(task_id)  # 2. 任务真实存在
        if task_id == "kb.index":  # 3. 核心: 真的会重建它
            # 2026-10-03 起 kb.index 收成一条 `gen_all.py`: 提示说跑 kb.index 的脚本, 要么直接出现在
            # run 列表里, 要么由 gen_all 的 GENERATORS 声明覆盖(集合单点收编, 不再是手抄副本)。
            covered = script in body or ("gen_all.py" in body and script in gen_scripts)
            assert covered, (
                f"{script} 的提示说跑 `{task_id}`, 但它的 run 列表与 gen_all.GENERATORS 都没覆盖 {script} —— "
                f"用户照做一遍仍然是红的(2026-09-24 实测的缺陷形态)"
            )
        elif task_id == "kb.check":
            assert f"{script} --check" in body, (f"{script} 的提示说跑 `{task_id}`, 但它的 run 列表里没有 `{script} --check`")
