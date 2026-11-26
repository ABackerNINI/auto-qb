# platform-fs · POSIX 目录 st_nlink 恒 ≥2 与代表文件探测(原文归档)
> 摘要: 目录 nlink 在 Windows/Linux 语义相反，拿目录当代表文件探测只在 Linux 炸；含 alias_kind_of 复发与守阵写法。
> 触发: st_nlink, 目录 nlink, 代表文件, lstat, 硬链接探测, alias_kind_of, IsADirectoryError, Linux CI, 空文件表, 形态判定排目录

### POSIX 目录的 `st_nlink` 恒 ≥ 2(Windows 目录 = 1): 拿目录当「代表文件」的探测只在 Linux 炸

- **触发**: 对 `save_path` 这类**目录** `os.lstat` 后按 `st_nlink > 1` 判硬链接; 或写只在本机跑过的平台分支用例。
- **判别**: Linux 目录 `nlink = 2 + 子目录数`(**恒 > 1**), Windows NTFS 目录 `nlink = 1`(本机实测目录 1 / 普通文件 1)
  ⇒ 同一段 `elif st.st_nlink > 1:` 在 Windows 走不到、在 Linux 必进。2026-10-19 GitHub Actions 实测:
  `relocate_mod._group_facts` 空文件表时 `first_native` 兜底成 `save_path`(目录), 随后 `names[0]` → `IndexError`,
  而本机全绿。
- **处置**: 「代表文件」只对**真文件**成立 —— 空文件表(读不到文件列表)整段探测跳过(`if names:`), 不要用
  `save_path` 兜底; 守阵用「录 `os.lstat` 探针 + 断言目录零探测」的写法, 让 Windows 也能红验
  (`tests/unit/test_relocate_paths.py::test_precheck_empty_file_table_skips_representative_probe`)。
- **复发** +1(2026-11-07, `alias_fs.alias_kind_of`): 同一个 nlink 判据换了个入口又踩一次 —— 形态判定把
  **真目录**(空目录就已 nlink=2)认成 `KIND_HARDLINK`, 于是 `retarget_alias` 里「链接位被非空真目录占据」的
  拒绝分支前置条件(`existing is None`)不成立, 直接拿目录本体去 `os.unlink` —— Linux CI 抛
  `IsADirectoryError`, 本机(Windows 目录 nlink=1)全绿。
  **为什么没命中**: 本档是按「拿目录当**代表文件**去探测」这个动作写的, 而这次的动作是「判一条路径**是不是
  链接、是什么形态**」; 路由到本档时只读成「别拿目录当代表文件」, 没把它读成「任何按 nlink 判形态的地方都得
  先排掉目录」。**处置**: 形态判定入口先排目录 —— `alias_kind_of` 在 `S_ISLNK` 之后、nlink 判据之前
  `S_ISDIR -> None`(目录只可能是真目录或已判完的链接形态; 硬链接指向目录两平台都建不出来), 守阵
  `tests/unit/test_alias_fs.py::test_alias_kind_of_real_dir_is_none`(Windows 上恒真、靠 Linux CI 红验)。

