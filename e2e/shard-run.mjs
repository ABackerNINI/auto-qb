// @ts-check
/**
 * S5 e2e 并行化(计划 26-11-05-0118 §04 S5 / §06 D14)的 shard 包装器 —— shard 数参数化的单点。
 *
 * 用法(npm script 已带 fast 门禁口径, index/total 用 `--` 透传):
 *   npm run test:e2e:fast:shard -- --index 1 --total 3
 *   npm run test:e2e:fast:shard -- --index 2 --total 3 --headed   # 其余参数原样透传 playwright
 *
 * 做三件事, 缺一不可:
 *  1. 置 `E2E_SHARD_TOTAL` —— playwright.config.mjs 据此 testIgnore 掉 CPU 敏感量具 spec
 *     (perf / drawer-content-perf / traffic-fx-frames, 并发下量具数字会漂); 它们由 `npm run test:e2e:perf-serial`
 *     串行补跑。env 与 `--shard` 同源设置, 不存在"shard 了但没排除"的漂移窗口。
 *  2. 恒传 `--shard=index/total` 给 playwright —— 每个 shard 是独立进程, 各自拉起独立
 *     webServer(桩 `--port 0` OS 分配, 互不冲突; `reuseExistingServer:false` 保留)。
 *  3. 直接调 `node node_modules/playwright/cli.js`(不走 npx): Windows 上 spawnSync('npx')
 *     走 cmd 包装, 与 e2e/global-teardown.mjs 记的 stdio/进程树问题同源, 少一层包装少一类坑。
 *
 * shard 数怎么定: 先 S4 清完固定睡等再按实测时长定(§06 D14 原文) —— 见
 * memory-bank/plans/26-11-05-0118-plan-flaky-test-governance.html §04 S5 的三档实测对照。
 *
 * 直跑 `npx playwright test --shard=x/N` 而不经本包装器是允许的(串行全量口径不变), 但那时
 * CPU 敏感 spec 不会被排除 —— 想要"排除 + 补跑"的完整形态必须走本包装器。
 */
import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const CLI = path.join(ROOT, 'node_modules', 'playwright', 'cli.js');
if (!existsSync(CLI)) {
  console.error(
    `[e2e:shard] playwright cli 不存在: ${CLI}\n` +
      '  NEXT: 先装依赖(uv 同步不覆盖 node; npm install / 按仓库既有口径装 playwright)'
  );
  process.exit(2);
}

/* 参数解析: 只认 --index/--total(带值), 其余原样透传 —— 不认识也不拦(playwright 自己裁决)。 */
const argv = process.argv.slice(2);
const passthrough = [];
let index = null;
let total = null;
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--index' && i + 1 < argv.length) {
    index = Number(argv[++i]);
  } else if (argv[i] === '--total' && i + 1 < argv.length) {
    total = Number(argv[++i]);
  } else {
    passthrough.push(argv[i]);
  }
}

/* fail fast: index/total 缺失或非法立即红, 不给"全量跑了一遍才发现 shard 没生效"的机会。 */
const bad = [];
if (!Number.isInteger(index) || index < 1) bad.push(`--index ${argv[argv.indexOf('--index') + 1] ?? '?'}(须为 >=1 整数)`);
if (!Number.isInteger(total) || total < 1) bad.push(`--total ${argv[argv.indexOf('--total') + 1] ?? '?'}(须为 >=1 整数)`);
if (Number.isInteger(index) && Number.isInteger(total) && (index > total || total === 0))
  bad.push(`--index ${index} > --total ${total}`);
if (bad.length) {
  console.error(`[e2e:shard] 参数非法:\n  - ${bad.join('\n  - ')}\n` + '  NEXT: npm run test:e2e:fast:shard -- --index 1 --total 3');
  process.exit(2);
}

/* child_process env 注入 + CLI 组装(见上"做三件事")。 */
const env = { ...process.env, E2E_SHARD_TOTAL: String(total) };
const args = [CLI, 'test', ...passthrough, `--shard=${index}/${total}`];
console.log(`[e2e:shard] shard ${index}/${total} | testIgnore CPU 敏感 spec 生效 | playwright ${passthrough.join(' ') || '(默认口径)'}`);
const result = spawnSync(process.execPath, args, { stdio: 'inherit', env, cwd: ROOT });
process.exitCode = result.status ?? 1;
