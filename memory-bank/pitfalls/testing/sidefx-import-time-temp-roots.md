# sidefx 会话守卫的临时根集合不得在模块导入时固化

> 摘要: sidefx 会话守卫的临时根集合不得在模块导入时固化
> 触发: 串行 -n 0 跑测试出现 sidefx 越界, 临时目录内删除/建链被判越界, TEMP_ROOTS 与 gettempdir 不一致
**Refs:** memory-bank/issues/26-11-02-2142-test-sidefx-serial-false-positive.html, memory-bank/tasks/26-09-18-test-sidefx-guard.md

### 模块导入时固化的临时根集合, 会被之后的自举切换打成全量假阳性

- **触发**: 任何「临时根来源在导入时求值、之后又被改写」的顺序 —— 本项目具体形态是 `tests/conftest.py` 先
  `import sidefx`(此刻 `tempfile.gettempdir()` 还是系统 temp), 紧接着 `_tmp_bootstrap.bootstrap()` 才把
  `TMPDIR` 切到实例根 `R:\Temp\auto-qb-tests\<实例>` 并清 `tempfile.tempdir` 缓存。旧实现把
  `TEMP_ROOTS = _temp_roots()` 写在模块顶层 ⇒ 根集合停在切换前的系统 temp。
- **判别**: 串行(`test.one` 固定 `-n 0`)跑测试会话收尾出现大量 FSDEL/SYMLINK 越界, 且路径全在实例根内;
  最直接的信号是 `sidefx.is_temp_path(tempfile.gettempdir()) == False`。并行闸门(`test.quick`/`test.full`)
  反而全绿 —— 因为 xdist worker 启动时 `TMPDIR` 已就位, worker 内导入拿到的是正确根。**"并行绿、串行红"
  就是本坑的指纹**, 不是业务代码坏。
- **处置**: 临时根按**调用时**求值 + 带环境签名缓存失效(本项目现实现: `_roots_signature()` 取
  `gettempdir()` + `TMPDIR/TEMP/TMP` 三项, `_ROOTS_CACHE` 比对签名不符即重算), **不要**退回导入时快照。
  验证: `commands run test.one -- tests/test_sidefx.py`, 应全绿且会话台账「越界 0」。
  修完的回归点: `tests/test_sidefx.py::test_sidefx_temp_roots_follow_tmpdir_switch`。
- **守阵**: `tests/test_sidefx.py::test_sidefx_temp_roots_follow_tmpdir_switch`(构造陈旧快照 + 切 `TMPDIR`
  后必须按当前根重算); 同类顺序敏感点写静态/行为守卫, 不要只靠"跑一遍看绿"。
- **复发**: 0
