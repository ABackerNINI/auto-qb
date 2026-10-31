# 分钟戳命名 × 幂等查重 = 跨分钟竞态 CI 偶发红 (用例冻结 timekit.now)

> 摘要: 用例对文件名带分钟级戳 (`%y-%m-%d-%H%M`) 的制品做「重复建幂等拒绝」断言时, 两次真调用跨分钟边界 ⇒ 派生文件名不同 ⇒ `exists()` 永不命中 ⇒ 拒绝分支永不触发, CI 偶发红本机绿 —— 生产幂等语义 (同路径拒绝) 正确, 是用例没钉住「同路径」前提。修法: monkeypatch 冻结 `timekit.now` 钉同一时刻。26-10-17 `test_memory_bank.py` 实证。
> 等级: L0
> 触发: flaky, 分钟戳, 时间戳命名, 幂等, 重复建, 跨分钟, timekit, monkeypatch, 冻结时钟, CI 偶发红, 时刻相关, exists 查重

### plan/report/baseline 族文件名带分钟级戳, 重复建断言两次真调用跨分钟永不撞名

- **触发**: 写/改用例断言「同一逻辑对象二次创建必须幂等拒绝」, 而目标文件名由命令派生并内嵌分钟级时间戳 (`new_doc.py` 的 plan / report / baseline 族 `{stamp}-<topic>`); 或排查「单条用例本机绿、CI 偶发红, 失败点恒在重复建断言且 err 为空 (没走拒绝分支)」。
- **判别**: 查重机制若是 `target.exists()` 撞**同名文件**, 「同路径」就依赖两次调用的派生戳一致 —— 真墙钟下相邻调用跨分钟边界即生成两个不同文件名, 第二次照建成功, 断言红。机制级红验: 把 `timekit.now` 换成「每调用一次抬一分钟」的假钟重放两次 `kb.new plan`, 会建出文件名差一分钟的两件、第二次无拒绝输出, 与 CI 失败同形。**别误判成产品缺陷**去改命名或查重 —— 「同路径幂等拒绝」语义没破 (task 族的按 slug 查重是另一层语义)。
- **处置**: 用例内冻结时间单点: 先 `frozen = timekit.now()` 取一次, 再 `monkeypatch.setattr(timekit, "now", lambda: frozen)` —— `timekit.now()` (UTC+8 naive) 是全库取时唯一入口, 冻结它即冻结一切派生面 (文件名戳 / 头部日期 / 排序键); 注意 `import timekit` 必须在 `_new_doc()` 这类 helper 之后 (helper 负责把 skill scripts 插进 `sys.path`)。**别**为绕开竞态改生产命名 —— 去时间戳撞命名契约, 提精度到秒只是缩小窗口不清零。
- **守阵**: 暂无专项机检 (确定性由用例自身的冻结时钟保证); 同族先例 [flaky-midnight-daycount.md](flaky-midnight-daycount.md) —— 两坑同构: 「生产按时间派生语义正确, 用例未固定时刻」。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
