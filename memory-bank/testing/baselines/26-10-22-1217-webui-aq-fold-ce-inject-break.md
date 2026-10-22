# 3990 passed + 10 skipped(根) —— aq-fold 补 ce 透传 + e2e 回归守阵后全量基线

> 摘要: aq-fold 补 ce 透传 + e2e 回归守阵后全量基线
> 基线时间: 2026-10-22 12:17

## 验收数字

`commands run test.full` 实测(裸数字只写本切片这一处):

- TOTAL 表: **20728** stmts / **116** miss / **7088** branch / **106** partial / **99%**
- 汇总行: **3990 passed, 10 skipped in 77.87s (0:01:17)**

逐条口径注记:

- 本轮唯一 prod 改动是 `src/auto_qb/webui/static/shared/ctl_bits.js`(前端 JS, 不在 pytest 覆盖率分母内); e2e 规格不在 pytest 的 testpaths 内, 由 `npm run test:e2e:fast` 兜住(实测 214 passed)
- 10 skipped 全为**环境条件跳过**(符号链接/junction 权限相关: `test_file_access.py`「无法创建目录符号链接(权限不足)」、`test_grouping_relocate.py`「本机 cannot 建 junction」等), 与本次改动无关; 同棵树早前同一会话内一次采样同为 3990+10, 判定为沙箱权限态噪声
- 基线测在「已含本次代码改动、尚未提交」的工作树上; 修复本体自 test.full 通过后未再变动(红验期间临时摘除后已原样还原, 见档案步 5)
- 耗时 77.87s 是单次采样(同时段机器负载口径见 `testing/baseline.md`)

## 本改动面

- `src/auto_qb/webui/static/shared/ctl_bits.js` —— `AQ_FOLD_COMPONENT` 补 `inject:["ce"]` + `provide(){ return { ce: this.ce }; }`(仓库既有透传范式, 与 `traffic_card.js:15` / `CE_FIELD_BASE` 同款), 并写长注释记录事故机制(全局 mixin provide 劫持 + 插槽注入断裂)
- `e2e/traffic-source-switch.spec.mjs`(新) —— 双皮肤 6 例回归守阵(读路径: 磁盘 false 必须显关闭 + 无「默认」徽标 + 与卡头摘要同判 + 刷新后仍关闭; 写路径: 拨动→脏标记→「保存并应用」→PUT 载荷 false; 第二现场: 规则卡「触发与节奏」段 execute_once=daily), 全打 `@fast`; 红验: 摘掉透传 6/6 全红
- `memory-bank/issues/26-10-22-0435-bug-webui-aq-fold-ce-inject-break.html`(新) + 索引重建
- `memory-bank/pitfalls/web-ui/mixin-ce-inject-break.md`(新) + 索引重建
- `memory-bank/tasks/26-10-22-webui-aq-fold-ce-inject-break.md`(新) + 本基线切片 + 索引重建
