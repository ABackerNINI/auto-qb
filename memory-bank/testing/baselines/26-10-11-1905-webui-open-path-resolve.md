# 3126 —— WEBUI 打开目标解析口径优化(文件优先 + 辅种组按单个 + 目录"进入")

> 摘要: 用户令「WEBUI 打开路径优化」四点 —— ①解析尝试顺序 = 文件(单文件种子) > root_path/content_path > save_path; ②打开后「选中条目」、多条目不选中; ③组内只含一个种子时按单个种子处理; ④组内成员路径一致(辅种组, 都指向同一份文件)时也按单个处理。后端解析单点重构: 新 `_probe(rec) -> (target, select)` —— 先按 content/root **已存在文件** → 选中(单文件种子的唯一"选中"层级); 再按 root 优先 / content 次之取**已存在目录** → 进入目录(不选中); 都不可用回落 save_path(下载中未落盘不 404)。组分支新增 `_paths_consistent(recs)`(content_path / root_path **任一**归一后同值即"同一份内容", 空值不参与) —— 组内单成员或路径一致 → 用代表成员走同一套解析; 否则退回组 key 首元(save_path)。打开层 Windows 目录新增 `_win_shell_enter`(`ShellExecuteExW` + 目录 PIDL 走 `open` 默认动作, 长路径安全)= 真"进入"该目录; 旧 `_win_shell_open`(`SHOpenFolderAndSelectItems`)实测对目录 pidl 也是"打开父窗口并选中该目录", 只作 enter 失败降级。两函数共用新抽 `_win_shell_with_pidl`(COM 配对 / PIDL 释放 / `\\?\` 剥除单点); `tests/sidefx.py` LAUNCH 记账器纳入 `_win_shell_enter`。纯后端 + 测试改动, 无前端/静态资产改动。
> 基线时间: 2026-10-11 19:05
> 档案: [tasks/26-10-11-webui-open-path-resolve](../../tasks/26-10-11-webui-open-path-resolve.md)

**Refs:** memory-bank/tasks/26-10-11-webui-open-path-resolve.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步; 工作树含本轮 6 个 Python 文件改动时实测)
- 命令: `commands run test.full`
- **实测 (Windows)**: **3126 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16503 语句 / 148 未覆盖 / 5620 分支 / 133 partial; 本轮两次采样 pytest 29.95s / 30.99s, 任务壳 32.0s / 33.0s)
- 改动面(摘要): `src/auto_qb/webui/server/routes/fs.py`(`api_open_path` 解析口径 + 新 `_probe`/`_paths_consistent`) + `src/auto_qb/infra/utils.py`(`open_path` 目录分支 + 新 `_win_shell_with_pidl`/`_win_shell_enter`) + 测试 `tests/test_web_hr.py` / `tests/test_utils.py` / `tests/test_web_longtail.py` / `tests/sidefx.py`; 回写件 `memory-bank/pitfalls/backend/qb-content-path-semantics.md` / `memory-bank/modules/webui-static-contract.md` / `memory-bank/activeContext/26-10-05-2015-webui-open-path-fallback.md` / 本切片。见 kb.baseline。
