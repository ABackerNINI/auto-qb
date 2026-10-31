# 1693 passed + 1 skipped / 0 failed —— CarPT 已达标样张验证 + dl_id 修复后新基线

> 摘要: 用户补交 CarPT status=2 已达标页样张(17 行数据)验证通过 —— 表头/档位/完成时间(无秒)全解析正确;
> 验证挖出真缺陷并已修: **CarPT 的 H&R ID 与种子 id 是两个 id 空间**(8017746 ↔ details.php?id=173107),
> 原 `download_url(tid)` 会拿 H&R ID 去下载 ⇒ 新增 `HrEntry.dl_id`(行内链接提取, download 优先/details 兜底),
> service 下载时 `entry.dl_id or tid`。测试数不变 1693(+断言), 语句 11227→11238。基线时间: 2026-09-27 12:46
> 档案: 26-09-22-backend-partial-hr-verify

TOTAL 91%(11238 语句 / 816 未覆盖 / 3728 分支 / 331 partial; test.full 17.0s;
覆盖率口径见 [../baseline.md](../baseline.md))。
