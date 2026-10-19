# 3737 —— 免重启整组迁移 P3-P6 执行体/对账/收尾落地后全量基线

> 摘要: 免重启整组迁移 P3-P6 执行体/对账/收尾落地后全量基线
> 基线时间: 2026-10-19 07:57

## 验收数字

`commands run test.full` 实测(2026-10-19 08:06 跑, 格式化 + guardian 退休补丁后最终一次):

```
TOTAL                                                20200    390   6890    260    98%
3739 passed, 10 skipped in 33.45s
```

口径: 覆盖率门槛 `--cov-fail-under=98`(本轮新增 P3-P6 约 1900 语句, 逐分支补测后回到 98%);
新增用例 62 条(见下「本改动面」), 无跳过转红。真机 qB 验证不在本轮(本机无 qB 测试环境)。

## 本改动面

**产品代码(新增 3 文件 + 改 10 文件)**

- 新增 `src/auto_qb/infra/relocate_journal.py`: guardian 两本账的第二本(journal/spec/pid 锁, 全原子写)。
- 新增 `src/auto_qb/tools/`(`__init__` + `finalize_watch.py`): 收尾 guardian 独立进程 ——
  心跳 10s、三证判 qB 退出(进程不在 + 端口拒连 + 稳定 30s)、校验目标、先落 removing 再逐条删链接、最后 removed。
- 新增 `core/modules/relocate_units.py` 的 P3/P6 纯判定区: job 落账 roundtrip、三层物理解析第 1 层、
  动态收尾集合、停滞判据、执行期恢复、§3.5 对账表 8 行(纯函数)。
- `core/modules/relocate_mod.py`(+约 700 行): P3 任务线状态机(预检→暂停→qB 搬→轮询→校验→
  建链接/目录别名(分块)→穿透→重归组→落账→武装→恢复), P6 对账/重拉 guardian/重建链接/收尾/撤销,
  job 账落 state、重启不重发 setLocation、relocating 登记。
- `core/modules/grouping_mod.py`: 组键首元走物理位置解析三层(① job 登记表 ② 目录级链接 realpath
  ③ 代表文件只识别不并组)、`regroup_scope`、搬迁窗口让路缺文件扫描、跨组检测共用同一解析。
- `torrents/store.py`: `relocating_hashes` / `third_party_link_groups` 两个纯内存登记。
- `core/module.py` + `core/qbmanager.py`: `ctx.grouping` 模块句柄(relocate 建链后重归组不经 import 兄弟模块)。
- `core/modules/ops_mod.py`: 跳检在搬迁窗口内 skip(与缺文件扫描同一条让路纪律)。
- `webui/commands.py`: 单件/批量移动位置在开关开时走 migration 闸门 + 执行体, 回执带 truth; 关时逐字节原路径。
- `webui/server/routes/torrent_cmds.py`: location 端点 `confirm` 透传(形状单点保持一行 return)。
- `rules/actions/transfer.py`: move_to 走闸门(发起/幂等 skip/需确认 skip/拒绝 fail 四态), dry-run 不触发。
- `webui/static/shared/add_torrent.js` + `triggers.js`: 添加对话框提交前落点预检 + 二次确认(取消即不提交),
  投递点登记进金清单。

**测试(新增 3 文件 + 补 2 文件, 62 例)**

- `tests/test_relocate_exec.py`(24): 正常链路/停滞不搬回/长耗时 watching/第 3 条链接失败回滚/
  qB 断连不重发/单成员 direct/dry-run/单步预算/对账六支/撤销成本/guardian 三证/落账恢复/重启不重发/
  三入口接线与规则四态/跳检让路。
- `tests/test_relocate_paths.py`(20): 目录别名形态/内容根非空回滚/穿透失败留场/形态拒绝与暂停失败/
  拉起 argv/撤销拒绝/对账三处置/任务线异常隔离/收尾轮询超时/journal 与 pid 锁/guardian 退化与 CLI。
- `tests/test_grouping_relocate.py`(9): P4 六守阵(不裂组/搬迁窗口/新成员并组/跨组仍拦/junction 并组/
  硬链接打标并拒迁) + 解析恒等 + 重归组退化。
- `tests/test_relocate_units.py`(+4): 对账表 8 行/停滞边界/执行期恢复/解析与收尾集合/落账 roundtrip。
- `tests/test_web_relocate.py`(+1): 添加对话框预检接线与金清单登记。
