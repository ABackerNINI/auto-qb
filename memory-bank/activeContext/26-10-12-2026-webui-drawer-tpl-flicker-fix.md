# 变体模板表格闪烁修复 · 三层探针取证闭环（dtHoldAnchors 验证 + 探针伪影反转 + 44/44 回归）

> 摘要: 用户报「WEBUI种子详情模板所有表格闪烁, 修复」。U5 收口后追查: ①**探针伪影反转** —— 曾报「2,0,2,0 完美交替、blank 恰好一半」的周期性闪烁读数, 实为**双 rAF 循环共享同一 `window.__blink` 数组**的探针 bug(切页后旧循环看空宿主恒写 0 与新循环写 2 交替 push); 改用全局单循环 + `__stop` 停止标志后, 前 20 轮单循环探针的"未复现"全部得到解释。②**三层探针取证**(修复后的 dtHoldAnchors 代码上): 静态数据 20s×3 锚/头/表/首行身份全程不变(peers 段 1853 帧 rowFlips=0); **API 级数据 churn**(route 截拦 `/peers` 速度逐拍变, 静态桩测不到的真实路径)1445 帧 `rowFlips=0` `uniq=1` —— 每拍整帧重建 + anchFill 保活, 行内容走引擎响应式原地更新; **空↔非空 flap** 锚身份全程唯一、表头幸存、gen 不升、控制台零报错。③**修复落地验证**: dtHoldAnchors(早分支清帧后把离文档的记账锚接回宿主 `display:none` 隐藏持有 ⇒ 不摘 on ⇒ 桥不卸载)命中真实缺陷面(真机复现取证所见的"卸挂闪烁 + 游离旧锚消失不恢复"两种面貌), 判据 `!isConnected`(初版按父节点判会把已就位的锚每次渲染后挪走藏掉, 已修)。④**回归**: drawer-bridge-stub + 三套 variant-tables + sticky-flush + merge 共 **44/44 过**; 18 个临时探针全部清除(纪律: 探针不进仓库)。⑤**回写**: 坑档 drawer-switch-flicker.md 追加「复发 +1(第六次)」完整条目(契约面判别 + 探针自证纪律)。⑥ rid 增量振荡理论排除(后端 sync_torrent_peers 恒 rid=0 全量整包, 前端无 rid 处理也不会拿到残-list)。

> 最后活动: 2026-10-12 20:26

**Refs:** memory-bank/pitfalls/web-ui/drawer-switch-flicker.md,memory-bank/tasks/26-10-12-webui-drawer-table-rework.md

## 残留(设计内, 非缺陷)

- 空列表拍桥的 `.group-table`(行容器)随 `v-if` 行数卸载、数据回来重挂 —— 空态期锚整体 `display:none` 不可见, 用户看到的是「表格→空态文案→表格」的空态语义本身(P3-5); 表头(aq-table 在 v-if 外)不重挂, 排序/列宽偏好归引擎不受影响。若用户真机复现的正是"空↔非空振荡"场景且对重建敏感, 再议 v-show 化(注意: 会改 rowAfter/roving 重挂语义, 有回归面)。

## 停手点

- 未 commit / 未 push(用户未要求); 工作区唯一改动 = `src/auto_qb/webui/static/shared/drawer_templates.js`(dtHoldAnchors + anchFill display 复位)。
- test.full / dev.e2e 全量未跑(本波改动面经 44/44 抽屉回归 + 路径 A 冒烟覆盖; 全量回归留待用户指令)。
