"""非 ASCII 图形符号闸门: 判据常量与存量冻结清单 (机械生成, 勿手改)。

判据的规范单点在 memory-bank/conventions/code-style.md「非 ASCII 图形符号禁令」表 A/B/C
(2026-11-08 拍板 D1)。本模块是它的机检实现; test_code_style_table_is_single_source
双向比对两张表, 只改一侧当场红。

FROZEN 由只读全库扫描生成: key = (仓库根相对路径, 字符类), value = 该类在该文件的命中处数。
带病上岗 —— 存量全登记, 只拦新增; 部分递减不红, 但清光一类后必须同步撤下该条目
(否则回加会被放过), 由 test_repo_matches_frozen 强制。

生成口径就是本模块的 SCAN_* / EXCLUDE_* / EXEMPT_CELLS 常量, 与守阵 scan() 同源。
本文件与守阵均不得出现表 A 的字面字符 —— 合成红验一律用 chr() / U+XXXX 文字描述构造。
"""

from __future__ import annotations

import os
from pathlib import Path

# ---- 表 A: 禁用类 (码位区间是判据单点, 与 code-style.md 表 A 逐字对齐) --------------------------
BAN_CLASSES: dict[str, tuple[tuple[int, int], ...]] = {
    "circled": ((0x2460, 0x24FF), (0x2776, 0x2793)),
    "misc_symbol": ((0x2600, 0x26FF), ),
    "dingbats": ((0x2700, 0x27BF), ),
    "symbol_arrow": ((0x2B00, 0x2BFF), ),
    "geometric": ((0x25A0, 0x25FF), ),
    "emoji": ((0x1F000, 0x1FAFF), ),
    "invisible": ((0xFE0F, 0xFE0F), (0xFFFD, 0xFFFD), (0xFEFF, 0xFEFF)),
}

# ---- 扫描面 --------------------------------------------------------------------------------------
SCAN_ROOTS = (
    "src",
    "tests",
    "tests-real",
    "e2e",
    "tools",
    "scripts",
    "extensions",
    ".commands",
    ".agents",
    "docker",
    ".github",
    ".vscode",
)
SCAN_SUFFIXES = frozenset(
    {
        ".py",
        ".js",
        ".cjs",
        ".mjs",
        ".ts",
        ".yml",
        ".yaml",
        ".html",
        ".css",
        ".json",
        ".toml",
        ".ini",
        ".cfg",
        ".sh",
    }
)
SKIP_PARTS = frozenset(
    {
        "node_modules",
        "__pycache__",
        ".git",
        "auto-qb-data",
        ".venv",
        "venv",
        "tmp-analysis",
        ".pytest_cache",
        "htmlcov",
    }
)


def collect_files(repo_root: Path) -> list[Path]:
    """扫描面内全部候选文件; 守阵 _scan 与 FROZEN 生成器共用这一份口径。

    根级文件按后缀**自动收集**, 不再靠白名单枚举 —— 白名单会随时间漂移: 评审发现
    根级 hatch_build.py / .github / .vscode 配置曾被漏扫, 与规范「覆盖文件」声明静默不符。
    用户运行时配置 config.yml 走 EXCLUDE_FILES 显式排除(红线面, 只读不纳管)。
    """
    files: list[Path] = []
    for directory in SCAN_ROOTS:
        for dp, dns, fns in os.walk(repo_root / directory):
            dns[:] = [x for x in dns if x not in SKIP_PARTS]
            files.extend(Path(dp) / fn for fn in fns if os.path.splitext(fn)[1].lower() in SCAN_SUFFIXES)
    files.extend(
        path for path in sorted(repo_root.iterdir()) if path.is_file() and path.suffix.lower() in SCAN_SUFFIXES
    )
    return files


# ---- 排除面: 整目录 (第三方设计骨架 / 参考资源, 浏览器渲染展示层, 非运行时代码) -------------------
EXCLUDE_DIRS: dict[str, str] = {
    ".agents/skills/delivery-artifact/references": "第三方设计骨架与参考资源: 视觉设计示例, 符号是展示内容而非本项目代码",
    ".agents/skills/autoclaw-design-capability/审美相关skill": "第三方设计骨架: 审美 skill 的示例与模板, 非运行时代码",
}

