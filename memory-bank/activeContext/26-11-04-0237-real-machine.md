# real-machine

> 摘要: 真机轨口径三改(2026-11-04 用户拍板, grilling 两轮收敛): 测试qB清退真实种子; 四实例免token免鉴权; 真机实测转常用验收手段(准入三类改两类, 功能完工即 agent 自跑真机验收)。
> 最后活动: 2026-11-04 02:37
**Refs:** memory-bank/testing/real-machine.md

**R0(2026-11-04 02:37):** 口径三改落盘, 规程单点 `testing/real-machine.md` + 路由(README.md:31 / testing/_index.md) + memory-bank skill DoD 4(真机自检) + `.commands/real` real.env note 同步改写。

## 口径变更(用户拍板, grilling 收敛)

1. **测试 qB 清退真实种子**: 用户已移除全部真实种子, 口径定为测试实例**只允许** `real-fake` 假种子, 真实 PT 种子禁入; `real.guard` 的「真实种子归零」保留作回归防线。连带: §03 种子层 **L0 重定义**为「real.seed 假种子 paused 只读」(原「现成真实种子」层退役), 大库量级观测归语料回放轨; RM00 退路同步改。
2. **四实例免token免鉴权**: 用户已在 36595/36596/56589/56590 全开 WebUI「跳过本地验证」, 本机直连零凭据, **用户永不需要提供 token**。代码层 `QBT_TEST_<端口>` 环境变量注入 / `instances.local.json` / `lib/qb.py` 403 鉴权降级**全部退役删除**(instances.py/qb.py/env_registry.py/runner.py/rm08/rm10 + 删 instances.example.json 与盘上残留 instances.local.json); 401/403 改 **fail-closed** 报错直指「去 qB WebUI 重新勾选」, 不加任何绕行(Q3 用户明确选移除不选逃生门)。
3. **真机实测转常用验收手段**: 准入判据**三类改两类**(删「③只有人眼能判(观感)」—— 观感归 e2e 桩轨截图断言; 仅「桩数据失真足以改变结论」的场景按失真理由进真机, agent 自跑 `dev.webui`+浏览器自动化)。触发时机从「定期排期驱动」改「**功能完工即触发**」: 收尾 DoD 自检, 完工功能落入两类 ⇒ 当轮 agent 自跑真机验收, 没做须明示理由; **仍不挂自动闸门**; 常驻排期锚降格为兜底巡检(漂移判定/回归)。机制写给 agent, 不预设人工参与。

## 改动面

- **代码**: `tests-real/lib/{instances,qb,env_registry}.py`、`runner.py`(real.env 输出)、`rm08_webui_read`/`rm10_notify` 用例(api_key 空凭据直连)、删 `tests-real/config/instances.example.json`(及盘上 gitignored 的 instances.local.json, 内含旧 token)。
- **命令包**: `.commands/real/config.toml` real.env 的 when/note。
- **文档**: `testing/real-machine.md`(摘要/触发词/四轨表/准入判据/约束2/§2.5/§2.5.1 表/§2.5.2 表/§03 L0/§06 两种触发形态/§08 观感爬档/§11 反模式+2)、`testing/_index.md`(kb.index 重建)、`memory-bank/README.md:31`、`.agents/skills/memory-bank/SKILL.md` DoD 4 加真机自检。
- **不动**: 历史 real-* 切片与 real-baselines 存量(Q11 只加不改), `config.yml` 红线。
