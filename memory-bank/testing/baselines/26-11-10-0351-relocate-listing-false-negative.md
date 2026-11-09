# 5890 passed, 2 skipped —— 全量基线: relocate 运行时F自检链接对象判别修复(qB 列目录不解析文件级 symlink)

> 摘要: 计划 26-11-10-0230 S1-S3 批实测: 5890 passed, 2 skipped (177.50s), 覆盖率 99% (26210 stmts / 45 miss)
> 基线时间: 2026-11-10 03:51

## 验收数字

```text
TOTAL                                                26210     45   9138     57    99%
5890 passed, 2 skipped in 177.50s (0:02:57)
```

(实测时点: HEAD d262e5ed + 本批工作树改动, `commands run test.full` 2026-11-10 03:51; 较上一基线 26-11-10-0132 的 5883: +7 = 本批新用例 5(链接对象判别三态 + 混合抽样 + 预检支零改动钉) + 已并入 develop 的 schema_version 字面量守卫 2(38fa8690))

## 本改动面

- **relocate_proof.py**(src/auto_qb/core/modules/relocate_proof.py): 链接跟随自检支新增「链接对象判别」—— `_link_object_hit`(qb_dir 经 file_access.map_to_container 换算 syscall 路径 + utils.add_long_path_prefix_for_win 前缀, 逐条目 os.lstat, qB 条目 (size, mtime) 与链接自身双字段一致 => 链接对象态; lstat OSError 按保守不等); `_d_evidence` 判别只在 name_filter 分支生效(link_follow_evidence 是唯一传 name_filter 的调用方, 预检 D 级常规支语义零改动), 汇总口径: 任一与 dst 一致 => POSITIVE(原语义) / 存在与 dst 和链接对象都不符 => NEGATIVE(原语义) / 抽样全部链接对象态 => unavailable(调用方 _qb_side_check 按 skipped 处理, detail 写明「qB 列目录未解析文件级 symlink(条目=链接对象元数据), 真伪不可判」)。
- **test_relocate_proof.py**(tests/): 新用例 5 —— 事故形态红验(链接对象态 -> skipped, 改前判 negative)、目标态 positive 不回归、两不符态 negative 不回归、混合抽样(链接对象+真不符)判负、预检常规支不触发判别; 桩形态跟随既有 `_DirClient`/`_entry`, 源侧用真实 os.symlink(本环境可建)。
- 基线切片: 本文件(`kb.new baseline`, --total 从 test.full 结论行誊写)。
