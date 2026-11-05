# 浏览器冒烟 · 能力与定位原文(外迁)

> 摘要: `pitfalls/testing/smoke.md`「能力与定位」节原文外迁(2026-11-05 压缩), 正文原样照搬; 冒烟规程单点是 memory-bank/testing/smoke.md。
> 触发: 冒烟能力, ui_harness, e2e, 门禁, 模式矩阵, 开机自检, dev.e2e-check

## 能力与定位

- **触发**: 改任何前端渲染逻辑。
- **判别**: 能力 = `scripts/ui_harness.py`(真 create_app+QbManager+FakeClient+合成种子+命令泵,
  由 `playwright.config.mjs` 的 webServer 托管) + `e2e/` 42 个 spec(@playwright/test, 双皮肤,
  按断言块拆分)。前端渲染**pytest 覆盖不到** ⇒ **改前端必跑 `npm run test:e2e:fast`(@fast 门禁);
  触碰乐观 UI/菜单/列设置加跑对应 spec; 全量矩阵轮收尾/排障串行人跑**。
- **处置**: 模式矩阵 env 参数化(计划 26-10-06-0708 §3.2)—— `E2E_CMD_RESULT=ok|error|hang` /
  `E2E_SKIP_CHECK=on|off` / `E2E_HR_SCENE=on|empty|off` / `E2E_TORRENTS=N`, 每轮独立起桩
  (六行命令见 `.commands/dev/config.toml` 的 `dev.e2e` note)。
  开机自检 (2026-10-31 机械化, issue 26-10-31-2226-feat-e2e-smoke-env-selfcheck): `dev.e2e` 首条已挂
  `scripts/e2e_selfcheck.py` —— node_modules/@playwright/test 缺失、e2e 端口占用(含占用进程身份/clone 归属)
  当场给 NEXT 修复动作, 不过不进 spec; 单跑 `commands run dev.e2e-check`。
