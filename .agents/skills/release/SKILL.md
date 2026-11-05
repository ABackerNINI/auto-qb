---
name: release
description: '机械化发版管线: 触发词「发版」起跑的八步流水(提案→bump→提交→快进合并→CI门→tag→Release页), 机器算号+agent 改判留痕, major 永不自动, 版本号锚发布分支, tag/Release 页双远端。USE FOR: 用户说「发版」/「发布新版本」/「打 tag」时; 发版管线任一步的执行与排障。DO NOT USE FOR: 版本方案本身的问题(看 conventions/release.md 与计划 26-09-22-2318)、日常提交(那是 ship)、依赖版本巡检(那是 deps-upgrade)。'
user-invocable: true
---

# release:机械化发版管线

三层载体(通用性契约:脚本零项目事实, 移植改动面 = bump 配置 + commands 包 config + 口径文档):
- **规程面**(本文件):顺序/判断点/停手规则/降级路径/留痕要求;
- **机械面**:`.commands/release/` 包 task id 族, 薄引用 `scripts/` 本体;
- **口径面**:版本语义/major 判据/分支模型在 `<项目>/conventions/release.md`(项目侧单点)。

## 触发与边界

- 触发词「**发版**」(与「提交/入库/推上去」同列显式触发清单):说一次, agent 全程跑完不再回问;
- 平时**不自主发版**——收口时口头提议不算机制;
- **major 永不自动**:决策表只产 patch/minor;major 只在用户显式拍板三判据全中后, `release.suggest --major` 显式旗标放行。

## 管线八步(每步 = task id + 判断点)

| 步 | task id | 机械面 | agent 判断点 |
|---|---|---|---|
| ① | `my-commit-flow.sync` | 同步(硬步骤) | — |
| ② | `test.full` + `dev.e2e` + `real.suite`(`real.guard` 前置)+ `test.linux`(视平台改动) | 本地全测门;`mutants.status` 只核验不进门 | 门红即停, 修完重走 |
| ③ | `release.suggest` → 改判 → `release.bump` → (改 CHANGELOG 草稿) | 机器提案 + bump-my-version 改文件 + 刷元数据 | **改判窗**:可改档, 必留痕(CHANGELOG 注记 + commit body 一句原因);补发首版等特例在此定 |
| ④ | `ship.commit`(🔖 专用发版提交, bump+CHANGELOG 同笔) | 闸门 + 提交 + 同步 + 推送 | 提交信息带 gitmoji 与动机/实测 |
| ⑤ | `release.merge` ×2(先 `--remote gitee` 后 `--remote github`) | ff-only 显式 ref 推发布分支 + ls-remote 核验 | 分叉/非快进 → **停手要人**, 不自动 merge/rewind;github 这跑是发版轮唯一非静默推送(CI 门依赖它, ship.push 的镜像推送只推 develop 且尽力而为不保证), 失败即停 |
| ⑥ | `release.ci-gate` | GitHub check-runs 轮询至全绿 | 红 → 停 tag 前, 修复提交后重走(可重入);超时/零 run → 停手报告 |
| ⑦ | `release.tag` | tag 锚发版提交 + 显式 ref 双远端推送 + 核验 | tag 名 `vX.Y.Z` 不带 hash;已存在 → 校验指向而非重建 |
| ⑧ | `release.build` + `release.page` | wheel 构建(BUILD_ID 侧车)+ gitee 主线/github 镜像 Release 页(纯注记) | gitee token 未配 → 降级过渡(WARN 不失败, 口径=tag+CHANGELOG 即发布);镜像失败只报告一次;发布件停在 dist/ 由用户取用, 附件上传(API 面待核)留阶段 2 |

收尾:切最后一刀 `kb.wrap` + 结果行回执(版本号/新 tag/页地址)。

## 停手清单(任何一条命中即停, 报告要人)

1. 本地全测门红(②);
2. 发布分支非快进/分叉(⑤);
3. CI 红或超时未收敛、全程零 run(⑥);
4. tag 指向冲突(本地/远端已有但指向 ≠ 发版提交)(⑦);
5. gitee 建页失败**且 token 已配置**(⑧——token 未配是降级不是失败)。

## 降级路径

- **gitee token 未配**:Release 页降级过渡, WARN 记入当轮报告;token 配好后补建(重跑 `release.page` 即可, 幂等);
- **GitHub API 限额/不可达**(`ci_gate` rc=3):停手报告, 不换代理不重试;
- **github 镜像 push/Release 失败**:只报告一次, 不重试不回滚主线(唯一例外口径:发版轮 develop/master 推送必须成功 —— develop 由 `ship.push` 保证, **master 的 github 推送由步骤 ⑤ 的第二跑保证**, 二者失败都即停)。

## 幂等重入(黄金法则 1)

管线每步独立 rc、可重入:已完成的步校验后跳过——tag 已存在校验指向、Release 页已存在按重入、merge 远端已同点按重入;CI 门重跑只是再轮询。修复后从**停手的那一步**继续, 不从头重跑。

## 陷阱与约定(实施实证)

- **wheel 构建必须走 `commands run release.build`**(内部即 `uv build` 加 `--wheel` 限定):全量 `uv build` 是 sdist→wheel 两段式, wheel 从解压 tarball 构建(无 .git), BUILD_ID 会被钩子静默跳过 —— 发布件溯源断裂;
- CHANGELOG 草稿由 `release.suggest --emit-changelog` 生成, agent 精修;历史无 tag 区间用提交哈希区间;
- 版本号是兼容性契约不是进度条:补发大积压仍按 delta 算号, 积压量由 CHANGELOG 承载;
- 本 skill 的 `.md` 面会被命令漂移检查扫描——文档内命令一律写 task id 形态(`commands run <id>`)。
