# 6 组实测 PASS / 0 FAIL / 1 项未采(升级路径) —— WEBUI 重启首屏首刷真机验收: P1/P2 框架可见时刻 + 静态 ?v= 重验 0 采数

> 摘要: 计划落地代码(P1 分片并发+脚本 preload / P2 静态树哈希+immutable)的真机验收采数。外部 Playwright 探针(gitignored 工作区, develop 零桩)量「产品重启后首次刷新 WebUI」的框架可见时刻(v-cloak 卸除 / .topbar 可见)、带 `?v=` 的静态重验数、四皮肤各一次。实测框架可见 v-cloak 卸除 101–331ms、topbar 可见 150–375ms, 全部远低于 P1 ≤3s / P2 ≤1.5s; `?v=` 静态重验 304 = 0 (122 条版本化 URL 走 immutable 缓存), 2 条 304 全为不带 `?v=` 的裸 URL(/shared/boot.js、/shared/icon.png), 已如实标注。升级路径(改静态文件后 V 变化 + 旧 URL 不再被引用)未采, 原因见 §05, 不虚报。
> 基线时间: 2026-11-23 12:32
> 基线 commit: c66e2bbe(分支 docs/webui-boot-loop-closure, 纯本地无远端; 采数期间 HEAD 未动, 工作树全程 clean)

**Refs:** memory-bank/testing/real-machine.md, memory-bank/testing/real-baselines/26-11-18-0821-webui-boot-first-data-S3.md

## 01 前置核对与探针目标

- `commands run real.guard` PASS: 36595(pid 37768)/36596(pid 29800) 均 v5.2.3 firewalled、免鉴权; 真实种子 0; 36596 上 real-fake 假种子 210 个, 36595 上 0 个。分支 `docs/webui-boot-loop-closure` clean, HEAD c66e2bbe。
- **探针目标澄清**: 端口 36595 服务的是 qBittorrent 原生 MooTools WebUI(页面无 `#app`/v-cloak, `?v=1v9ur0b` 为 qB 自带令牌), 不是本轮被测的 Vue 皮肤 UI。P1/P2 代码落在 auto-qb 产品静态前端(`src/auto_qb/webui/static/{atlas,prism,console,flux}/`, `index.html` 含 `#app v-cloak` 与 `?v=__AQB_V__`), 由产品进程 `runner_s0.py` 以派生配置(qB 后端 36596 承载 210 枚假种子, WEB 39000, skip_local_verify)起的 WebUI 承载。故所有数字采自 `http://127.0.0.1:39000/`, 后端真机 36596(210 种子)。
- V 值自证: 服务端下发 V = `4a73ca9003d33302`, 与 `compute_static_version('src/auto_qb/webui/static')` 逐字相等; 带 `?v=` 的响应头为 `cache-control: public, max-age=31536000, immutable` + ETag。

## 02 探针与调用命令(全部在 tests-real/.work/browserboot/, gitignored)

- `node refresh_accept.cjs` —— `refresh_probe.cjs` 的 gitignored 副本, 仅改输出文件名, 并加 `page.on('response')` 逐条记 URL/状态码 + v-cloak 轮询标记。冷启 + 同 context F5, 端口常量 39000 原样。输出 `accept_refresh_36596.json`。
- `node instrument_probe.cjs http://127.0.0.1:39000/<skin>/ accept_instr_<skin>.json <skin>` ×4 —— 现成探针, addInitScript 外部打点(轮询式, 不碰 develop 源码), 记录 v-cloak 卸除 / topbar 可见 / fetches / longtasks。输出 `accept_instr_{atlas,prism,console,flux}.json`。
- `node boot_probe.cjs` 亦跑过四皮肤(`accept_skin_*.json`), 但其 `addInitScript` 在 `document.documentElement` 尚为 null 时注册 MutationObserver 抛 `parameter 1 is not of type 'Node'`, 所有 performance 标记为 null; 其 `topbarVisibleFromGotoMs` 824–840ms 仍可用, 但框架时刻以 instrument_probe 为准(该 bug 已记录, 非产品缺陷)。

## 03 实测数字(原样贴关键行)

