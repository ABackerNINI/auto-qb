# backend-relocate-fastresume-finalize

> 摘要: 方案验证轮收口: 原案证伪+修正案 N2-N8 全绿, 计划 26-11-05-0808 入库, 实现轮 S1-S5 待认领
> 最后活动: 2026-11-06 06:42
**Refs:**

**R0(2026-11-05 08:18):** 方案验证轮收口: 原案证伪+修正案 N2-N8 全绿, 计划 26-11-05-0808 入库, 实现轮 S1-S5 待认领

**R1(2026-11-06 04:03):** R1 grilling 收敛: 收敛公理 D10(收尾不依赖退出顺序与 auto-qb 存活)→ daemon 复活职权换位(下线窗口改写)+ 0247 再迁移并入(supersede 两形态), 0808 删除重写(D18)、0247 翻 Superseded、0247 切片迁出, D7-D18 拍板, N9-N12 实验前置+S1-S6 待认领

**R2(2026-11-06 04:43):** R2 实验轮 N9-N12 全绿: N9 四场景(app/shutdown 200 可用, 关闭态 37.6s 收敛)/N10 经 junction 搬移 moving 信号仍现/N11 双门独立/N12 指纹级回滚; S5 输入=硬约束两条(重定向须在搬移后+旧 mover 须被覆盖)+搬后失败语义待拍板+编辑器相对路径纪律; S1-S6 待指令

**R3(2026-11-06 04:53):** R2 拍板 D19-D20(S5 细则定稿入计划 0808: 先搬后重定向+旧 mover 通用补条目+失败分段)+ real.down 红线违规入池 26-11-06-0448(bug/standard, 与档案双向链)

**R4(2026-11-06 06:20):** 认领修复 issue 26-11-06-0448(用户指派): real.down cmd_down 移除外部进程强杀, 改走 WebAPI app/shutdown 优雅退出(Qb.shutdown 空体 POST + 镜像路径核验 + 等端口释放 + 失败 fail-closed 无强杀降级); 新增真机轨安全守阵, 红验旧实现必红且副作用越界 0, 修复后定向全绿; real.down --dry-run 与本地 HTTP 往返双验; test.full 全绿, 数字见 kb.baseline(基线切片 26-11-06-0616); 回写 real 命令包 note / 红线坑档处置 / 真机规程 2.2, issue 两处状态 Open→In Progress→Done 并重建索引; uv trampoline 坑复发 +1; 收口评审不触发, 未立档案, 本轮无提交动作

**R5(2026-11-06 06:42):** 用户指派补做真机实测并授权既有红入池: ①真机验收 real.down 经 WebAPI app/shutdown 优雅退出(环境2 qB 5.2.3, 6/6 PASS —— 端口释放 / 目标进程退出 / 对照实例 56589 零误伤 / fastresume 在 shutdown 窗口内被重写 / 重启后假种子状态逐字读回, 收尾清场并恢复开工前无进程状态), 逐字证据 testing/real-baselines/26-11-06-0639-real-RM00.md; issue 0448 验证方式补第 6 条并作废「未做真机实测」旧结论, 真机规程 2.2 与红线坑档补背书; ②test.pkg 4 条既有红(mutants DEFAULT_DESELECT 悬空路径)按 create-issue 规程入池 26-11-06-0635(test/standard, Open, 未修), 索引重建; 本轮无提交动作
