# ship.commit 逐路径 add 撞「已暂存删除」路径 / 零参数全量提交会带进会话目录

> 摘要: ①commit.py 按纪律逐路径 `git add -- <path>`(禁 -A), 对**已暂存的删除**(`D `)必然 pathspec 落空 —— 删除一旦进暂存区, 该路径在工作区与索引里都不复存在, `git add` 无处匹配; ②**零参数 = 全量暂存**, 未被 `.gitignore` 覆盖的会话目录(`.workbuddy/memory/`)会被一并入库, 事后补忽略还会撞 ① 的变体(`git add` 忽略路径直接失败); ③同一全量暂存面还会把**平台工作目录**(后台日志 `.zwork/`、临时证据区 `.zcode-tmp/`)卷进提交, 且**跨会话成双份**(两笔提交各带一份, 合流后都在)。
> 触发: ship.commit, git add 失败, pathspec did not match, addIgnoredFile, 删除文件, 提交失败, 蒸馏切片, 全量提交, .gitignore, 会话记忆入库, .workbuddy, .zwork, .zcode-tmp, 临时证据入库, 跨会话双份, 提交前扫 status

- **触发**: 本轮删除过已跟踪文件(如按 DoD 蒸馏 activeContext 切片)后跑 `commands run ship.commit`,
  暂存步骤报 `RESULT: FAIL git add 失败: <被删路径>` + `fatal: pathspec ... did not match any files`
  (2026-09-28 实测, 删除已随前次失败留在暂存区)。
- **判别**: `git status --porcelain` 看该路径首列 —— `D `(删除已暂存)必踩: 索引已无此文件、工作区也没有,
  `git add -- <path>` 无处匹配; ` D`(删除未暂存)则索引还留着条目, `git add -- <path>` 能正常登记删除。
- **处置**: `git restore --staged <path>` 把删除退回未暂存态(` D`)后重跑 ship.commit 即过
  （旧版脚本的 workaround, 仍有效）。
  **根修已落**（issue 26-09-28-0128, 随 my-commit-flow v3 commit 4ba6cb7f, 2026-09-28）:
  commit.py 暂存循环按文件存在性三分流 —— 工作区存在 → `git add`; 工作区无而索引有(` D`)→
  `git rm --cached` 登记删除; 都不在(`D `)→ 跳过(删除已在暂存区), 逐路径 add 不再撞 pathspec 落空。
  守阵: `test_commit.py::test_staged_delete_skips_add` + `test_unstaged_delete_uses_rm_cached`。

## 变体: 撤文件出版本库时「补 .gitignore」与「git add」互相打架(2026-09-29 实测)

- **触发**: 想把某个**不该入库**的目录撤出版本库(本轮是误入库的 `.workbuddy/memory/2026-09-29.md`),
  于是 `git rm --cached` + 在 `.gitignore` 补一条 —— 然后 `ship.commit`(零参数)报
  `git add 失败 .workbuddy/memory/2026-09-29.md —— hint: Disable this message with "git config set
  advice.addIgnoredFile false"`: 忽略规则一生效, 该路径就不再是 `git add` 的合法目标。
- **判别**: `.gitignore` 新覆盖到**已从索引移除但仍在改动清单里**的路径 ⇒ 必然踩;
  这跟上面 `D ` 的 pathspec 落空是同一类(路径对 git 而言"不存在"), 只是报错文案不同。
- **处置**: **子集提交只传被改的配置文件** —— `commands run ship.commit -- .gitignore`;
  索引里那个 `D ` 删除条目**不用 add**, 会随 `git commit` 一并落进这一笔
  (实测: 该笔 = `.gitignore` +3 / 记忆文件 -52, `git ls-files .workbuddy` 之后为空)。
  ❗别为此去 `git restore --staged`(那会把文件重新加回索引, 等于没撤出), 也别撤 `.gitignore`。
- **预防**: `ship.commit` **零参数 = 全量暂存** —— 提交前先看一眼 `git status --short` 有没有
  不该进版本库的目录。会话记忆(`.workbuddy/memory/`)、agent 技能目录(`.codebuddy/` `.workbuddy-ai/`)
  一律不入库, 进版本库的知识库是 `memory-bank/`; 本轮已把 `.workbuddy/` 补进 `.gitignore`。

## 变体二: 平台工作目录被全量暂存卷进提交, 且**跨会话成双份**(2026-10-16 实测)

- **触发**: 会话产生过平台工作目录(后台命令日志 `.zwork/`、临时证据区 `.zcode-tmp/`:
  截图 / `results.json` / 探针脚本), 而它们当时不在 `.gitignore` 里 —— 随后**任何**零参数
  `ship.commit` 都会把它们一并入库(实测: 本会话的提交带进 `.zwork/` 5 份日志 + 自己两份 scratch;
  另一个会话的提交把 `.zcode-tmp/` 下 9 张真浏览器截图 + `results.json` 带了进去)。
- **判别**: ①提交前 `git status --porcelain` 里的 `??` 路径与本次改动无关; ②提交后
  `git show --stat HEAD` 里出现这类路径即命中。⚠ 更贵的一层是**合流**: 两笔提交各带一份同类
  垃圾, rebase 合流后两边都在 —— 顺手还得决定谁删、以及不要把别人的已入库件当自己的一起删掉
  (本轮实测: 合流时用 `git add` 把对方那 10 个文件**恢复回索引**, 只把自己那份剔除, 最终提交的
  diffstat 里就只剩自己的改动)。
- **口径早已写明**: `tasks/26-10-04-webui-tooltip-declutter.md` 与
  `testing/baselines/26-10-07-2313-webui-tooltip-declutter-r2.md` 都注「临时证据 / 勿入库」——
  这类件本就不该进版本库, 别当「只是几张图」。
- **处置**: ①`.gitignore` 补两条(`.zwork/` 与 `.zcode-tmp/`, 已落 AutoClaw 段, 带事故注记);
  ②`git rm -r --cached .zcode-tmp` 撤出跟踪(磁盘副本保留); ③**提交走上面的子集处方**:
  `commands run ship.commit -- .gitignore <本次改到的记忆文件>` —— 索引里的 `D ` 删除条目
  会随 `git commit` 落进同一笔(实测: 该笔 = `.gitignore` + 10 条撤销跟踪 + 坑档/索引)。
  ❗忽略规则生效后, **别把已忽略的路径递给 `ship.commit`**(那是上面「变体」的 `addIgnoredFile`
  的反向形态: 工作区仍在、但 git 已不当它是 add 目标)。
- **预防**(与上一条并列, 这是同一根因第二次踩): 提交前扫一眼 `git status --short`, 看到非本次
  改动的 `??` 路径 → 要么给它落忽略、要么删掉; 平台再冒出新的工作目录时照此补一条。
