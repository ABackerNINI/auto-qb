# 部分种子 HR 在线核实
> 摘要: **2026-09-28 用户定调推翻 v2 模型(每轮全量翻页 / legacy+split 双频控 / 熔断停用回落本地 / 40 键配置面), v3 模型重建计划已立档 [plans/26-09-28-1932](../plans/26-09-28-1932-plan-hr-verify-rebuild.html)(doc-status Open, 22:55 修订)待批准实施: 四行判定表 + 12 格情形矩阵(命中考察中(A)→管束 — **本地达标与否都管**, 删了前功尽弃; 站点终态档 B/C/D 与移出未列出→放行, 终态不可逆; 无证据→本地兜底: 达标放行/未达标管束) + 单波型取数(每波全量对账目标 + A/B/C 轮流翻页 + 三个停翻条件: 完成时间覆盖/**remain==0 连续 5 行到期段强信号**/本地全集 infohash 覆盖, 任一成立即停 — 覆盖对象集 = 未对账∪考察中, 终态种子不再翻页下载; .torrent 下载=身份登记一次(同 tid 永不重下, 状态追踪靠 tid 读页面), **已见 A 档行无条件全下载**(硬规则, 不依赖覆盖区间推断), B/C/D 行按覆盖区间+宽泛名称粗配(重合段≥K)下载(D1 已拍板), 粗配只是疑似触发器/定论一律 infohash 精配, 本地没有的种子不下载; **超额线 SEED_EXEMPT_RATIO=3**(做种≥3×required+extra ⇒ 放行+免除在线对账, 不进覆盖对象集, 特别老藏深的种子不再拉深覆盖; 网站绝对权威 — 被动命中考察中仍转管束); 完成时间可信度分层, 纯辅种由到期段信号/末页收尾) + 单频控三键 + 熔断/停用/退避全删(档位级数据有效性截断式 — 失效点之前数据有效, 失败档 refresh_interval 自然重试; 证据无时效只有真伪, 两级证据年龄与整波覆盖证据退役; 排序失效 = 强制早停(立即停翻不翻页, 失效点之前数据有效, 该档等下周期; 命中不依赖排序故漏 HR 不可能)), 配置 40→14 键; **22:15 全文梳理轮: 修复 17 处口径漂移 + 补齐两个完备性缺口(①骤降保护回归 §5.3 — 行数<基线30% ⇒ 覆盖证据不成立, 防改版吞行整批误放行; ②空对象集停翻语义 §4.2 — 每档 1 页轻量波; §3 重编号 3.3 超额线/3.4 证据健康); **22:22 用户方案完善证据防伪: A 档流转守恒校验(上波考察中行在本波 A/B/C 留存 ≥LANE_RETENTION_MIN(0.7), 不达标 ⇒ 覆盖证据不成立)+ 种子级失踪观察期(22:38 收紧: 失踪者一律当作无证据 — 上波 A 档行本波未在 A/B/C 找到 ⇒ 观察期维持管束, 无小样本豁免无快路径; streak 用种子自身位置局部覆盖证明推进, 连续 2 波判移出; 流转守恒校验只拦批量「未列出」签发; 行 4 特例: 没看到不终结考察中)+ 总量骤降 30% 保留为粗保险**; v2 审计 F1-F4 由 v3 计划整体消解**。此前: M1-M4 + 七批实报 + v2.9-v3.5 + M5.1-M5.5(在线核实 v2)代码侧全部落地并经审计(报告 26-09-28-0030)。核心链路不变: 浏览器扩展代取(登录态不出浏览器) → 后端解析算 infohash → (站点, tid) 索引对账 → 判定联动。
> 触发: 部分种子, HR 核实, 浏览器扩展, 三态判定, 档位即结论, 站点文件, 多实例, BTSchool, CarPT, hr_check, hr_once, hr_status, hr_resume, 取数通道, 本地端点, 取数线程, 登录失效, 复用轮, 回填, 超龄豁免, completed_age_limit, 早停, 骤降保护, suspended, 配额双桶, quota_model, 限流
> 最后活动: 2026-09-28 23:24 (提交轮: 合流 Gitee 3 个提交后文档轮改动入库; 期间 `_doc-map.md` 撞 index-auto cap(12,203 > 12,200), 按 [pitfalls/kb/cap-counting.md](../pitfalls/kb/cap-counting.md) 处置① 收口 gen_doc_map 头部并行 + 单件折行 150→400 ⇒ 12,185(余 15), 未动 cap; test.full 1830 passed / 4 skipped(91%))

