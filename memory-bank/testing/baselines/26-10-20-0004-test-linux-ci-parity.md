# 3756 passed + 1 failed + 10 skipped(Windows 单侧) —— 修 Linux CI 三条红后的 Windows 侧全量(relocate 空文件表 IndexError + 进程表分派用例)

> 摘要: 修 Linux CI 三条红后的 Windows 侧全量(relocate 空文件表 IndexError + 进程表分派用例)
> 基线时间: 2026-10-20 00:04

## 验收数字

```
TOTAL                                                20328    390   6956    262    98%
1 failed, 3756 passed, 10 skipped in 210.00s (0:03:30)
FAIL Required test coverage of 98% not reached. Total coverage: 97.54%
```

口径注记:
- 本侧 = Windows(本机 `.venv` Python 3.14.7, `commands run test.full`, xdist `-n 4`)。**Linux 侧本轮未跑**: 本机无 Docker/WSL, `commands run test.linux` 跑不了 —— 真值以 GitHub Actions 复跑为准。
- `1 failed` = `test_web_traffic_qb.py::test_api_traffic_qb_global_24h_reads_only_involved_day_files`(**既有、与本轮改动无涉, 且墙钟相关**): 隔离单跑同样红; 开工同步的 44 笔未触碰 traffic 相关四文件; 上一基线切片同一份代码全绿 ⇒ 随本地墙钟/日期变化翻转, 不是本轮引入。
- 覆盖率门槛未达是既有状态(上一基线同一量级): 按用户本轮指令「覆盖率问题先不用管」不处理。
- 语句数比上一基线 +1、未覆盖 -1: 本轮新增的 `if names:` 分支(`relocate_mod._group_facts`)。

## 本改动面

- `src/auto_qb/core/modules/relocate_mod.py`: `_group_facts` 的「代表文件探测」(第三方链接/硬链接识别)整段收进 `if names:` —— 空文件表时不再拿 `save_path` 这个**目录**顶替代表文件(POSIX 目录 `st_nlink >= 2` 会落到 `names[0]` → IndexError)。空表路径仍由 `evaluate_group` 按「文件列表为空, 无法判定内容布局」拒绝, 行为不变。
- `tests/test_relocate_paths.py`: 新增 `test_precheck_empty_file_table_skips_representative_probe`(录 `os.lstat` 探针, 断言空表时 `save_path` 一次都没被探测; 撤掉源码修复即红) + 改写 `test_guardian_process_names_parsing` 为平台中立(tasklist/ps//proc 三支解析 + 按平台/`/proc` 现查验分派 + 三条来源异常吞噬); docstring 「## 测试计划」清单同步两条。

