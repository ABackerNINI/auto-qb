// @ts-check
import { expect, test } from '@playwright/test';
import { SKINS } from './harness.mjs';
import { installRuntimeErrorGuard } from './lib/errors.mjs';
import { openApp } from './lib/gestures.mjs';
import { readInst, withVm } from './lib/vm.mjs';

/**
 * 设置页 · 限速曲线 period 自动排序 —— 前端层(计划 26-11-18-0801 S4, 拍板 D9/D10/D11)。
 *
 * 断言面(对齐计划 §04 S4 行 e2e 验收判据):
 *   1) 新增定位插入(D9): 「添加曲线」默认 1D(day 键)按天数定位插入(有序列表下 = 插最前),
 *      否决尾部追加; 插入后自动展开, openCurves 按实际插入下标记录、其后条目序号后移保展开态;
 *   2) 改值提交重排(D10): period 输入 @input 逐键写树不动; @change(失焦/回车)提交时整段重排,
 *      openCurves 按条目身份跟随搬移(展开的条目重排后仍在展开, 序号跟人走);
 *   3) 解析失败放弃(D11): 任一 period 解析不了 -> 整段放弃重排; 新增退回尾部追加;
 *   4) 乱序树渲染有序(GET 面整链): 乱序草稿树经真实「保存并应用」落盘 -> 保存后重拉
 *      GET /api/config(后端 _sort_tree_curve_periods, S3) -> 编辑器渲染有序。
 *
 * blur 口径: Playwright fill() 后接 press('Tab') 真实失焦触发 change(Enter 会冒泡进曲线头
 * @keyup.enter 折叠手势, 逐键交互不用; D10 末段特意用 Enter 一条 —— 钉处理器对回车提交的
 * 焦点收口, 折叠副作用是既有行为不在断言面)。
 *
 * vm 探针口径(lib/vm.mjs D4 守则): 曲线树序/openCurves 是 vm 内部状态(草稿不落盘, 无 DOM
 * 取径), 读数属第 2 类; 其余交互一律真实手势。唯一例外是「乱序草稿树」的**注入**(第 1 类,
 * 注入/复原桩态): UI 手势造不出乱序盘面(新增/改值两条路径都已是排序写入), 乱序盘面的现实
 * 入口只有手改 config.yml(D3 辅入口) —— 注入草稿树 + 真实保存手势即等价复现该场景。
 */

