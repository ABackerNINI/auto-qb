# 残留的仓库副本让全仓扫描守阵假红(test_free_port_single_source 端口实现散落)

> 摘要: gitignored 的旧全量仓库副本被 `rglob` 扫描守阵算进「源码散落」, 报错指向副本而非产品代码; 移出副本即绿, 不是代码缺陷。
> 触发: test_free_port_single_source, 端口实现散落, tmp-analysis, 旧仓库副本, rglob, 扫描守阵假红, 环境残留
**Refs:**

### 全仓 `rglob` 扫描把 gitignored 的旧仓库副本算进「源码散落」

- **触发**: 仓库根的 gitignored 目录里留着旧的全量仓库副本(如 `tmp-analysis/w2b-save/`, 内含 `tests/*.py` 等分析快照), 再跑全量 `commands run test.full`; 扫描型守阵用 `REPO.rglob("*.py")` 找重复实现时会扫进该副本。
- **判别**: 失败信息点名「端口实现散落」并列出 `tmp-analysis/<副本>/tests/*.py`, 但 `git status` 干净、当期源码里并没有第二份实现 —— 报错指向副本而非产品代码; 把副本移出仓库或单跑该文件后即绿。
- **处置**: 不要为此改产品或删减守阵; 把旧副本移出仓库(保留留档)或删除: `Move-Item tmp-analysis/<副本> $env:TEMP/<name>-<date>`, 复跑 `commands run test.full` 确认转绿。判据同 [ghost-pkg-residue.md](ghost-pkg-residue.md): 环境残留不是代码缺陷。
- **守阵**: 无(扫描型守阵本身是触发器); 若同类假红反复出现, 再单独评估给扫描面加 gitignored 目录排除(那属另一 issue, 不顺手改)。
