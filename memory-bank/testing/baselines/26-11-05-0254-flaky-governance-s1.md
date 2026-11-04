# 5364 passed + 2 skipped —— flaky 治理 S1 基建(clock 单点/统一假钟/wait_until 收编/四类守阵)后全量基线

> 摘要: flaky 治理 S1 基建(clock 单点/统一假钟/wait_until 收编/四类守阵)后全量基线
> 基线时间: 2026-11-05 02:54
**Refs:** memory-bank/plans/26-11-05-0118-plan-flaky-test-governance.html

## 验收数字

- `commands run test.full` 实测(2026-11-05 03:0x, Windows 本机, 终态连跑两轮同数字):
  - 覆盖率 TOTAL 表: **TOTAL 24472 / 52 miss / 99%**(statements 24472, missed 52, branch 8386, brMiss 33)
  - 汇总行: **5364 passed, 2 skipped in 126.59s (0:02:06)**(同数字另两轮 117.72s/149.29s, 波动为机器负载)
  - 口径: 全量 pytest 含覆盖率报表(-n 8); 2 skipped 为平台条件跳过; 数字为该次运行实测, 非均化
  - 新增守阵 4 条(tests/test_flaky_timing_guards.py) + 新单点行为阵 9 条(tests/test_clock.py)全绿; 红绿双验: 四类守阵各植入一枚违例均当场红, 清除后复绿

## 本改动面

- `src/auto_qb/infra/clock.py`(新增): 生产时钟单点 —— `Clock` protocol(now()/monotonic()) + `SystemClock` + 进程级 `SYSTEM_CLOCK` 单例; S2 起生产代码唯一合法取时入口, 本阶段只建点不改造调用方。
- `tests/clock.py`(新增): 测试侧时间控制单点 —— 统一假钟 `FakeClock`(advance/freeze, 兼容可调用与 time() 两种旧注入形态) + `fake_clock` 夹具(函数级自动复位, 不做模块级共享) + `wait_until` 条件轮询单一实现; 模块 docstring 带用法规范。
- `tests/helpers.py`: 两处旧轮询雏形收编 —— `drive_skip` 内联循环改走 `wait_until` 单点; 旧 `wait_until` 改为 clock 单点再导出(既有 `from helpers import wait_until` 调用点不破, S3 迁移后删别名)。
- `tests/conftest.py`: 注册 `fake_clock` 夹具进全局命名空间(用例直接 `def test_x(fake_clock)`)。
- `tests/flaky_allowlist.py`(新增): 四类守阵白名单单点 —— 存量违例集中登记(键=文件, 值={行文本全等: 条数}), 每文件条目带清理归属理由; 守阵两侧对账(新增未登记红 + 条目失效红), S2/S3/S4 清理后只减不涨。实测存量: tests/ 裸 time.sleep 27 处/15 文件、e2e waitForTimeout 91 处/20 文件、src/ 裸取时 161 处/43 文件、bind 位固定端口 0 处。
- `tests/test_flaky_timing_guards.py`(新增): 四类守阵(① tests 裸 sleep ② e2e waitForTimeout ③ src 裸取时(clock.py 豁免) ④ bind 位固定端口) + 合成源活性探针红验内建(扫描逻辑退化即红)。
- `tests/test_clock.py`(新增): clock 单点行为回归阵 9 条(协议契合/advance-freeze 语义/夹具新鲜度/wait_until 快路径·超时·终判·别名)。
