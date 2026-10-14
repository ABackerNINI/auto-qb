# 认领并修复 webui 跨层常量守阵缺口(cross-layer-constant 批次)

> 摘要: 用户指令「认领并修复 memory-bank/issues/26-10-11-0310-refactor-webui-cross-layer-constant-convention-dup.html」—— webui dup-code 轮(档案 `26-10-11-webui-dup-code-fixes`)当期三条延后项之一的跨层常量批次。开工同步快进 `22f34e13→a369c99a`。复验: 四组常量对均在(STATE_RANK / REANNOUNCE_BLOCKED_STATES / ETA 哨兵 / 键位正则), ETA 哨兵 tpl 处数 4→3 系 26-10-11-1722 计划单元格收敛非漂移; 守阵覆盖缺口 = ③ ETA 哨兵与 ④ 键位正则无跨层机械比对(测试里还手抄第三份正则), ① 的 STATE_RANK_LAST 无守阵, ② 已有逐项守阵。按 issue 建议第一支「保持守阵+补全机械比对」落地(未触前端构建面): views.py 提 `_SHOW_STATE_RANK_LAST` 命名常量; test_webui_static_skins.py 增 3 条跨层守阵(STATE_RANK_LAST 比对 / ETA 哨兵全树扫描零命中即红 / 键位正则逐字比对)并注册+改两处文档字符串; test_web_shortcuts.py 消第三份手抄(改导入后端单点); keys.py/shortcuts.js 注释补守阵指针。三条新守阵全部红绿双验(3 类突变判红 + 3 个活性探针), test.one 两文件 50 passed, test.full 3209 passed + 4 skipped(基线切片 `26-10-15-0450`)。issue 状态流水 Open → In Progress → Done; 认领方 = 任务档案(追加不新建), doc-refs 双向闭合。
> 最后活动: 2026-10-15 04:50

**Refs:** memory-bank/tasks/26-10-11-webui-dup-code-fixes.md

## 正在进行

- **修复已落地并收口**: issue 两处徽标 + meta 置 Done, 状态日志含复验 / 实际修法 / 与建议改道原因 / 验证方式四段; 认领链双向闭合(issue.doc-refs → 档案, 档案 Refs → issue + 基线 + 本切片, 基线 Refs → 档案); 档案 R2 续轮段已追加(Summary / 子任务表第 8 行 / 未做项出账 / 进度日志); kb.index 重建。

## 关键结论(供后续执行参考)

- **修法取舍**: issue 建议两支(①保持守阵/登记防漂移 ②后端出常量+前端构建期注入)选 **①** —— ②触前端构建面且收益中/风险中; 守阵补全后漂移即刻判红, 已消除"两处同改靠人记"的核心风险。②留待真有第二处跨层常量增长时再评估, 改道原因已写入 issue。
- **ETA 哨兵守阵的扫描面**: 按全静态树(.js/.html 除 vendor)抓 `sec/eta >= <数>` 比较点而非硬编码文件表 —— issue 入池时记的"4 处 tpl"已被 26-10-11-1722 计划改成 3 处, 硬编码文件表会漏也会假红; 零命中即红(坑档 guard-dead-branch: "没扫到"必须与"没违规"可区分)。
- **键位正则消第三份表示**: test_web_shortcuts.py 的手抄正则改导入后端 `_KEYS_SERIAL_RE` —— 跨层 JS↔Python 的一致由新守阵 `_scan_keys_serial_re` 逐字比对, 测试消费端从此只有一份 Python 真值。
- **红绿双验实录**(3 类突变 + 3 探针): format.js `8640000→8640001` / shortcuts.js `[A-Z]→[A-Za-z]` / app.js `STATE_RANK_LAST 9→8` 各判红且报错带文件行号与两侧值对照; ETA 零命中 / KB_DEF_RE 声明缺失 / STATE_RANK_LAST 声明缺失三探针均报红; 全部还原后复绿。
- **退回成本**: 守阵为纯增量(既有扫描函数旁新增两支 + 一支扩展), 无行为变化; 若将来上前端构建期常量注入, 三个扫描函数可整体退役, 退役时连同步删三处注释指针即可。