# ---- 排除面: 整文件 (功能性数据 / 逐字镜像, 改动破坏机检语义或引用保真) ---------------------------
EXCLUDE_FILES: dict[str, str] = {
    "config.yml": "红线面: 用户运行时产品配置, 按 AGENTS.md 红线节不受本闸门管辖(根目录自动收集后显式排除)",
    ".commands/my-commit-flow/scripts/msg_check.py": "功能性数据: gitmoji 映射表与 VS16/ZWJ 簇边界, emoji 是被校验的输入数据",
    ".commands/my-commit-flow/scripts/test_commit.py": "功能性数据: 提交信息里的 gitmoji 是被断言数据",
    ".commands/mutants/scripts/mutants_dump.py": "第三方输出形态说明: 引用 mutmut stats.emoji_by_status 的对照注释",
    ".agents/skills/release/scripts/suggest_bump.py": "功能性数据: gitmoji 是 DECISION_TABLE 的字典键与判定常量",
    "tests/test_release_suggest_bump.py": "功能性数据: gitmoji 是参数化用例与被断言数据",
    "tests/flaky_allowlist.py": "逐字镜像: 行文本是数据(全行全等匹配), 改注释即守阵失效",
    "tests/fixtures/hr/nexusphp_myhr_last.html": "逐字镜像: 站点页面夹具的自述注释",
    "tests/fixtures/hr/nexusphp_myhr_page1.html": "逐字镜像: 站点页面夹具的自述注释",
}

# ---- 排除面: 局部 (文件, 字符类) 粒度, 只豁免该类, 同类文件新增其它类仍判红 ----------------------
EXEMPT_CELLS: dict[tuple[str, str], str] = {
    ("src/auto_qb/webui/static/shared/tpl/dialog-shell.html", "dingbats"): "WebUI 可见文案: 关闭图标 U+2715, 0229 批先例豁免",
    ("src/auto_qb/webui/static/shared/tpl/settings-detail.html", "dingbats"): "WebUI 可见文案: 关闭图标 U+2715, 0229 批先例豁免",
    ("src/auto_qb/webui/static/shared/tpl/settings.html", "dingbats"): "WebUI 可见文案: 关闭图标 U+2715, 0229 批先例豁免",
    ("src/auto_qb/webui/static/shared/tpl/traffic-card.html", "dingbats"): "WebUI 可见文案: 关闭图标 U+2715, 0229 批先例豁免",
    ("src/auto_qb/webui/static/shared/tpl/xtpl.html", "dingbats"): "WebUI 可见文案: 关闭图标 U+2715, 0229 批先例豁免",
    (".agents/skills/commands/scripts/run.py", "invisible"): "逐字引文: 注释描述 GBK 乱码形态的 U+FFFD 取证文本, 改即失真",
}

