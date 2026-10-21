# 26-10-22-test-hr-row-key-surface-dup — HR 两张表行键面收单点(测试侧常量)

**Status:** Done
**Added:** 2026-10-22
**Updated:** 2026-10-22
**Summary:** 认领 issue 26-10-21-0502(refactor, light): HR 两张表的行键面闭集断言在 `test_hr_status` 与 `test_web_hr` 各手写一份全量字面量, 后端加字段须同改两处、漏改即两守阵口径分叉。收为 `tests/webui_helpers.py` 单点常量(`HISTORY_ROW_KEYS` / `ENTRY_ROW_KEYS` / `ENTRY_ROW_KEYS_API`, R1 追加 `HISTORY_LANE_KEYS` / `SITE_STATUS_KEYS`), 各处断言改引同一处, 守阵语义不变(探针实测: prod 加字段对应断言变红)。复验修正 issue 两处口径: history 实为 **22 键**(非 23); entry 面两处**本就不同集**(模型面 20 键 vs 响应面 +`local_present`), 故 API 面走 `ENTRY_ROW_KEYS | {"local_present"}` 派生。R1 补做 lane 子键面(两处去重)与 `SiteStatus` 键面(单处搬家, 无去重收益)。
**Topics:** test-hr-row-key-surface-dup
**Refs:** memory-bank/issues/26-10-21-0502-refactor-test-hr-row-key-surface-dup.html

## 原始请求

1. 「认领并修复 memory-bank/issues/26-10-21-0502-refactor-test-hr-row-key-surface-dup.html」

## 思考过程与决策

- **复验先于动码**(issue 协议第 5 条): 基线 `39771d41` 上四处字面量仍在, 两测试文件全绿, 现象属实。
- **issue 的两处口径需修正**(复验实测, 不改 issue 正文只在新日志行说明):
  - history 行实为 **22 键**(ts … by), 不是摘要里的 23; 两侧逐字相同 ⇒ 可直接共用一个常量。
  - entry 面两侧**本就不同集**: `test_hr_status` 断言的是 `EntryDetail.to_dict()`(模型面 20 键), `test_web_hr` 断言的是端点响应面(21 键, 多 `local_present` —— 由 `server/routes/hr.py::mark_local_present` 在响应层 join 追加)。硬套「同一个常量」会**抹掉这条差异** ⇒ 拆两层: `ENTRY_ROW_KEYS`(模型面) + `ENTRY_ROW_KEYS_API = ENTRY_ROW_KEYS | {"local_present"}`。
- **常量放测试侧而非 prod**: `EntryDetail.to_dict = asdict(self)`, 键面就是 dataclass 字段集。若期望键面也从 dataclass 派生(或放 prod 常量), 加字段时「实现」与「期望」同步漂移, 守阵形同虚设。测试侧字面量 = 独立契约面, 这是本条 issue 要保的语义。
- **不扩面**(范围守恒): lane 子键面(7 键, `test_hr_status` 内另有两处)、`SiteStatus`/`LaneStatus` 键面同属「字面量重复」但不在本条 issue 列举范围内, 本轮**未动**。

## 实现计划

1. 复验四处字面量仍在(基线 `39771d41`, 两文件全绿)。
2. 常量入 `tests/webui_helpers.py`(HR 段, 三常量 + 为何不派生的注释)。
3. 四处断言改引常量(`test_hr_status`:246/540 区、`test_web_hr`:140/308 区), 两侧补 import。
4. 探针验证守阵仍咬: 临时给 `EntryDetail` 加 `probe_extra` 字段 → 两处同红(2 failed), 还原后归绿。
5. 全量闸门 + 基线切片 + 回写。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 复验: 四处字面量仍在, 两测试文件全绿 | Done(2026-10-22) |
| 2 | `webui_helpers` 收三常量(HISTORY / ENTRY / ENTRY_API) | Done(2026-10-22) |
| 3 | 四处断言改引常量 + 两侧 import | Done(2026-10-22) |
| 4 | 探针: prod 加字段 → 两处同红; 还原归绿 | Done(2026-10-22) |
| 5 | 全量闸门 + 基线切片 + issue 置 Done | Done(2026-10-22) |
| 6 | R1: lane 子键面两处去重(`HISTORY_LANE_KEYS`) | Done(2026-10-22) |
| 7 | R1: `SiteStatus` 键面收进同一常量模块(`SITE_STATUS_KEYS`) | Done(2026-10-22) |
| 8 | R1: 探针验守阵(HistoryLane / SiteStatus 各加字段 → 红) + 全量闸门 + 新基线切片 | Done(2026-10-22) |

## 进度日志

### R0 · 立档 (2026-10-22)

用户指派认领 issue `26-10-21-0502-refactor-test-hr-row-key-surface-dup`, 单轮完成: 复验 → 收单点 → 四处改引 → 探针验守阵 → 全量闸门 → issue 置 Done。
实测数字见 `commands run kb.baseline`(本轮新切片), 本档案与 issue 正文一律引用不抄。

- 2026-10-22 03:36 认领并修复 issue 26-10-21-0502: HR 两张表行键面收 tests/webui_helpers.py 单点三常量, 四处闭集断言改引; 探针验守阵仍咬(prod 加字段两处同红); 全量绿

### R1 · 同族键面补做 (2026-10-22)

用户追加指令: 「lane 子键面与 SiteStatus 键面一同修复, 如果已有 issue 则认领, 没有不用立新 issue」。

- **先查 issue**: `grep SiteStatus|HistoryLane|lane 子键 memory-bank/issues/*.html` 只命中本档案认领的那一条(且是 R0 自己写的「未动」注记), **没有独立 issue** ⇒ 按指令不立新件, 在同一档案续作 R1, 并在 issue 的状态变更日志追加一行说明(状态仍 Done, 不重开)。
- **lane 子键面**(`HistoryLane.to_dict`, 7 键): 两处字面量(`test_history_rows_field_surface` 断言 `row["lanes"][0]` / `test_history_lanes_defaults_and_fallbacks` 断言 `rich.to_dict()`) → `HISTORY_LANE_KEYS` 去重。
- **`SiteStatus` 键面**(39 键): 复查发现**只有一处**(`test_site_status_to_dict_field_surface`), 无第二份可去重 ⇒ 收进同一常量模块(`SITE_STATUS_KEYS`)只为「所有 HR 键面单点在同一处」, **无去重收益**, 如实记账。
- **红验**(守阵没被削弱): ① `HistoryLane` 加 `probe_lane` → 两处断言**同时红**; ② `SiteStatus` 加 `probe_site` → 红。还原后两文件归绿。
- **未动**: `LaneStatus`(14 键, 波次级)与 `QuotaStatus`(既有断言是「与 prod asdict 比」的派生式)不在用户点名范围, 保持原样。

- 2026-10-22 03:47 R1: lane 子键面两处去重(HISTORY_LANE_KEYS) + SiteStatus 键面收同一常量模块(SITE_STATUS_KEYS); 探针验守阵仍咬; 全量绿
