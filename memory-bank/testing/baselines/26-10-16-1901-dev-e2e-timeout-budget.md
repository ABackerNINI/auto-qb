# 3483 passed + 4 skipped —— 抬 dev.e2e timeout 到 1200s(全量轮实测 661s 不再被强杀)

> 摘要: 全量 e2e 套件涨到 280 例后, `dev.e2e` 包内旧 600s 预算会在跑完前被引擎到点强杀(同日实测 `[FAIL] dev.e2e 超时(600s)`), 全量轮只能绕过引擎直跑。用户拍板**抬 timeout 600→1200s**(≈1.8× 实测); 复跑证明新预算够用: 同一命令经引擎跑完, 引擎报 661.1s, 用例面零失败。同时复核 `.commands/` 改动面(pack/engine 脚本测试)与全量 pytest。
> 基线时间: 2026-10-16 19:01

- test.full: 3483 passed + 4 skipped / TOTAL 17684 语句 245 未覆盖 6012 分支 180 partial / 98%(闸门过)。耗时 348.7s —— 与同树早前采样 193.3s 构成区间 **193–349s**(口径见 baseline.md; 本片偏慢, 采样期同机其它 clone 在跑)。
- test.pkg(`.commands/` + commands 引擎的脚本测试 —— 本轮改了 `.commands/dev/config.toml`, 该面不在 testpaths 里): **164 passed / 75.65s**。
- 全量 e2e(经 `commands run dev.e2e`, 新预算 1200s): **270 passed / 10 skipped / 0 failed**, 引擎报 **661.1s**。判据 = 同一命令在旧 600s 预算下会被强杀(同日实测失败行), 新预算留 ≈1.8× 余量。
- 本改动面: `.commands/dev/config.toml` 的 `[tasks."dev.e2e"] timeout` 600→1200 + note 首句改写(历史沿革 360→600→1200 + 本次实测 + 「再涨该重估(拆轮/与 CI 分工), 别靠调数字顶」的判据)。引擎侧无上限逻辑(`task.timeout` 直接进 `communicate(timeout=)`), 1200 被照用。
- 知识库: 抬 timeout 的决定回写进 `memory-bank/pitfalls/web-ui/tbl-pad-x-single-point.md`(「命令面待定」→「已处置」)与切片 `memory-bank/activeContext/26-10-16-1821-webui-dt05-head-parity.md`; 18:28 那条基线切片按体例不可变, 保持原样(其「全量轮入口待定」由本条收口)。
- Linux 侧未跑 —— 改动为包配置数值与知识库文档, 无平台分支; 本条 Windows 侧数字为事实源。

## 本改动面

- `.commands/dev/config.toml`: `[tasks."dev.e2e"] timeout = 600 → 1200`; note 首句改为「2026-10-16 全量套件 280 例实测 10.9m ≈ 654s —— 旧 600s 预算被引擎到点强杀(历史: 2026-10-06 164s; U2 后 ~356s 顶满旧 360s, 2026-10-12 放宽到 600s) ⇒ 再放宽到 1200s」。
- `memory-bank/pitfalls/web-ui/tbl-pad-x-single-point.md` · `memory-bank/activeContext/26-10-16-1821-webui-dt05-head-parity.md`: 决定与验证回写。
