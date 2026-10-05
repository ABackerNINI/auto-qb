# 全面 Code Review · 批 F2 完成 (前端 JS 其余 25 件 + CSS/HTML 机制面)

> 摘要: 计划 [26-10-05-0951](../plans/26-10-05-0951-plan-full-code-review.html) 批 F2 评审轮完成 (只读, 零改码), HEAD `a4d14a8d` 与起点/F1 同 commit。25 件 JS / 7,013 行按 LOC 降序全文件过目 (vendor 2 件按 S1 矩阵口径抽查: Vue 3.5.13 / uPlot 1.6.32 官方 dist, 只核版本与集成面), CSS 18 件 + HTML 18 件按 D1 拍板只查 XSS 汇入点与机制回归面 (aq-tip / 皮肤 / 轮询边界), 不做审美评审。重点维度 R8 R9 R10 逐文件勾选; 坑档 web-ui 30 主题逐条对照 (19 篇直接命中)。**XSS 核对表 (D1 清单法, 覆盖 F2 全部 61 件)**: 非 vendor JS 的 HTML 邻接写点仅 boot.js 4 处 (innerHTML/insertAdjacentHTML 注入内容全为打包期静态 tpl-manifest 模板清单与同源静态分片, fail() 拼串数据源亦全静态 —— F1 核对表预告的归属件在此核销); 1 处选择器插值 (dialogs.js:495 `#sp-"+dir`, dir 内部常量); setAttribute 三处全白名单或纯文本 (theme.js data-theme 经 THEMES 注册表 / aq-tip data-aq-tip 经 textContent 渲染明示不吃 HTML); document.cookie 皮肤值经正则白名单; HTML 模板 **v-html / onclick= 系内联事件 / srcdoc / iframe / javascript: 全 0 处**, 动态内容全走 Vue 插值自动转义, 全部 :href 均为 sprite 内部图标常量; CSS 18 件 url() 外链/@import/expression 全 0, 注释平铺状态机无早闭 (css-comment-terminator 零复发); dialogs.html:135 ↔ dialogs-mgr.html:1 跨分片半配对注释受 manifest 冻结守阵 (test_web.py _ui_manifest rels) 钉住; 皮肤三入口 (cookie/detectUi/theme.js) 全白名单, 轮询边界 (hidden 停排 / 可见即刷 / qb 图三守卫 / hr 按需拉) 机制一致 —— **0 条 XSS 登记**。发现 3 条 (**P3 ×3**): **F2-01 (R10) add_torrent.js 注释漂移** —— :43-44 头注释与 :520 内联注释仍称「multipart 提交不走 this.api() / 原生 fetch」, 实现 (:519-521) 是 this.api + JSON base64 (files_b64, auth.js:21 恒置 application/json), 旧 multipart 版已退役 · **F2-02 (general) delete_flow.js:108 `_deleteDetails` 死变量死分支** —— `const names = []` 零写入, :114 `names.length === 1` 恒假不可达, 单目标命名实际由 members[0].name 承担 (F841 的 JS 同族位, 工具空白) · **F2-03 (R9) loadDir (add_torrent.js:248) 与 doSearch (view.js:23) 无请求代际守卫** —— 快速连点目录/连续改搜索词时前序慢响应可后到覆盖新状态; HTTP 乱序真实可达但自愈型 (再点一次/再输入即纠正), 无数据面后果故 P3 (F1-01 同族, 那条因落袋错弹窗不自愈定 P2)。复验不登记 4 项 + 坑档复发核对 (lifecycle 四个匿名监听未随 unmounted 摘除但根实例永不去挂载 / _logout 不停 SSE 但登出后零请求零落地 / polling refresh 无并发守卫但同 rid 起跑自愈 / 手势监听 mouseup 自摘; aq-tip 双篇、columns-persist 双轨、combobox 四轮加固、hover 3px 门限、tpl-comment-split-orphan、css/js-comment-terminator 等 F2 范围历史坑处置在位零复发)。工具源: eslint 仓库无配置沿 F1 判; node --check 25/25 全过; grep 清单采纳 0, 人工发现 3。test.full **2610 passed + 4 skipped / 99%** (164/138, 15511/5342) 与基线逐位持平 —— 首跑 166/139 (98%) 按 F1 先例复跑即回, 判 ±2 级覆盖抖动非漂移。发现表落盘 [报告草稿批 F2 章节](../reports/26-10-05-1036-report-full-code-review.html)。
>
> 最后活动: 2026-10-05 14:20

**Refs:** memory-bank/plans/26-10-05-0951-plan-full-code-review.html · memory-bank/reports/26-10-05-1036-report-full-code-review.html · memory-bank/pitfalls/web-ui/_index.md · 前序切片 [批 F1](26-10-05-1305-full-code-review-batch-f1.md) · [批 E](26-10-05-1300-full-code-review-batch-e.md) · [批 D](26-10-05-1210-full-code-review-batch-d.md)

## 本轮完成

- sync 成功记 HEAD `a4d14a8d`; 五步动作序列走完 (读档 计划 §03/§06 + web-ui 索引 30 主题 → 坑档逐条对照 19 篇命中 → LOC 降序 25 件 JS 全文件过目 + CSS/HTML 36 件机制面清单 → node --check 替代 + XSS grep 清单逐条人工复核 → 登记去重)。
- XSS 数据源→渲染点核对表 (10 行) 落报告批 F2 章节, 覆盖 25 JS + 18 CSS + 18 HTML 全部汇入点; F1 移交的 boot.js innerHTML 三处归属件在此核销 (静态打包面)。
- 发现表 3 条回填报告草稿批 F2 章节 (含逐文件勾选结论 25/25 / 复验不登记项 4+1 / 工具源小结 / 收尾基线对照); 逐条对照底册附录 A–D 无撞车 (池 2002/2120/2211/1408 族均不涉)。
- 报告脚注批次进度更新为 F2✓ (3 条: P3 ×3; XSS 核对表 0 登记)。
- test.full: 首跑 98% (166/139) 复跑 **2610 passed + 4 skipped / 99%** (15511/5342, 164/138) 与基线逐位持平, 抖动排除过程写进章节。

## 遗留 / 待办

- F2-01/02/03 全 P3: S5 汇总分流转 S6 入池 (建议类型 chore ×2 + refactor ×1), 无需提前单独处理。
- F2-03 收口式样可参照 drawer.js `_drawerStale` (path/query 戳落袋前比对)。
- 剩余批次: G (torrents/ + rules/, 0402 跳检闸门规则侧主面) / H (infra/tray/scripts/extensions/docker)。
