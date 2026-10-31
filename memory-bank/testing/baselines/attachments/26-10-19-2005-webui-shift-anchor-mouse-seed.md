# 3747 passed + 10 skipped(根, 覆盖率 98%) —— WEBUI Shift 连选 Esc 后以光标为起点(鼠标五入口手势前落锚点)修复后全量基线

> 摘要: 3747 passed + 10 skipped(根, 覆盖率 98%) —— WEBUI Shift 连选 Esc 后以光标为起点(鼠标五入口手势前落锚点)修复后全量基线
> 基线时间: 2026-10-19 20:05

## 验收数字

`commands run test.full`(2026-10-19 20:00 实测, 32.8s):

```
3747 passed, 10 skipped in 32.76s
TOTAL    20256    394   6914    261    98%
```

口径: 根套件(pytest.ini 的 8 worker); `TOTAL` 列序 = 语句数 / 未覆盖 / 分支数 / 部分分支 / 覆盖率。
10 skipped 全为环境性(与本轮改动无关): 6× `test_alias_fs.py` + 2× `test_file_access.py`
符号链接权限(Windows 非特权缺 SeCreateSymbolicLinkPrivilege), 1× `test_grouping.py`
normcase 大小写折叠, 1× `test_web_hr.py` 仅大小写敏感 FS 成立的断言 —— 与本机既有基线
(26-10-19-0739 / 26-10-19-0810)同为 10 skip; 总采集数 3757 与 26-10-19-1938 基线一致
(彼环境仅 2 skip 故 passed 3755)。

回写后复验(2026-10-19 20:07): 补完切片 / 坑档 / 基线后重跑 `commands run test.full` 得
**3747 passed, 10 skipped**(35.50s), `TOTAL 20256 / 394 / 6914 / 261` 与上表逐位一致(耗时差为
机器负载)。`commands run kb.check` 全绿(回写守卫无违规 / 新增面 71 件通过 / 日期守卫无违规)。

## 本改动面

- `webui/static/shared/shortcuts.js`: `_selSeedAnchorFromCursor` 泛化为逐 kind(group/member/unit)
  试落(原按 `_selContext` 单 kind, 辅种页恒为 group, 覆盖不到成员行的 member kind); 保留
  「已有有效起点不动」与「无有效起点以当前光标落」两条不变量; 仅数据页落点。
- `webui/static/shared/selection.js`: 五个点击入口(onGroupClick / onMemberClick / onTorrentClick /
  onShowClick / onShowEpClick)在改写 `kbCursor` 之前, Shift 限定地调
  `_selSeedAnchorFromCursor()` —— 修「Shift 连选后 Esc 清选择, 再次 Shift 连选不以光标为起点」
  (锚点缺失时兜底链读到刚点的行, 区间塌成单行); 文件头注补该纪律。
- `tests/test_web_shortcuts.py::test_shift_anchor_unified`: 新增 ①b(五入口 seed 调用位于
  kbCursor 改写之前且限 Shift)与 ④b(落点覆盖 member/unit kind + 数据页守卫)两组断言;
  docstring「## 测试计划」清单同步。
- `memory-bank/pitfalls/web-ui/overlays.md`: §起点补 ③「鼠标先落起点再改写光标」(2026-10-19
  报障; 与 ② 键盘路径同祸), 处置补逐 kind 试落口径。