# ---- 冻结清单 (机械生成, 勿手改) ----
FROZEN: dict[tuple[str, str], int] = {
    ('.agents/skills/commands/scripts/_config.py', 'misc_symbol'): 5,
    ('.agents/skills/commands/scripts/_tree.py', 'misc_symbol'): 2,
    ('.agents/skills/commands/scripts/install_wrapper.py', 'circled'): 2,
    ('.agents/skills/commands/scripts/install_wrapper.py', 'dingbats'): 3,
    ('.agents/skills/commands/scripts/run.py', 'circled'): 3,
    ('.agents/skills/commands/scripts/run.py', 'dingbats'): 4,
    ('.agents/skills/commands/scripts/run.py', 'misc_symbol'): 1,
    ('.agents/skills/memory-bank/scripts/_common.py', 'circled'): 4,
    ('.agents/skills/memory-bank/scripts/_common.py', 'dingbats'): 2,
    ('.agents/skills/memory-bank/scripts/_common.py', 'misc_symbol'): 9,
    ('.agents/skills/memory-bank/scripts/check_doc_links.py', 'dingbats'): 2,
    ('.agents/skills/memory-bank/scripts/check_doc_templates.py', 'misc_symbol'): 4,
    ('.agents/skills/memory-bank/scripts/check_html.py', 'misc_symbol'): 1,
    ('.agents/skills/memory-bank/scripts/check_kb_structure.py', 'dingbats'): 3,
    ('.agents/skills/memory-bank/scripts/check_kb_structure.py', 'misc_symbol'): 1,
    ('.agents/skills/memory-bank/scripts/check_mutation_anchor.py', 'circled'): 8,
    ('.agents/skills/memory-bank/scripts/check_mutation_anchor.py', 'dingbats'): 1,
    ('.agents/skills/memory-bank/scripts/check_wording.py', 'circled'): 5,
    ('.agents/skills/memory-bank/scripts/check_wording.py', 'dingbats'): 7,
    ('.agents/skills/memory-bank/scripts/check_wording.py', 'misc_symbol'): 1,
    ('.agents/skills/memory-bank/scripts/gen_all.py', 'dingbats'): 3,
    ('.agents/skills/memory-bank/scripts/gen_baseline_recent.py', 'circled'): 3,
    ('.agents/skills/memory-bank/scripts/gen_doc_map.py', 'circled'): 1,
    ('.agents/skills/memory-bank/scripts/gen_doc_map.py', 'misc_symbol'): 1,
    ('.agents/skills/memory-bank/scripts/gen_kb_index.py', 'misc_symbol'): 1,
    ('.agents/skills/memory-bank/scripts/nav_page.html', 'circled'): 3,
    ('.agents/skills/memory-bank/scripts/nav_page.html', 'misc_symbol'): 6,
    ('.agents/skills/memory-bank/scripts/timekit.py', 'dingbats'): 1,
    ('.agents/skills/memory-bank/scripts/wrap_session.py', 'misc_symbol'): 1,
    ('.agents/skills/release/scripts/apply_bump.py', 'circled'): 1,
    ('.agents/skills/release/scripts/ci_gate.py', 'circled'): 1,
    ('.agents/skills/release/scripts/ff_merge.py', 'circled'): 1,
    ('.agents/skills/release/scripts/release_page.py', 'circled'): 1,
    ('.agents/skills/release/scripts/tag_release.py', 'circled'): 1,
    ('.agents/skills/skill-creator/scripts/init_skill.py', 'dingbats'): 10,
    ('.agents/skills/skill-creator/scripts/init_skill.py', 'emoji'): 1,
    ('.agents/skills/skill-creator/scripts/package_skill.py', 'dingbats'): 7,
    ('.agents/skills/skill-creator/scripts/package_skill.py', 'emoji'): 2,
    ('.commands/dev/config.toml', 'circled'): 6,
    ('.commands/dev/config.toml', 'misc_symbol'): 3,
    ('.commands/dev/scripts/test_dev_pkg.py', 'circled'): 1,
    ('.commands/doc/scripts/test_doc_pkg.py', 'circled'): 1,
    ('.commands/env/scripts/test_env_pkg.py', 'circled'): 1,
    ('.commands/kb/scripts/test_kb_pkg.py', 'circled'): 1,
    ('.commands/my-commit-flow/.my-commit-flow.toml', 'dingbats'): 6,
    ('.commands/my-commit-flow/.my-commit-flow.toml', 'misc_symbol'): 4,
    ('.commands/my-commit-flow/scripts/_pipeline.py', 'circled'): 13,
    ('.commands/my-commit-flow/scripts/_pipeline.py', 'dingbats'): 8,
    ('.commands/my-commit-flow/scripts/_ship_config.py', 'misc_symbol'): 2,
    ('.commands/my-commit-flow/scripts/commit.py', 'circled'): 4,
    ('.commands/my-commit-flow/scripts/commit.py', 'dingbats'): 1,
    ('.commands/my-commit-flow/scripts/commit.py', 'misc_symbol'): 8,
    ('.commands/my-commit-flow/scripts/push.py', 'dingbats'): 1,
    ('.commands/my-commit-flow/scripts/sync.py', 'circled'): 5,
    ('.commands/my-commit-flow/scripts/sync.py', 'dingbats'): 1,
    ('.commands/my-commit-flow/scripts/test_pipeline.py', 'circled'): 2,
    ('.commands/my-commit-flow/scripts/test_pipeline.py', 'dingbats'): 1,
    ('.commands/my-commit-flow/scripts/test_snapshot.py', 'circled'): 4,
    ('.commands/my-commit-flow/scripts/test_sync.py', 'circled'): 3,
    ('.commands/release/config.toml', 'circled'): 8,
    ('.commands/review/config.toml', 'circled'): 2,
    ('.commands/review/config.toml', 'misc_symbol'): 1,
    ('.commands/review/scripts/check_review_trace.py', 'circled'): 6,
    ('.commands/review/scripts/check_review_trace.py', 'dingbats'): 2,
    ('.commands/review/scripts/review_pack.py', 'circled'): 3,
    ('.commands/review/scripts/test_review_pkg.py', 'dingbats'): 25,
    ('.commands/test/config.toml', 'dingbats'): 1,
    ('.commands/test/scripts/linux_ci.py', 'circled'): 2,
    ('e2e/add-partial-receipt.spec.mjs', 'circled'): 2,
    ('e2e/column-prefs.spec.mjs', 'circled'): 6,
    ('e2e/ctx-custom.spec.mjs', 'circled'): 4,
    ('e2e/delta-sync.spec.mjs', 'circled'): 10,
    ('e2e/drawer-content-perf.spec.mjs', 'circled'): 4,
    ('e2e/drawer-merge.spec.mjs', 'circled'): 4,
    ('e2e/drawer-peers-variant-tables.spec.mjs', 'circled'): 6,
    ('e2e/drawer-switch-no-flash.spec.mjs', 'circled'): 3,
    ('e2e/drawer-tables.spec.mjs', 'circled'): 13,
    ('e2e/drawer-trackers-variant-tables.spec.mjs', 'circled'): 3,
    ('e2e/dt-live-update.spec.mjs', 'circled'): 8,
    ('e2e/dt-table-face-bg.spec.mjs', 'circled'): 1,
    ('e2e/dt-table-face-bg.spec.mjs', 'misc_symbol'): 1,
    ('e2e/dt-table-layout-parity.spec.mjs', 'circled'): 8,
    ('e2e/gtm-alert.spec.mjs', 'circled'): 11,
    ('e2e/hr-history.spec.mjs', 'circled'): 23,
    ('e2e/hscroll-indicator.spec.mjs', 'circled'): 21,
    ('e2e/hscroll-indicator.spec.mjs', 'misc_symbol'): 1,
    ('e2e/kbd-scroll-band.spec.mjs', 'circled'): 1,
    ('e2e/lib/errors.mjs', 'circled'): 2,
    ('e2e/lib/gestures.mjs', 'circled'): 1,
    ('e2e/lib/mode.mjs', 'circled'): 2,
    ('e2e/lib/probes.mjs', 'circled'): 6,
    ('e2e/lib/scope_ring.mjs', 'circled'): 8,
    ('e2e/lib/vm.mjs', 'circled'): 4,
    ('e2e/main-table-pinned-selected.spec.mjs', 'circled'): 2,
    ('e2e/menus.spec.mjs', 'circled'): 10,
    ('e2e/missing-sites-import.spec.mjs', 'circled'): 12,
    ('e2e/move-dialog-fit.spec.mjs', 'circled'): 17,
    ('e2e/multiselect-shows.spec.mjs', 'circled'): 10,
    ('e2e/multiselect-shows.spec.mjs', 'misc_symbol'): 1,
    ('e2e/optimistic.spec.mjs', 'circled'): 19,
    ('e2e/perf.spec.mjs', 'circled'): 14,
    ('e2e/relocate-pair-filter.spec.mjs', 'circled'): 8,
    ('e2e/rename-dialog-fit.spec.mjs', 'circled'): 9,
    ('e2e/search-auto-refresh.spec.mjs', 'circled'): 2,
    ('e2e/search-uncovered-no-duplicate.spec.mjs', 'circled'): 7,
    ('e2e/shift-select-anchor.spec.mjs', 'circled'): 12,
    ('e2e/site-alerts.spec.mjs', 'circled'): 3,
    ('e2e/site-alerts.spec.mjs', 'misc_symbol'): 1,
    ('e2e/state-moving.spec.mjs', 'circled'): 10,
    ('e2e/table-head-a11y.spec.mjs', 'circled'): 5,
    ('e2e/traffic-gap-zones.spec.mjs', 'circled'): 10,
    ('e2e/trigger-scope.spec.mjs', 'circled'): 5,
    ('e2e/views.spec.mjs', 'circled'): 10,
    ('e2e/window-invalidation.spec.mjs', 'circled'): 3,
    ('tests-real/lib/app.py', 'invisible'): 1,
    ('tests-real/lib/app.py', 'misc_symbol'): 1,
    ('tests-real/lib/guard.py', 'misc_symbol'): 1,
    ('tests-real/rm03_rules/test_rm03_drift.py', 'circled'): 1,
    ('tests-real/rm03_rules/test_rm03_rules.py', 'circled'): 2,
    ('tests-real/rm04_relocate/test_rm04_relocate.py', 'circled'): 1,
    ('tests-real/rm05_tracker_tags/test_rm05_tracker_tags.py', 'circled'): 12,
    ('tests-real/rm06_hr/test_rm06_hr.py', 'circled'): 8,
    ('tests-real/rm07_traffic/test_rm07_traffic.py', 'circled'): 22,
    ('tests-real/rm07_traffic/test_rm07_traffic.py', 'misc_symbol'): 2,
    ('tests-real/rm08_webui_read/test_rm08_missing_groups.py', 'circled'): 8,
    ('tests-real/rm08_webui_read/test_rm08_webui_read.py', 'circled'): 40,
    ('tests-real/rm08_webui_read/test_rm08_webui_read.py', 'misc_symbol'): 2,
    ('tests-real/rm09_webui_write/test_rm09_webui_write.py', 'circled'): 27,
    ('tests-real/rm10_notify/test_rm10_export_merge.py', 'circled'): 9,
    ('tests-real/rm10_notify/test_rm10_notify.py', 'circled'): 39,
    ('tests-real/rm10_notify/test_rm10_notify.py', 'misc_symbol'): 2,
}
