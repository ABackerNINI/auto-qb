# HR 实例注册表被测试污染

> 摘要: 测试期 `hr.runtime` 的注册表路径必须被 conftest 重定向到临时目录 —— 用例的 `data_dir` 是每例唯一的 `tmp_path`, 不隔离就是**每个用例往用户真实 `%LOCALAPPDATA%/auto-qb-hr/instances.json` 追加一条死条目**(实测跑一次 `test_hr_runtime.py` 净增 24 条), 累积后被扩展「立即发现」在 TTL 窗口内整批采纳成无关实例。
> 等级: L0
> 触发: 加 hr runtime 测试, 发现端点测试, 扩展发现列表出现无关实例, 主实例连不上 Failed to fetch, instances.json 无界增长, 写 app-data, 注册表条目堆积, 测试污染用户数据

### 测试不得写用户真实 HR 实例注册表

- **触发**: 写任何构造 `HrRuntime` 并 `start()`(或直接 `InstanceRegistry(default_registry_path())`)的用例。
- **判别**:
  - 注册表条目 id = `sha1(config.data_dir)[:12]`(`runtime._registry_entry_id`)。而测试的
    `make_config(tmp_path)` 把 `data_dir` 设成**每个用例唯一的 `tmp_path`** ⇒ 每个用例都算
    「一个全新实例」, upsert 的去重键对不上, **只能新增不能覆盖**。
  - **症状不在测试里, 在用户侧**: `instances.json` 无界增长。2026-10-16 实报时 684 条 / 127KB,
    按心跳时间聚成 26 簇、几乎每簇正好 24 条 —— **一簇 = 一次 `test_hr_runtime.py` 运行**
    (该文件 34s 跑完, 簇跨度 ~30s, 每簇的 `ts` 停在跑测试那一刻, 之后再无心跳)。
  - 现场取证(修复前后对比跑测试即可, 不用读代码):
    `python -c "import json,os;print(len(json.load(open(os.path.join(os.environ['LOCALAPPDATA'],'auto-qb-hr','instances.json')))))"`
  - 用户侧表现: 跑完测试 **2 分钟内**点扩展「立即发现」⇒ 那 24 条死条目仍在 `INSTANCE_TTL_S`(120s)
    窗口内, `alive()` 照样报「存活」⇒ 24 条死条目 + 1 条真实例 = 25 条被**整批采纳**, 列表全是无关
    实例; 而后端按**文件序**(= 最后心跳升序)返回 ⇒ `instances[0]` 恒为最旧的死实例 ⇒
    「主实例暂不可用 —— 连不上端点(Failed to fetch)」。
- **处置**:
  - `tests/conftest.py` 会话级 autouse 夹具 `_isolated_hr_registry`: 把 **`auto_qb.hr.runtime` 命名
    空间里**的 `default_registry_path` 指向 tmp 目录。**只 patch runtime 的引用**, 不动
    `hr.discovery.default_registry_path` 本身 —— 否则 `test_default_registry_path_platform_shape`
    (断言真实平台形态)会跟着被改掉。
  - 需要**逐用例**独立文件的用例(如 `test_hr_discovery._isolate_registry`)照旧 monkeypatch,
    会自然覆盖会话夹具, 不必改。
  - 顺带根治「读时过滤、写时不剪」: `InstanceRegistry.upsert` 现在顺手剪掉超 `INSTANCE_TTL_S` 的
    条目(与 `alive` **共用** `_entry_fresh` 判据, 防两处漂移)⇒ 文件不再无界增长, 存量死条目在
    下一个活实例心跳时被清掉, **无需手工清理**。
- **守阵**: `tests/test_hr_discovery.py::test_hr_registry_path_is_isolated_from_real_file`
  (runtime 用的路径必须 ≠ 真实 app-data) +
  `test_registry_prunes_expired_on_upsert`(剪枝边界与 `alive` 同判据)。两条均已红验。
- **!别指望 sidefx 台账兜住这类**: 记账器覆盖 `POPEN`/`LAUNCH`/`REG`/`REGVAL`/`FSDEL`/`SYMLINK`/
  `BIND`/`CONNECT`, 碰文件系统的只有 `FSDEL`(删)与 `SYMLINK` —— **普通文件写入不在记账面内**,
  写到白名单外的用户数据(如 app-data)台账看不见。同族陷阱见
  [side-effects.md](side-effects.md)(注册表键那节的表亲: 都是「写完不清理、测试里看不见」)。
