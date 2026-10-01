# 26-10-02-hr-token-atomic-write — 后端 hr.token 生成改原子写

**Status:** Done
**Added:** 2026-10-02
**Updated:** 2026-10-02
**Summary:** 清偿 issue 26-10-01-2151(W1 波 1/3): hr.channel resolve_token 的 O_TRUNC 直写改走 utils.atomic_write, 半截密钥不再持久化 —— 与 web.token 修法(5965cc07)同范式, 读取侧零改动; +3 守阵(生成可读回 / 已有 token 不漂移 / 写一半中断自愈); 基线 2217 passed + 3 skipped / 97.51%(26-10-02-0345 @ 8b7831cd)。

**Topics:** backend-state-persistence
**Refs:** memory-bank/issues/26-10-01-2151-bug-hr-channel-credential-atomic-write.html

## 原始请求

用户授权 issue 清偿路线图 W1 波(后端速赢)实施, 本档案承担第 1/3 阶段: 认领 issue [26-10-01-2151-bug-hr-channel-credential-atomic-write](../issues/26-10-01-2151-bug-hr-channel-credential-atomic-write.html) 并修复 —— hr.channel resolve_token 用 O_TRUNC 直写 hr.token, 生成瞬间非优雅终止会留下非空半截密钥被持久化, 扩展侧鉴权 401(通道密钥静默漂移)。修法按上游 5965cc07(web.token 同族修复)的范式复用, 单独提交推送。

## 思考过程与决策

- 修法单点: 生成侧 4 行直写(`os.open(O_TRUNC)` + `fdopen` + `write`)换成 `atomic_write(path, lambda f: f.write(token))` 一行; 读取侧(`exists` -> ascii 读回 -> strip 判空)零改动。
- 权限与字节等价: atomic_write 走 mkstemp(默认 0600)与原 `os.open(..., 0o600)` 等价; token 是纯 ASCII hex, utf-8 落盘与原 ascii 编码逐字节相同。
- 原 `os.makedirs(data_dir, exist_ok=True)` 一并移除: atomic_write 内建同目录 makedirs, 保留即冗余; data_dir 经 config 校验恒非空(`_strip_none` 剔空走默认 `auto-qb-data`), 行为不变。
- 守阵三件套照搬 5965cc07 在 tests/test_web.py 的写法, patch 地址换成 `auto_qb.hr.channel.atomic_write`。
- 范围守恒: 全 src `O_TRUNC` 代码命中在本笔后清零(仅余两条注释), W1 波后续阶段(last-seen 死代码 / CSRF / 鉴权加固)不在本笔。

## 实现计划

1. `src/auto_qb/hr/channel.py` resolve_token: 直写块 -> `atomic_write`(补 import)。
2. `tests/test_hr_channel.py`: +3 守阵并同步头部「## 测试计划」清单。
3. 收尾: issue HTML 翻 Done(封面徽标 + meta + 状态变更日志 + 修复后补充) -> `kb.index` -> activeContext 切片 -> `test.full` 基线切片 -> ship.commit。

## 子任务状态表

| 段 | 内容 | 状态 |
|----|------|------|
| 代码修复 | resolve_token 改走 atomic_write | 完成(26-10-02) |
| 守阵 | test_hr_channel.py +3(可读回 / 不漂移 / 中断自愈) | 完成(26-10-02) |
| 收尾回写 | issue Done / kb.index / activeContext 切片 / 基线切片 26-10-02-0345 | 完成(26-10-02) |
| 提交 | ship.commit 推 Gitee | 完成(26-10-02) |

## 进度日志

- **2026-10-02 开工**: sync 至 0657c86f; 认领 issue 26-10-01-2151 并建档(本文件), issue 头部补 doc-refs 双向登记; Status In Progress。
- **2026-10-02 实施完成**: resolve_token 直写块换 `atomic_write`(删前置 makedirs, 理由见思考过程); tests/test_hr_channel.py +3 守阵并同步头部测试计划; test.quick 2146 passed / 3 skipped(0657c86f)。
- **2026-10-02 收尾**: sync 合流远端前移(8b7831cd, 覆盖率提升 P2-a)后在新基线跑收尾闸门 —— test.full 首二跑撞已知 flaky `test_budget_unit_wait_and_caps`(issue 26-10-02-0306, 整文件 77 passed / 单跑绿, 与本改动无涉, 范围守恒不动), 三跑全绿 **2217 passed + 3 skipped / 97.51%**(28.5s, rc=0), 基线切片 26-10-02-0345; issue 翻 Done(封面徽标 + meta + 状态变更日志 + 复验 + 修复后补充); activeContext 路线图切片更新 W1 1/3 进展; Status → Done。
