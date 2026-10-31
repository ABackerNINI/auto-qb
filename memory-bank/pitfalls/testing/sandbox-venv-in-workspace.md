# 沙箱工作区里新建的 venv 读不到自己的 pyvenv.cfg (exit 107)

> 摘要: agent 沙箱给工作区目录打了 Low 完整性标签 + 沙箱 capability ACE, 在**工作区内**新建的 venv, 其 `Scripts/python.exe` 读不到**同目录的** `pyvenv.cfg` —— 报 `Cannot read ... pyvenv.cfg` / exit 107 (`uv run` 另报 `uv trampoline failed to spawn Python child process: permission denied (os error 5)`); 重建 venv 无效, 把同一份 venv 拷到工作区外即正常。处置 = `UV_PROJECT_ENVIRONMENT` 指到工作区外。
> 等级: L0
> 触发: exit 107, Cannot read pyvenv.cfg, pyvenv.cfg 不可读, uv run 失败, 工具 venv 坏, permission denied os error 5, uv trampoline, venv 重建无效, gtm 测试跑不了, UV_PROJECT_ENVIRONMENT
**Refs:** memory-bank/tasks/26-10-21-test-gtm-coverage-gate.md

### 工作区内 venv 自读 pyvenv.cfg 失败 → 重建也没用

- **触发**: 在 agent 工具 shell 里对**工作区内的子包**(实测 `tools/global-traffic-monitor`)跑它的依赖同步或测试命令(`commands run env.sync` / `commands run test.gtm`, 二者底层分别是 uv 的依赖同步与测试执行)。venv 建在工作区内(`<子包>/.venv`), 且该工作区目录树带着沙箱标记(`icacls <工作区>` 可见 `Mandatory Label\Low Mandatory Level:(OI)(CI)(NW)` + `S-1-4-<capability>:(OI)(CI)(W,D,DC)`)。工作区**外**的老 venv(如仓库根 `.venv`, 打标前建的)不受影响, 所以「主仓能跑、子包不能跑」。
- **判别**: 三层证据, 缺一不可 ——
  · `cat .venv/pyvenv.cfg` **能读**(文件本身没坏, 内容正常), 但 `.venv/Scripts/python.exe -V` 报 `Cannot read '<abs>/pyvenv.cfg'` 且 **exit 107**(`uv run` 则报 `uv trampoline failed to spawn Python child process ... permission denied (os error 5)`)。
  · 删掉重建**症状不变**(换 uv 托管解释器 / 换 `--python` 装成完整副本, 都还是 107) ⇒ 不是 venv 内容坏, 是位置坏。
  · `cp -r .venv /tmp/venvcopy && /tmp/venvcopy/Scripts/python.exe -V` **正常** ⇒ 判死: 位置问题, 不是 venv 问题。
  · 反证: 同一台机器上 `icacls .venv /setintegritylevel Medium` / `icacls /grant` 一律「拒绝访问」—— 沙箱 token 不给改 ACL 的权限, 所以**别在 ACL 上折腾**。
- **处置**: 把工程环境放到工作区外, 用 uv 的官方开关重定向:
  ```bash
  export UV_PROJECT_ENVIRONMENT=/tmp/gtm-venv     # Windows: H:/Temp/gtm-venv
  commands run env.sync && commands run test.gtm  # 仍在子包目录里跑, addopts/rootdir 口径不变
  ```
  之后 `commands run <task>`(引擎继承调用方环境)同样能跑。**这是本机沙箱的绕道, 不是项目口径**: 命令配置文件里**不要**写死 `UV_PROJECT_ENVIRONMENT`, CI 与用户本机照旧用子包内 `.venv`。踩到时在交付说明里点明「本机数字取自工作区外 venv, 与 CI 同一份 addopts」。
- **复发**: 0
