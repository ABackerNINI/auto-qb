# 5058 passed + 2 skipped(根); 覆盖 TOTAL 23370 stmts / 167 miss / 7980 branches / 153 partial / 99% —— 真机轨口径三改(免token/清退真实种子/常用验收)入库前全量

> 摘要: 真机轨口径三改(免token/清退真实种子/常用验收)入库前全量
> 基线时间: 2026-11-04 02:53
**Refs:** memory-bank/activeContext/26-11-04-0237-real-machine.md

## 验收数字

- `commands run test.full` 实测(2026-11-04 02:53, 148.3s, **rebase 合流 origin/develop cc3c1b2a 后重跑**): **5058 passed + 2 skipped(根)**
- 覆盖率 TOTAL 表(誊写): 23370 stmts / 167 miss / 7980 branches / 153 partial / **99%**
- 口径注记: 合流前(HH 树, 02:42)首测 5040 passed + 2 skipped in 229.1s; rebase 带入远端 11 笔提交(含新测试面)后复测如上, 两次均一次性绿。远端对 `real-machine.md` 唯一改动是 Refs 追加, 已与本地口径改写合并(保留双方)。

## 本改动面

- `tests-real/lib/instances.py`: token 机制退役 —— 删 `TOKEN_ENV`/`_local_tokens()`/`token_for()`/`LOCAL_FILE`, `make()` 不再传 token; 头注释改四实例免鉴权口径
- `tests-real/lib/qb.py`: 删 token 参数与 403 鉴权降级; 401/403 改 fail-closed 报错直指「去 qB WebUI 重新勾选跳过本地验证」
- `tests-real/lib/env_registry.py`: 头注释免token口径
- `tests-real/runner.py`: `cmd_env` 删 token「已设/未设」展示, 改打印免鉴权口径
- `tests-real/rm08_webui_read/test_rm08_webui_read.py`: 腿A 派生配置 `api_key` 改空凭据直连 + 两处 docstring 同口径
- `tests-real/rm10_notify/test_rm10_notify.py`: `write_export_cfg` 删 token 断言, `api_key` 空凭据
- 删 `tests-real/config/instances.example.json`(机制退役)
- `.commands/real/config.toml`: `real.env` when/note 改免token口径
- `memory-bank/`: testing/real-machine.md 口径改写(两类准入/功能完工触发/L0 重定义/免token) + Refs 合流, testing/_index.md(kb.index 重建)、README.md:31、`.agents/skills/memory-bank/SKILL.md` DoD 4 加真机自检、activeContext/26-11-04-0237-real-machine.md 新切片
- 测试面: `tests/` 零改动(`test_real_machine_safety.py` 不涉被删 API, 无需适配)