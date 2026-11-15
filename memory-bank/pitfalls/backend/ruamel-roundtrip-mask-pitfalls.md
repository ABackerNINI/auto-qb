# ruamel round-trip 掩码/回填三坑: 异常文本泄敏 / 引号形态继承 / alias 爆炸面

> 摘要: ruamel round-trip 掩码/回填三坑: 异常文本泄敏 / 引号形态继承 / alias 爆炸面
> 触发: ruamel, CommentedMap, DuplicateKeyError, 掩码, 哨兵, unmask, 回填, 引号, PlainScalarString, alias, 锚点, 共享引用, mask_yaml_text, 异常文本, 泄敏, detail

## 本篇只回答

配置备份掩码化(mask_yaml_text)与哨兵回填(unmask_yaml_doc)链路上 ruamel 的三个坑: 异常文本把明文值泄进响应、回填值继承旧引号形态、alias 共享引用的爆炸时机。单点: `src/auto_qb/config/writer.py`。

### ruamel DuplicateKeyError 的异常文本逐字回显重复键的明文值 —— 错误 detail 不能拼 {e}

- **触发**: 对不可信 YAML 文本跑 ruamel 解析(配置备份 bundle 导入/导出的解析面), 解析失败后把异常文本拼进 HTTP detail 或任何会进响应/日志的文案。
- **判别**: 响应/日志里出现形如 `found duplicate key "password" with value "b"` 的片段 —— ruamel 的 DuplicateKeyError **逐字回显重复键的键名与明文值**, 掩码还没来得及做就泄了(D2: 机密不出机被异常文本旁路)。
- **处置**: detail 只留固定文案 + 异常类型名(`f"...: {type(e).__name__}"`), 绝不拼 `{e}`; `from e` 保留原始异常供服务端排障。导出侧(routes/backup.py `_config_yaml_section`)与导入侧(本机坏 YAML 竞态分支)两处同口径。
- **守阵**: 评审 + 测试断言 detail 不含明文值(routes/backup.py 掩码失败 500 用例)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

### CommentedMap 回填值继承旧值引号形态 —— 哨兵回填要 PlainScalarString 钉回无引号

- **触发**: 导入管线把 bundle 里的哨兵值回填成本机现值(unmask_yaml_doc)时, 直接 `node[key] = 旧值字符串` —— CommentedMap 的赋值会**继承旧值(哨兵)的引号形态**: 哨兵 `"********"` 带引号, 回填后本机现值也被写成带引号标量, 破坏 byte 级保真(R7)。
- **判别**: 导入落盘后 diff 磁盘文件, 非敏感行之外的标量引号形态变了(本应无引号的值变成 `"..."`)。
- **处置**: 回填时显式钉回无引号形态 —— 值包成 `PlainScalarString`(ruamel 的标量类型, 写盘时无引号); 参见 `writer.py::unmask_yaml_doc` 的回填实现。
- **守阵**: S2 测试钉「导入 round-trip 后非敏感行 byte 级不变」。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

### alias(锚点/共享引用)在遍历改值时才是爆炸面 —— load/dump 线性路径反而安全

- **触发**: 手造 YAML 用锚点(`&a`/`*a`)让多个键共享同一节点, 再对文档树做递归遍历改值(掩码/哨兵扫描/回填) —— 共享引用会让同一节点被多次改写/重复计数, `seen` 集合防不住环结构, 递归可能不终止或结果依赖遍历序。
- **判别**: bundle 的 config_yaml 段含 `&`/`*` 锚点语法; 或遍历改值后同一物理节点出现互相矛盾的改写结果。
- **处置**: 入口拒收 —— 解析后形状闸检测 alias 共享引用即 422 拒(backup.py `_scan_yaml_doc_shape`, 堵在遍历之前); 自己写遍历器时, 只在「load/dump 线性路径」(解析→掩码→dump)上操作, 任何递归改值前先过形状闸。
- **守阵**: S2 形状闸测试(手造锚点 bundle 拒收用例)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
