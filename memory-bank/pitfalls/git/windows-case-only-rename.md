# Windows 仅大小写改名: write_bytes 打开旧文件, unlink 把原文件删掉

> 摘要: Windows 仅大小写改名: write_bytes 打开旧文件, unlink 把原文件删掉
> 触发: 大小写改名, case rename, write_bytes, 改名后文件消失, git status 意外 D, ignorecase

### Path.write_bytes/open(w) 到「仅大小写不同」的路径会打开已存在的旧文件, 再 unlink 即删件

- **触发**: Windows (大小写不敏感 FS) 上用 Python 做仅大小写改名, 惯性写法 `new.write_bytes(text)` + `old.unlink()` —— `new` 与现存 `old` 仅大小写不同, open(w) 按不敏感匹配直接打开**旧件** (内容写进旧件), 随后 unlink 把**同一个文件**删掉。事例: 26-10-31 修 RM 计划件名时九件一度从磁盘消失 (HEAD 已提交, 从 git 恢复后用安全序列重做)。
- **判别**: 脚本逐件打印「成功」但 `ls` 里目标名不存在; `git status` 出现意料外的整批 `D`; 想用 `lower.exists()` 预检防碰撞也无效 —— 大小写不敏感 FS 上它恒 True (就是旧文件自己)。
- **处置**: 改名走安全序列: ①写**临时名** (与新旧名差异都不止大小写, 如加 `.tmp-rename` 后缀) ②`old.unlink()` ③`os.rename(tmp, 新名)` (目标已不存在, 纯 rename)。git 侧落大小写改名: `git rm --cached <旧名>` + `git add <新名>` (core.ignorecase 会把纯改名折叠成 M, 直接提交会保留旧大小写; `git mv -f` 亦可)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
