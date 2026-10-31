# 覆盖率闸单阈值在双 OS 上必有一侧恒红, 且 pytest-cov 的阈值改 config.option 不生效

> 摘要: 覆盖率闸单阈值在双 OS 上必有一侧恒红 —— Windows 独有代码(ctypes/junction/注册表后端)在 Linux 上跑不到, 实测 Windows 99.27% / Linux **98.74%**, 于是 `--cov-fail-under=99` 让 ubuntu CI 恒红而 Windows 正常。修法是**按平台定档**(Windows 99 / 其余 98.5), 且阈值**不能**在 `pytest_configure` 里改 `config.option` —— pytest-cov 早在 `pytest_load_initial_conftests` 就用**早期解析的命名空间**建好了插件, 之后只读自己那份, 改 `config.option` / `session.config.option` 全部静默无效(闸门反而彻底失效, 比红更危险)。必须改插件实例 `config.pluginmanager.getplugin("_cov").options.cov_fail_under`。
> 等级: L0
> 触发: 覆盖率闸, cov-fail-under, 双 OS, ubuntu CI 恒红, pytest-cov, config.option 不生效, 平台定档, 分母不同, Windows 独有代码

### 单一覆盖率阈值 + 双 OS ⇒ 必有一侧恒红 (2026-10-30)

- **触发**: 仓库同时跑 Windows 与 Linux CI, `pytest.ini` 的 addopts 里写死 `--cov-fail-under=99`;
  代码里有平台独有分支(本仓: `infra/alias_fs.py` 的 ctypes/junction 封装 91 语句 + 25 分支、autostart
  注册表后端、relocate_journal、traffic_sample)。或想「按平台给不同阈值」而把钩子写在 `pytest_configure`。
- **判别**:
  - **症状 A(阈值侧)**: 一侧全绿、另一侧恒定红在 `FAIL Required test coverage of 99% not reached`,
    且用例全过。实测: Windows `Total coverage: 99.27%`, Linux `98.74%` —— 差 0.53pt, 恰好是
    Windows 独有代码的行数。核法: 两侧各跑一次 `coverage json` 后按 `missing_lines+missing_branches`
    排序, 差额会集中在 2-4 个平台独有文件上。
  - **症状 B(钩子侧)**: 阈值钩子写了但闸门**完全不出现**(既无 `FAIL` 也无 `reached`) —— 这比红更危险,
    等于闸门静默失效。判别: 故意跑一个小文件(覆盖率 ~18%), 若没有 `FAIL Required test coverage ...`
    那行, 说明阈值没生效。
- **根因(B)**: `pytest-cov` 在 `pytest_load_initial_conftests`(tryfirst)里用
  `early_config.known_args_namespace` 建 `CovPlugin`, 并 `register(plugin, "_cov")`; 报告期读的是
  **`self.options`(那份早期命名空间)**, 不是最终的 `config.option`。而 `--cov-fail-under` 的
  **默认值是 `0.0` 而不是 `None`**(所以「判 None 才算未设」也会漏判, 得判 falsy)。
- **处置**:
  1. **阈值按平台定档, 且只写一处**: `pytest.ini` 的 addopts 里**删掉** `--cov-fail-under`;
     改在 `tests/conftest.py::pytest_configure`:
     ```python
     plugin = config.pluginmanager.getplugin("_cov")
     if plugin is None or getattr(plugin.options, "cov_fail_under", 0):
         return
     plugin.options.cov_fail_under = 99.0 if sys.platform == "win32" else 98.5
     ```
     口径与 `tools/global-traffic-monitor` 的「双 OS 阈值取较低者」一致。
  2. **别去给平台独有代码贴 `# pragma: no cover` 来强行对齐分母**: 那些行在 Windows 上是**可测且有测试**
     的, 贴了就同时放弃 Windows 侧的卡口 —— 用降门槛换对齐, 亏。
  3. 显式 `--cov-fail-under=<非零>` 仍优先(钩子让路); `=0` 按「未设」处理(与 pytest-cov 的 `>0` 语义一致);
     彻底不测覆盖率用 `--no-cov`。
- **守阵**: 无自动机检(阈值是配置口径)。旁证: `commands run test.linux` 的收尾行必须出现
  `Required test coverage of 98.5% reached` —— 出现 `99%` 说明钩子没生效、`pytest.ini` 又被写回了。
- **复发**: 0
