# 26-10-02-memory-bank-issue-clearance-roadmap — Issue 全量清偿路线图(滚动执行)

**Status:** In Progress
**Added:** 2026-10-02
**Updated:** 2026-10-02
**Summary:** issue 池全量清偿路线图的滚动档案:v1(26-10-01-1758)摸排 31 条分七波;v2(26-10-02-0234)在清偿 12 条 + 新入池 46 条后改版,未决 31→59 条重排九波(W1 后端速赢 → W2 WebUI 正确性 → W3 数据安全大件 → W4 性能 → W5 HR/统计拍板 → W6 体验批 → W7 扩展 → W8 穿插 → W9 挂账)。波次推进待用户逐波显式授权。

**Topics:** issue-clearance-roadmap
**Refs:** memory-bank/plans/26-10-01-1758-plan-issue-clearance-roadmap.html

## 原始请求

- v1(2026-10-01 17:58): 用户要求摸排全部未决 issue、分类排序并出计划(当时 31 条未决),产出 plans/26-10-01-1758。
- v2(2026-10-02 02:34): 用户告知「新增/解决了大量 issues, 重新摸排一下还有哪些 issue, 分类排序, 不用具体分析代码, 分析代码的事留到认领的时候做, 写一个计划」——按 doc-forms 改版协议对原计划做 v2 同文件改版(变更记录 + 抬 doc-updated),不建 v2 新文件。

## 思考过程与决策

- **改版不新建**: 命中 doc-forms「计划改版 = 同文件内 ## 变更记录 + 抬 doc-updated」;本档案补上 v1 会话缺失的立档(v1 只写了 activeContext 切片,未建 tasks 档案——立档阈值 #4 本应命中)。
- **零代码分析口径不变**: 计划表内只给摸排注(入口提示/复验标记/挂账关系),分析动作留到认领时。
- **test 类型清零是本轮结构变化**: v1 把 4 条 test 卡点单列为闸门波 W1;v2 池内 test 0 条,闸门已绿(基线 26-10-02-0203: 2143 passed + 3 skipped / 96.49%),起点前移到数据与凭据。
- **拍板件绑工程件**: HR 三问项与 hr-verify-sync-hr-tags、流量历史图问项与 stats-redesign 绑在同一波(W5),避免决策悬空。
- **26-09-22-2221 特殊标记**: 用户曾明确排除,本轮重新入列(W3)但标注开工需单独授权。
- **transmission-compat(In Progress)**: 可行性报告 26-10-01-2347 已出(建议暂不做),停在拍板,挂 W9 不排期。

## 实现计划

九波路线、每条摸排注与执行规则见 [plans/26-10-01-1758](../plans/26-10-01-1758-plan-issue-clearance-roadmap.html) §1-W9 与 §8;本档案不复制,只记执行与验证。

## 子任务状态表

| 波次 | 内容 | 状态 |
|------|------|------|
| v1-已清偿 | v1 所列 31 条中的 12 条(v1-W1 5/5 闸门波、v1-W2 3/4、v1-W3 1/5、v1-W6 1/9、v1-W7 2/5) | 完成(26-10-01/02, 见 issues Done 分区) |
| W1 | 后端速赢:凭据/状态/鉴权(4 bug: hr-token 原子写 · last-seen 死代码 · CSRF · 鉴权加固) | 完成(26-10-02, 3/3 阶段全清: bc24631b · 54db09f2 · 36dc8ba6) |
| W2 | WebUI 正确性 bug 簇(7: 热重载对 · 误报对 · 设置页对 · 删除标签作用域) | Open |
| W3 | 数据安全大件(3 feat: 跨组交叉[需重新授权] · 整组迁移 · 现场重建) | Open |
| W4 | 性能专项(4: api-state · shows-view · poll-gate · max-tasks 自适应) | Open |
| W5 | HR 语义与统计拍板簇(2 feat + 4 question) | Open |
| W6 | WEBUI 体验批(12 feat + 1 question) | Open |
| W7 | 扩展与低优先级(3 feat) | Open |
| W8 | 轻量穿插(4 refactor + 4 docs + 3 chore + 2 桌面 bug) | Open |
| W9 | 战略存疑与缓做挂账(6,不排期) | Open(挂账) |

## 进度日志

- **2026-10-02 02:34 v2 改版完成**: 池实测 103 条记录 = 59 未决(58 Open + 1 In Progress)+ 43 Done + 1 Superseded;类型分布 bug 13 · feat 22 · question 8 · perf 5 · refactor 4 · docs 4 · chore 3 · test 0,档位 standard 39 / light 19。计划 HTML 同文件改版(doc-updated → 26-10-02-0234),变更记录补 v2 行;本轮零代码变更,收尾基线另记切片。
- **2026-10-02 05:11 W1 波收官(3/3)**: 阶段 3/3(web 鉴权加固双件)同批落地 —— A) skip_local_verify 开启时跨站防护(Host 白名单 + 写方法 Origin, 默认路径零变化); B) SSE 票据化 / config-public 限 loopback / uvicorn proxy_headers=False(档案 tasks/26-10-02-web-auth-hardening.md, 提交 36dc8ba6 + B 笔); 收官基线 test.full 2288 passed + 3 skipped / 99.01%(切片 26-10-02-0459)。W1 四条 bug 全清, 下一波 W2 待用户授权。
