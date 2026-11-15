"""test_webui_static_ui_prefs 测试计划: 计划 26-11-14-0624 S4 —— ui_prefs 双清单登记闸守阵(D8/D11)

ui_prefs.js 顶层的 PREF_KEYS / PREF_EXCLUDED 是浏览器 localStorage/sessionStorage 键族的
完整对账面(D8): 新增存储键必须登记其一, 否则本守阵红(D11 拍板: 静态扫描, 不加运行时校验)。

扫描器口径(与 ui_prefs.js 头注「对账范围」同界):
- 扫描面 = static/ 全树递归的**全部 .js**(不按目录裁剪: `autoqb.ui.theme` 在 prism/js/theme.js、
  `gtm.spike.ack` 在 shared/dialogs.js, shared/ 之外一样在闸内); HTML 不扫(里面出现的键字面量
  是注释/standalone 页自用), .mjs 等(树里现无)同不扫。
- 收什么 = 代码位(先剥注释, 不被注释骗过)里**全匹配**族形态的字符串字面量: 点分族
  `autoqb.*` / `gtm.*` 与下划线族 `autoqb_*`。引号定界收双引号/单引号/**无插值反引号模板**
  三形态(回引 \\1; 带 `${...}` 插值的模板内容含插值字符, 天然不匹配)。const 单键定义
  (`const QB_FX_STORE_KEY = "..."`、对象字面量 QB_YAXIS_STORE_KEYS 等)不必单独跟使用点 ——
  定义里的字面量本身就在代码位, 全量收齐后由「每个扫到的键必须登记」统一裁决。
  !漏收是 D8 最危险失效形态, 故字面量形态宁滥勿缺; 唯一固有闸外是**动态构造键名**
  (字符串拼接/带插值模板 —— 不是完整字面量, 静态扫描天然看不见), 新增键请一律写完整字面量。
- 全匹配形态即闸界, 不需要黑名单: cookie `autoqb_ui`(boot.js `"autoqb_ui=" + skin`, 字面量
  带等号)不匹配; 事件名 `autoqb:*` 冒号族不匹配; standalone 页 fx/showcase.html 的 `fxsc.*`
  族不匹配且不在 .js。代价是**过宽方向**: 将来若有族形态前缀的非存储字符串(按约定不该有)
  会误红 —— 误红逼人显式处置, 好过漏收(与「零命中即红」同一保守取向)。
- 双清单侧独立提取: 按 `const PREF_KEYS = [` ... `];` 区间剥注释后取引号字面量(与扫描器
  同三形态), 与扫描器互不复用(两侧一致性守阵先例: webui_static_scan_js._scan_keys_serial_re)。
- 负例红绿双验(§04 S4 验收判据)用 **tmp 全树副本注入**: 比 monkeypatch 扫描面更端到端,
  连「扫描器能否找到新增文件/新增行」一起验; 不真改 static/ 生产文件。

实测口径(2026-11-14 grep): PREF_KEYS 18 键 / PREF_EXCLUDED 7 键(计划初版 16 + 实测新增
autoqb.ui.qbFx / autoqb.ui.kbdPersist, ui_prefs.js 双清单头注有记)。**故意不钉死精确计数**
—— D8 的登记口径是「登记进双清单即绿」, 钉死会让合法登记也红; 只钉下限防清单被整段清空。

## 测试计划(每个测试函数一条)
- test_registry_double_list_anchored: 双清单声明锚定 —— 两个区间声明都找得到(判据被改名/
  删除后守阵不许空转, 见 pitfall guard-dead-branch)、清单非空(下限 dead-guard: PREF_KEYS
  >= 10 / PREF_EXCLUDED >= 5)、单清单内无重复键、双清单交集为空(一键不得双登: 同时进
  bundle 与排除面语义矛盾)
- test_scanned_keys_all_registered: 主闸(真实树) —— 扫描器收齐 static/ 全部 .js 族形态存储键
  字面量, 每键必须 ∈ PREF_KEYS ∪ PREF_EXCLUDED 否则红(逐键带 文件:行); 反向对账: 每个登记
  键必须在使用面出现(死登记/拼写漂移红); 扫描零命中红(守阵不许空转)
- test_boundary_exclusions_not_in_gate: 闸外形态边界钉 —— 先锚定三类闸外字面量**真实存在
  于树里**(排除不许是"树里本来就没有"的假绿): cookie autoqb_ui(boot.js)、事件名
  autoqb:themechange(prism/js/theme.js)、fxsc.* 族(fx/showcase.html); 再断言扫描结果不含
  它们, 且全部命中落点都是 .js
- test_negative_unregistered_key_red_then_green: 负例红绿双验 —— tmp 全树副本注入四形态
  未登记键(点分 autoqb.ui.* 直写 / 下划线 autoqb_* 直写 / const 单键定义+使用点 / 无插值
  反引号模板直写), 守阵逐键红; 四键登记进副本 PREF_KEYS 后守阵绿(红绿双验留痕, 全程不碰
  static/ 生产文件)
"""

