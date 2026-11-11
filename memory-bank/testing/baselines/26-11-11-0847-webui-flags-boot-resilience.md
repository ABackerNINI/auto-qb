# 6008 —— webui flags boot 韧性入库基线

> 摘要: webui flags boot 韧性入库基线
> 基线时间: 2026-11-11 08:47
**Refs:** memory-bank/issues/26-11-11-0633-bug-webui-flags-boot-resilience.html

## 验收数字

```text
TOTAL                                                26747     55   9362     66    99%
6008 passed, 2 skipped in 150.23s (0:02:30)
```

(实测时点: 2026-11-11 第 3 轮评审零 actionable 后终轮 `commands run test.full`, 覆盖率 99.66%(门槛 99.5%); 较上片 6007: +1 = 本批新增 node 电池 test_r4_webflags_boot_retry_and_ensure, 2 skipped 为存量 skip 不变; 本切片为本批组合树的测试数字权威, 其余处一律引用不手抄。另: 本批中途一次全量曾出 1 failed(test_legacy_review4_scripts::test_qb_capture_dry_true_zero_requests, 网络类用例), 单跑与复跑全量均过, 判 flaky 与本批无关。)

## 本改动面

- `src/auto_qb/webui/static/shared/lifecycle.js`: `loadWebFlags` 重写 —— 分档单飞槽表(`_flagsLoadSlots` 按重试链长分键, 归置带槽主判等, 方法不加 async 直返槽内 promise)+ 失败按 `retryDelays` 退避续试(e.auth 不重试)+ `flagsLoaded` 态写回; 新增 `loadWebFlagsBoot`(boot 期 1s/3s 退避共 3 发)与 `ensureWebFlags`(未取到补一发, 已取到零副作用); 本机免鉴权 boot 入口改调 `loadWebFlagsBoot`; 全局右键监听 `_onCtxMenu` 头部加惰性补拉挂点(早退分支之前)。
- `src/auto_qb/webui/static/shared/state.js`: flags 邻位新增 `flagsLoaded: false` 显式建字段("未取到"与"未启用"的判据单点)。
- `src/auto_qb/webui/static/shared/auth.js`: bootstrap 成功路径 `loadWebFlags` → `loadWebFlagsBoot`(一行, 带重试档)。
- `src/auto_qb/webui/static/shared/qb_traffic_chart.js`: `openQbHistory` 在未启用 toast 门控前加"未取到先 `await ensureWebFlags` 再判"(不把"没取到"当"没启用"误报)。
- `src/auto_qb/webui/static/shared/shortcuts_engine.js`: `_kbDrawerTab` 改 async(调用方全 fire-and-forget, 返回值无人消费), traffic 门控同款"未取到先补拉再判"。
- `src/auto_qb/webui/static/shared/drawer.js` / `drawer_general.js`: `openMoveDialog` / `openTorrentDrawer` 开框/开面板路径各加 fire-and-forget `ensureWebFlags()`(迁移提示/流量页签按响应式亮起)。
- `tests/test_webui_static_r4_poll_auth_lifecycle.py`: 新增 `_NODE_WEBFLAGS_PROBE` + `test_r4_webflags_boot_retry_and_ensure`(成功收口/单发不续试/1s+3s 退避三发/穷尽止/auth 不重试/flagsLoaded 分叉/ensure 语义/同档单飞/档位分槽+挤占回归钉); 监听对称电池补右键挂点行为(普通目标 + input 早退路径); docstring 测试计划同步。
- `tests/test_webui_static_dom_panel_traffic.py`: 门控区补 flagsLoaded 显式建 + openQbHistory await 补拉接线 + 双 boot 入口 `loadWebFlagsBoot` 扫描断言。
- `tests/test_web_shortcuts_drawer.py`: `_kbDrawerTab` 两处门控锚点跟新结构(await 补拉字面量钉入)。
- `tests/test_webui_static_r4_drawer.py`: submitMoveDialog 电池补 `ensureWebFlags` 计数桩 + 回路 2/3 判别断言。
- `tests/test_webui_static_dom_panel_drawer.py`: openTorrentDrawer 守阵补惰性补拉挂点扫描断言。
- `memory-bank/issues/26-11-11-0633-bug-webui-flags-boot-resilience.html`: 状态 Done + 复验/修法/验证数字回写。
