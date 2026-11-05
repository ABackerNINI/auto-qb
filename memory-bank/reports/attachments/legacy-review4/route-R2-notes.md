# R2 路线小结(存量评审 R4 · config·rules·infra)

owner: clone2-main · freeze: f088329291e6 · 快照: D:\Projects\zcode\auto-qb-review4-snap\auto-qb-zcode-clone2

## 批次勾选表

| 批 | 内容 | findings 过检 | 状态 |
|---|---|---|---|
| R2-1 | 校验面 config/validation ≈2.3K | 10 (minor 7 / nit 3) | done |
| R2-2 | schema 与装载 ≈2.5K | 4 (minor 3 / nit 1) | done |
| R2-3 | 写入与迁移 ≈1.9K | 4 (minor 4) | done |
| R2-4 | rules 全域 ≈3.4K | - | pending |
| R2-5 | infra 存储 ≈1.4K | - | pending |
| R2-6 | infra 工具 ≈1.9K | - | pending |

## R2 复验结论

- **D-01 已消失**: sections.py `_validate_qbittorrent` 已补三 str 键类型检查(260-262 行,与 web.token 同形态,注释自证 26-10 修复)。
- **D-01 loaders 侧已消失**: loaders.py:93-101 load_qbittorrent_config 现为纯字段透传,无日志/回显。
- **C-02 已消失**: 底册锚实为 src/auto_qb/core/curves.py:76(非 config/validation/curves.py),签名已显式 Optional,RUF013 不再成立。

## 自弃发现记录

(暂无 refute;R2-2 面2 零发现;R2-1 引文校验 10/10 全过)

## 执行备注

- **review.check 快照用法缺陷(S0 工具问题,待拍板入池)**: `review.check --root <快照目录>` 被 `_resolve_root` 的 `.git` 存在性检查拒收(缺 .git 即 die),而命令 help 明文写存量用法就是 `--root <快照目录>`;实际 `_verify` 直接从 root 读文件比对,与 git 无关,检查是误伤。等价通路:每批先 `git diff --stat f088329291e6..HEAD -- <批文件>` 确认零变更后,对工作树根(默认 root)跑校验,语义与快照比对等价。R2-1 已验证零 diff。
