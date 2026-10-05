# 全面 Code Review · 批 F1 完成 (前端 JS 主干: config_editor / drawer / shortcuts / config_hub / dialogs / commands)

> 摘要: 计划 [26-10-05-0951](../plans/26-10-05-0951-plan-full-code-review.html) 批 F1 评审轮完成 (只读, 零改码), HEAD `a4d14a8d` 与起点同 commit。先读在途 [reannounce 计划 26-10-05-0923](../plans/26-10-05-0923-plan-reannounce-confirm-rework.html) §03/§04 全文 (前端改动面 = S3 commands.js :470–500 聚合分支 + sticky 文案), commands.js 只登记计划未覆盖增量并逐条标「落地后复验」。6 文件 / 6,466 行全部逐文件过目, 重点维度 R8 R9 R10 逐文件勾选; 坑档对照 web-ui 30 主题逐条 (深读 13 篇)。**XSS 清单法 (D1 拍板)**: 渲染点 grep 六文件合计 1 处 HTML 邻接汇入点 (commands.js:676 blob 下载, blob: 本地生成 + 文件名清洗, 有防护) + 3 处选择器插值 (CSS.escape 全覆盖), v-html/innerHTML 系 0 处, 全部动态内容经 Vue 插值自动转义 —— **0 条 XSS 登记**; 凭据面 Bearer 恒走头不进 URL/storage, console 仅 [perf] 时序数字。发现 5 条 (**P2 ×1 + P3 ×4**): **F1-01 (P2) 跳检预检迟到回执写进无关弹窗** —— drawer.js `_skipPrecheck` 落袋守卫只复核 seq 与 modal.visible, 不校验 modal 身份; 取消跳检框后预检在途回执 (批量 60s 上限) 落地时若用户已打开其它 modal (限速/重命名/删除确认, 共用 `this.modal` 单例), verdict/okDisabled/okText 被按跳检三分流改写, 无关弹窗出现跳检明细行 · F1-02 (P3) config_editor.js CE_FIELD_BASE `sectionExists` 同名键定义两次 (:1240-1245, 两体逐字相同, 改一处漏一处的静默陷阱; ruff F811 的 JS 对应位工具空白) · F1-03 (P3) commands.js `waitCmd` race 以 auth 异常拒绝时 `stop.v=true` 与 `_cancelCmdWait` 被跳过, SSE waiter + 定时器悬挂至超时自愈 (有界, 备查) · F1-04 (P3, 池 2002 前端半边定位补全) 警示条取数单点 = config_hub.js hubRiskList/hubCollectRisk, risk 文案系 schema 原文复述, 健康判定仅「已配置」一道门槛, 与 hubLedOf 的 host warn 两套口径脱节 —— 并入池 26-09-22-2002 不重开 · F1-05 (P3, reannounce 计划未覆盖, 落地后复验) cmdStats 单槽 vs 并发命令: 后发命令重写槽, 先发命令回执的时序数字合并进后发槽, [perf] 日志可能误归因 (限诊断日志, 零 UI 后果)。复验不登记 6 项 (_bulkTargets 虚拟组空成员不可达 / drawerDel 无 catch 论证不出拒绝路径 / submitSpeedDialog 主速空串仅请求失败态 / setFilePriority index 无轮询重排面 / _kbViewportRow 全 DOM 扫描非热路径 / 坑档复发核对: 六文件全部历史坑处置在位零复发形态)。工具源: 仓库无 eslint 配置按约跳过并注明; node --check 6/6 全过; XSS grep 清单采纳 0。test.full **2610 passed + 4 skipped / 99%** (164/138, 15511/5342) 与基线逐位持平 —— 首跑曾出 166/139 (98%), 同 HEAD 复跑即回, 判定多线程收尾覆盖抖动非漂移。发现表落盘 [报告草稿批 F1 章节](../reports/26-10-05-1036-report-full-code-review.html)。
>
> 最后活动: 2026-10-05 13:05

**Refs:** memory-bank/plans/26-10-05-0951-plan-full-code-review.html · memory-bank/plans/26-10-05-0923-plan-reannounce-confirm-rework.html · memory-bank/reports/26-10-05-1036-report-full-code-review.html · 前序切片 [批 A](26-10-05-1100-full-code-review-batch-a.md) · [批 B1](26-10-05-1130-full-code-review-batch-b1.md) · [批 B2](26-10-05-1135-full-code-review-batch-b2.md) · [批 C](26-10-05-1150-full-code-review-batch-c.md) · [批 D](26-10-05-1210-full-code-review-batch-d.md) · [批 E](26-10-05-1300-full-code-review-batch-e.md)

## 本轮完成

- sync 成功记 HEAD `a4d14a8d`; 五步动作序列走完 (读档 计划 §03/§06 + reannounce 计划 §03/§04 → 坑档 web-ui 30 主题逐条对照、13 篇深读 → LOC 降序 6 件全文件过目 → eslint 缺配置注明 + node --check 替代 + XSS grep 清单 → 登记去重)。
- XSS 数据源→渲染点核对表落报告批 F1 章节 (4 行: blob 下载写点 / CSS.escape 选择器 ×3 / Vue 插值兜底面 / 凭据面), F2 复用同一 grep 方法续查 boot.js innerHTML 三处 (静态模板清单, 归 F2 机制面)。
- 发现表 5 条回填报告草稿批 F1 章节 (含逐文件勾选结论 6/6 / 复验不登记项 6 项 / 工具源小结 / 收尾基线对照); F1-05 与 reannounce 计划关系标注「未覆盖增量 + 落地后复验」, F1-01/02/03 标「无交叠」。
- 报告脚注批次进度更新为 F1✓ (5 条: P2 ×1 / P3 ×4; XSS 清单 0 登记)。
- test.full: 2610 passed + 4 skipped / 99% (15511/5342, 164/138) 与基线切片逐位持平; 首跑 166/139 抖动已复跑排除并写进章节备注。

## 遗留 / 待办

- **F1-01 (P2) 建议入池**: 修法 = modal 单例落框守卫补「modal 身份戳」第三条件 (_openModal cfg 带一次性 id 或 _skipCheckDialog 记 tag), 并把「单例 modal + 异步落框」守卫收成单点防同形复发 (drawer-switch-flicker 复发 2「成对协议须显式锚」同构教训)。
- F1-04 定位信息已并入池 26-09-22-2002 口径 (修复时与 hubLedOf 健康判定合流), 不新开条目。
- F1-05 标注 reannounce 计划落地后复验 (若实施轮顺手动 cmdStats 面一并收)。
- 剩余批次: F2 (其余 25 JS + CSS/HTML 机制面, 复用 XSS 清单法) / G (0402 规则侧主面) / H。
