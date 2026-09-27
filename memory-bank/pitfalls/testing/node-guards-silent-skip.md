# node 守阵在本机静默跳过 = 假绿, 阈值类改动必配红验

> 摘要: 扩展行为守阵(`tests/test_extension_proxy.py` 的 node VM 场景)在没有 node 的机器上**静默 return 当 pass**
> (docstring 明示的同口径), 于是「test.full 全绿」对这一层守阵是**假绿灯**: 09d4109(26-09-27)把 site-caps.js
> 阈值提至 page 60/时·600/日、torrent 50/时·200/日, 但三条钉旧值 10/50 的守阵红了**一天没人看见** ——
> 改阈值的人跑的是无 node 的全量。教训: ①改 site-caps 阈值必须真跑 node 沙箱守阵(守阵里的魔法数字与
> site-caps.js 是硬耦合, 改一边必改另一边); ②「全绿」要区分真绿与跳过绿, 收尾怀疑守阵没真跑时先确认
> node 在不在; ③本机没有 node 时可下载便携版 zip 到临时目录只给当次命令配 PATH(零安装零持久态)。
> 触发: node, nodejs, 静默跳过, 假绿, 全绿, site-caps, 配额, 阈值, 硬上限, 守阵, test_extension_proxy,
> VM 沙箱, 便携, portable, PATH, 阈值漂移, 配额双桶

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
