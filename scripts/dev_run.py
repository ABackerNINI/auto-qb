#!/usr/bin/env python
"""dev.run 包装: HR 发现口注入测试带(计划 26-11-10-0515 S5; §05 P1 拍板 = CLI 覆盖路线)。

dev 世界(本 clone 真机试跑)默认把 HR 发现口钉到**测试带** 28788, 与 hr_ext_stub.py 的
新默认同带 —— 工具链起的东西一律测试带(装置三), 生产带 18788-18795 结构上留给生产实例
与生产扩展。注入面 = 产品 CLI 的 --hr-discovery-port(对 config 语义零侵入: 不写
config.yml、不改 schema/校验口径, 只覆盖本进程内存生效值, 退出即消失; 磁盘侧物化迁移/
WebUI 编辑器/版本备份仍指向真实配置路径)。

显式豁免口 --hr-prod-discovery(风险表「dev.run 注入改变真机验证的发现口」的对策面):
传了就不注入, 发现口回到配置文件原值(生产带) —— 用户想真机验证生产带发现行为时的
「故意的」豁免, 不属遗漏。

用法(日常经 commands run dev.run -- <args>; 除豁免旗标外 <args> 原样透传给 auto-qb):
    commands run dev.run -- config.yml --dry-run                      # 注入: 发现口 28788
    commands run dev.run -- --hr-prod-discovery config.yml --dry-run  # 豁免: 用配置原值(生产带)
"""
from __future__ import annotations

import sys

#: 测试带发现口(与 hr_ext_stub.py 新默认同带; 候选表 +0..+7 = 28788-28795)
TEST_BAND_DISCOVERY_PORT = 28788
#: 豁免旗标(dev.run 面; 与产品 CLI 的 --hr-discovery-port 分属两层)
EXEMPT_FLAG = "--hr-prod-discovery"


def inject_port(argv: list[str]) -> list[str]:
    """argv 注入: 剥掉豁免旗标; 未豁免则在最前插入 --hr-discovery-port 28788。

    插在**最前**是刻意的: argparse 同名参数后者胜 —— 用户显式传 --hr-discovery-port
    时自己的值仍能覆盖注入值(注入值只是默认面, 显式面永远赢)。
    """
    prod = EXEMPT_FLAG in argv
    rest = [a for a in argv if a != EXEMPT_FLAG]
    if prod:
        return rest
    return ["--hr-discovery-port", str(TEST_BAND_DISCOVERY_PORT)] + rest


#: 出口模式旗标(cli.py 先于 QbManager 构造返回, 注入在这些路径不生效 —— 横幅照实说)
EXIT_MODE_FLAGS = ("--hr-once", "--hr-status", "--hr-confirm-empty")


def main() -> int:
    exit_mode = any(f in sys.argv[1:] for f in EXIT_MODE_FLAGS)
    if EXEMPT_FLAG in sys.argv[1:]:
        print("[dev.run] HR 发现口显式豁免: 用配置文件原值(故意的)", flush=True)
    elif exit_mode:
        # 评审 minor 2026-11-11: 出口模式不构造 QbManager, 注入旗标是静默 no-op ——
        # 照常打「注入测试带」会与随后的状态报告(按配置原值显示发现端口)同屏矛盾
        print("[dev.run] 出口模式(--hr-once/--hr-status/--hr-confirm-empty): 发现口注入不生效, 用配置原值", flush=True)
    else:
        print(f"[dev.run] HR 发现口注入测试带 {TEST_BAND_DISCOVERY_PORT}(豁免: --hr-prod-discovery)", flush=True)
    sys.argv = ["auto-qb", *inject_port(sys.argv[1:])]
    # 交给正式 CLI: 与 `python src/auto-qb.py <args>` 完全等价(含单实例锁/托盘/日志初始化)
    from auto_qb.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
