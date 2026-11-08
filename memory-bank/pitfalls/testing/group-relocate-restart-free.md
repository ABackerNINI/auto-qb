# Fake qB 驱动迁移执行体的两个断言陷阱(ActionResult.ok 恒真 / 硬链接删目标不悬空)

> 摘要: 写迁移执行体测试时两处「看起来对、其实恒真/恒假」的断言形态 —— `ActionResult.ok` 是 classmethod 不是属性; 同卷硬链接下删目标路径不会造出悬空链接。
> 触发: ActionResult,is_ok,硬链接,悬空,迁移执行体,jar

### `result.ok` 恒真: 那是 **classmethod**, 不是布尔属性

- **触发**: 断言动作结果成败时顺手写 `assert r.ok` / `assert not r3.ok`(凭「其他库的 result 都有 .ok」的直觉)。
- **判别**: `tests/helpers` 里 `ActionResult` 只有 `status` + `message` 两个字段, 成败谓词叫 `is_ok` / `is_failed` /
  `is_skipped` / `is_pending`; `ok` 是**构造器** `ActionResult.ok(...)`。于是 `r.ok` 取到的是**类方法对象**,
  恒为真值 ⇒ `assert r.ok` 永远过(假绿), `assert not r.ok` 永远红, 且报错信息里只有 `ActionResult(failed, ...)`
  的 repr, 看不出是「属性不存在」。
- **处置**: 一律用 `is_ok` / `is_failed` / `is_skipped`。review 测试时看到 `.ok` / `.failed` / `.skipped` 直接判为写错。
- **守阵**: 本仓无静态守卫; 靠 review 口径(见上)。已知踩点: P3 执行体首轮测试两条假红/假绿(2026-10-19)。

### 同卷硬链接: 删目标路径**不会**造出悬空链接(数据还在)

- **触发**: 想构造「链接在、但穿透读不到」的现场, 于是在逐文件硬链接建好后 `os.remove(dst/<file>)`,
  期望原路径链接变成悬空 ⇒ 穿透校验失败。
- **判别**: 硬链接是同一 inode 的第二个名字 —— 删掉 dst 那个名字, inode 仍被原路径的名字引用着,
  `os.path.exists(src/<file>)` 依然 True、`getsize` 依然对得上; 测试里表现为「删了文件但 `_penetration_ok`
  仍返回 True」, 相位一路前进到 armed。
- **处置**: 不要用「删目标」模拟悬空。按被测行为注入(`monkeypatch` 掉 `_penetration_ok`)或改跨卷 symlink 形态;
  真要物理悬空就同时删两个名字, 但那已经不是「链接在却读不到」的现场了。
- **守阵**: `tests/test_relocate_paths.py::test_exec_penetration_failure_keeps_scene`(注入式)。
