// @ts-check
import { expect, test } from '@playwright/test';
import { baseUrl, SKINS_ALL } from './harness.mjs';
import { collectRuntimeErrors, installRuntimeErrorGuard } from './lib/errors.mjs';

/**
 * flux 站点 chip 形状分层 + 三种 chip hover 辉光(计划 26-11-10-0921 W2 e2e 部分, R10/R9)
 *
 * **报障面**: flux 站点 chip 的 hover 辉光「仅显示一侧或两侧」—— 根因 = 控件层 clip-path
 * 裁 box-shadow(console_hub.css 硬知识「切角与发光是死敌」): .site-chip 本体持 3px 微切角
 * polygon, hover 时 fx-mount.css 挂的 --fx-glow-stack 四边辉光被本体裁剪成两侧。W1(399bdb2e)
 * 把切角从本体挪到 ::before 绘制层(fx-mount.css 文件尾「站点 chip 形状分层」段), 本体
 * clip-path 覆盖为 none。**为什么必须真浏览器量**: clip-path 裁的是绘制输出, 静态守阵
 * (test_webui_static_skins_skin.py::test_frontend_fx_site_chip_shape_layering)只读文件文本,
 * 看不见级联胜负(components.css:332 的本体 polygon 若在链尾重新胜出, 文本守阵无感)。
 *
 * flux 不在 e2e 默认 SKINS(['prism','atlas'], harness.mjs:102) —— 本 spec 显式取
 * SKINS_ALL 里的 flux(不改 SKINS 默认值, 运行时长不翻倍), 对齐计划 R10 的兜底口径。
 *
 * **主判据 = 修复前后才变化的 computed 值**(每条都能独立抓回退):
 *   a. .site-chip 本体 getComputedStyle(el).clipPath === 'none'(本体重新持裁剪 = 辉光
 *      被整圈裁掉, 用户报障回归; 把 clip-path 放回本体 ⇒ 本条红, 已实测);
 *   b. ::before 的 clipPath 含 'polygon(3px'(切角在绘制层; 改坏 polygon 3px→4px ⇒ 红,
 *      已实测)。Chrome 序列化会把 `3px 0` 补成 `3px 0px`, 前缀 `polygon(3px` 不受影响。
 *
 * **旁证(不得当修复判据)**: clip-path 裁剪不改 computed box-shadow, 且 W1 修复前三种 chip
 *   已同挂 --fx-glow-stack(fx-mount.css 媒体块内共用一条 hover 规则)—— box-shadow 的
 *   computed 值在修复前后恒等, 回滚 W1 该值仍绿, 所以只能作旁证:
 *   - glass(默认 preset)hover 时三种 chip(.cat-chip/.tag-chip/.site-chip, 非 .f-on)的
 *     boxShadow 非空(not 'none')且彼此逐字一致 —— 三条 hover 规则同消费一个 --fx-glow-stack,
 *     任一 chip 的辉光配方被单独改坏(ink 重挂/层数增减)即红;
 *   - crisp preset 下 hover 的 boxShadow 各层 alpha 全 0(供给面全关)—— Chrome 不把全透明
 *     shadow 塌缩成 'none'(实测 = color(srgb 0 0 0 / 0) 四层), 故断言「每层 alpha=0」而非
 *     字面 'none';
 *   - .f-on(该值已在筛选中)下 hover 的 boxShadow === 'none' —— hover 规则 :not(.f-on)
 *     显式排除选中态, 选中 chip 不吃辉光。
 */

/* 本 spec 只对 flux 有意义: fx 三件与 data-fx-preset 只存在于 flux(D14 隔离拍板),
 * 三旧皮肤既无 fx-mount.css 也没有 data-fx-preset 属性, 主判据在其它皮肤恒不成立。 */
const FLUX = SKINS_ALL.filter((skin) => skin === 'flux');

/** 主判据采样的 site-chip 数上限: 桩 300 种子下 torrents 页 ~22 个, 全量断言不设上限也
 * 是一次性 evaluate; 仍给上限防未来种子数放大后断言变慢。 */
const SITE_CHIP_SAMPLE = 24;

