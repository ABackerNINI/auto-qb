# 3620 passed + 10 skipped(根, TOTAL 18609/302/6302/205, 覆盖率 98%) —— alias_fs 测试无 symlink 特权环境改 skip 后全量基线

> 摘要: alias_fs 测试无 symlink 特权环境改 skip 后全量基线
> 基线时间: 2026-10-18 21:07

## 验收数字

`commands run test.full`(2026-10-18 21:0x 连跑两次, 数字一致):

```
TOTAL   18609   302   6302   205   98%
3620 passed, 10 skipped in 38.72s / 42.00s
```

口径: 根套件(pytest.ini 的 8 worker); `TOTAL` 列序 = 语句数 / 未覆盖 / 分支数 / 部分分支 /
覆盖率(成功路径只印整数位)。两条注记: ① skipped 4 -> 10, 新增 6 条全部是
`tests/test_alias_fs.py` 真实建链用例在无 symlink 特权环境(WinError 1314)下的约定 skip
(issue 26-10-18-2030 修复; 有建链能力的环境照常真实执行, 覆盖不缩水);
② 语句数较上期基线变大来自期间 rebase 合入的 alias_fs P0 等提交, 非本轮改动面。

## 本改动面

issue 26-10-18-2030 修复(**仅测试, 生产代码零改动**): `tests/test_alias_fs.py` 增加宿主 symlink
能力准入(`_probe_symlink_capability`: 试建 + 复核 islink + 穿透读, 判据同
`test_file_access._dir_symlink_or_skip`)与准入标记 `_SYMLINK_REQUIRED`(skipif), 6 条真实建链用例
在无特权环境由 failed 转 skipped(不再污染全量与 ship.commit 合并后闸门); `test_alias_primitives`
拆出 symlink 形态部分为 `test_alias_primitives_symlink` —— 硬链接 / 普通文件 / ValueError 部分
不依赖建链能力, 任何环境照跑, 无特权机器不丢硬链接覆盖。文件头 docstring 测试计划同步并补
「环境能力 skip」小节。关联件: issue 26-10-18-2030(已 Done, 含修法/验证数字);
判据先例 issue 26-09-29-2031。
