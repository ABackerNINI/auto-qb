# 全面 Code Review · 批 H 完成 (26-10-05-1530)

> 摘要: 计划 [26-10-05-0951](../plans/26-10-05-0951-plan-full-code-review.html) 的批 H 评审轮完成, 发现回填报告底稿 [26-10-05-1036](../reports/26-10-05-1036-report-full-code-review.html) §2 批 H 章节。41 文件 / 15,044 行(infra 9 + tray/入口 4 + scripts 16 + extensions 7 + docker 4)全部过目, 登记 7 条(H-01 P1 qb_capture NameError 落盘前必崩 / H-02·H-03 P2 / H-04…H-07 P3); R8 重点面(扩展凭据出网/file_access 路径穿越/docker 凭据注入面)均核过无发现; 工具源 ruff 87 + bandit 19 逐条复核采纳 0。每批开工 sync 成功, 本轮 HEAD a4d14a8d(与起点同 commit); 收尾 test.full 2610+4 / 99% 持平。评审轮只读零改码, 未 commit。
> 最后活动: 2026-10-05 15:30

## 本轮做了什么

批 H 评审轮(只读, 零改码): infra/ 9 件 + tray/ + 入口 4 件 + scripts/ 16 件 + extensions/hr-fetch-proxy 7 件 + docker 4 件, 共 41 文件 / 15,044 行。重点维度 R6 R7 R8。

- 深度分层: src 15 件 + extensions 7 件 + docker 4 件全文件过目; scripts 按「与主程序/生产数据/出网耦合面」分层 —— 全读 5 件(qb_capture / hr_fetch_experiment / dev_webui / sync_agent_skills / update_config_key_surface), 抽查 11 件(sim_×5 / ui_×2 / check_×3 / bench_expr: docstring + subprocess/网络/写盘面 grep + 关键段复核)。
- 重点核对面结论: file_access.py 路径穿越 — SEC-1 双侧 realpath 校验兜住 `..` 与符号链接, 无洞; 扩展凭据出网面 — cookie 不出浏览器 / token 仅回环 / task.url 无 passkey / 日志不含凭据, 干净; docker 凭据注入面 — config 与数据均不进镜像。
- 工具源: ruff 87 条 + bandit 19 条逐条人工复核(风格债归池 1408, 其余沿批 G 判法不采纳); extensions grep 清单(innerHTML 8 处全转义 / eval 0 / fetch 域约束成立) 0 登记。
- 收尾: test.full 2610 passed + 4 skipped / 99%, 语句/分支总数 15511/5342 与基线切片逐位持平, 无漂移。报告批 H 章节 + footer 进度已回填。

## 发现(7 条: P1 ×1 / P2 ×2 / P3 ×4, 明细见报告批 H 表)

- **H-01 (P1)** scripts/qb_capture.py:990 `_sanitize_mapping` 引用未定义名 `seen` → write_corpus 必 NameError, capture 全流程在任何文件落盘前崩掉(整场语料丢失); 测试只盖 Sanitizer/accumulator 故绿。
- **H-02 (P2)** infra/notify.py:45 ICON_ICO 指向不存在的 infra/assets/(真实在 src/auto_qb/assets/), AUMID 注册表 IconUri 恒写坏路径, toast 来源图标恒缺失; 与池 26-10-01-2203 任务栏图标同族不同件。
- **H-03 (P2)** infra/utils.py convert_bool_in_dict 列表分支缺 isdecimal 守卫(字典分支有), exporter 出口处列表内 "1"/"on" 被静默转 bool。
- **H-04 ~ H-07 (P3)** utils.py:758 docstring 占位符损坏 · infra/__init__.py 依赖纪律漏 notify→config 例外 · locking.py 锁文件路径推导边界(不可达备查) · compose 8081:8080 绑全网卡(部署加固提示)。

## 撞车与底册

- 池 26-10-01-2203 tray Ctrl+C: 现状结构未变, issue 成立, 不重开(报告复验不登记项①)。
- 版本双源 = 底册 A.1 #15, 不重开。
- 无新 P0。

## 下一步

- S5 汇总分级(全批发现合并 + P0/P1 可达性复验 + 入池清单定稿) → S6 报告定稿 + create-issue 入池。H-01 建议入池排序最前(唯一可达 P1, 修复面一行 + 一条端到端用例)。
