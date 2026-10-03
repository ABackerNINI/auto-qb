# 基线切片 26-10-04-0630 — CI 新增 windows-latest job

> 摘要: `.github/workflows/ci.yml` 新增 `test-windows` job(windows-latest, Python 3.12/3.13 矩阵,
> fail-fast false), 步骤复用原 ubuntu job(checkout / 固定 SHA 的 setup-uv / setup-python /
> 依赖同步 + 全量 pytest, 即 `commands run env.sync` 与 `test.*` 收录的等价命令); 不上传 coverage
> (Windows 侧先只做通过性验证), 原 artifact 改名 `coverage-ubuntu-<py>` 防撞名。src/ 与 tests/ 零改动。

- 时间: 2026-10-04 06:30 (GMT+8); 会话起点 sync 至 0c518e0b, 提交轮再 sync 无新远端
- 分支: develop @ 0c518e0b(+ 本轮未提交改动: .github/workflows/ci.yml + memory-bank 回写件)
- 命令: `commands run test.full`
- 实测: **2442 passed + 4 skipped, 32.57s, 覆盖率 TOTAL 99%**(14495 语句 / 136 未覆盖 / 4864 分支 / 107 partial)
- 相对上基线(26-10-04-0553: 2442 passed + 4 skipped)**净增 0 用例**: 本轮只改 CI workflow YAML,
  生产代码与测试零改动, Linux 侧数字不受影响(不重跑 `commands run test.linux`)。
- 未验证面: Windows CI 矩阵含 Python 3.13(本机 3.12, 未实测) —— 以首次 GitHub Actions 运行为准;
  Windows runner 上依赖同步 / pytest 的平台行为(路径分隔符 / 临时目录)首次真跑才见分晓。
