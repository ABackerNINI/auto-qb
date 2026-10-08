# webui-qb-traffic-seed-header-controls — 修回归: 种子流量图的时间档位/纵轴控件消失

> 摘要: 用户报「上次更改使种子流量图的时间视图选择按钮和纵轴模式选择按钮弄消失了」。根因 = 2026-10-08
> 版式改(切片 26-10-08-0713)把时间档位(.qb-tabs)+ 纵轴控件(.qb-tools)上提到头部时**只接了一个形态
> 宿主** —— 加进了流量形态头部(全局/分组), 而**种子流量图走的是种子形态头部**(`kind === "seed"` +
> `tab === "traffic"`, 见 `qbCurScope` 的 torrent 分支), 该头部没有这段控件 ⇒ 整组消失。修法 = 种子形态
> 头部补同款控件组(`.qb-headctl`, 门 = `qbCurScope === 'torrent'`), 三皮肤补 `.qb-headctl` 版式(恒换到
> 第二行)。**零 JS 改动**; 守阵只改写断言口径(零新增测试函数); 真浏览器三皮肤实测控件齐全不越界、零 pageerror。
> 已闭环。
> 最后活动: 2026-10-09 07:40

**Refs:** memory-bank/tasks/26-10-09-webui-qb-traffic-seed-header-controls.md,memory-bank/testing/baselines/26-10-09-0740-webui-qb-traffic-seed-header-controls.md

- 任务档案: [26-10-09-webui-qb-traffic-seed-header-controls](../tasks/26-10-09-webui-qb-traffic-seed-header-controls.md) —— 根因推导、落点选择与实测数字都在档案, 本切片只留指针。
- 落地(纯前端静态层 + 测试侧, Python 产品代码零改动): `shared/tpl/drawer.html` 种子形态头部末位插入 `.qb-headctl`(内含与流量形态头部**逐字同源**的 `.qb-tabs` + `.qb-tools`, 门 `v-if="qbCurScope === 'torrent'"`); 三皮肤 `views.css` 各加 5 行(`:has(> .qb-headctl)` 开换行 / `.qb-headctl { flex: 1 1 100%; display:flex; gap:12px }` / 内层不收缩 + 紧凑档)。
- 关键判据(易被后人改坏): ①**控件是两处挂点**, 改一处必须同步另一处 —— 守阵把两块内层(空白归一后)比对, 不同步即红; ②种子头部的门必须是 `qbCurScope === 'torrent'`(单点派生: 种子形态 + 流量页签 + 功能开启); ③`.qb-headctl` 必须置于头部**末位**且 `flex: 1 1 100%`(置于中间会把模板切换器/收起/关闭顶到第三行); ④非流量页签下该组不渲染 ⇒ 种子头部仍是单行 44px(不得给 `.drawer-head` 无条件开换行)。
- 实测: test.full **全绿 / 0 failed / TOTAL 99%**(基线切片 [26-10-09-0740](../testing/baselines/26-10-09-0740-webui-qb-traffic-seed-header-controls.md), 相对上基线 passed ±0 —— 只改断言口径未新增测试函数; 精确数字见 kb.baseline); 旁证真浏览器三皮肤 1440x900: 档位 13 钮 / 纵轴 3 钮 / 控件框 `x=29 w=1388`(未越界)/ 头部 65px(两行)/ 图或空态仍可见 / 零 pageerror。
- 未验证面: 窄视口(≤900px)种子头部换行的逐档观感未走查(规则已写, 靠 `flex-basis:100%` + `flex-wrap` 抗挤压)。
