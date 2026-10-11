# open-path 打开目标解析(下载中回退修复 + 顺序/组口径优化)

> 摘要: 同专题两轮。**2026-10-05**: 用户报「详情面板点开保存路径提示『打开目标文件夹失败: 目标文件不存在或不可访问』, 路径实际存在, 同路径已完成种子可正常打开」—— 根因 = `fs.py` `/api/open-path` 旧链「content_path 不是目录 ⇒ 当单文件种子定位选中 ⇒ 文件不存在即 404」无回退; qB 的 content_path 是**逻辑完成名**, 下载中未落盘(或 .!qB 后缀)时必走错分支, 而详情面板四个路径按钮全共用该端点。修 = 按实际存在形态分流 + 回退 save_path。**2026-10-11**: 用户令「WEBUI 打开路径优化」四点 —— 顺序=文件(单文件种子)>root_path/content_path>save_path / 打开后选中条目(多条目不选中) / 组内只含一种子按单个处理 / 组内路径一致(辅种组同一份文件)也按单个处理 ⇒ 解析收成单点 `_probe` + `_paths_consistent`, 打开层 Windows 目录由"在父目录高亮"改**进入**(新 `_win_shell_enter`: `ShellExecuteExW`+目录 PIDL, 长路径安全)。
> 最后活动: 2026-10-11 19:05

**Refs:** memory-bank/tasks/26-10-11-webui-open-path-resolve.md

## 已完成

- [x] (2026-10-05) 根因定位(`fs.py::api_open_path` torrent 分支 `isdir(content)=False` 一律 `select=True`, 未落盘即 404) + 三段分流修复(isfile→选中 / isdir→打开内容目录 / 都否→回退 save_path, 仅回退目标也不可访问才 404); 安全边界不变。
- [x] (2026-10-11) 解析顺序与组口径优化: 新单点 `fs.py::_probe(rec)->(target, select)`(文件 content/root → 目录 root/content → save_path) + `_paths_consistent(recs)`(content_path/root_path **任一**归一全同、空值不参与;**或**组内 `len==1` ⇒ 按单个种子解析), 组 key 已保证 save_path/文件集一致故只补内容路径维; `infra/utils.open_path` 目录分支改 enter 优先、`_win_shell_open` 降级; 新 `_win_shell_with_pidl` 收 COM 配对/PIDL 释放单点; `tests/sidefx.py` LAUNCH 记账器纳入 `_win_shell_enter`。
- [x] 守阵: `test_api_open_path_endpoint`(HA–HL + k_a 单成员 / k_b content 一致 / k_d root 一致 / k_c 不一致) + `test_utils.py::test_win_shell_enter_pidl_routes`; 4 个测试文件头部「## 测试计划」清单同步。
- [x] 回写: 坑档 [qb-content-path-semantics](../pitfalls/backend/qb-content-path-semantics.md)(解析顺序 + 组判据)+ [windows-long-path](../pitfalls/backend/windows-long-path.md)(进入目录路线)+ `modules/webui-static-contract.md` open-path 行 + `kb.index`; 本轮基线见 `kb.baseline`(切片 `26-10-11-1905-webui-open-path-resolve`)。

## 正在进行

(无)
