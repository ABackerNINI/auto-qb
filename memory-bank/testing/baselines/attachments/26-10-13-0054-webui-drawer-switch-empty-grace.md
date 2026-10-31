# 3167 —— 抽屉三列表软切换空态宽限: peers 收口后扩至 trackers/files(第九次复发, 同族一并修)

**Refs:** memory-bank/pitfalls/web-ui/drawer-switch-flicker.md,memory-bank/activeContext/26-10-13-0027-webui-drawer-switch-empty-grace.md,memory-bank/testing/baselines/26-10-13-0027-webui-drawer-switch-empty-grace.md

> 摘要: 承接上一基线(peers 单列表宽限)。用户指令「提交后修复 trackers/files 的同族问题」—— 该缺陷的覆盖面是**抽屉三列表(peers/trackers/files)共有的数据落袋语义**: 软切换(FX-29)「保留旧数据撑几何 + 遮罩防串显, 数据全部到手才掀罩」的「到手」只判"响应回来了", **空响应同样算**(覆盖旧数据 + 登记 `_drawerDone` 掀罩 ⇒ 渲染层判空 ⇒ 一帧空态); 真机换目标后 qB 对新种子的首个列表响应常瞬时为空 ⇒ 三页签各自闪自己的空态文案(用户页「暂无已连接用户」/ Tracker 页「暂无 tracker」/ 内容页「无文件列表」)。修法: 把 peers 的局部宽限**上提为三列表共用单点** `drawer_store.js::_drawerGraceHold(src, hash, count, refetch)`(标记守卫 + 一次性消费 + 1s 重拉 + 复核), 标记 `_drawerGrace = {peers, trackers, files}` 由 `_switchDrawerTarget` 于 `_loadDrawerTab` **之后**同置, timer 由 `_stopDrawerPoll` 逐个收口; 三 fetcher 同接入, 差异压到"判空表达式"一处(peers 取 dict 键数 / trackers·files 取数组长)。测试面同批改造: 静态守阵 `test_drawer_peers_switch_empty_grace_wiring` → `test_drawer_list_switch_empty_grace_wiring`; 单页签 e2e 用例迁出 `drawer-peers.spec.mjs`, 新建合并 spec `e2e/drawer-switch-empty-grace.spec.mjs`(三页签 × 双皮肤)。
> 基线时间: 2026-10-13 00:54

上一基线：memory-bank/testing/baselines/26-10-13-0027-webui-drawer-switch-empty-grace.md

## 验收数字

- `test.full`: **3167 passed + 4 skipped** / 覆盖率 `TOTAL 16718 158 5688 139 99%`(98.65%; 上一基线记 3166 —— 本波守阵为**改造非新增**(peers 单列 → 三列表共用), 二者测试数应相等; 实测 +1 差异在 HEAD(上一提交 c448ba8c)与工作树上**同时存在**(3167), 即非本波引入, 疑为某参数化守阵受环境/未跟踪目录影响, 未定位, 两次均全绿)。
- e2e(全量 `dev.e2e`): **206 passed + 10 skipped + 0 failed**(6.3m)。上一轮出现的 `drawer-peers-sticky-flush` atlas 亚像素几何 flaky(±1px 容差边缘)本轮未复现(单独复跑亦 4/4 绿)。
- e2e(三页签新 spec 单跑): **6 passed / 0 failed**(用户/Tracker/内容 × prism+atlas, 各 ~4s)。
- 红验(拆 `_drawerGrace` 置位): e2e 三页签 × 双皮肤 **6/6 全红**, 逐条命中各页签空态文案; 还原即绿(闭环)。
- 复现探针(临时, 未进仓库; peers): classic/07/08/09 全 `C80`→`E0`(80 对端真量级 + 切换目标首拍 /peers 返空); 恒非空对照 275 帧全 `C80`、0 空态帧。

## 本波改动面

- **生产代码**(1 文件): `src/auto_qb/webui/static/shared/drawer_store.js` —— 新增 `_drawerGraceHold` 单点; 三 fetcher(`_fetchDrawerPeers|Trackers|Files`)接入(`deferred` 短路 finally); `_switchDrawerTarget` 置 `_drawerGrace`(三置, 于 `_loadDrawerTab` 之后); `_stopDrawerPoll` 收口 retry timer + 标记; 头注归属清单补 `_drawerGraceHold`。
- **测试**: `tests/test_webui_static_dom_panel.py`(守阵改造 + 计划清单同步); `e2e/drawer-switch-empty-grace.spec.mjs`(新增, 三页签 × 双皮肤); `e2e/drawer-peers.spec.mjs`(单页签用例迁出, 原位留指针 + 头注改版)。
- **知识库回写**: 坑档「第九次」条补「同族一并修」段 + 探针纪律⑦(先枚举同族面, 能单点收口就一次收口); `modules/webui-static-contract.md` 宽限描述改为三列表单点; activeContext 切片 `26-10-13-0027-webui-drawer-switch-empty-grace.md` 更新(最后活动 00:54)。

## 已知偏差 / 移交

- 口径取舍(同上一基线): 「空响应 = 未就绪 vs 真没有」前端无法区分, 取「宁可多等 1s 也不误报空」—— 真没数据的种子会先显示 1s 加载态再落空态。
- `test.full` 计数 3166 → 3167 的 +1 未定位(见上; 与上一提交同值, 非本波引入), 未深究。
- `drawer-peers-sticky-flush` atlas 亚像素几何 flaky 仍在(既发, 与本波无关), 未入池。
- 存量债务(同前, 未动): `modules/webui-static-contract.md` 超 evergreen cap(本波 +~200 字符); activeContext 切片数债务(> 70)。
- 未 commit / 未 push(本波完成后待用户指令)。

> ⚠ **已被取代(2026-10-13)**: 本条描述的「三列表宽限 + 1s 重拉」诊断与机制已被用户否掉并整体回退
> (「种子的常态就是没有对端」—— 空响应不是"未就绪"); 诊断更正与最终修法见
> `26-10-13-0148-webui-drawer-switch-no-flash.md` 与坑档 `drawer-switch-flicker.md` 第九次条目。
