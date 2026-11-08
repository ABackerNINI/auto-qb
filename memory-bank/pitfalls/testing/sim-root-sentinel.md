# dev.sim 工作根的 B1 哨兵: 预建空目录不写哨兵, 第二次起跑必被拒

> 摘要: `scripts/sim_qb.py` 的 `prepare_root` 只在 root 目录**不存在**时才写哨兵 `.auto-qb-sim-root`; 自己先 `mkdir` 出来的空目录第一次跑会被当"合法空目录"放过但不留哨兵, 跑过一次目录非空后, 之后每次起 sim 都撞 `B1: --root 已存在且非空, 但缺哨兵`。
> 触发: dev.sim, B1, 哨兵, sim root, 已存在且非空, BoundaryViolation, 删除场景

### 预建 root 目录 → 首跑过了, 复跑 B1 拒绝

- **触发**: 脚本化起 sim 前先 `mkdir -p <root>` 再 `commands run dev.sim -- --root <root>` (2026-10-04, P6 桩验证实测: 同 root 先跑 `--self-test` 再跑主验证, 第二跑即炸)。
- **判别**: 报错 `BoundaryViolation: B1: --root 已存在且非空, 但缺哨兵 .auto-qb-sim-root —— 拒绝在非仿真目录上跑删除场景`; `ls -a <root>` 只有 `runs/` 没有哨兵文件。根因: `prepare_root` 的哨兵写入只在 `os.path.exists(root)` 为假的分支里, 已存在的空目录走"合法放行"分支但不补哨兵。
- **处置**: 让 sim 自己建 root (传一个不存在的路径), 或手工补哨兵: `printf 'auto-qb sim root\n' > <root>/.auto-qb-sim-root`。仿真 root 是一次性验证现场, 复用前先确认哨兵在。
