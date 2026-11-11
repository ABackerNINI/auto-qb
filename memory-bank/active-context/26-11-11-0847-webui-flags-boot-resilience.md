# webui-flags-boot-resilience

> 摘要: 修 issue 0633 webui flags boot 韧性: loadWebFlags 有限重试(1s/3s)+flagsLoaded 态+惰性补拉(右键/开抽屉/设定位置框/Ctrl+\ /Alt+5)+分档单飞槽表; 三轮评审 9 条全修; 全量测试全绿(见 kb.baseline)
> 最后活动: 2026-11-11 08:47

**R0(2026-11-11 08:47):** 修 issue 0633 webui flags boot 韧性: loadWebFlags 有限重试(1s/3s)+flagsLoaded 态+惰性补拉(右键/开抽屉/设定位置框/Ctrl+\ /Alt+5)+分档单飞槽表; 三轮评审 9 条全修; 全量测试全绿(见 kb.baseline)

**R1(2026-11-11 08:47):** 评审实战记录: 第 1 轮分面(正确性/安全/测试缺口)3 代理 8 条 —— 最值钱的是测试缺口面的"await 未钉"两条 major(token 存在性断言钉不住删 await 的回归, 须字面量钉); 第 2 轮复评抓到修复自身的真 bug(单槽 finally 归置不判槽主, 异档并行先结算方错杀在途槽位 → 改分档槽表); 第 3 轮零 actionable 且做了变异验证(把分档槽退回单槽形态, 电池确实红 = 判别力实证)。教训: 修复循环不是走过场 —— 修复增量本身会引入新缺陷, 复评轮必须真派。

**R2(2026-11-11 08:47):** 工程要点沉淀: ①单飞 promise 槽"方法不加 async"——async 包装把 return 的 promise 再包一层外层 promise, 并发方判等失效; ②分档单飞按策略(重试链长)分槽而非单槽+档位标记, 归置必须带槽主判等(`slot[len] === p` 才 delete); ③"未取到"与"未启用"用 flagsLoaded 态分叉, 消费面 await 挂点(openQbHistory/_kbDrawerTab)先补拉再落门控, fire-and-forget 挂点(右键/开抽屉/开框)靠 Vue 响应式亮起 —— 语义诚实与改动面的折中实现。新坑已写 pitfalls/web-ui/webui-flags-boot-resilience.md。

**R3(2026-11-11 08:47):** 收尾面: 基线切片 26-11-11-0847(较上片 +1 新电池, 全绿见 kb.baseline); issue 0633 翻 Done 并回写复验/修法/评审留痕; 中途一次全量 flaky(test_legacy_review4_scripts 网络类用例)单跑+复跑均绿, 判与本批无关未入台账; 本地未提交(用户未说提交), 待 ship.commit 时带 Review trailer。