/** 打开 flux 种子页(三种 chip 都在平铺行的列里: site/category/tags)。 */
async function openTorrents(page) {
  await page.goto(`${baseUrl()}/flux/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#app')).not.toHaveAttribute('v-cloak', { timeout: 15_000 });
  await page.click('nav.tabs [data-view="torrents"]');
  await expect(page.locator('.group-row.torrent-row').first()).toBeVisible({ timeout: 30_000 });
}

/**
 * 把指针真放进某个 chip(表列可横向滚出视口 ⇒ 先 scrollIntoView; 被吸顶/遮挡时逐个试到
 * `:hover` 成立为止, 探不到返回 null —— 宁可失败也不要在没悬停的样本上"验通过",
 * 手法对齐 main-table-pinned-hover.spec.mjs 的 hoverRow)。命中后等 boxShadow 计算值
 * **稳态**(连续三拍全等, 拍距 150ms, 静默 >= 300ms > box-shadow 过渡 --dur-fast glass
 * 140ms —— 手法对齐 main-table-pinned-selected.spec.mjs 的 awaitBgsStable「连续三拍」,
 * 不用固定睡等赌过渡走完: 过渡期 getComputedStyle 拿到的是中间值, 睡短了读到中间值,
 * 睡长了白耗; 三拍全等对任何过渡时长都成立, 过渡不落定则 poll 超时红)再返回终值。
 */
async function hoverChip(page, sel) {
  const chips = page.locator(sel);
  const n = Math.min(await chips.count(), 12);
  for (let i = 0; i < n; i++) {
    const chip = chips.nth(i);
    await chip.scrollIntoViewIfNeeded().catch(() => {});
    const box = await chip.boundingBox();
    if (!box || box.height < 4 || box.width < 4) continue;
    const x = Math.min(Math.max(box.x + box.width / 2, 8), 1432);
    const y = Math.min(Math.max(box.y + box.height / 2, 8), 892);
    if (x !== box.x + box.width / 2 || y !== box.y + box.height / 2) continue; // 钳到视口外 = 没滚进来, 换下一个
    await page.mouse.move(x, y);
    const hit = await page.evaluate(
      ({ sel, idx }) => !!document.querySelectorAll(sel)[idx]?.matches(':hover'),
      { sel, idx: i },
    );
    if (hit) {
      const readShadow = () => page.evaluate(
        ({ sel, idx }) => {
          const el = document.querySelectorAll(sel)[idx];
          return { cls: el.className, shadow: getComputedStyle(el).boxShadow };
        },
        { sel, idx: i },
      );
      const seq = [];
      await expect.poll(async () => {
        seq.push(await readShadow());
        if (seq.length > 3) seq.shift();
        return seq.length === 3 && seq[0].shadow === seq[1].shadow && seq[1].shadow === seq[2].shadow;
      }, { timeout: 5_000, intervals: [150] }).toBe(true);
      return seq[seq.length - 1];
    }
  }
  return null;
}

/**
 * shadow 串逐层判「每层 alpha 全 0」(crisp 供给面全关的形态, 见文件头旁证段注)。
 * 契约 = **每一层**都必须采到 alpha 且为 0: 按顶层逗号切层(rgb()/color() 内的逗号在
 * 括号里, 深度 0 才是层界), 只对整串做 alpha 统计会把不带 alpha 段的层漏掉 —— Chrome
 * 把全不透明色序列化成 rgb(r, g, b) 无 alpha 段, --fx-glow-stack 公式日后若直挂实色层,
 * 漏检层就是可见实色层, 不允许。采不到 alpha 的层(含 rgb() 形态/解析不出颜色的怪层)
 * 一律判 false 红 —— 宁可红也不要在不可见性上给假信心。
 */
function allLayersTransparent(shadow) {
  const layers = [];
  let depth = 0, layer = '';
  for (const ch of String(shadow)) {
    if (ch === '(') depth++;
    if (ch === ')') depth--;
    if (ch === ',' && depth === 0) { layers.push(layer); layer = ''; continue; }
    layer += ch;
  }
  if (layer.trim()) layers.push(layer);
  if (!layers.length) return false;
  return layers.every((l) => {
    // alpha 段两种序列化形态都认: color(srgb r g b / a) 的 "/ a)" 与 rgba(r,g,b,a) 的尾参
    const alphas = [...l.matchAll(/\/\s*([\d.]+)\s*\)/g)].map((m) => Number(m[1]));
    const rgba = l.match(/rgba\([^)]*,\s*([\d.]+)\s*\)/);
    if (rgba) alphas.push(Number(rgba[1]));
    return alphas.length > 0 && alphas.every((a) => a === 0);
  });
}

for (const skin of FLUX) {
  test.describe(`flux 站点 chip 形状分层与辉光 ${skin}`, () => {
    installRuntimeErrorGuard(test);

    test(`主判据: site-chip 本体无 clip-path, 切角 polygon(3px 在 ::before 绘制层 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openTorrents(page);

      const rows = await page.evaluate((cap) => {
        const chips = [...document.querySelectorAll('.site-chip')].slice(0, cap);
        return chips.map((el) => ({
          cls: el.className,
          body: getComputedStyle(el).clipPath,
          before: getComputedStyle(el, '::before').clipPath,
        }));
      }, SITE_CHIP_SAMPLE);

      expect(rows.length, '种子页没有 site-chip(站点列被移出默认列集? 结构变了)').toBeGreaterThan(0);
      for (const r of rows) {
        // a. 本体不再裁剪 —— 重新持 clip-path 时 box-shadow 辉光被整圈裁掉(报障回归)
        expect(r.body, `site-chip 本体又持 clip-path(${r.body}, ${r.cls}) —— 控件层裁剪会把 ` +
          'hover 辉光整圈裁掉, 用户报「辉光仅显示一侧或两侧」回归(计划 26-11-10-0921 主判据 a)')
          .toBe('none');
        // b. 切角在绘制层 —— polygon 漂移/丢失 = 3px 微切角视觉消失(R3「逐字恢复」拍板被推翻)
        expect(r.before, `site-chip::before 缺切角 polygon(${r.before}, ${r.cls}) —— ` +
          '切角绘制层丢失/漂移, 3px 微切角视觉不再由 ::before 供给(计划 26-11-10-0921 主判据 b)')
          .toContain('polygon(3px');
      }
    });

    test(`旁证: hover 辉光三 chip 一致 / crisp 全透明 / .f-on 无辉光 @fast (${skin})`, async ({ page }) => {
      collectRuntimeErrors(page);
      await openTorrents(page);

      // glass(默认 preset): 三种 chip 逐个真悬停, 悬停态各自读 boxShadow(一次只能 hover
      // 一个元素, 三个值是先后采的), 再对账一致。
      const hovered = {};
      for (const kind of ['site-chip', 'tag-chip', 'cat-chip']) {
        const hit = await hoverChip(page, `.${kind}:not(.f-on)`);
        expect(hit, `.${kind} 指针没能落进任何 chip(列滚出视口/遮挡?) —— 不能在无悬停样本上判绿`)
          .not.toBeNull();
        expect(hit.shadow, `.${kind} hover boxShadow 为 none —— 辉光规则整条丢失(fx-mount.css ` +
          '媒体块内三种 chip 共用的 hover 规则被删/选择器改坏?)').not.toBe('none');
        hovered[kind] = hit.shadow;
      }
      expect(hovered['tag-chip'], 'tag-chip 与 site-chip hover 辉光不一致 —— 三种 chip 应同消费 ' +
        '一个 --fx-glow-stack, 任一被单独改坏即此红(旁证: 值修复前后恒等, 不作主判据)')
        .toBe(hovered['site-chip']);
      expect(hovered['cat-chip'], 'cat-chip 与 site-chip hover 辉光不一致 —— 三种 chip 应同消费 ' +
        '一个 --fx-glow-stack, 任一被单独改坏即此红(旁证: 值修复前后恒等, 不作主判据)')
        .toBe(hovered['site-chip']);

      // crisp preset: 供给面全关(glow 0px / ink transparent), hover 的 boxShadow 各层 alpha
      // 全 0 —— Chrome 不把全透明 shadow 塌缩成 'none', 故按「逐层 alpha=0」断言(文件头段注)。
      await page.evaluate(() => document.documentElement.setAttribute('data-fx-preset', 'crisp'));
      const crisp = await hoverChip(page, '.site-chip:not(.f-on)');
      expect(crisp, 'crisp 下 site-chip 没能悬停(前一步滚动位变了?)').not.toBeNull();
      expect(allLayersTransparent(crisp.shadow),
        `crisp preset 下 hover 仍有非透明辉光层(${crisp.shadow}) —— 风格供给面全关档漏光`)
        .toBe(true);
      await page.evaluate(() => document.documentElement.setAttribute('data-fx-preset', 'glass'));

      // .f-on(值已在筛选中): 点击 cat-chip 走真实筛选链路, hover 规则 :not(.f-on) 排除选中态。
      // 用 cat-chip 做 f-on 样本: 基线无 box-shadow(border 供给), 'none' 断言不被基线 inset 干扰。
      const cat = page.locator('.cat-chip:not(.f-on)').first();
      await cat.scrollIntoViewIfNeeded().catch(() => {});
      await cat.click();
      await expect(page.locator('.cat-chip.f-on').first()).toBeVisible({ timeout: 5_000 });
      const fOn = await hoverChip(page, '.cat-chip.f-on');
      expect(fOn, '.f-on cat-chip 没能悬停').not.toBeNull();
      expect(fOn.shadow, '.f-on chip hover 仍有辉光 —— hover 规则的 :not(.f-on) 排除分支被改坏, ' +
        '选中态不该吃辉光').toBe('none');
    });
  });
}
