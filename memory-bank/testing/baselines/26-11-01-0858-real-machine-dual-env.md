# 4444 passed, 10 skipped; TOTAL 22420 197 7688 155 99% (coverage gate 过) —— 双环境化: 真机轨环境注册表 + 环境2(C盘机)首轮基建实测

> 摘要: 双环境化: 真机轨环境注册表 + 环境2(C盘机)首轮基建实测
> 基线时间: 2026-11-01 08:58
**Refs:** memory-bank/issues/26-10-31-0641-test-real-machine-test-standing.html

## 验收数字

`commands run test.full` (167.8s, 2026-11-01 实测):

```text
TOTAL                                                22420    197   7688    155    99%
4444 passed, 10 skipped in 165.09s (0:02:45)
```

口径: 全量 pytest 含覆盖率报表; 相对上基线逐位对比不写, 看差值 `commands run kb.baseline -n 2`。
`tests-real/` 不在 testpaths, 本轮全部改动对基线数字零扰动(src/ 零改动); TOTAL 行数差来自同期远端提交。首轮曾 2 failed(`test_memory_bank` 索引守卫: 改 memory-bank 文件后未跑 `kb.index`), 重建索引后全绿 —— 守卫按设计命中。

真机面(环境2 首轮): `real.up` 拉起 56589/56590 + `real.guard` 双端口全绿(均 `firewalled`, v5.2.3); `real.env` 探测正确(缺省→环境2, `QBT_REAL_ENV=1`→环境1)。

## 本改动面

- `tests-real/lib/env_registry.py`(新): 双环境注册表单点 —— 端口/镜像前缀/EXE/BT 监听端口, `QBT_REAL_ENV` 显式 > EXE 存在性探测(1→2 序) > fail-closed。
- `tests-real/lib/instances.py` / `lib/guard.py` / `lib/app.py`: PRIMARY/SECONDARY/TOKEN_ENV、白名单三件套(WHITELIST_PORTS/IMAGE_PREFIXES/EXE + 新增 BT_LISTEN_PORTS)、QB_PORT 与防手滑断言全部改为注册表派生; token 口径改「不落盘, 用户每轮会话给(QBT_TEST_<端口>)」, instances.local.json 机制保留但不创建。
- `tests-real/runner.py`: 新增 `env` 子命令(环境 id/端口/EXE/token 配置方式)。
- `tests-real/rm00..rm10` 各 test 与 conftest、`tools/diag_l2.py`/`diag_log.py`: 端口字面量清零 —— 代码级改 `instances.PRIMARY/SECONDARY`/guard 派生, docstring 角色化(「主实例/副实例」), rm10 BT 端口黑名单改 `guard.BT_LISTEN_PORTS`。
- `tests-real/config/instances.example.json`: 双环境四端口说明。
- `.commands/real/config.toml`: 新增 `real.env` task; 各 note 去环境1 硬编码。
- `memory-bank/testing/real-machine.md`: 触发词/§01 约束1/§2.2/§2.3 双环境化; §2.5 拆 2.5.1(环境1 事实保留)/2.5.2(环境2 首轮实测事实: 网卡残留坑/BT 端口 27049·32719/transfer 原值/0 真实种子/无 R 盘/gtm 不可达); §2.6/§2.13 环境专属事实标注。
- 锚 issue 26-10-31-0641: §04 环境登记 callout + `real.env` 行; §08 双环境化记账。
