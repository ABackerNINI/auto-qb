# docker 文件访问层实施审查 + 两处 P2 修复

> 摘要: 用户令「审查计划 26-09-27-1407 及其实施(d50fa12), 重点安全/兼容/BUG」。交叉验证计划、
> 报告 26-09-27-1352 与全量触点后判定: 红线①逻辑进/逻辑出与红线②miss 一律不可判定均落地、
> 收编完整性成立(残留命中全是 data_dir 派生口径外)、W4 交付物齐; 但发现 2 个 P2:
> ①`map_to_container` 按 casefold 后前缀长度硬切原串(ß/İ 等变长折叠字符进 from ⇒ 切片错位 ⇒
> exists 误判「不存在」, 红线 §05 窄条件重演面); ②routes/fs.py 五处两态布尔消费在 Mapped miss
> 时 UNDETERMINED `__bool__` 抛 TypeError ⇒ 裸 500(多盘只映射一块或配错时浏览/新建/打开全炸)。
> 次级: SEC-1(Mapped 符号链接逃逸退化为词法 —— 容器侧 realpath 做得了, P3 加固)、组 key 快照
> 零差异无专用用例(W2 测试清单漂移)、自检探针 rmdir 失败残留、exists 返回注解。
> 用户令「修复BUG」: 两 P2 当轮修复(`_fold_prefix_len` 原串边界定位 + `_determinable` 三态
> 消费单点)+ 回归 +2; 用户令「提交」: 本切片与基线切片随主提交入库。
> 触发: docker, 文件访问层, path_map, 三态, UNDETERMINED, casefold, 符号链接逃逸, 审查修复
> 最后活动: 2026-09-27 17:12

## 状态

**Done**(两 P2 已修 + 回归绿 + 文档回写; SEC-1 未纳入随 W5; W5 真机验收未动)。

## 待办(下一步从这里接)

1. **SEC-1 加固**(P3, 建议随 W5): `MappedFileAccess` 内对映射后容器路径做 realpath 并校验仍落
   挂载根内, 逃逸按 miss 处理 —— 把 fs.py 目录浏览「词法退化」已知限制真正关掉。
2. **W5 真机验收**(计划 §W5 全项): drvfs disk_usage/getsize 实测、缺文件扫描快照对比、
   :ro/:rw mkdir 双态、跳检真触发、Linux 同路径对照; 数字回填 docs/deployment.md §14。
3. **回写欠账**(本轮因会话通道串扰未盲改既有 CJK 文档, 留待下一会话): progress/implemented-core.md
   「文件访问层」条目补本轮修复一句; pitfalls 候选两条(casefold 变长切片 / 三态消费单点);
   memory-bank 各 _index.md 与 kb.index 重跑。

## 取证锚点(复核用)

- 基线 origin/develop @ d50fa12(预检 my-commit-flow.sync 齐平); 改动 5+2 文件:
  infra/file_access.py(_fold_prefix_len + map_to_container 原串切片) · webui/server/routes/fs.py
  (_determinable + 五处调用点) · tests/test_file_access.py(+1) · tests/test_web.py(+1) ·
  plans/26-09-27-1407 changelog(+1 条) · baselines/26-09-27-1712 切片(新) · 本切片(新)。
- 判定依据: 既有映射用例零改动全绿(边界/根命中语义不变); 1725 = 1723 + 2(恰为本轮两条回归);
  真实测试名以 tests/test_file_access.py:196 与 tests/test_web.py:3885 为准。
