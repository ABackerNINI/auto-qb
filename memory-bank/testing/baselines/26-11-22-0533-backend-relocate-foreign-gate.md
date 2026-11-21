# 6789 —— 6789 passed, 6 skipped —— backend-relocate-foreign-gate(计划 26-11-21-1600)收尾基线

> 摘要: 6789 passed, 6 skipped —— backend-relocate-foreign-gate(计划 26-11-21-1600)收尾基线
> 基线时间: 2026-11-22 05:33
**Refs:** memory-bank/tasks/26-11-22-backend-relocate-foreign-gate.md

## 验收数字

`commands run test.full` 实测(2026-11-22 05:21, Windows, 2m44s, 树 = 4e0c6662 含远端 8aea3d16 合流):

```
TOTAL                                                30681     83  10942     86    99%
6789 passed, 6 skipped, 8 warnings in 164.00s (0:02:44)
```

覆盖率闸门通过(99% 线 rc=0)。与上基线(26-11-21-1341, 6748P)相比净增 41 测试、skipped 同为 6; 本轮五批零覆盖率回退(relocate_foreign/units/exec/daemon/webui 投影新面全部有守阵)。

## 本改动面

本切片 = 计划 26-11-21-1600(S1-S3)五批 + 接缝终审钉档的终态快照:

- S1/B1(41d40168): 内容根预筛(relocate_units.foreign_gate_passes 纯函数 + relocate_foreign A/B 两路接线, 兄弟目录种子不再误标 mismatch)。
- S2/B2(1d4ae8cb): 通知账随 job 终态清理(kind=A/mismatch 删、kind=B 留; _set_job 边沿 + superseded 直写点 + _load_jobs 恢复面三接线) + mismatch 文案改口径(后端 WARNING + decorate 单点 + 浮窗/抽屉)。
- S3/B3 后端(42a9face): daemon 日志落盘 logs/recycle_daemon.log + 流程 INFO 行(进窗路径 L1/L2 标注 + 逐成员结果) + WAIT 等待提示(三维翻转去重) + rewritten 合并日志。
- S3/B3 前端(de73d571): views_relocate.finalize_state 三态投影(等改写窗/待回连核验/收尾完成含新保存路径) + decorate 行状态单点 + 浮窗/抽屉消费 + e2e 新 spec(SKINS_ALL 四皮肤)。
- 接缝钉档(4e0c6662): mismatch 重判语义按拍板「接受现状+钉档」写全(终态类别前提) + done/failed 双面守阵。