## 状态

**在线核实 v3 模型重建计划已立档, v2 模型被推翻(未实施)** —— v2(M5.1-M5.5)代码仍在线上跑, 但模型级重构
计划 [26-09-28-1932](../plans/26-09-28-1932-plan-hr-verify-rebuild.html) 已出, 待用户批准后按 M1-M5 实施;
实施明细与数字的唯一权威在
[任务档案](../tasks/26-09-22-backend-partial-hr-verify.md)进度日志; 审计证据 (逐项 file:line 核对 +
安全性/稳定性评估 + 配置全表/默认节奏/限流全景) 在
[报告 26-09-28-0030](../reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html)。
实施计划 [26-09-27-1815](../plans/26-09-27-1815-plan-hr-verify-audit-fixes.html) doc-status Implemented;
设计定稿在主计划 §14 ([26-09-22-2204](../plans/26-09-22-2204-partial-hr-site-verify-plan.html))。

## 未完成

- **v3 重建计划待批准 (2026-09-28 定调)**: [plans/26-09-28-1932](../plans/26-09-28-1932-plan-hr-verify-rebuild.html)
  doc-status Open —— 用户批准后按 M1 判定 → M2 波次引擎 → M3 频控失败 → M4 配置迁移 → M5 呈现收尾 实施;
  **F1-F4 不再单独修复**(载体被 v3 重写消解: F3 随 parse_missing_rate_max 删除, F1/F2 随早停②归一与停用改退避消解,
  F4 随重写消除); M0 前置实测中「考核期 P 恒定」一项随反算 P 机制删除而作废, 其余实测项并入 v3 M5 真机走查。
- **真机走查**(需用户装扩展): 先 chrome://extensions **reload 扩展** (1 分钟轮询/登录页检测/新选项页要重载生效),
  再 `--hr-once` + 主程序一轮 + 配置面「模板一 → 粘 token → 自动拉站点 → 一键授权 → 立即拉取」全链路。
- **M0 前置实测三项 (+审计提议第④项)**(**阻塞早停②/豁免 A 的启用**, 不阻塞代码): ① HR 页完成时间倒序;
  ② 考核期 P 恒定 (`--hr-status` 观测面直接产证据); ③ `?page=N` 真实参数名与英文站分页形态;
  ④ (新) B/C 档「剩余达标时间」展示形态 (0/空白/非零 → 分别对应 F1 的三条分支)。
- **非 NexusPHP 第三站点**(需样本): 有更便宜来源 (JSON 接口/逐种标记) 按 `adapters/__init__.py` 注册 —— 不拿到样本不猜。
- ⛔ **待用户定**: config.yml 含明文 qB 凭据入不入池 issue; 选项页风格档案 26-09-26-0031 doc-status 是否改 Done。
- **配置面两件事 (程序只提示不代改)**: `hr_check.channel.extension_id` 留空 (启动 WARNING 提示中) +
  `config.yml` 的 `token: 123456` 改留空自动生成 —— 详见报告 §3 残余风险表。

## 指针

- [计划 26-09-27-1815 (v2 实施)](../plans/26-09-27-1815-plan-hr-verify-audit-fixes.html) ·
  [审计报告 26-09-28-0030](../reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html) ·
  [上轮设计审查 26-09-26-1628](../reports/26-09-26-1628-report-hr-online-verify-audit.html) ·
  [主计划 §14](../plans/26-09-22-2204-partial-hr-site-verify-plan.html) ·
  [任务档案](../tasks/26-09-22-backend-partial-hr-verify.md) ·
  [扩展说明](../../extensions/hr-fetch-proxy/README.md)
- 实测: 离线 fixture + 真回环在 `tests/test_hr_*.py` (18 个文件); 全量数字只认
  [testing/baseline.md](../testing/baseline.md) 单点; **真机链路仍未实测**。

**Refs:** memory-bank/reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html
