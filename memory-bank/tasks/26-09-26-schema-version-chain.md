# 26-09-26-schema-version-chain — 落盘文件 schema 版本号与逐级升级链实施

**Status:** Done
**Added:** 2026-09-26
**Updated:** 2026-09-26
**Summary:** 按计划 [26-09-26-0506-plan-schema-version-chain](../plans/26-09-26-0506-plan-schema-version-chain.html) 落地: 新框架 `infra/versioning.py`(CURRENT_VERSIONS / MIGRATIONS / detect_version / migrate, 相邻版本逐级迁移链) + 三类集成(state 读写双单点过链盖章 + run() 持锁后物化 / hr「旧迁新拒」/ config 校验前迁移分派 + 六处同步 + writer/exporter 盖章), 存量文件缺失= v1 零迁移成本。
**Topics:** backend-schema-version-chain

## 原始请求

用户 2026-09-26:「实施计划26-09-26-0506-plan-schema-version-chain.html」(计划初版由上一会话按用户口径立档: 「所有落盘的文件需要增加版本号以及升级脚本；升级脚本只考虑从低一个版本的文件升级到下一个版本，形成升级链」, 当时指示暂缓实施)。

## 思考过程与决策

- **两处计划未定死、实施时定的点**: ①`hr/model.SCHEMA_VERSION` 与 `versioning.CURRENT_VERSIONS["hr_site"]` 的单一事实来源 —— 前者改为后者的**导入期别名**(作 dataclass 默认/from_json 回填), 写盘盖章由 `store._write` **调用时动态读** CURRENT_VERSIONS(导入期别名在测试替换版本表时会错位, 实测踩到: commit 后文件仍是 v1); ②run() 物化点的「磁盘版本落后」信号 —— `_load_state()` 返回 dict 形态不变(测试既有断言依赖), 迁移描述记入实例属性 `_state_migration_desc` 供 `_materialize_state_migration` 消费。
- **盖章一律写载荷副本**(`_state_write_payload` / writer `_stamp_schema_version`), 不改内存真相: 否则恢复路径的返回值会带上版本键, 既有断言「内存态即磁盘内容」的语义被搅浑; writer 盖章用 **int** 而非字符串 —— `_sync_mapping` 对值未变化的键跳过赋值以保注释/引号形态, 树里 int 与 ruamel int 才能判等。
- **config 的 BaseLoader 字符串世界**: 标量全为字符串, `load_config` 在迁移分派前把 `schema_version` 归一成 int(失败保留原值, 由 detect_version 报「必须是整数」); validate_config 另加形状防御层(int(str(v)) 剥壳, dict/list 值不会把 TypeError 甩出聚合报错网)。
- **豁免既判**: 迁移函数不进生产(三表皆空, 现行结构即 v1), 链式执行由单测临时假 v2/v3 验证; `_parse` 未来版本维持「不符即拒」且 recoverable=False(不挪走不猜备份, 既有判例), `schema_version=99` 既有断言原样通过。
- **范围守恒**: 前端对 `risk` 字段的呈现方式未改(升级链标记以 risk 文案承载, 无新增前端机制); `pyproject`/`__version__` 双源漂移属软件版本管理专题, 不碰。

## 实现计划

1. 框架: `infra/versioning.py` + `SchemaVersionError(infra/errors.py)` + infra 包 docstring 登记。
2. state: `_load_state` 读回过链(.bak 回退分支同样) + `_state_write_payload` 两写点盖章 + `_materialize_state_migration` 挂 run() 加载之后(持锁后, dry-run 只内存) + `__init__` 早期加载只内存迁移。
3. hr: `store._parse` 旧版本 migrate 后照常 from_json、未来/非法版本维持拒绝(recoverable=False); `_write` 动态盖章; 迁移 INFO 只报一次(`_migration_logged`, 防无锁只读路径轰炸)。
4. config: `loaders._migrate_config_schema` 校验前分派(未来版本 ConfigError 报清两个版本号) + KNOWN_CONFIG_KEYS / validate 形状校验 / schema Field(int, risk 请勿手改) / impact L0 / 文档 —— `schema_version` 不进 Config dataclass。
5. 测试 + 文档回写(keys.md / client-and-state.md / baseline.md) + 计划状态流转。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 框架 versioning.py + SchemaVersionError | Completed | 迁移函数不盖旧章/框架逐级盖章; 缺项 fail-fast 不跳级 |
| state 集成(rule_engine + qbmanager) | Completed | 读写双单点 + 物化接线守阵(inspect.getsource, 沿 _cleanup_orphan_tmp 先例) |
| hr 集成(store + model 别名) | Completed | 旧迁新拒; 盖章动态读版本表 |
| config 集成(loaders + 六处同步 + writer/exporter) | Completed | 运行期不写回, 物化在下次 WebUI 保存 |
| 测试 +24 条 | Completed | test_versioning 新建 12; rule_engine +5 / hr_store +2 / config +2 / writer +2 / exporter +1 |
| 文档回写 | Completed | keys.md 配置键表+state 结构行 / client-and-state.md 版本迁移节 / baseline.md |
| dev.run 冒烟 | Completed | minimal.yml 派生 data_dir 会落生产目录(红线), 改用等价法: 复制到临时目录并把 data_dir 指向临时目录再 --dry-run |

## 进度日志

- **2026-09-26 05:36**: 开工 sync 自检遇「远端 2b19f42e 未 fetch」; fetch 后确认纯落后 1 提交且与脏文件(上一会话立档件)在 `_doc-map.md` 重叠 —— 按 pitfalls/git/sync-pull 安全流程补丁出仓(`--output=`) → restore → ff 快进 → 施回, `_doc-map.md` 冲突按生成物口径重跑 `kb.index` 取并集, plans/_index.md 补丁干净施回。
- **2026-09-26 06:02**: 框架 + 三类集成落码完毕; 首轮受影响测试 164 过 3 挂(空文件 data=None 未防 / 两处断言需跟上「文件带版本章」新行为), 全部按新行为修正断言后 167 全过。**踩到坑**: hr 迁移测试暴露 `_write` 用导入期绑定的 SCHEMA_VERSION, monkeypatch 版本表后 commit 写盘仍是 v1 —— 修正为 `_write` 调用时动态读 `CURRENT_VERSIONS["hr_site"]`。
- **2026-09-26 06:32**: 提交阶段发现 ship.commit 在 src/auto_qb/config/*.py 上 git add 被拒 —— .gitignore 的 `config/` 规则(162c04b 今日 02:14 为 Docker 凭据目录所设)按「任意层级」语义误伤 `src/auto_qb/config/`(该包最后一次提交在规则引入之前, 故今天才暴露)。处置: 锚定为 `/config/` —— 根目录凭据目录红线语义不变(check-ignore 双向实测: config/config.yml 仍命中, src 包不再命中), 随本提交入库。
- **2026-09-26 06:20**: `commands run test.full` **1665 collected: 1664 passed + 1 skipped / 92%**(11112 语句 / 783 未覆盖 / 3692 分支 / 331 partial, 19.7s); 较基线净增 24 条用例, 数字已记 baseline.md 顶部。改动文件已过 dev.fmt。实机冒烟(minimal.yml → 临时目录等价配置 --dry-run): 启动链干净 —— 配置以 v1 口径加载(无 schema 报错)、持锁建目录、state.json 缺失静默; qB(16585)未运行, 主循环按既有重连逻辑等待, 与本次改动无关; dry-run 全程未产生 state.json(无迁移无写盘, 符合口径)。改动**未提交** —— 待用户显式说「提交」后走 ship.commit / ship.push。
