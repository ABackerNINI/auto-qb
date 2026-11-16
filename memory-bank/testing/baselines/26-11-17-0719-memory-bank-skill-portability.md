# 6286 —— 批9b 四处外置配置后全量绿(双收集面实测)

> 摘要: skill 轨道可移植性改造批9b(四处操作性命中外置配置)后双收集面实测(2026-11-17 07:19)
> 基线时间: 2026-11-17 07:19

## 验收数字

`commands run test.full`(tests/ 收集面)实测(2026-11-17 07:19, 115.3s):

```
TOTAL                                                27855    226   9822     98    99%
6286 passed, 19 skipped in 113.87s (0:01:53)
```

`commands run test.pkg`(.commands 包 + commands 引擎收集面)实测(同轮, 18.9s):

```
549 passed, 36 subtests passed in 18.63s
```

增量口径(**收集面分层**, 批9b 评审修正后; 上基线 26-11-17-0622):

- tests/ 收集面(test.full 消费): 6291 → 6305 收集项, **+14 passed** = test_kb_nav_data +4
  (repo_deny 配置生效/回落零项目词+提示一次/混型回落/显式空合法)+ test_kb_nav_server +5
  (remotes 读配置/回落 origin+提示一次/names[0] 兜底/混型回落/显式空)+ test_memory_bank_cli **净 +1**
  (test_config_nav_readers_shapes 新用例; 既有「本仓 project.toml 成态」用例系**加断言改造**([nav] 两节在场钉), 不计增量)
  + tests/test_deps_upgrade_user_agent.py 新文件 +4。
- .commands 包收集面(test.pkg 消费): 546 → 549 passed, **+3 passed** = release 包 TagMessageTest
  3 例(tag_message 三分支)。**该面不在 test.full 收集面内**(test_release_pkg 在 test.pkg 显式收集)。
- 17 个新增用例函数按面分摊 = 14 + 3, 与两轮实测严格对账(评审曾按单面静态推 +17, 已修)。

## 本改动面

- 批9b 四处外置(计划 26-11-17-0010 S11 收口, 用户拍板「全部外置配置, 照 S1 同款模式」):
  - `.agents/skills/memory-bank/scripts/_common.py`(+config_nav_repo_deny / config_nav_remotes 两读者)
  - `.agents/skills/memory-bank/scripts/nav_data.py`(REPO_DENY → [nav] repo_deny, 回落通用+提示)
  - `.agents/skills/memory-bank/scripts/nav_server.py`(MAIN_REMOTE_CANDIDATES → [nav] remotes, 回落 origin+提示)
  - `.agents/skills/memory-bank/config/project.toml`(+[nav] 节, 本仓实例原值搬家, 行为零变化)
  - `.agents/skills/release/scripts/tag_release.py`(默认附注 → tag_message 纯函数 + --tag-note-prefix)
  - `.commands/release/config.toml`(release.tag run 行 + --tag-note-prefix auto-qb 项目事实)
  - `.agents/skills/deps-upgrade/scripts/check_updates.py`(USER_AGENT → user_agent() 读配置)
  - `.agents/skills/deps-upgrade/config/project.toml`(新建, [user_agent])
  - PORTING 依赖面同步三处(memory-bank runbook / release / deps-upgrade)
  - 测试守阵 17 例按收集面分摊(上面增量口径; 五文件头部测试计划同步)
  - 提示文案评审修正两处(去掉「为空」—— 显式空列表=合法配置不回落)
- grep 白名单审计复验: 操作性代码命中 0(批9b 前 4 处全归零), 全量 695 处逐文件白名单分类留痕任务档案。
