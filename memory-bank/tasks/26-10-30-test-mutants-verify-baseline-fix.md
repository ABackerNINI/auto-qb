# 26-10-30-test-mutants-verify-baseline-fix — mutants.verify 判据修复: 基线常红致恒判 KILLED

**Status:** Done
**Added:** 2026-10-30
**Updated:** 2026-10-30
**Summary:** `mutants.verify` 判据从「套件有 failed 即 KILLED」改为「本次失败 - 基线失败 的差集 + 复跑复现」; 顺带修 `-x` / 字节码缓存 / 未落地 apply / 结果文件分钟戳四个同族缺陷; 新增 18 例守阵
**Topics:** test-mutants-verify-baseline-fix

## 原始请求

1. 「另一会话报告: `mutants.verify` 在本机结构性失效 —— 它跑全量套件, 而全量套件在 WSL Linux 上有 3 个既有平台失败, 基线常红。修复」
2. 「Please resume the unfinished tasks.」

## 思考过程与决策

- **病根不在「套件红」, 在「判据用错」**。老 `cmd_verify` 用「输出里有 failed 就算 KILLED」当判据 ——
  这在基线全绿时才等价于「这个变异被抓住了」。基线常红时它对**每条**候选恒真 ⇒ 全杀 = 没杀。
  实测证据: 本机 Linux 侧 `3 failed, 4144 passed`, 老口径的 S4 结果文件 5 条全 KILLED, 且汇总行是
  `1 failed, 1395 passed` —— 套件 4144 条只走到 1395 就断了。
- **第二个缺陷: `-x`**。它让 pytest 停在**第一条既有失败**上, 变异体根本没被执行 —— 与上一条叠加,
  产出的是「既没跑完、又必然判死」的双重假数。
- **修法选型: 基线感知的差集, 不去修那 3 条平台失败**。理由: 那 3 条是另一缺陷(测试缺 `_WIN_ONLY` 标记),
  修绿了也只是把判据的正确性押在「这台机器永远全绿」上 —— 任何一次 flake / 半成品守阵都会让 verify
  重新退化成全杀。差集判据与机器状态解耦, 才是结构性修法。
- **新增失败要复跑复现才算 KILLED**。实测抓到一次反例: `x__url_host__mutmut_6` 在某一轮多出
  `test_hr_discovery.py::test_start_binds_first_free_candidate`(端口绑定类 flaky, 与变异无关) ⇒ 一次红
  不足以定罪。复跑只跑新增失败的那几条 node id(~1-2s), 不复现记 FLAKY(未判定, 不污染分母)。
- **未判定三态单列**: APPLY_FAIL / TIMEOUT / UNKNOWN / FLAKY 都不并进 SURVIVED —— 否则「没判定」
  会被当成「真洞候选」, 与 mutmut-survived-verdict 里「超时单列」的纪律一致。
- **同族缺陷一并修**(同一条循环里的判定正确性): `-B`+清 `__pycache__`(假 SURVIVED, 见
  redverify-pycache-stale-verdict) · apply 未落地校验(恒 SURVIVED) · 单次套件 timeout(死循环挂死) ·
  结果文件按输入清单定名(老实现带分钟戳 ⇒ 跨分钟重跑换文件, 「幂等可续跑」形同虚设)。
- **不动 `src/`**: 本轮是工具链判据修复, 生产代码零改动。
- **未做(明确留口)**: 3 条 Linux 平台失败不修, 只在基线切片与坑档里点明「基线越红判据越弱」。

## 实现计划

1. 复现: 在镜像里跑未变异全套件, 量出既有失败集合(3 条) → 确认老口径必然全杀。
2. 重写 `cmd_verify`: 基线 + 差集 + 复跑复现 + 未判定三态 + 超时 + 结果文件定名。
3. 抽 `_verdict` 为纯函数, 新增 `.commands/mutants/scripts/test_mutants.py` 守阵。
4. 端到端在真实镜像上跑 4 组候选, 覆盖 SURVIVED / KILLED(真) / APPLY_FAIL 三条路径。
5. 同步包内文档(`config.toml` / `references/why.md`)与 skill 判据。
6. 坑档 `mutmut-survived-verdict` 复发 +1 并改写处置 3; 建基线切片; `test.full` / `test.pkg` 复核。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 复现基线常红(镜像实测 `3 failed, 4144 passed`) | Done(2026-10-30) |
| 2 | `cmd_verify` 改基线感知 + 差集判定 | Done(2026-10-30) |
| 3 | 纯函数 `_verdict` + 18 例守阵 | Done(2026-10-30) |
| 4 | 端到端 4 组候选实测(含真 KILLED 与 APPLY_FAIL) | Done(2026-10-30) |
| 5 | 包内文档 + skill 判据同步 | Done(2026-10-30) |
| 6 | 坑档复发 +1 / 基线切片 / 全量复核 | Done(2026-10-30) |
| 7 | 3 条 Linux 平台失败(测试缺 `_WIN_ONLY` + realpath 取证过宽) | Done(2026-10-30) |
| 8 | Linux 覆盖率闸改平台定档(99 / 98.5) | Done(2026-10-30) |

