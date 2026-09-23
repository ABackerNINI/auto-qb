# 26-09-15-backend-torrentrecord-fields — TorrentRecord 全字段缓存 (快照 21 → 70 字段)

**Status:** Done
**Added:** 2026-09-15
**Updated:** 2026-09-15
**专题:** 数据层 / 为 WEB UI 供数
**Legacy-ID:** TASK006
**Summary:** 快照 21 → 70 字段 (`_raw` 降为兜底) + `to_dict()`; 基线 879 (2026-09-15)
**Topics:** backend-torrentrecord-fields

## 原始请求

- 2026-09-15: 让 `TorrentRecord` 缓存 qB 全量字段 (用户提供真机 `TorrentDictionary` 样例), 为后续 WEB UI 替代 qB 界面供数; 用户拍板**跳过定稿评审直接实施**。

## 思考过程与决策

- 字段表分三层: `_REQUIRED_SNAPSHOT_FIELDS` 21 必填 + `RE_ADD_FIELDS` 6 升格 + `_EXTENSION_FIELDS` 43 可选 (全表 70)。
- 决策 D1-D5: slots 全量声明 (`_raw` 降为前向兼容兜底) / `RE_ADD_FIELDS` 升格快照 (变化即入变化集) / 新字段全可选 (默认取 qB 哨兵 `-1` / `-2` / `8640000`) / `REQUIRED` 校验面不变 / 缓存≠展示 (新字段不进 `_VIEW_FIELDS`, 视图重建成本零变化)。
- 兜底原样透传; 新增 `to_dict()` 全字段导出。
- 原则: 视图/规则/HR/分组消费字段全在旧集合内 → 零行为变化。

## 实现计划

- [x] `compat.py` 字段表分三层 (70 字段)
- [x] `record.py` 新增 49 slots + `to_dict()`
- [x] 测试 +9 净 +7 (升格 / 未知字段落 `_raw` / 哨兵默认 / 扩展字段 / `to_dict` / 守卫 `SNAPSHOT→slots` / 真机样例回归 / 视图纪律)
- [x] 真机只读冒烟 (`.openclaw/tmp/smoke_full_fields.py`, sync rid=0, 119 种子) — 字段全声明 `_raw` 无残留; 补发现 4 个样例之外字段 (`reannounce` / `has_tracker_error` / `has_tracker_warning` / `has_other_announce_error`)
- [x] 文档回写

## 子任务状态表

| ID | 描述 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| 6.1 | 字段表分层与 slots 声明 | Complete | 2026-09-15 | `compat.py` / `record.py` |
| 6.2 | 测试补强 (+9 净 +7) | Complete | 2026-09-15 | 基线 879 passed |
| 6.3 | 真机只读冒烟 | Complete | 2026-09-15 | 119 种子, 补 4 字段 |
| 6.4 | 计划文档 | Complete | 2026-09-15 | `memory-bank/plans/26-09-15-1302-record-full-fields-plan.html` |

## 进度日志

### 2026-09-15

- 实施完成, 基线 879 passed。
- 踩坑: 编辑 `record.py` 时把 `to_dict` 插入 `state_enum` 的 `return` 之前 → 变成死代码 + 26 个测试连锁失败 (已修复)。
- 提交 `998136f`; 本机 `uv` 不在 PATH (用 WinGet Links 全路径), `.venv` 曾丢失已 `uv sync` 重建。

## 历史会话纪要 (原文归档)

> 以下为 `activeContext.md` 会话纪要的**原文归档** (2026-09-17 机械迁移, 未删改; 含一处历史 GBK 编码损坏条目),
> 按时间倒序保留。新增进展请写 `## 进度日志`, 不要再往 `activeContext.md` 堆长纪要。

- 2026-09-15: TorrentRecord 鍏ㄥ瓧娈电紦瀛樺疄鏂?鈥?鐢ㄦ埛缁欑湡鏈?TorrentDictionary 鏍蜂緥璺宠繃瀹氱璇勫鐩存帴瀹炴柦; compat.py 瀛楁琛ㄥ垎灞?_REQUIRED_SNAPSHOT_FIELDS 21 + RE_ADD_FIELDS 6 鍗囨牸 + _EXTENSION_FIELDS 43 鍙€? 鍏ㄨ〃 70), record.py 鏂板 49 slots(鍗囨牸 6 + 鎵╁睍 43, 榛樿鍊煎彇 qB 鍝ㄥ叺 -1/-2/8640000) + `to_dict()`; REQUIRED 鏍￠獙闈笉鍙? apply_delta/store 闆堕€昏緫鏀瑰姩(_raw 闄嶄负鍓嶅悜鍏煎鍏滃簳); 瑙嗗浘/瑙勫垯/HR/鍒嗙粍闆惰涓哄彉鍖?鏂板瓧娈典笉杩?_VIEW_FIELDS, 娴嬭瘯閿佹); 娴嬭瘯 +9 鍑€ +7(鍗囨牸/鏈煡瀛楁钀?_raw/鍝ㄥ叺榛樿/鎵╁睍瀛楁/to_dict/瀹堝崼 SNAPSHOT鈫攕lots/鐪熸満鏍蜂緥鍥炲綊/瑙嗗浘绾緥), 鍩虹嚎 879; 鐪熸満鍙鍐掔儫(.openclaw/tmp/smoke_full_fields.py, sync rid=0 119 绉嶅瓙)瀛楁鍏ㄥ０鏄?_raw 绌哄苟琛ュ彂鐜?4 涓牱渚嬪瀛楁(reannounce/has_tracker_error/has_tracker_warning/has_other_announce_error); 鍧? record.py 缂栬緫鏃?to_dict 鎻掑叆鎶?state_enum 鐨?return 鎸ゆ垚姝讳唬鐮?26 涓祴璇曡繛閿佸け璐? 宸蹭慨澶?; test_autostart_windows_registry 鍦ㄦ矙绠?shell 鐪熷啓娉ㄥ唽琛ㄥ彈闄愬け璐?HEAD 鍚屾牱澶辫触, 闈炴湰娆″紩鍏? testing.md 宸叉敞); 鏈満 uv 涓嶅湪 PATH(鐢?WinGet Links 鍏ㄨ矾寰?, .venv 鏇句涪澶卞凡 uv sync 閲嶅缓; 宸叉彁浜?998136f
