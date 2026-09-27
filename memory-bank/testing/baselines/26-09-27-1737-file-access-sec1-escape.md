# 基线 · 1742 passed + 3 skipped —— 文件访问层 SEC-1 逃逸加固轮(容器侧挂载根 realpath 校验)

> 摘要: activeContext 切片 26-09-27-1712 待办① SEC-1 落地: `MappedFileAccess` 新增挂载根逃逸
> 校验单点(`_match` + `_root_contained`) —— 映射命中的容器路径经 realpath 解析后必须仍落挂载根
> 真实路径内, 逃逸按 miss(存在性 UNDETERMINED / 取值 FileAccessError); `scandir` 剔除逃逸条目
> (一个坏链接不炸整个目录浏览); fs.py 目录浏览「词法退化」已知限制关闭。
> 数字取自合并树复测(`commands run test.full`, 基线 origin/develop @ da3a190)。
> 基线时间: 2026-09-27 17:37(1742 数字为提交前合并树复测)
> 档案: memory-bank/activeContext/26-09-27-1712-docker-fs-pathmap-review-fixes.md(待办①)

- **测试增量**: +3 —— `test_mapped_symlink_escape_treated_as_miss`(真实 symlink 端到端: 逃逸按
  miss / scandir 剔除 / 挂载内链接不受影响)、`test_mapped_escape_containment_logic`(realpath 桩,
  无 symlink 特权环境可跑)、`test_mapped_mount_root_via_symlink`(挂载根本身经符号链接不误伤);
  前两条含 symlink 建链, 无权限环境(本机 WinError 1314)自动 `pytest.skip`。
  tests/test_file_access.py 头部「## 测试计划」同步。

TOTAL 1742 passed + 3 skipped / 91%(11691 语句 / 852 未覆盖, test.full 17.2s, 合并树复测)
对比前基线(26-09-27-1723): 1741 passed + 1 skipped / 91%(11662 语句) —— +1 恰为本轮恒跑新用例
(逃逸判定逻辑, realpath 桩); skipped 1→3 为本机 symlink 特权缺失(两条端到端用例自动跳过,
有权限环境照常跑); 既有用例(含既有映射用例: 边界 / 根命中 / 尾斜杠 / `\\?\` / scandir 回译 /
ß 变长前缀)零回归。覆盖率口径见 [baseline.md](../../testing/baseline.md)。
