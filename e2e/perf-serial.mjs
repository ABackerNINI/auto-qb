// @ts-check
/**
 * CPU 敏感量具 spec 的**串行补跑**入口(计划 26-11-05-0118 §04 S5 / §06 D14)。
 *
 * shard 轮转(playwright.config.mjs 在 E2E_SHARD_TOTAL 下 testIgnore)把这两份 spec 排除了:
 *   - e2e/perf.spec.mjs           —— 量具节拍/CPU 时间断言(longtask/强制布局计数)
 *   - e2e/drawer-content-perf.spec.mjs —— mut 预算按 ~500ms 观察窗标定, 并发下数字会漂
 * 本脚本把它们收回串行口径跑绿, 与 shard 轮转相加 == 全量。
 *
 * 用法: npm run test:e2e:perf-serial [-- 透传 playwright 的额外参数]
 *
 * 门控档: E2E_TORRENTS 默认抬到 600 —— perf.spec.mjs 的「行窗口化生效」用例按
 * TORRENTS>500 门控, 默认 300 档整组 skip, 600 档才真跑(已显式设 E2E_TORRENTS 则尊重现值);
 * drawer-content-perf 用 page.route 自造千文件树, 不受该档影响。env 组合与桩形态的关系见
 * e2e/harness.mjs —— 本脚本只动种子数一档, 其余模式维度保持默认。
 *
 * 串行保证: 显式 delete E2E_SHARD_TOTAL(若残留会让 config 把这两份 spec 又 ignore 掉,
 * 等于白跑) —— 但这是防御, 正常使用里它只会在 shard 包装器的子进程 env 里出现。
 */
import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const CLI = path.join(ROOT, 'node_modules', 'playwright', 'cli.js');
if (!existsSync(CLI)) {
  console.error(
    `[e2e:perf-serial] playwright cli 不存在: ${CLI}\n` +
      '  NEXT: 先装依赖(按仓库既有口径装 playwright)'
  );
  process.exit(2);
}

const env = { ...process.env };
delete env.E2E_SHARD_TOTAL;
if (!env.E2E_TORRENTS) env.E2E_TORRENTS = '600';

const argv = process.argv.slice(2);
const args = [
  CLI,
  'test',
  'e2e/perf.spec.mjs',
  'e2e/drawer-content-perf.spec.mjs',
  ...argv,
];
console.log(
  `[e2e:perf-serial] CPU 敏感 spec 串行补跑 | E2E_TORRENTS=${env.E2E_TORRENTS} | ${argv.join(' ') || '(无附加参数)'}`
);
const result = spawnSync(process.execPath, args, { stdio: 'inherit', env, cwd: ROOT });
process.exitCode = result.status ?? 1;