import os
import re
import shutil

from webui_helpers import STATIC_ROOT

# ui_prefs.js 在 static/ 内的相对落点(双清单单点; 扫描时它的声明区不算用法侧)
UI_PREFS_REL = "shared/ui_prefs.js"

# 族形态存储键字面量(全匹配): 点分族 autoqb.* / gtm.* + 下划线族 autoqb_*。
# !首字符定界用引号回引 \\1(双引号/单引号/反引号三形态): 只收字符串字面量(含无插值
#  反引号模板), 裸标识符/注释位(已剥)不收; 带 ${...} 插值的模板因内容含插值字符不匹配 ——
#  漏收是 D8 最危险失效形态, 字面量形态宁滥勿缺(见模块 docstring);
# !字符类只认 [A-Za-z0-9_.] / [A-Za-z0-9_]: cookie "autoqb_ui="(带等号)与事件名
#  "autoqb:*"(冒号族)天然不匹配 —— 闸外形态靠形状排除, 不维护黑名单(见模块 docstring)。
_STORAGE_KEY_LITERAL_RE = re.compile(r'(["\'`])((?:autoqb\.[A-Za-z0-9_.]+|autoqb_[A-Za-z0-9_]+|gtm\.[A-Za-z0-9_.]+))\1')

# 双清单声明区间(独立提取, 与扫描器互不复用)
_PREF_LIST_DECL_RE = r"const %s\s*=\s*\[(.*?)\];"


def _blank_js_comments(text):
    """剥 JS 注释但**保留行号**: 块注释内容与行注释尾段换成等长空白(换行原样保留)。

    与 webui_static_scan_common._strip_js_comments 同口径(存在性判定不被注释骗过:
    memory-bank/testing 列偏好守阵那条坑), 区别只在保留偏移 —— 本守阵报错要定位到
    真实 文件:行, 行注释只认前面不是冒号的 `//`(避开 https:// 字面量), 同先例。
    """
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    out = []
    for line in text.splitlines():
        m = re.search(r"(?<!:)//", line)
        out.append(line[:m.start()] + " " * (len(line) - m.start()) if m else line)
    return "\n".join(out)


def _blank_pref_decl_spans(text):
    """把 ui_prefs.js 里 PREF_KEYS / PREF_EXCLUDED 两个声明区换成空白(换行保留)。

    登记闸对账的是**用法侧**: 声明区里的键字面量若算命中, 清单就成了自证(登记了没用到的
    死键也会被反向对账误判"在用")。区间在剥注释**之前**按原文定位; 替换与 _blank_js_comments
    同口径 —— 非换行字符换空格、换行原样保留, 声明区之后用法侧的报错行号才不错位。
    """
    for name in ("PREF_KEYS", "PREF_EXCLUDED"):
        m = re.search(_PREF_LIST_DECL_RE % name, text, re.S)
        if m:
            text = text[:m.start()] + re.sub(r"[^\n]", " ", m.group(0)) + text[m.end():]
    return text


