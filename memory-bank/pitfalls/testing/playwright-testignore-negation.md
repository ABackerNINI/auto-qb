# Playwright testIgnore 负模式不是白名单: 「命中任一即忽略」, 白名单隔离必须走 testMatch

> 摘要: Playwright `testIgnore` 语义是「命中任一模式即忽略」, 负模式 `!xxx` 不是 "all except" 白名单 —— 会把被点名保留的文件一并吃掉(on 模式实测 `--list` = 0); 按维度隔离 spec 子集必须走 `testMatch` 白名单, 并用 `--list` 自证两态 spec 集。
> 触发: playwright, testIgnore, 负模式, 否定写法, 白名单, all except, testMatch, spec 隔离, e2e 子集, 维度开关, E2E_BOOT_FIRST, boot-first, --list, spec 集自证, 隔离轮

**Refs:** playwright.config.mjs, memory-bank/tasks/26-11-18-webui-boot-first-data.md

### 按维度隔离 e2e spec 子集时, testIgnore 负模式(`!xxx`)会把被点名保留的文件一并吃掉

- **触发**: 想按某个维度(e2e 模式开关/分片/隔离轮)只跑一个 spec 子集, 直觉想用 `testIgnore` 写「忽略其它全部、保留点名文件」(`!` 负模式 / "all except" 写法); 或评审建议改用 testIgnore 否定写法替代现有白名单。
- **判别**: Playwright 的 ignore 语义是**「命中任一模式即忽略」**—— 负模式 `!xxx` 只是把 xxx 从忽略集里排除, 其余模式照常命中其余文件, 所以「忽略 `!指定.spec.mjs` 之外的一切」这种写法并不成立: 被点名保留的文件照样被其它模式吃掉。实测隔离轮(on 模式)下 `--list` = **0** —— 不是「只剩白名单 spec」, 是整个 spec 集消失。凡 `--list` 结果与预期 spec 集不符, 先查是不是拿 testIgnore 当白名单用。
- **处置**: 白名单隔离一律走 **`testMatch`**(数组 = 要跑的全部集合, `undefined` = 默认全套件), 不碰 `testIgnore`; 两种形态落盘前各跑一次 **`--list` 自证**: off 态列全套件、on 态只列白名单 spec, 两态 spec 集与预期逐字对上才算落对。实证: 批次③ E2E_BOOT_FIRST 隔离 —— `playwright.config.mjs` `BOOT_FIRST_ISOLATED` 分支(`testMatch` 白名单只剩 `**/boot-first-two-hop.spec.mjs`, `testIgnore` 置 `undefined`, 注释留证); 评审曾建议 testIgnore 否定写法, 实测 on 模式 `--list`=0 后改走 testMatch(文件头注释记录该结论)。
