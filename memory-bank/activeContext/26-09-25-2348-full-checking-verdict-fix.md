# full-checking 首样本竞态修复 (已完成)

> 摘要: 取证报告 [26-09-25-0853-report-full-checking-verdict-poison](../reports/26-09-25-0853-report-full-checking-verdict-poison.html) (doc-topic: full-checking-verdict) 定案后同轮修复。两个现象(误报「校验未通过 progress=0.0」+ 批量辅种部分不触发且无日志)同源: ①轮询判败加「曾见 checking」前提 + `CHECK_START_GIVEUP=600s` 启动宽限保险丝(`full_checking.py`); ②决策链 1.6 假失败自愈(记录指向已完成/已删除成员即清除不推断, 已中毒的组部署后下一轮扫描自动解, 次日日期口径兜底); ③冷却上限/1.6 推断 skip 提级 INFO(原 DEBUG 排障盲区); ④recheck 发送失败改由 `submitted` 标记让已登记轮询立即消亡(原靠失败分支清理, 被宽限语义破坏, send_error 用例抓出)。实测 1611 collected: 1610 passed + 1 skipped。
> 最后活动: 2026-09-25 23:48
> 下一步: 无(本轮完结); 已入库 `c46e67e`