def scan_storage_keys(root):
    """递归扫 root 下全部 .js 的族形态存储键字面量 -> {key: [("rel", line), ...]}。

    口径见模块 docstring: 全树递归不裁目录; 只认代码位(剥注释后)全匹配字面量。
    """
    found = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in sorted(filenames):
            if not fn.endswith(".js"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            text = open(path, encoding="utf-8").read()
            if rel == UI_PREFS_REL:
                text = _blank_pref_decl_spans(text)
            code = _blank_js_comments(text)
            for m in _STORAGE_KEY_LITERAL_RE.finditer(code):
                loc = (rel, code.count("\n", 0, m.start(2)) + 1)
                found.setdefault(m.group(2), []).append(loc)
    return found


def extract_pref_lists(ui_prefs_src):
    """从 ui_prefs.js 源码独立提取双清单 -> (pref_keys, pref_excluded)(声明缺失返回 None)。"""
    lists = []
    for name in ("PREF_KEYS", "PREF_EXCLUDED"):
        m = re.search(_PREF_LIST_DECL_RE % name, ui_prefs_src, re.S)
        if not m:
            lists.append(None)
            continue
        # 区间内先剥注释再取字面量: 每键行尾的读写点注释里若出现引号串不能混进清单
        body = _blank_js_comments(m.group(1))
        keys = [q[1] for q in re.findall(r'(["\'`])([^"\'`]+)\1', body)]
        lists.append(keys)
    return tuple(lists)


def ui_prefs_gate_problems(root):
    """登记闸主判据: 返回问题清单(空 = 绿)。双向对账 + 清单自洽, 报错逐键带 文件:行。"""
    problems = []
    pref_keys, pref_excluded = extract_pref_lists(
        open(os.path.join(root, *UI_PREFS_REL.split("/")), encoding="utf-8").read()
    )
    if pref_keys is None:
        problems.append("ui_prefs.js 找不到 `const PREF_KEYS = [...]`(双清单单点被改名/删除? 守阵不许空转)")
        pref_keys = []
    if pref_excluded is None:
        problems.append("ui_prefs.js 找不到 `const PREF_EXCLUDED = [...]`(双清单单点被改名/删除? 守阵不许空转)")
        pref_excluded = []
    if not pref_keys or not pref_excluded:
        problems.append("双清单出现空清单(对账面被清空?): PREF_KEYS=%d 条 / PREF_EXCLUDED=%d 条" % (len(pref_keys), len(pref_excluded)))
    if len(pref_keys) < 10 or len(pref_excluded) < 5:
        problems.append(
            "双清单条数低于下限 dead-guard(PREF_KEYS>=10 / PREF_EXCLUDED>=5, 实测 2026-11-14 为 18/7): "
            "PREF_KEYS=%d / PREF_EXCLUDED=%d —— 整段误删?" % (len(pref_keys), len(pref_excluded))
        )
    for name, keys in (("PREF_KEYS", pref_keys), ("PREF_EXCLUDED", pref_excluded)):
        dup = sorted({k for k in keys if keys.count(k) > 1})
        if dup:
            problems.append("%s 清单内重复登记: %s" % (name, ", ".join(dup)))
    overlap = sorted(set(pref_keys) & set(pref_excluded))
    if overlap:
        problems.append("一键双登(同时在 PREF_KEYS 与 PREF_EXCLUDED, 进 bundle 与排除面语义矛盾): " + ", ".join(overlap))
    scanned = scan_storage_keys(root)
    if not scanned:
        problems.append("扫描器零命中(static/ 全部 .js 无族形态存储键字面量? 扫描面/判据被改名? 守阵不许空转)")
    registry = set(pref_keys) | set(pref_excluded)
    for key in sorted(set(scanned) - registry):
        locs = ", ".join("%s:%d" % loc for loc in scanned[key][:4])
        problems.append(
            "未登记存储键 %s(%s%s) —— 必须登记进 ui_prefs.js PREF_KEYS 或 PREF_EXCLUDED 其一(D8/D11)" %
            (key, locs, "..." if len(scanned[key]) > 4 else "")
        )
    for key in sorted(registry - set(scanned)):
        problems.append("登记键 %s 在 static/ .js 用法面零命中(死登记/拼写漂移? 摘键要同步清清单)" % key)
    return problems


def _read(rel):
    with open(os.path.join(STATIC_ROOT, *rel.split("/")), encoding="utf-8") as f:
        return f.read()


def test_registry_double_list_anchored():
    """双清单声明锚定: 区间找得到、非空、下限、单清单无重复、双清单交集为空。"""
    pref_keys, pref_excluded = extract_pref_lists(_read(UI_PREFS_REL))
    assert pref_keys is not None, "ui_prefs.js 找不到 `const PREF_KEYS = [...]`(单点被改名/删除?)"
    assert pref_excluded is not None, "ui_prefs.js 找不到 `const PREF_EXCLUDED = [...]`(单点被改名/删除?)"
    assert len(pref_keys) >= 10, "PREF_KEYS=%d 条, 低于下限 dead-guard(实测 2026-11-14 为 18)" % len(pref_keys)
    assert len(pref_excluded) >= 5, "PREF_EXCLUDED=%d 条, 低于下限 dead-guard(实测 2026-11-14 为 7)" % len(pref_excluded)
    assert len(pref_keys) == len(set(pref_keys)), "PREF_KEYS 清单内重复登记"
    assert len(pref_excluded) == len(set(pref_excluded)), "PREF_EXCLUDED 清单内重复登记"
    assert not set(pref_keys) & set(pref_excluded), "一键双登(进 bundle 与排除面语义矛盾)"


def test_scanned_keys_all_registered():
    """主闸(真实树): 扫到的族键全登记 + 登记键全在用 + 扫描零命中红。"""
    problems = ui_prefs_gate_problems(STATIC_ROOT)
    assert problems == [], "ui_prefs 登记闸(D8/D11)发现问题:\n" + "\n".join(problems)
    # 注: 故意不钉"命中总数 == 25" —— 合法新增登记(D8: 登记即绿)会撞死它; 扫描面被裁剪
    # (如漏了 prism/ 递归)由 ui_prefs_gate_problems 的反向对账(登记键零命中即红)兜住。


def test_boundary_exclusions_not_in_gate():
    """闸外形态边界钉: cookie/事件名/fxsc.* 三类先锚定存在于树里, 再断言不在扫描结果。"""
    scanned = scan_storage_keys(STATIC_ROOT)
    # 锚定(排除不许是"树里本来就没有"的假绿): 三类闸外字面量逐一验真在源里
    assert '"autoqb_ui="' in _read("shared/boot.js"), "boot.js cookie 写入点被改名? 锚定失效"
    assert '"autoqb:themechange"' in _read("prism/js/theme.js"), "theme.js 事件名被改名? 锚定失效"
    showcase = _read("fx/showcase.html")
    assert '"fxsc.preset"' in showcase and '"fxsc.picks"' in showcase, "fx/showcase.html fxsc.* 键被改名? 锚定失效"
    assert '"gtm.spike.ack"' in _read("shared/dialogs.js"), "dialogs.js gtm 尖峰消警键被改名? 锚定失效"
    # 断言: 闸外形态不进扫描结果; gtm.spike.ack(闸内)对照必须在
    assert "autoqb_ui" not in scanned, "cookie autoqb_ui 不在闸内(boot.js document.cookie, 非 localStorage)"
    assert not any(":" in k for k in scanned), "事件名 autoqb:* 冒号族不进闸(存储键无冒号形态)"
    assert not any(k.startswith("fxsc.") for k in scanned), "standalone 页 fxsc.* 族不进闸(与 ui_prefs.js 头注同界)"
    assert "gtm.spike.ack" in scanned, "gtm.* 点分族应在闸内(gtm.spike.ack, dialogs.js)"
    # 扫描面只落 .js: 全部命中点的文件后缀逐一核
    for locs in scanned.values():
        assert all(rel.endswith(".js") for rel, _line in locs), "扫描命中落点出现非 .js 文件"


def test_negative_unregistered_key_red_then_green(tmp_path):
    """负例红绿双验(§04 S4): tmp 副本注入未登记键四形态逐键红, 登记进双清单后绿。"""
    work = str(tmp_path / "static")
    shutil.copytree(STATIC_ROOT, work)
    inject = os.path.join(work, "shared", "app.js")
    with open(inject, "a", encoding="utf-8") as f:
        f.write("\n\n/* ---- S4 负例注入(test_webui_static_ui_prefs, tmp 副本, 非生产内容) ---- */\n")
        f.write('try { localStorage.setItem("autoqb.ui.negDot", "1"); } catch (e) {}\n')
        f.write('try { localStorage.setItem("autoqb_negUs", "1"); } catch (e) {}\n')
        f.write('const NEG_STORE_KEY = "autoqb.ui.negConst";\n')
        f.write("try { localStorage.setItem(NEG_STORE_KEY, \"1\"); } catch (e) {}\n")
        # 反引号形态(评审补修 2 的回钉): 无插值模板是字符串字面量, 必须与引号形态同闸
        f.write('try { localStorage.setItem(`autoqb.ui.negTick`, "1"); } catch (e) {}\n')
    problems = ui_prefs_gate_problems(work)
    injected = [p for p in problems if "neg" in p]
    assert injected, "注入未登记键后守阵未红(负例失守):\n" + "\n".join(problems)
    for key in ("autoqb.ui.negDot", "autoqb_negUs", "autoqb.ui.negConst", "autoqb.ui.negTick"):
        assert any(key in p and "未登记存储键" in p for p in problems), ("负例 %s 未被逐键点名红(点分/下划线/const/反引号四形态都要各验一次)" % key)
    # 登记(双清单其一) -> 绿: 四键补进副本 PREF_KEYS, 重跑守阵必须零问题
    prefs = os.path.join(work, *UI_PREFS_REL.split("/"))
    src = open(prefs, encoding="utf-8").read()
    for key in ("autoqb.ui.negDot", "autoqb_negUs", "autoqb.ui.negConst", "autoqb.ui.negTick"):
        src = src.replace(
            "const PREF_KEYS = [",
            'const PREF_KEYS = [\n  "%s", /* S4 负例登记(tmp 副本) */' % key,
            1,
        )
    with open(prefs, "w", encoding="utf-8") as f:
        f.write(src)
    problems = ui_prefs_gate_problems(work)
    assert problems == [], "四键登记进双清单后守阵应绿(红绿双验留痕):\n" + "\n".join(problems)