test.describe('设置页 · 限速曲线 period 排序(S4)', () => {
  installRuntimeErrorGuard(test);

  /** 树内曲线 period 序(vm 内部探针, 第 2 类: 草稿树无 DOM 之外的取径)。 */
  const treePeriods = (page) =>
    readInst(page, `(vm.cfg.tree.config.global_speed_limit_curve && vm.cfg.tree.config.global_speed_limit_curve.curves || [])
      .map((x) => (x.curve && x.curve.period) || '')`);
  /** 展开态映射(序号 -> 是否展开; JSON 序列化便于整对象断言)。 */
  const openMap = (page) => readInst(page, 'JSON.stringify(vm.cfg.openCurves)');
  /** 头部徽章展示的 period 序(DOM 渲染序)。 */
  const badgeTexts = (page) => page.locator('.hb-curve-hd .hb-badge').allInnerTexts();
  /** 第 i 条曲线头部的 period 输入框。 */
  const periodInput = (page, i) => page.locator('.hb-curve').nth(i).locator('.hb-curve-hd input.hb-input');
  /** 等待树序收敛到手势后的期望值(Vue 渲染是异步微任务, 单次读数有竞态窗口)。 */
  const expectTree = (page, want) => expect.poll(() => treePeriods(page)).toEqual(want);
  const expectBadges = (page, want) => expect.poll(() => badgeTexts(page)).toEqual(want);

  /** 打开设置页「流量与限速」卡(卡片真实手势; 曲线区折叠缺省展开, 见 hubSubOpen)。 */
  async function openCurveCard(page) {
    await page.locator('nav.tabs-right button').first().click();
    await expect(page.locator('.hb-grid .hb-card').first()).toBeVisible({ timeout: 20_000 });
    await page.locator('.hb-card').filter({ has: page.locator('.hb-card-t', { hasText: '流量与限速' }) }).click();
    await expect(page.locator('.hb-sub-toggle', { hasText: '限速曲线' })).toBeVisible({ timeout: 15_000 });
  }

  /** 干净开局: 删草稿树里的曲线段(防盘面/此前用例残留), 展开态一并清零, 再真实手势启用。 */
  async function cleanSlate(page) {
    await withVm(page, `delete vm.cfg.tree.config.global_speed_limit_curve; vm.cfg.openCurves = {};`);
    await expect(page.getByRole('button', { name: '启用限速曲线' })).toBeVisible({ timeout: 15_000 });
    await page.getByRole('button', { name: '启用限速曲线' }).click();
    await expect(page.getByRole('button', { name: '＋ 添加曲线' })).toBeVisible({ timeout: 15_000 });
  }

  /** 改第 i 条 period 并失焦提交: fill 真实写值(@input 逐键写树) + Tab 失焦触发 @change 重排。 */
  async function commitPeriod(page, i, value) {
    await periodInput(page, i).fill(value);
    await periodInput(page, i).press('Tab');
  }

  for (const skin of SKINS) {
    test(`[${skin}] D9 新增定位插入: 1D 插最前 + 自动展开 + 其后条目展开态保住 @fast`, async ({ page }) => {
      await openApp(page, skin);
      await openCurveCard(page);
      await cleanSlate(page);

      /* 造 [7D, MONTH](逐条添加 + 改值提交; 单条时无重排面, 双条时 1D 恒插最前): */
      await page.getByRole('button', { name: '＋ 添加曲线' }).click();
      await expectTree(page, ['1D']);
      await commitPeriod(page, 0, '7D');
      await expectTree(page, ['7D']);
      await commitPeriod(page, 0, 'MONTH');
      await expectTree(page, ['MONTH']);

      /* 加 1D -> day 键最小 -> 插最前; 原第 0 条(MONTH, 展开)序号后移到 1, 展开态跟人走 */
      await page.getByRole('button', { name: '＋ 添加曲线' }).click();
      await expectTree(page, ['1D', 'MONTH']);
      expect(await openMap(page)).toBe(JSON.stringify({ 0: true, 1: true }));
      await expectBadges(page, ['1D', 'MONTH']);

      /* 再把 1D 改成 7D 造 [7D, MONTH], 加 1D 仍插最前(多元素列表的定位插入) */
      await commitPeriod(page, 0, '7D');
      await expectTree(page, ['7D', 'MONTH']);
      await page.getByRole('button', { name: '＋ 添加曲线' }).click();
      await expectTree(page, ['1D', '7D', 'MONTH']);
      expect(await openMap(page)).toBe(JSON.stringify({ 0: true, 1: true, 2: true }));
      await expectBadges(page, ['1D', '7D', 'MONTH']);
    });

    test(`[${skin}] D10 改值失焦重排: 整段重排 + openCurves 按条目身份跟随搬移 @fast`, async ({ page }) => {
      await openApp(page, skin);
      await openCurveCard(page);
      await cleanSlate(page);

      /* 造 [1D, 1D, MONTH](三条 1D 中间那条下一步改值区分开), 再把中间条改成 7D */
      await page.getByRole('button', { name: '＋ 添加曲线' }).click();
      await commitPeriod(page, 0, 'MONTH');
      await page.getByRole('button', { name: '＋ 添加曲线' }).click();
      await expectTree(page, ['1D', 'MONTH']);
      await page.getByRole('button', { name: '＋ 添加曲线' }).click();
      await expectTree(page, ['1D', '1D', 'MONTH']);
      await commitPeriod(page, 1, '7D');
      await expectTree(page, ['1D', '7D', 'MONTH']);
      expect(await openMap(page)).toBe(JSON.stringify({ 0: true, 1: true, 2: true }));

      /* 展开态做成可鉴别: 收起第 0 条(1D), 第 1 条(7D)/第 2 条(MONTH)保持展开
       * (点标题文本, 落点避开 period 输入框的 @click.stop) */
      await page.locator('.hb-curve').nth(0).locator('.hb-curve-hd .bh-t').click();
      expect(await openMap(page)).toBe(JSON.stringify({ 0: false, 1: true, 2: true }));

      /* 第 0 条 1D -> 30D 失焦提交: (0,) -> (1,30), 7D(1,7) 升到最前 -> 整段重排为
       * [7D, 30D, MONTH]; 身份跟随: 7D(旧序 1, 展开)搬到 0 仍展开, 30D(旧序 0, 收起)搬到 1 仍收起 */
      await commitPeriod(page, 0, '30D');
      await expectTree(page, ['7D', '30D', 'MONTH']);
      expect(await openMap(page)).toBe(JSON.stringify({ 0: true, 1: false, 2: true }));
      await expectBadges(page, ['7D', '30D', 'MONTH']);

      /* 回车提交路径(评审 minor 收口): Enter 触发 change 时焦点仍在原输入框(下标 key 复用
       * 同一 DOM 节点), 重排后该框显示的是另一条的 period —— 处理器提交重排后主动 blur,
       * 断言焦点已离开(继续键入不再写错条目); Enter 同时冒泡进曲线头折叠(既有行为, 不在
       * 断言面)。7D -> 100D: (1,7) -> (1,100), 30D(1,30) 升到最前 = 真重排(必走 blur 收口;
       * 选值若不触发重排则早退分支不 blur, 测不到) */
      await periodInput(page, 0).fill('100D');
      await periodInput(page, 0).press('Enter');
      await expectTree(page, ['30D', '100D', 'MONTH']);
      await expect(periodInput(page, 0)).not.toBeFocused();
    });

    test(`[${skin}] D11 解析失败放弃: 重排整段放弃 + 新增退回尾部追加 @fast`, async ({ page }) => {
      await openApp(page, skin);
      await openCurveCard(page);
      await cleanSlate(page);

      /* 造 [1D, 7D]: */
      await page.getByRole('button', { name: '＋ 添加曲线' }).click();
      await commitPeriod(page, 0, '7D');
      await page.getByRole('button', { name: '＋ 添加曲线' }).click();
      await expectTree(page, ['1D', '7D']);

      /* 第 1 条 7D -> XYZ 失焦: 键解析不了 -> 整段放弃重排, 树保持 @input 写下的原序 */
      await commitPeriod(page, 1, 'XYZ');
      await expectTree(page, ['1D', 'XYZ']);

      /* 再新增: 存在解析不了的 period -> 放弃定位退回尾部追加(哪怕新 1D 的键本可排进前面) */
      await page.getByRole('button', { name: '＋ 添加曲线' }).click();
      await expectTree(page, ['1D', 'XYZ', '1D']);
      expect(await openMap(page)).toBe(JSON.stringify({ 0: true, 1: true, 2: true }));

      /* 非字符串 period(评审 minor: typeof 守门)—— UI 手势打不出非字符串标量, 注入复现
       * 手改/粘贴面(第 1 类 evaluate, 同文件头理由); 非字符串条目放第 0 位, 让强转路径的
       * day 键有前位可抢: 修复前 String(['DAY'])==='DAY' 误解析出 day 键, 与新 1D 同键
       * cmp 连续越过后插到中间 -> [['DAY'],'1D','7D'] / openCurves {1:true}; 修复后 keys
       * 含 null -> 整段放弃退回尾部追加 -> [['DAY'],'7D','1D'] / openCurves {2:true}。
       * 树序与展开态两断言在两条路径下取值不同, 门被回退测试必红(首版注入 [1D,['DAY']]
       * 两路径结果全同, 无甄别力, 复评点名修正)。 */
      await withVm(page, `
        vm.cfg.tree.config.global_speed_limit_curve.curves = [
          { curve: { period: ['DAY'] } },
          { curve: { period: '7D' } },
        ];
        vm.cfg.openCurves = {};
      `);
      await page.getByRole('button', { name: '＋ 添加曲线' }).click();
      await expectTree(page, [['DAY'], '7D', '1D']);
      expect(await openMap(page)).toBe(JSON.stringify({ 2: true }));
    });

    test(`[${skin}] 乱序树渲染有序: 乱序草稿树真实保存 -> 重拉 GET 后端排序 -> 渲染有序 @fast`, async ({ page }) => {
      await openApp(page, skin);
      await openCurveCard(page);
      await cleanSlate(page);

      /* 注入乱序曲线段(第 1 类 evaluate, 理由见文件头): 手改 config.yml 场景的等价复现。
       * 每条带最小合法档位(校验要求 upload/download 至少一个非空列表, 保存才过得去)。 */
      await withVm(page, `
        vm.cfg.tree.config.global_speed_limit_curve = {
          enabled: 'true',
          interval: '60S',
          curves: [
            { curve: { period: 'MONTH', upload_curve: [{ '10GiB': { upload_speed_limit: '6MiB/s' } }] } },
            { curve: { period: '1D', upload_curve: [{ '1GiB': { upload_speed_limit: '2MiB/s' } }] } },
            { curve: { period: '7D', upload_curve: [{ '5GiB': { upload_speed_limit: '4MiB/s' } }] } },
          ],
        };
        vm.cfg.openCurves = {};
      `);
      await expectBadges(page, ['MONTH', '1D', '7D']);  // 乱序盘面原样渲染(前端不偷排)

      /* 真实「保存并应用」: PUT 落盘(乱序) -> 保存后重拉 GET(_sort_tree_curve_periods 排序)
       * -> 编辑器工作对象即有序, 渲染随之有序(动机主面, 计划 D2/D4) */
      await page.locator('button', { hasText: '保存并应用' }).click();
      await expect(page.locator('.toast-wrap .toast.ok').first()).toContainText('已保存', { timeout: 20_000 });
      await expectBadges(page, ['1D', '7D', 'MONTH']);
      await expectTree(page, ['1D', '7D', 'MONTH']);
    });
  }
});
