# 基线 · 1924 passed + 3 skipped / 91% —— issue 清偿路线图 W2 收尾

> 摘要: 清偿路线图(plans/26-10-01-1758-plan-issue-clearance-roadmap.html)W2「状态完整性与数据安全」
> 3/4 清偿后的收尾基线(第 4 条 26-09-22-2221 feat 跨组文件交叉冲突, 用户明确排除未动)。
> 通过数较 W1 收尾基线 26-10-01-2003 的 1909 → 1924(+15): W2 三笔守阵 **+12**(test_web +3 /
> test_ui +1 / 0219 族 +8), 其余 +3 为同窗合流的其它清偿轮净增量(L4-L8 审计清偿 / test_config
> 5 对重名死测试清偿后可见 / 幽灵包守阵, 逐笔以各自提交实测为准)。
> 基线时间: 2026-10-01 21:38, develop @ c353e899(W2-3 清偿提交, 系 923cebbf 合并远端 rebase 后的现
> hash; 工作树含本次收尾回写文档改动未提交)。

TOTAL **1924 passed + 3 skipped / 91%**(13300 语句 / 1030 未覆盖 / 4418 分支 / 435 partial,
test.full 27.75s, rc=0)。语句 13278 → 13300 与通过数增量同源(W2 守阵为主); 耗时在近期全量
采样区间(21-31s)内。

## W2 三笔提交要点(每条单独提交, 明细已迁 progress/implemented-core.md · implemented-webui.md)

1. **5965cc07** · issue 26-09-21-1347(web.token 非原子写): ensure_web_token 改走 utils.atomic_write
   单点(mkstemp 默认 0600, 落盘字节逐字节等价), 读取侧零改动; test_web +3 守阵(生成可读回 /
   已有 token 不漂移 / 写一半中断自愈)。
2. **9f73b6d8** · issue 26-09-21-1347(托盘 join 超时弃落盘): 退出编排 join 5s→10s + 超时 is_alive
   判定后 WARNING 明示未落盘(候选 B「UI 线程补写 state」因违反唯一写者纪律否决); test_ui +1 守阵
   (预算 10s / 超时 WARNING / 退出码 0 / IPC 仍清理)。
3. **c353e899** · issue 26-09-21-0219(.!qB 过渡态误判缺文件): 按计划 26-09-22-2038 修法 1 主体,
   grouping_mod.py 汇聚点单点容忍(.!qB 孪生存在不判缺失)+ 连续 3 次兜底(计数会话级内存态不落盘),
   孪生探测经 fa.exists() 三态适配文件访问层; 测试 +8(grouping 5 / utils 2 / file_access 1,
   红验 5 failed → 落码 7 passed); 计划 doc-status 完档 Done。

机检同轮: kb.index 16 索引重生成(issues 索引已收编, W2 三条在 Done 分区); kb.check 主键纪律 OK
(271 文档 / 167 专题无缺主键); 切片数 81 > 70 与「cap 债务 1 项」为既有债务不拦提交(doc.caps 现算
无 cap 债务, AGENTS.md 7975/8000 余量 25)。

**Refs:** progress/implemented-webui.md · progress/implemented-core.md ·
plans/26-09-22-2038-qb-move-dot-qb-suffix-fix-plan.html(0219 修法计划)
