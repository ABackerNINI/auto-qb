# 测试经 _data_dir 兜底写进 auto-qb-data 红线目录

> 摘要: 测试环境 data_dir 缺省落空串时, 模块侧 `_data_dir()` 按 `or "auto-qb-data"` 兜底 —— 测试驱动的 journal/spec 写点全部落进生产红线目录 `auto-qb-data/relocate/` (T2 引入 T3 发现, 残留 j1.json/ja.json 即此来); 修法 = autouse 夹具把 env 缺省钉到 tmp_path, 显式传参恒优先。教训: 默认值兜底指向生产目录本身就是坑。
> 触发: auto-qb-data 污染, 测试写红线目录, data_dir 兜底, _data_dir 默认值, 测试驱动触盘写点, env 夹具钉 data_dir, autouse 夹具, 残留 journal json, relocate 测试

## 本篇只回答

测试驱动会触盘的模块面 (journal/spec/state 外写点) 在测试环境 data_dir 缺省不实时的「写进生产红线目录」坑 —— 何时触发、怎么判别、怎么修。

### 测试 data_dir 缺省落空串, journal/spec 写点经 `_data_dir()` 兜底写进 auto-qb-data

- **触发**: 写「驱动相位机真实推进」的 relocate 测试 (armed job / 对账 / 纳入面), 环境构造把 `config.data_dir` 留空 (env helper 缺省不传 data_dir) —— 模块侧 `ExecMixin._data_dir()` 是 `str(getattr(cfg, "data_dir", "") or "auto-qb-data")`, 空串触发 `auto-qb-data` 兜底。T2 的 armed 驱动用例 (on_task_line 推进相位机) 在对账 ACT_REBUILD 时 `write_journal(self._data_dir(), ...)`, T3 纳入面 read/write_spec 同走该点 —— 写点全落 `auto-qb-data/relocate/` (生产运行数据目录, 已 gitignore, git 状态看不见)。
- **判别**: 跑完 relocate 测试后 `auto-qb-data/relocate/` 出现测试命名残留 (实报残留 j1.json / ja.json —— 测试 job id 命名的 journal), 该目录本该只有真实运行数据。**测试全绿是假阴性信号**: 生产目录被写脏不会让任何断言红, 只能靠「跑完看目录」或写点审计发现。
- **处置**: 测试文件加**函数级 autouse 夹具**把 env helper 的缺省 data_dir 钉到 `tmp_path` (tests/test_relocate_foreign.py `_foreign_data_dir`: 模块级游标变量, 夹具每用例置 `str(tmp_path)`、yield 后复位; `_env(data_dir=None)` 缺省取游标, **显式传参恒优先** —— 需要自定路径的用例不受影响)。凡测试驱动会触盘面写点的路径, env 夹具必须显式钉 data_dir; **「默认值兜底指向生产目录」本身就是坑**, 不指望调用方永远记得传参。残留 auto-qb-data/relocate/j1.json 与 ja.json 已于 26-11-21 经用户拍板删除 (内容为固定假时间戳 ts=1700000000.0 的测试 journal, 非真实运行数据) —— 判别信号不再恒真, 此后靠「跑完看目录」与写点审计双查。
- **预防**: 新增会触盘写点的模块测试文件, 照 `_foreign_data_dir` 形态自带头部夹具 (env 缺省 = 夹具钉的 tmp_path), 不要等红线残留被人工撞见; 同族先例 [hr-registry-pollution.md](hr-registry-pollution.md) (测试写用户真实 app-data, 同是「写真实数据面 + 测试全绿看不见」)。