## 进度日志

### R0 · 立档 (2026-10-30)

- 复现: WSL2 `Ubuntu-26.04` 镜像 `~/auto-qb-mut` @ `a00ee589`, 未变异全套件 `3 failed, 4144 passed, 10 skipped in 25.51s`。
- 重写 `cmd_verify`: 基线失败集合(按 镜像HEAD+并行度 缓存) → 逐条「本次失败 - 基线」判 KILLED;
  去 `-x`; `-B` + `PYTHONDONTWRITEBYTECODE=1` + 清 `__pycache__`; apply 落地校验; 新增失败复跑复现
  (不复现记 FLAKY); 单次套件 `timeout`(TIMEOUT); 结果文件 `s4-verify-<输入清单>.txt` 定名。
- 端到端实测: `norm_domains m3` / `migrate_config_1_2 m23` → SURVIVED(老口径皆 KILLED);
  `writer.x_unmask_tree m4` → KILLED(真, 复跑复现, 新增失败 `test_config_tree_requires_config_root`);
  不存在的 id → APPLY_FAIL。单条墙时 28s。
- 守阵: `.commands/mutants/scripts/test_mutants.py` 18 例(含「基线常红 + 无新增失败 ⇒ SURVIVED」这条原 bug)。
- 复核: `test.pkg` 全绿(数字见 kb.baseline 切片 26-10-30-0622); `test.full` 同切片。
- 坑档 `pitfalls/testing/mutmut-survived-verdict.md` 复发 +1(同一天两条独立路径), 教训: 判据性缺陷
  要改脚本 + 加守阵, 只写「别用」挡不住下一个人。

- 2026-10-30 06:26 mutants.verify 判据改基线差集 + 复跑复现, 补 18 例守阵; test.full 全绿(数字见 kb.baseline 26-10-30-0622)

### R1 · Linux 侧一并修绿 (2026-10-30)

- **授权**: 用户「linux失败一并修复」—— 3 条平台失败不再挂 Open。
- **两条 alias_fs 用例**: 桩 `ctypes.WinDLL`, Linux 上 `ctypes` 无此属性 ⇒ `monkeypatch.setattr`
  AttributeError(不是断言失败)。补 `_WIN_ONLY`(该文件已有此标记, 这三条是漏挂)。
- **relocate 用例**: 断言「src 不得被 os.lstat」过宽 —— 生产侧 `realpath_lexical` 走 `os.path.realpath`,
  POSIX 上是 Python 实现(逐段 `os.lstat`), Windows 上走 `nt._getfinalpathname` 不碰 `os.lstat` ⇒
  只在 Linux 假红。用例内把 `os.path.realpath` 换成恒等, 并在 docstring 记平台差异。
- **覆盖率闸**: 用例全过后仍红在 `Total coverage: 98.74% < 99`(Linux 永远够不到 —— 差额是 Windows 独有代码)。
  改平台定档: `tests/conftest.py::pytest_configure` 设 Windows 99 / 其余 98.5, `pytest.ini` 的 addopts
  删掉 `--cov-fail-under`(阈值单点)。
- **坑**: 阈值钩子最初写 `config.option.cov_fail_under`, 闸门**静默消失**(pytest-cov 用早期命名空间建插件,
  且默认值是 0.0 不是 None)。改为改 `_cov` 插件实例的 `options`。立坑档 `coverage-floor-platform`。
- **实测**: `test.linux` 绿(`4145 passed, 12 skipped` + 98.5% 闸 reached, 实际 98.74%);
  `mutants.verify` 重算基线 = **0 条既有失败**。

- 2026-10-30 06:55 3 条 Linux 平台失败修绿(2 条补 _WIN_ONLY + 1 条取证断言收窄到代表文件探测) + 覆盖率闸改平台定档(Windows 99/其余 98.5, pytest-cov 阈值须改 _cov 插件实例); test.linux 全绿 4145 passed/12 skipped, verify 基线 0 条既有失败
