## 统一 LF 后 kb.index 在 Windows 把生成物写成 CRLF: 一批无内容差异的 modified


- **触发**: 跑 `commands run kb.index`(或任何用 Python 文本模式写 `.md` 的生成器)后看 `git status`。
- **判别**: 一批 `_index.md` 被标记 modified, 但 `git diff` **返回 0**(clean filter 把两侧都归一成 LF ⇒ 无内容差异);
  `git ls-files --eol` 显 `i/lf w/crlf`, 而工作区其余文件是 `w/lf`(2026-10-02 起 `.gitattributes` `eol=lf`)。
  实测 2026-10-03: `kb.index` 后 9 个 `_index.md` 变 `w/crlf`。**这不是索引内容漂移** —— 别据此判断生成物变了。
  2026-10-04 根治后 `kb.index` 不再复现(处置①); 本条保留给存量**手写**文件与其它未登记的文本模式写盘点。
- **处置**: ①**根治已落地 (2026-10-04)**: 5 处生成器写盘点(`gen_all.py` / `gen_kb_index.py` / `gen_tasks_index.py` /
  `gen_docs_index.py` / create-issue 的 `gen_issues_index.py`)一律显式 `write_text(..., newline="\n")` —— 原先吃
  `newline=None` 的默认值, 落盘时按 `os.linesep` 翻换行, Windows 上就是 CRLF。守阵
  `tests/test_memory_bank_structure.py::test_generated_indexes_are_lf_only`(逐字节断言生成物无 CR; `--check` 用 `read_text`
  会把 CRLF 折成 LF, 对行尾不敏感, 所以这条缺陷此前能一路绿灯)。
  ②存量工作区(层3 未做)里**手写**文件仍可能是 CRLF, 归一只需 `git checkout -- <那批文件>`(内容零差异, 安全);
  提交侧 clean filter 本就会归一, 不归也**不进 commit**(blob 不变)。
  ③⚠ 生成物由 CRLF 改写成 LF 后, 若索引 stat 缓存还记着旧(CRLF)尺寸, `git status` 会报一批**幽灵 M** ——
  `git diff` / `git diff-files` 内容比对均为 0, `git update-index --refresh` 也刷不掉; 跑一次
  `git add -- <那批文件>` 刷新 stat 即净(内容与索引恒等 ⇒ 不产生任何暂存条目)。
- **复发 +1 (2026-10-05)**: 处置①修的是生成器, **其它 clone 盘上的旧 CRLF 生成物不会被自动清理** —— 本 clone
  首次跑 test.quick 即被守阵 `test_generated_indexes_are_lf_only` 抓到 11 个 `_index.md` 残留(`eol=lf` 归一化下
  git status 不可见); `kb.index` 重建即绿。没翻到本条的原因: 本轮任务是纯文档编辑, 未走 git 前置路由;
  守阵报错自带处置配方, 拦截闭环成立。
- **复发 +2 (2026-10-07)**: 同一根因换了个入口 —— **一次性清洗脚本**用 `Path.write_text(text, encoding="utf-8")`
  写回 64 个**手写** `memory-bank/*.md`, 默认 `newline=None` 在 Windows 上按 `os.linesep` 把 LF 翻成 CRLF,
  整批文件变 `w/crlf`; `.gitattributes` 归一化下 `git diff` **只显示改动行**(内容差异 84 行), 肉眼完全看不出来。
  **暴露它的是 git 的警告行**「CRLF will be replaced by LF the next time Git touches it」—— 不是任何守阵
  (守阵 `test_generated_indexes_are_lf_only` 只覆盖**生成物**, 手写文件没有对应守卫)。处置: 就地
  `p.write_text(p.read_text(), encoding="utf-8", newline="\n")` 重写, 复核 `b"\r" in p.read_bytes()` 归零。
  **为什么没命中**: 本条处置①的措辞是「**生成器**写盘点一律显式 `newline="\n"`」, 读起来像"只约束生成器";
  而这次是**一次性脚本写手写文档**, 不在那句话的射程内 —— 判据其实是「**任何** `write_text` 都要显式
  `newline="\n"`」, 与是不是生成器无关。**建议**: 写 md 类文件时 `newline="\n"` 当默认肌肉记忆, 别等守阵
  (手写文件那条路没有守阵兜底)。

