"""test_memory_bank_naming 测试计划: Memory Bank 结构守卫测试 (TASK010; 2026-09-18 随任务档案改名同步更新)。

守什么: 知识库的"跨会话连续性"完全依赖 `memory-bank/tasks/` 与入口文件的**结构化约定** —
一旦索引与档案脱钩 (登记了没文件 / 有文件没登记)、状态分区与档案 `Status` 不一致、
必备章节缺失, 下次会话就无法从 `tasks/` 续作; 一旦会话纪要回流进 `activeContext.md`,
该文件会重新膨胀成流水账 (2026-09-17 复盘的真实故障)。这些判定都是纯静态的, 用测试守住成本极低。

2026-09-18 起档案命名由 `TASKnnn-<slug>.md` 改为 `YY-MM-DD-<slug>.md`(全局序号在 9 个并行
worktree 下必然撞号)。本文件在兼容期内同时接受两种命名, 主键一律取"去掉编号 / 日期前缀后的 slug"。

2026-09-30 **cap 债务制**改造 (计划 `memory-bank/plans/26-09-30-2112-plan-memory-bank-cap-debt.html`):
尺寸类 cap 从"提交前置条件"降级为**债务**(超限只是读起来更贵, 事实源完好) —— 除 `AGENTS.md`
(越过它发生的是 IDE 注入**截断**, 尾部对模型真不可见, 是硬规定, 超了仍拦)。所以本文件删掉了
对 KB 角色**现行文档尺寸**的断言, 换成「债务可发现性」断言: 造一个超限文件, 它必须被报成
warn 而不是 problem —— 守住"降级后的严重度仍然正确", 而不是"今天的文件恰好不超"。

## 测试计划

- test_slug_is_unique_ignoring_date_prefix: 去掉日期 / 编号前缀后 slug 唯一 + 索引同键只登记一次 (防并行分支同专题两份档案)
- test_task_file_naming_and_sections: 文件名符合 `YY-MM-DD-<slug>.md`(兼容旧 `TASKnnn-<slug>.md`), 且五个必备章节齐全

知识库目录化守卫 (检查器在 memory-bank skill 的 `scripts/check_kb_structure.py`, 进程内 import):

- test_kb_topic_files_have_metadata / test_kb_files_respect_caps / test_kb_class_names_and_topic_filenames: 三行头元数据 / **硬规定** cap / 类名与文件名

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


常驻锚防流水守卫 (检查器 memory-bank skill 的 `scripts/check_mutation_anchor.py`, 2026-10-31 加):


kb.tier 分级清理四动作 (2026-10-31 R0, 计划 26-10-31-0534; 实现在 memory-bank skill 的
`scripts/kb_tier.py`, **进程内 import**, tmp 夹具不碰真实 memory-bank/):


CLOSED_KEEP=60 索引出口 (计划 26-10-31-0534 R3/D5/D14, 2026-10-31 加; tasks 主索引的已完结区只留
最近 60 条, 全量清单另落 `tasks/attachments/_archive.md`, 形态与 issues 侧同款; plans 侧守阵在 test_docs_forms.py):


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
    DATE_PREFIX_RE,
    FILE_RE,
    INDEX,
    INDEX_ID_RE,
    LEGACY_PREFIX_RE,
    MB,
    REQUIRED_SECTIONS,
    ROOT,
    SKILL_SCRIPTS,
    STATUS_RE,
    TASKS,
    _kb_checker,
    _slug_of,
    _task_files,
)


def test_slug_is_unique_ignoring_date_prefix() -> None:
    """并行 worktree 各自立档会产出重复: 同一专题两份档案 (2026-09-18 实测 TASK014/TASK015 逐字节相同)
    + 索引里重复登记。重复条目在 dict 式解析里会静默覆盖, 双向一致与状态分区两个守卫都发现不了,
    所以必须单独守。改名后同一专题在不同日期建档会产生不同文件名, 因此比对必须**忽略日期前缀**。"""
    slugs: dict[str, list[str]] = {}
    for path in _task_files():
        slugs.setdefault(_slug_of(path), []).append(path.name)
    dup_slugs = {slug: names for slug, names in slugs.items() if len(names) > 1}

    assert not dup_slugs, f"存在同 slug 的重复任务档案 (同一专题两份, 需合并): {dup_slugs}"

    indexed = INDEX_ID_RE.findall(INDEX.read_text(encoding="utf-8"))
    dup_ids = sorted({key for key in indexed if indexed.count(key) > 1})

    assert not dup_ids, f"索引中同一档案被重复登记: {dup_ids}"


def test_task_file_naming_and_sections() -> None:
    files = _task_files()
    assert files, "tasks/ 下没有任何任务档案"

    for path in files:
        assert FILE_RE.match(path.name), (f"任务文件名不符合 YY-MM-DD-<slug>.md (slug 为英文小写连字符): {path.name}")
        text = path.read_text(encoding="utf-8")
        assert STATUS_RE.search(text), f"{path.name} 缺少合法的 `**Status:**` 行"
        for section in REQUIRED_SECTIONS:
            # !必须锚到**行首标题**: `section in text` 会被正文里的字面量骗过 ——
            # 本档案的日志里正好写了"把 `## 进度日志` 标题丢了"这句, 于是缺章节也判绿(2026-09-22 实测)。
            assert re.search(rf"^{re.escape(section)}\s*$", text,
                             re.M), (f"{path.name} 缺少必备章节 `{section}`(须是行首的 `## ` 标题, 正文里提到不算)")


def test_kb_topic_files_have_metadata() -> None:
    """每个主题文件与 `_about.md` 都含三行头元数据 —— 生成器的数据源, 缺了索引行就是空的。"""
    problems = _kb_checker().check_metadata(ROOT, MB)
    assert not problems, "\n".join(problems)


def test_kb_class_names_and_topic_filenames() -> None:
    """类名 ∈ 固定枚举; 主题文件名匹配 `^[a-z0-9]+(-[a-z0-9]+)*\\.md$`。"""
    problems = _kb_checker().check_names(ROOT, MB)
    assert not problems, "\n".join(problems)
