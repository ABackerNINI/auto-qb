# 1685 passed + 1 skipped / 0 failed —— 规则系统可行性实验报告落盘 (纯文档轮, 含合流)

> 摘要: 想法.md L298 的可行性实验(禁止 IYUU辅种 分类种子开始下载)结论文档化 —— 落报告
> `reports/26-09-27-0047-report-rule-iyuu-stop-guard.html` + 档案 `tasks/26-09-27-rule-iyuu-stop-guard.md`
> + activeContext 切片 + 索引重建; **无 src/ 无 tests/ 改动**(实验全部在内存 Fake 内完成, 未连真实 qB)。
> 收尾附带: 蒸馏一张最老切片(守 40 上限, 内容并入 `progress/roadmap.md`); 坑 `pitfalls/testing/tmpdir.md`
> 复发 +1(合并后编号 **12**), 并把最早的九踩流水外迁 `pitfalls/testing/attachments/`(该文件合并后已顶 cap);
> 新坑一条(`pitfalls/git/editing-traps.md`: 文本模式写回已含 CRLF 的内容 ⇒ `\r\r\n`)。
> 📌 数字取自**合流后**的 base `f1879040`(另一 clone 的两笔 WEBUI 搜索提交已并入);
> 合流前的 base `38918da8` 上同一套为 1683 + 1(本轮自身未改测试)。
> 基线时间: 2026-09-27 01:05
> 档案: 26-09-27-rule-iyuu-stop-guard

- **测试增量**: **0** —— 本轮未新增/修改任何测试; 守卫面(doc-forms / memory-bank 两文件)实测 34 绿
  (`commands run test.one -- tests/test_docs_forms.py tests/test_memory_bank.py`)。
- **⚠ 与历史切片对不上的口径(已定位, 非本轮引入)**: 上一条切片 `26-09-26-2121` 记 1680 + 1, 而本轮
  合流前实测**收集 1684**(+3), 合流后 1686(+2, 来自并入的两笔 WEBUI 搜索提交)。判据: 合流前
  `git diff 5935e91 HEAD -- tests/ src/ uv.lock pyproject.toml` **全空** ⇒ 那个 +3 与本轮无关;
  上几条切片(1669 / 1673 / 1679 / 1680 / 1682)测自**两 clone 并发期各自未提交的树**, 收集数天然对不齐。
  **以本切片(合流后的树)为准**; 下次对不上先查并发窗口, 别当回归。
- **合流**: 提交预检发现落后 `f1879040` → 按「同步路径」仓外 patch → `git restore` 清空 → `merge --ff-only`
  快进 → `apply --3way` 施回; 唯一冲突 `pitfalls/testing/tmpdir.md`(双方都在追复发流水)手工解。回写件
  (索引 / 切片 / 坑)全部落在**合并后的新基线上**重建, `kb.check` 6/6 绿。
- **闸门耗时**: 引擎口径 25.7s(含起进程), pytest 自报 20.26~25.0s —— 本机全量 19~26s 区间内, 无异常。

TOTAL 91%(11308 语句 / 815 未覆盖 / 3720 分支 / 331 partial; `webui/views.py` 97%; 覆盖率口径见
[../baseline.md](../baseline.md))。