# 5195 passed + 10 skipped —— webui 迁移可见性两条 minor 修复后全量

> 摘要: 5195 passed + 10 skipped —— webui 迁移可见性两条 minor 修复后全量
> 基线时间: 2026-11-04 21:54
**Refs:** memory-bank/tasks/26-11-04-webui-relocate-visibility.md

## 验收数字

```
TOTAL                                                24404    228   8356    171    99%
5195 passed, 10 skipped in 172.92s (0:02:52)
```

- 环境: Windows 本地, `commands run test.full`(含覆盖率闸 99.0%)。
- node 探针用例在本机实际执行(node 可用); 非 node 环境按既有惯例静默跳过。
- 真机另跑 RM04-15/17/19 全 PASS(real-fake 副实例), 明细见 `tests-real/.work/rm04/*_evidence.json`。

## 本改动面

- src/auto_qb/core/modules/relocate_units.py: `RelocateJob` 新增 `created_at`(设置时间源)与 `tag_on`(曾 add 账), 双向持久化
- src/auto_qb/core/modules/relocate_exec.py: `_start_job` 以同一 stamp 落 `created_at`/首笔 `updated_at`; `_carry_prev_tag_state`(同 job_id 重发继承 tag_on 并清进程内镜像记忆)
- src/auto_qb/core/modules/relocate_lifecycle.py: 终态 remove 收窄为 `tag_on=True`; 新增 `_note_tag_state` 落账; reconcile 只扫非终态+曾 add 终态
- src/auto_qb/core/modules/relocate_mod.py: `_set_job` 返回账上现值(防 tag_on 被旧对象覆盖)
- src/auto_qb/webui/views_relocate.py + static/shared/drawer_rows.js: 详情「迁移」段新增「设置时间」(旧 state 无源显示 "—")
- src/auto_qb/webui/static/shared/decorate.js: 装饰指纹纳入 `created_at`
- tests/test_relocate_tag_mirror.py: +4 例(未 armed 撤销/未 armed 失败零写; 摘除失败跨重启按账重试; job_id 复用继承旧账)
- tests/test_webui_relocate_visibility.py: created_at 投影/「设置时间」行/指纹断言
- tests-real/lib/relocate_visibility_ui.mjs + rm04 可见性用例: RM04-15 增抽屉设置时间真渲染取证; RM04-17 收紧 remove 恰 1 次; 新增 RM04-19 未 armed 终态零 remove