首刷/冷启与 F5(`refresh_accept.cjs`, t0 = `page.goto`):

```text
[cold first load] framework=833ms static=124 200=125 304=0          (vcloak=321ms)
[F5 refresh (warm cache)] framework=150ms static=124 200=123 304=2 api=9   (vcloak=101ms)
```

重复一轮(同探针增强前): `cold framework=972ms 304=0` / `F5 framework=156ms 304=2`, 同量级。

F5 的 2 条 304 逐条归因(非 `?v=`、非 HTML):

```text
nonApi 304: [{"url":"http://127.0.0.1:39000/shared/boot.js","status":304,"ct":""},
             {"url":"http://127.0.0.1:39000/shared/icon.png","status":304,"ct":""}]
v-urls=122 status={"200":122}, v-304=[]        // 版本化 URL 零重验
non-v urls: / (307), /atlas/ (200 text/html), /shared/boot.js (304), /shared/icon.png (304)
```

四皮肤(instrument_probe, 每套独立 context 冷启, t0 = 页面 init script):

| 皮肤 | v-cloak 卸除 | topbar 可见 | 墙钟可见(goto→topbar) | 资源数 | consoleErrs |
|---|---|---|---|---|---|
| atlas | 328ms | 365ms | 849ms | 133 | 0 |
| prism | 331ms | 370ms | 847ms | 140 | 0 |
| console | 327ms | 368ms | 835ms | 133 | 0 |
| flux | 331ms | 375ms | 846ms | 138 | 0 |

墙钟可见含 Playwright 启动/goto commit 开销(比页面级 performance 标记多约 0.5s), 判据以页面级 v-cloak / topbar 标记为准, 墙钟值并列供对照。

## 04 判据对照与结论

| 判据 | 门槛 | 实测最好/最差 | 结论 |
|---|---|---|---|
| P1 框架可见(v-cloak 卸除 / topbar) | ≤3s | 101ms(F5 vcloak) / 375ms(flux topbar); 墙钟最差 849ms | **PASS** |
| P2 框架可见(同上, 严口径) | ≤1.5s | 同上, 最差 849ms 墙钟仍 < 1.5s | **PASS** |
| 静态重验(带 `?v=`, HTML 除外) | 0 | 0 (122 条版本化 URL 全 immutable 命中; 2 条 304 均不带 `?v=`) | **PASS**(附 注) |
| 四皮肤各一次 | 4/4 | atlas/prism/console/flux 全采, 全 PASS | **PASS** |
| 升级路径(V 变 + 旧 URL 不再被引用) | — | 未采 | **未采(§05)** |

注: 裸 URL `/shared/boot.js`(index.html 末行 `<script src="/shared/boot.js">` 未带 `?v=`)与 `/shared/icon.png`(brand-mark `<img>` 及 boot.js 注入片段未带 `?v=`)走 `no-cache` → F5 必回源重验得 304。不在「带 `?v=`」判据面内, 但属真实静态重验, 如实记账, 不并入 PASS 口径。

## 05 升级路径未采原因

工作区现成 `source_stub_probe.cjs` / `source_stub_restart_probe.cjs` 依赖前端源码内 `__AQBP` 打桩, 而 develop 代码已确认零 `__AQBP` 桩(D3 硬约束, 不得注入); 其余探针(cold/restart_live/inject)只量启动时序, 不做 V 变化与旧 URL 引用对照。端到端验证「改静态文件 → V 变 → 旧 URL 不再被引用」需临时改 develop 静态文件并重启产品, 与本轮 D3(develop 零桩/探针只在 gitignored 工作区)冲突, 故本轮不采、不臆造数字。只读自证已完成(V 与 compute_static_version 逐字相等 + immutable 头, 见 §01)。

## 06 证据文件落点(gitignored 工作区, 保留不删)

`tests-real/.work/browserboot/accept_refresh_36596.json`、`accept_instr_{atlas,prism,console,flux}.json`、`accept_skin_{atlas,prism,console,flux}.json`、`refresh_accept.cjs` 及探针脚本原档。裸数字只写本证据档这一处, 未手抄到其他文件。
