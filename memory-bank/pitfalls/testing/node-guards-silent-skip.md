# node 守阵在本机静默跳过 = 假绿, 阈值类改动必配红验

> 摘要: 扩展行为守阵(`tests/test_extension_proxy.py` 的 node VM 场景)在没有 node 的机器上**静默 return 当 pass**
> 等级: L0
> (docstring 明示的同口径), 于是「test.full 全绿」对这一层守阵是**假绿灯**: 09d4109(26-09-27)把 site-caps.js
> 阈值提至 page 60/时·600/日、torrent 50/时·200/日, 但三条钉旧值 10/50 的守阵红了**一天没人看见** ——
> 改阈值的人跑的是无 node 的全量。教训: ①改 site-caps 阈值必须真跑 node 沙箱守阵(守阵里的魔法数字与
> site-caps.js 是硬耦合, 改一边必改另一边); ②「全绿」要区分真绿与跳过绿, 收尾怀疑守阵没真跑时先确认
> node 在不在; ③本机没有 node 时可下载便携版 zip 到临时目录只给当次命令配 PATH(零安装零持久态)。
> 触发: node, nodejs, 静默跳过, 假绿, 全绿, site-caps, 配额, 阈值, 硬上限, 守阵, test_extension_proxy,
> VM 沙箱, 便携, portable, PATH, 阈值漂移, 配额双桶, options.js 沙箱, 顶层 let, 词法绑定, 喂不进状态

### 3 条配额守阵漂移红了一天没人看见 (2026-09-28)

- **触发**: 本轮(扩展日志降噪)为真跑新守阵, 下载便携 node 临时入 PATH 跑 `tests/test_extension_proxy.py`,
  `test_extension_quota_caps_and_refuses` / `test_extension_quota_windows_roll_over` /
  `test_background_events_ring_dual_write` 三条**同时红** —— 而前一天 `test.full` 一直「全绿」。
  根因: 三条守阵用 node VM 真跑 background.js + site-caps.js, 断言钉死「本小时访问上限 10 次」
  「日上限 50」(2026-09-25 立法时的值); 09d4109(26-09-27, 配额双桶)把阈值提到 page 60/600、torrent 50/200
  却没动守阵。守阵在这台机器上没有 node → `if not node: return` 静默当 pass, 全量的 passed 数里混着
  根本没执行的守阵。
- **判别**: pytest 报告里 node 守阵**无 skip 标记**(函数直接 return, 不是 pytest.skip), 「3 skipped」
  与 node 守阵无关 —— 从总数上看不出守阵没跑。`node --version` 报 command not found 即坐实本机
  node 守阵全是假绿; 改过 `site-caps.js` / background.js 数值后必须借真 node 复跑一次。
- **处置**: ①守阵阈值改为**从 site-caps.js 现值动态取**(场景与断言不再硬编码魔法数字), 2026-09-28
  已随用户指令修复, node 真跑全绿; ②node 已按用户指令装进 `C:\Program Files\nodejs` 并入系统 PATH,
  守阵从「跳过绿」回到「真绿」; ③若换无 node 的机器, 便携 zip
  `https://nodejs.org/dist/v22.14.0/node-v22.14.0-win-x64.zip` 解压后当次命令前
  `export PATH="<目录>:$PATH"` 即可, 跑完即弃。

### options.js 沙箱探针: 顶层 `let` 状态不在沙箱全局上, 直接赋值**静默无效** (2026-10-16)

- **触发**: 计划 26-10-15-2357 S3/S4 实施期写临时探针(未入库, 落 `/tmp/probe_s3.js`)真跑 `options.js` 验
  「疑似失效标记 / 顶部总览」时, 最自然的写法 `sandbox.instancesState = [...]` / `sandbox.instanceHealthState = {...}`
  **读到的仍是空** —— `vm.createContext` 里只有顶层 `function` / `var` 会成为沙箱全局对象的属性; `let` /
  `const` / `class` 是**词法绑定**, 既不在 `sandbox` 上、也无法从外部赋值(赋值只是给全局对象挂了个同名
  属性, 脚本内部解析到的仍是自己那份词法绑定)。
- **判别**: 症状 = 「喂了数据但被测函数读到初始值」, **且不报错** —— 与「函数真有 bug」长得一模一样(假红);
  反过来, 若断言只查「不崩」就变成假绿。options.js 的 `instancesState` / `instanceHealthState` / `logAll`
  全是这类状态, 后台 `background.js` 的 `healthBuf` 同款。
- **处置**: 驱动内部状态**走被测代码自己的入口** —— 把 `chrome.storage.local.get` 桩喂上数据后调
  `refreshConnFromStorage()`(本轮回填路径), 不要直接给沙箱对象赋状态名; 只有 `function` 声明
  (`connStateOf` / `renderConnOverview` / `probeMainInstance` / `discoverNow` 等)能直接 `sandbox.<fn>()` 调。
  另: options.js 顶层就注册事件与读 DOM, 沙箱必须给 `document.getElementById` 桩(返回可复用元素对象,
  带 `value/textContent/innerHTML/classList/open/addEventListener`), 否则加载即抛。
