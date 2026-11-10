# 包入口脚本 __main__ 漏 raise SystemExit(main()) = 引擎报 [ok] 但静默空转

> 摘要: 包入口脚本 __main__ 漏 raise SystemExit(main()) = 引擎报 [ok] 但静默空转
> 触发: __main__, SystemExit(main()), 静默空转, [ok] 秒回, 入口脚本, 快照重入, ship.gate

## 本篇只回答

.commands 包的入口脚本(与 sync.py/commit.py/push.py 同构的 task script)为什么 `__main__` 块漏一行就会"跑成功但什么都没做", 以及新写入口时怎么一眼自查。

### 新入口脚本照抄了快照自举却漏抄最后的 `raise SystemExit(main())`, task 报 [ok] 秒回但零输出零动作

- **触发**: 给包新增 task 入口脚本(如 gate.py), `__main__` 块只照抄了 sync.py 的快照自举四行(`from _snapshot import maybe_respawn` + `maybe_respawn(__file__)` + `if _rc is not None:` + `raise SystemExit(_rc)`), 漏了块尾的 `raise SystemExit(main())`; 或复制别的入口时删改了尾部。模块级 main() 定义、docstring、参数面全都齐, 唯独 CLI 路径没人调 main。
- **判别**: `commands run <task>` 报 `[ok] <task> (0.3s)` 且**零输出**; 直接 `python <script>.py` 同样 rc=0 无输出。对照: 真 CLI 直跑(`python -c "import ...; mod.main([])"`)功能完全正常 —— 只断 CLI 入口断链。危险在于退出码恒 0, 引擎按成功透传, **静默空转比报错坏**(ship.gate 这种"预跑闸门"会假绿, 让人以为闸门跑过了)。
- **处置**: `__main__` 块固定五行收尾 —— **逐字照抄 [sync.py:540-546](../../../.commands/my-commit-flow/scripts/sync.py) 的块体, 以真文件为单点**(`from _snapshot import maybe_respawn` + `maybe_respawn(__file__)` + `if _rc is not None:` + `raise SystemExit(_rc)` + `raise SystemExit(main())`); 照抄漏掉 `if _rc is not None:` 守卫行时, 非 snapshot 路径 `maybe_respawn` 返回的是子进程 rc(非 None), `raise SystemExit(rc)` 直接退出 rc —— 又一个静默空转。新增入口后**必跑一次真 CLI**(经 `commands run`, 不只跑包内测试)核对输出行数与秒数 —— 秒回 + 零输出 = 空转信号; 单测里 `main([])` 直调救不了这个坑(那条路径根本没经过 `__main__`)。
- **守阵**: 无机检(入口脚本 `__main__` 块的形态守卫可作后续议题; 当前靠新增 task 的 dogfood 步骤兜 —— 计划 26-11-11-0408 §04 步 5 即真 CLI dogfood)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
