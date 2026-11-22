# 平台差异与打桩: 六类「本机绿不算绿」判别法

> 摘要: `pitfalls/testing/patching.md`「判别法: 六类本机绿不算绿」节原文整体外迁 —— 判断一条失败是不是平台差异的六类判据(记账器越界 / 平台专属模块 / 真 socket / 路径 API / 路径归一化 / os.stat 桩)与以 `monkeypatch` 固定平台的处置。
> 触发: 判别法, 六类, 本机绿不算绿, 平台差异, monkeypatch, 固定平台, 路径归一化, os.stat 桩, 形态④

### 判别法: 六类"本机绿不算绿"

- **触发**: 判断一条失败是不是平台差异。
- **判别**: 凡是"**记账器判越界 / 平台专属模块导入 / 真实 socket 连接 / 平台相关的路径 API /
  路径存在性归一化(结尾点 · 空格 · 大小写, 见 ⑥) / 给 `os.stat` 打桩造三态
  (Windows 的 `os.path.exists` 是 C 内建、桩穿不透, 见 ⑦)**"这六类,
  本机绿**不算绿**。平台相关测试必须以 `monkeypatch` **固定平台**(测试主体是"平台逻辑"而非"当前真实平台");
  纯 Windows 行为(长路径 `\\?\` 前缀)直接断言在 Linux CI 上**必失败**。
- **处置**: 按上面各类分别用 `monkeypatch.setitem(sys.modules, …)` / 补 `dir_fd` 绝对路径 / patch 真实名字
  / 桩打到判定层(见 ⑦)。

**形态④ 平台相关的路径 API(`os.path.normcase` 在 Linux 是恒等函数)**: 触发/判别/处置(含
`sim_fsmock._key` 修法与 `sim_qb._norm` 同类未修现状)原文见 [patching-form-path-api.md](patching-form-path-api.md)。
