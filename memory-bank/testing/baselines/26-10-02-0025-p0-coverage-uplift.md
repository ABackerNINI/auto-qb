# 基线 · 1997 passed + 3 skipped / 93% —— 测试覆盖率提升 P0 快赢轮(T0.1-T0.7)

> 摘要: 计划 26-10-01-2157(测试覆盖率提升 91%→96%)P0 阶段收官基线 —— 七项快赢任务落地, 综合覆盖率 90.83% → 93.24%。
> 档案: [plans/26-10-01-2157-plan-test-coverage-uplift.html](../../plans/26-10-01-2157-plan-test-coverage-uplift.html)。
> 基线时间: 2026-10-02 00:25, develop @ 41aa9f00 (与远端合流后的新基线上实测; 工作树含本笔改动与收尾回写, 未提交)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告 —— 两侧都重测前不当作两侧事实源)。

TOTAL **1997 passed + 3 skipped / 93%**(13377 语句 / 774 未覆盖 / 4444 分支 / 329 partial,
test.full 20.53 / 20.57s 两采样, rc=0)。**精确综合口径**(coverage json 导出, 行 + 分支出口合计):
**16,616 / 17,821 = 93.24%**(语句 12,603/13,377 = 94.21%, 分支 4,013/4,444 = 90.30%)。
相对计划基线(26-10-01-2157 实测 @ 40334066: 16,093/17,718 = 90.83%)**+523 已覆盖单位**;
其中分母同步 +103(合流的远端提交带入新代码: hr/status.py、routes/hr.py 种子明细端点、
writer readonly 防线、schema 字段等), 新代码已由远端自带测试与本笔共同覆盖。

## 本笔改动面 (P0 任务逐项, 目标文件全部清偿到 0 missing 行 + 0 missing 分支)

- T0.1 `infra/versioning.py` `_migrate_hr_site_1_2` 整函数(plan 欠账 21)→ test_versioning.py +3:
  quota→rate / refresh→wave 双支路全字段 / 非 dict 入参不派生 / 非法数值兜底(day_window 缺失、
  计数非 int、时间戳不可转换)。
- T0.2 表达式引擎四件(env 77 + eval 69 + types 34 + lexer 12)→ test_expr_eval.py +8、
  test_expr_parse.py +3: 取值器/函数表补遗、文件访问层错误映射、运行期错误路径参数化 12 条、
  算术与比较运行期支路、静态校验边界、trace 节点遍历与 _jsonable 兜底、lexer 转义/越界时刻/
  非法字符/非十进制数字、types 规则直测、名字表未映射注解跳过、expr_cache 自建。
- T0.3 `config/validation/sections.py` 校验矩阵(plan 欠账 61)→ test_config.py +8: hr_check 段/
  channel/sites 条目/站点绑定跳过口径/fs.path_map 四类/web 段/tracker.rules 非列表跳引用/
  notify.channels 单键映射, 消息断言 + 分支真抵达(含合法形态不报错侧)。
- T0.4 `webui/server/routes/events.py` SSE 生成器整块(plan 欠账 19)→ test_web.py +2:
  hello/事件/keepalive/终结退订全路径 + 异常死亡也退订。!不走 TestClient 流式读(starlette 1.6
  portal.call 会挂死无限流, 实测 90s), 直调端点 anyio 驱动 body_iterator; keepalive 猴补 0.05s
  且挂钟下界留 20ms 余量(timing-tolerance)。
- T0.5 `routes/hr.py` 三段(plan 欠账 27)→ test_web.py: refresh 单站受理 + 门面缺席 409、
  confirm-empty 四态(缺 site/未启用/未接入 400 + 写入失败 409)、种子明细端点 service 缺席 409。
- T0.6 入口壳与 CLI(plan 欠账 ~35)→ test_cli.py +9: 参数互斥矩阵 5 条、confirm-empty 清单解析/
  空清单报错、--hr-once 透传、--tray 双开唤起失败回落、auto-qb.py 与 __main__.py 守卫双态
  (runpy 进程内, 零子进程)、cli.py __main__ 守卫直执行。
- T0.7 `config/writer.py` + `migrations.py` 长尾(plan 欠账 ~45)→ test_config_writer.py +17:
  掩码非映射透传/还原守卫与哨兵旧值、盖章非 dict 跳过、版本闸门非整数形状放行、首存无源、
  非映射 YAML 重建、round-trip 列表与原生标量、物化版本坏包 ConfigError、_url_host 形状、
  schema v1→v2 三形态与 v2→v3 条目清理、非映射 config 段物化空转、相对备份路径、
  _set_path/_delete_path 形状防御。

## 红验与防回沉

- 变异红验 6 条(≥10% 抽样, 全部当场红、逐条精确还原): versioning quota 支路翻转 →
  test_migrate_hr_site_v1_v2_full 红; sections fs 空值检查摘除 → test_validate_fs_errors 红;
  events hello 帧篡改 → test_api_events_sse_stream_lifecycle 红; cli html-dir 互斥摘除 →
  test_main_arg_mutex_errors[html-dir-needs-once] 红; writer unmask 哨兵守卫翻转 →
  test_unmask_tree_guards_and_sentinel_old_value 红; eval expr_cache 自建摘除 →
  test_eval_cache_created_on_missing 红。还原后 `git status src/` 干净。
- P3-M1 阈值随本切片抬起: pytest.ini addopts 追加 `--cov-fail-under=92`(实测 93.24% − 1 个点
  余量, 口径见计划 §5; test.quick 的 --no-cov 豁免不动)。
