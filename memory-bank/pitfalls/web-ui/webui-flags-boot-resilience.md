# 前端单飞 promise 槽: 方法加 async 判等失效 / 单槽归置错杀在途链

> 摘要: 前端单飞 promise 槽: 方法加 async 判等失效 / 单槽归置错杀在途链
> 触发: 单飞,单飞槽,promise 槽,并发叠发,async 判等,槽主判等,错杀在途

## 本篇只回答

前端给「同一端点防并发叠发」写单飞(在途请求复用同一 promise)时的两个实现陷阱: async 包装破坏判等、单槽无主归置错杀在途链。实证出自 issue 26-11-11-0633(loadWebFlags boot 韧性)第 1/2 轮评审各抓一条。

### async 方法里写单飞, 并发方判等失效

- **触发**: 把单飞方法写成 `async loadWebFlags() { if (this._p) return this._p; this._p = ...; }` —— 看似返回同一个 promise, 实际每次调用都返回 async 函数自己的**外层 promise**(return 的内层 promise 被 adopt, 对象身份不同)。
- **判别**: 电池里 `p1 === p2` 断言红(两次调用返回不同对象); 运行期无症状(语义仍收敛, 只是判等/复用判定失效)。
- **处置**: 单飞方法**不加 async**, 用普通函数 + 内部 IIFE: `const p = (async () => {...})(); this._p = p; return this._p;` —— 并发方拿到的就是同一个对象。`p.finally(...)` 的派生 promise 若入槽, 槽内与判等基准必须同一个对象。
- **守阵**: node 电池断言同档两次调用 `===`(test_webui_static_r4_poll_auth_lifecycle.py 电池第 7 组)。

### 单槽 + finally 无条件归置, 异档并行时先结算方错杀在途链

- **触发**: 单飞槽只有一个句柄位(`_flagsLoadPromise`), 不同策略(如「boot 带退避重试」与「惰性单发」)的调用并存时, 后启动方覆写槽位; 先结算方的 `finally(() => { this._p = null })` **无条件清槽**, 把仍在途的另一链从槽里错杀 —— 后续同档调用查到空槽另起请求, "在途复用不叠发"的承诺在并行窗口失效(服务端宕机 + 连续交互 = 每次交互各发一发)。
- **判别**: 评审/推演问一句"两条链并存时, 先结算方的归置会不会清掉后启动方的槽"; 行为难直接观测, 靠电池变异验证(把分档退回单槽, 电池红 = 有判别力)。
- **处置**: **按策略分档分槽**(每档一个键, 如 `_flagsLoadSlots[len]`), 各档独立持槽互不挤占; 归置带**槽主判等**: `p.finally(() => { if (slot[len] === p) delete slot[len]; })`。若坚持单槽, 归置前必须判 `this._p === 本链 promise` 才清。
- **守阵**: 分档槽表电池(test_webui_static_r4_poll_auth_lifecycle.py 电池第 8 组: 异档另起单发 / 惰性结算不挤占 boot 槽 / 请求计数钉总发数)。
