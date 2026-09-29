# 守阵「跑到」不等于「覆盖到」—— 夹具数据让目标分支不可达, 守阵常年假绿灯

> 摘要: 一个测试名字/断言都对, 但**夹具数据让被测分支根本进不去**, 于是它测的是另一条路;
> 症状是「未导入的名字 / 未定义变量潜伏到真机才炸」, 而测试长期全绿。判据只有一条:
> 把源码修复**注回去**(stash 源码改动)该守阵必须红 —— 不许只验绿。
> 触发: 红验, 守阵, 假绿灯, 假绿, 分支不可达, 未导入, NameError, 未执行行, 覆盖率盲区, 夹具, 注入 bug, 原地改配置, 热重载短路

### 夹具让目标分支不可达 / 夹具原地改配置 ≠ 热重载(同一轮实报两条形态)

- **触发**: 写或改守阵时 —— 尤其是「断言某个副作用发生了」而那侧作用由多层分支的**内层写入**,
  或被测对象是热重载/挂载口这类「按值比较后短路」的逻辑。
- **判别**(两条形态):

1. **分支不可达**: `tests/test_hr_service.py::test_terminal_vanish_writes_release` 断言的是
   「终态条目退役并落放行记录」, 但夹具的 B 行名称写成 `"OTHER 21"` —— 与本地锚点
   (`EXAMPLE 21`)**粗配不上** ⇒ 该行不下载 ⇒ 条目 `infohash_v1` 为空 ⇒ 冻结里
   `for h in (infohash_v1, infohash_v2)` 空转, **落记录那三行永不执行**; 而它断言的
   `h21 in data.verified` 由第一波的「未列出」批量签发满足 —— 于是 `LANE_SATISFIED`
   (未导入)那行从未跑过, 守阵一直绿。真机一走到就 `NameError` 崩整波。
   **处置**: 夹具回放里核对「被断言的那条记录是**哪条路径**写的」; 断言的实体要唯一指向
   目标分支(本轮改成断言 `source == SOURCE_SATISFIED` + 快照字段)。
2. **夹具原地改配置 ≠ 热重载**: `_FakeManager` 场景里 `runtime.config.trackers[x].hr_check.enabled = False`
   是**原地改同一个对象**, 挂载口的「无变化短路」按值比较 ⇒ 判等 ⇒ 直接 return, 被测路径
   根本不执行(症状: 断言「端点应被收掉」失败)。**处置**: 模拟热重载一律**整对象替换**
   (`config.trackers = make_config(...).trackers`), 与生产里「重新加载出全新对象」同形。

## 静态兜底: 动态测试覆盖不到的分支, 用「名字解析」兜

「未导入的名字只在真机走到那一行才炸」在本仓已复发 **3 次**(`service.py::_freeze_terminal` 的
`LANE_SATISFIED` 崩整波 / `service.py::channel_state` 的 `CHANNEL_OK` 卡死视图发布 / 
`webui/routes/torrent_cmds.py` 的 `List` 潜伏)。三道守阵各管一段, 缺一不可:

1. `test_all_modules_import`(import-all): 管**导入期**求值(装饰器 / 默认值 / 类体);
2. `test_all_annotations_resolve`(`inspect.get_annotations(eval_str=True)`): 管**注解**
   (含 PEP 649 惰性求值下的 typing 名字);
3. `test_no_undeclared_global_names`(函数体名字解析): 管**函数体里的名字** —— 它只在被**调用**时求值,
   动态测试永远可能没走到那条路。实现按作用域链解析(自有绑定 / 外层 / 模块全局 / 内建), 局部名识别
   刻意**过宽**(宁少报不假报); 注解不归它管(第 2 道负责)。

- 深挖时用权威工具: `uv run --with pyflakes python -m pyflakes src/auto_qb tests`(按需拉取, **不入依赖**) ——
  它还会报未使用导入 / 未使用局部变量, 本仓此类噪音多, 故只作排障不入闸门。
- 纪律不变: 新守卫写完必须**回退修复看它红**(本轮: 全库零误报 + 回退即红)。

## 通用判据 —— 红验怎么写

- 红验的**正确写法**: 只 stash **源码**改动(`git stash push -- <src 路径>`), 保留测试改动,
  跑新守阵 —— 全红才算守阵成立; 只跑绿等于没验(本仓先例: 一条守阵曾对已注入的 bug 假绿灯,
  见 [annotations-lazy-eval.md](annotations-lazy-eval.md))。
- 覆盖率的「未执行行」提示比覆盖率百分比有用: 断言所依赖的那一行若在 `coverage` 里是红的,
  守阵就是假的。
- 相关: [assertions.md](assertions.md)(恒真/量错对象)、[stubs-sim.md](stubs-sim.md)(替身保真度)。
