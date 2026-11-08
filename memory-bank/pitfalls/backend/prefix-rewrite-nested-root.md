# 前缀替换的幂等判定别只查目标前缀命中 —— 新旧根互为前缀时目标命中可能是源命中的推论

> 摘要: `core/fastresume.rewrite_save_paths` 初版「先查新根前缀命中 ⇒ already 跳过」在 new_root 是 old_root 真前缀(父方向嵌套, new<old)时误判: 值命中新根前缀只因它命中旧根(旧根以新根开头), 并非「已在新根」⇒ 旧根键值被跳过永不改写; daemon 记 already 出账后核验永不过 ⇒ journal 永久悬挂(D10 收敛公理违反)。收口评审 #1 blocker(2026-11-07, 修复 commit 4f70190f)。
> 触发: 写前缀替换, 幂等判定, already 跳过, 嵌套根, 新旧路径包含关系, 改写永不生效, 核验永不过, journal 悬挂
**Refs:** memory-bank/tasks/26-11-05-backend-relocate-fastresume-finalize.md

### 幂等判定只能认「改写确为无操作」, 不能认「命中目标前缀」

- **触发**: 写「旧值 → 新值前缀替换 + 幂等跳过」逻辑(路径改写/字符串模板重定向); 新旧根可能互为前缀 —— 嵌套目录迁移、目标=源祖先/后代、同根加后缀。
- **判别**: already/unmatched 分支先于源(旧根)命中判定, 或两判定并存且目标命中单独短路。画命中矩阵即可暴露: 嵌套 new<old 时旧根下任意值**两根同时命中** —— 新根命中是旧根命中的必然推论, 不是「已在目标」的独立证据。
- **处置**: 判定顺序钉死 —— 先算旧根命中与改写产物; 产物==原值(字节面无操作), 或(目标也命中 且 旧根是新根前缀, 即嵌套 old<new 值已在新根内, 再改只会二次加深)才 already 跳过; 嵌套 new<old(目标=源祖先)时目标命中不作数, 必须改写。单点 `core/fastresume.py::rewrite_save_paths`(docstring 含两向嵌套裁决)。
- **守阵**: `tests/test_core_fastresume.py::test_rewrite_nested_new_prefix_of_old_rewrites`(new<old 方向: 值虽命中新根前缀仍必须改写) + `test_rewrite_idempotent_skips_already_at_target`(old<new 方向: 已在新根内跳过)。
