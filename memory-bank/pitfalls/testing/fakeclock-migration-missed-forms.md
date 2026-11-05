# 旧假钟批量迁移易漏 clock() 调用形与位置参数直构位

> 摘要: 把多套旧假钟批量迁到统一假钟(tests/clock.py)时, 按类名/替换表机械改最易漏两类形态 —— 直接调用旧假钟实例的 `clock()` 方法形(新假钟 API 是 `now()`/`monotonic()`, 类名相同但方法名不同), 与绕过属性、位置参数直构旧类的构造位(如 `_FixedClock(t0)`); 漏改位在替换轮里测试照绿(该用例没跑到旧 API), 拖到后续轮才假红。
> 触发: 假钟迁移, 旧假钟, tests/clock.py, clock() 调用形, 位置参数直构, 直构位, _FixedClock, 迁移漏改, 裸取时残留, 批量替换
**Refs:** memory-bank/tasks/26-11-06-test-flaky-governance.md, memory-bank/plans/26-11-05-0118-plan-flaky-test-governance.html

### 批量迁移假钟时漏掉 `clock()` 方法调用形与位置参数直构位 (S3 实踩)

- **触发**: 多套旧假钟批量迁到统一假钟(实测: S3 把 hr_helpers.Clock / traffic_sample_support._Clock / 两处内嵌 _FixedClock 等旧假钟迁 `tests/clock.py` 后删除)时, 按「旧类名 → 新类名」的机械替换推进。旧假钟的用法形态不止「类名引用」一种, 至少五类: ① `from xxx import Clock` 导入位; ② 实例属性引用位(`helpers.Clock(...)`); ③ **旧实例直接调 `clock()` 方法形**(统一假钟 API 是 `now()`/`monotonic()`, 方法名对不上, 只换类名不改方法名=运行时 AttributeError); ④ **位置参数直构位**(`_FixedClock(t0)` 这种不带关键字绕属性的构造, 换了构造签名即炸); ⑤ monkeypatch time 的散点混用位(与假钟并存, 收敛时成漏网)。
- **判别**: ① `grep -rn "clock()" tests/` 与 `grep -rn "\.\w*Clock(\|Clock(" tests/` 扫残留调用形/直构位(类名删掉后这些位会直接 ImportError/TypeError, 但**只替换类名不删旧类**时它们静默存活); ② 迁移轮全量绿不代表干净 —— 漏改位常落在低频用例里, 当轮没执行到旧 API 就照绿; 用 `grep -rln "<旧类名>" tests/` 确认归零才算迁完。
- **处置**: 迁移前先枚举用法形态清单(上面五类)再定替换表, 而不是只对类名; 旧类**迁完即删**, 用「删除后全量绿」当迁移完成的判据(类留着, 漏改位永远测不出来); 直构位改关键字参数构造; `clock()` 调用形逐一对应到 `now()`/`monotonic()` 语义(挂钟 vs 单调钟别接错)。
- **守阵**: `tests/test_flaky_timing_guards.py` 的裸取时/裸 sleep 守阵拦不住「旧假钟类残留」本身 —— 守阵钉的是新增违例, 迁移完整性靠「旧类删除+grep 归零」这条人工判据(见判别②), 别指望守阵兜底。
- **复发**: 0
