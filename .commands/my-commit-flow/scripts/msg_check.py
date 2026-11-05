"""提交消息机检(纯函数) —— ship.commit 在 `git commit -F` 之前调用(计划 26-11-06-0124)。

三态(拍板 D1):
  硬拦   → violations: [(id, 明细)],调用方 emit 失败行;逃生 = 配置 `msg_check_allow` 白名单
           (拍板 D5: 只放行硬拦档 —— 警告无 suppress 需求、自动修不会误伤;未知 id 由
           `_ship_config.config_problems` 报 STOP, 不静默忽略)
  自动修 → fixed: 仅骨架位(文件头 BOM / 已知 gitmoji 承接空格 / 首行后空行),修后文本由调用方写回并
           逐行打印「已自动修正:」留痕 —— 沉默即成功只属于零修正的绿
  警告   → warnings: 打印不拦。正文零代改(拍板 D4)—— 正文与 subject 承接位之外的字符问题一律只报

检测依据全部实测或语料核对(计划 §02, 2026-11-06;收口评审轮补了 200 笔全量回测):
  - BOM 过 `git commit -F` **不被剥离** → 必须自己剥(A1);
  - CRLF / 行尾空白被 `cleanup=whitespace` 自动剥离 → 不查;
  - `#` 开头行在 `-F` 下**原样保留**(注释剥离只发生在编辑器流程)→ 查(d5);
  - 反引号是既有用法(语料 21/200 行),`-F` 路径无 bash 替换风险 → 不查;
  - 段落标签硬拦会误伤真实写作形态(复合标签头/项目符号子项/叙述段, 见 c2 注)→ c2 降警告(拍板 D3 修正)。

判定顺序 = **修先于检**:剥 BOM → 归一 gitmoji 承接空格 → 补首行后空行,之后的硬拦/警告全部基于
修后文本 —— 否则修了还报、报的又是修前形态,输出自相矛盾。本模块不 import 本包其它模块、除
check_message_file 读文件外无 IO:纯函数面可独立单测,快照语义下随包复制即可运行。
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

# gitmoji 官方全集(gitmoji.dev, 75 个;提取单点 = .agents/skills/gitmoji/references/gitmoji-reference.md,
# 2026-11-06 程序提取)。比对前统一去 VS16(U+FE0F): 参考表里 🗑️/♻️/⚡️ 等带变体选择符, 语料两种形态都有。
GITMOJIS = frozenset(
    """
⏪ ♻ ♿ ⚗ ⚡ ⚰ ✅ ✈ ✏ ✨ ➕ ➖ ⬆ ⬇ 🌐 🌱 🍱 🍻 🎉 🎨 🏗 🏷 🐛 👔 👥 👷 👽 💄 💚 💡 💥 💩 💫 💬 💸
📄 📈 📌 📝 📦 📱 📸 🔀 🔇 🔊 🔍 🔐 🔒 🔖 🔥 🔧 🔨 🗃 🗑 🙈 🚀 🚑 🚚 🚧 🚨 🚩 🚸 🛂 🤡 🥅 🥚 🦖
🦺 🧐 🧑‍💻 🧪 🧱 🧵 🩹 🩺
""".split()
)

# 硬拦条目 id —— `msg_check_allow` 白名单的合法词表(拍板 D5: 只放行硬拦档)。
# c2 曾在硬拦档(拍板 D3a), 2026-11-06 收口评审的语料回测(严格 120/200、词前缀 103/200、近 20 笔
# 7/20)证伪了「语料 100% 合规」的前提(当时仅抽查 3 笔), 用户改拍降为警告 —— 词表随之收窄。
VIOLATION_IDS = frozenset({"a2", "a3", "b1", "b2", "b4", "d1", "d2", "d3", "d7"})

# 乱码签名(a3, 保守显式子串): 二次损伤不可逆, 只能重写消息。⚠ 双次 mojibake 的产物**是**合法
# UTF-8, a2 的 strict 解码兜不住它 —— a3 的覆盖边界就是这张签名表本身, 未收录组合会漏网(接受),
# 反向误伤走白名单 a3。签名一律双字起步(单字拉丁字母如 å 会误伤合法欧文)。
MOJIBAKE_SIGNATURES = (
    "\ufffd",  # 已被 errors=replace 写死过的替换符
    "锟斤拷",  # UTF-8 → GBK 经典双 mojibake
    "烫烫烫",
    "屯屯屯",  # MSVC 堆填充(粘贴日志类)
    "â€",  # UTF-8 → CP1252(â€™ = ')
    "Ã©",
    "Ã¨",
    "Ã­",
    "Ã³",
    "Ãº",
    "Ã±",  # 同上系(e/è/i/o/u/ñ)
    "å®",
    "å¥",
    "å›",
    "å­",  # UTF-8 中文 → Latin-1 系(安/好/回/字 的起始字节对)
    "æ–",
    "ä¸",  # 同上(新/中 的起始字节对)
)

# 强模板占位符(d1, 硬拦): 明确是没填完的消息骨架。SLOT 走行首锚定(句中「SLOT 注释」类合法引用在
# 语料 3/200, 行首才是未填槽形态); <hash> 不收 —— 它不是消息骨架词表, 语料 2/200 全是引用输出契约
# 的合法行文。TODO/XXX/FIXME 词面易撞合法引用(如「清掉 TODO 注释」)→ 降警告(d1w)。
PLACEHOLDER_STRONG = ("<动机>", "<影响面>", "<取舍>", "<实测>", "<中文", "待填")
_SLOT_LINE_RE = re.compile(r"^SLOT\b", re.M)
PLACEHOLDER_SOFT = ("TODO", "XXX", "FIXME")

# 正文标签(c2 警告/a5): 拍板 D3 于 2026-11-06 依语料回测改拍降为警告(见 VIOLATION_IDS 注)。
# 口径 = 词前缀(矩阵原义, 不要求冒号紧邻): 复合标签头(实测数字:/取舍与要点:/动机/取舍:)都认,
# 项目符号子项(「- 复验:」)与叙述段只提醒不拦。冒号形态: 全角冒号 = a5 警告(拍板 D4: 标点不代改)。
_LABEL_HEAD_RE = re.compile(r"^(动机|取舍|影响面|实测)")
_LABEL_RE = re.compile(r"^(动机|取舍|影响面|实测)(?:\([^)]*\))?:\s?")
_LABEL_FULLWIDTH_RE = re.compile(r"^(动机|取舍|影响面|实测)(?:[（(][^）)]*[）)])?：")

# 不可见字符(a4w): 拍板 D4 = 正文零代改, 只报位置。ZWJ 在 emoji 组合(🧑‍💻)里是合法连接符,
# 邻位是 emoji 时跳过;NBSP 在 gitmoji 承接位由 B3 归一(骨架位例外), 其余位置只报。
INVISIBLE = {"\u200b": "ZWSP", "\u200c": "ZWNJ", "\u2060": "WORD-JOINER", "\u00a0": "NBSP", "\u200d": "ZWJ"}

# 承接空格归一的目标集(B3): 半角/全角空格、tab、NBSP 一律归一为单个半角空格。
_JOINT_WS = " \t\u00a0\u3000"


@dataclass
class MsgReport:
    """一次机检的结果。text = 修后文本(无修正 = 原文),调用方据此写回消息文件。"""

    fixed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    violations: list[tuple[str, str]] = field(default_factory=list)
    text: str = ""


def _first_grapheme(s: str) -> str:
    """首字形簇: 基字 + 后随 VS16/变体选择/肤色修饰,ZWJ 连接的后续 emoji 一并入簇。

    gitmoji 只有这两类组合: 🗑️ = 基字+VS16,🧑‍💻 = 🧑+ZWJ+💻 —— 不入簇会把 🧑‍💻 拆成两半,
    承接空格归一会插到 ZWJ 中间把 emoji 拆坏。旗类(regional indicator 对)不入簇也**不能**拆 ——
    B3 因此只对归一后命中 GITMOJIS 的已知集生效(见下), 未知 emoji 一律不动文本。
    """
    if not s:
        return ""
    out = s[0]
    i = 1
    while i < len(s):
        ch = s[i]
        if ch in "\ufe0f\ufe0e" or 0x1F3FB <= ord(ch) <= 0x1F3FF:  # VS16/VS15/肤色修饰
            out += ch
            i += 1
        elif ch == "\u200d" and i + 1 < len(s):  # ZWJ: 连接符 + 被连接的 emoji 一并消费
            out += ch + s[i + 1]
            i += 2
        else:
            break
    return out


def _is_emoji_like(ch: str) -> bool:
    """首字像 emoji 吗 —— 区分 b1(纯文本开头, 提示补 gitmoji)与 b2(自造 emoji, 提示换标准集)。

    CJK(含扩展 A)/ 假名 / 谚文 / 全角标点 / 中文标点不算 emoji —— 它们起首走 b1, 别给出
    「不在标准集」的误导性诊断;箭头(→ U+2190)起步的 BMP 区与 SMP emoji 区算。
    """
    cp = ord(ch)
    if (
        0x3400 <= cp <= 0x4DBF  # CJK 扩展 A
        or 0x4E00 <= cp <= 0x9FFF  # CJK 统一表意
        or 0x3000 <= cp <= 0x303F  # 中文标点
        or 0x3040 <= cp <= 0x30FF  # 假名
        or 0xAC00 <= cp <= 0xD7A3  # 谚文
        or 0xFF00 <= cp <= 0xFFEF  # 全角标点
    ):
        return False
    return cp >= 0x2190 or cp in (0xA9, 0xAE, 0x2122)


def review_text(text: str, allow: frozenset[str] = frozenset()) -> MsgReport:
    """机检单点: 输入消息原文(已按 UTF-8 严格解码),返回修后文本 + 三清单。

    allow = 放行的硬拦条目 id 集(白名单, 拍板 D5);警告与自动修不受白名单影响。
    """
    fixed: list[str] = []
    warnings: list[str] = []
    report = MsgReport(fixed=fixed, warnings=warnings, text=text)

    def _v(vid: str, detail: str) -> None:
        if vid not in allow:  # 白名单只放行硬拦档;放行 = 静默跳过(配置文件本身就是记录)
            report.violations.append((vid, detail))

    if not text.strip():
        _v("d7", "消息为空或全空白 —— git 会拒, 早拦给出明确原因")
        return report

    # ---- A1 BOM(git -F 不剥, 实测): 留着会让 emoji 判定与 log 显示全歪 ----
    if text.startswith("\ufeff"):
        text = text[1:]
        fixed.append("剥离文件头 UTF-8 BOM(U+FEFF)")

    lines = text.split("\n")
    # subject = 第一个非空行(git cleanup 会剥前导空行 —— 按将要入库的形态判定, 不制造假红)
    si = 0
    while si < len(lines) and not lines[si].strip():
        si += 1
    subject = lines[si] if si < len(lines) else ""

    # ---- B3 gitmoji 承接空格(骨架位): 缺→补一格;多/全角/NBSP→归一单个半角 ----
    # 只对**已知 gitmoji** 生效: 未知 emoji(旗类 🇨🇳/自造集)的簇边界没把握, 动它就是改坏正文
    # (收口评审 major: 🇨🇳 曾被拆成「🇨 🇳」写回文件)—— 未知 emoji 走 b2 硬拦重写, 不自动修。
    cluster = _first_grapheme(subject)
    if cluster.replace("\ufe0f", "") in GITMOJIS:
        rest = subject[len(cluster):]
        stripped = rest.lstrip(_JOINT_WS)
        if stripped and rest != " " + stripped:
            lines[si] = cluster + " " + stripped
            fixed.append("gitmoji 承接空格归一为单个半角空格")
            subject = lines[si]
            text = "\n".join(lines)

    # ---- C1 首行后缺空行(有正文时): 否则 `git log --oneline` 下正文全被并进 subject ----
    if si + 1 < len(lines) and lines[si + 1].strip():
        lines.insert(si + 1, "")
        fixed.append("首行与正文之间补空行")
        text = "\n".join(lines)
    report.text = text

    # ---- a3 乱码签名(命中一个即报;文本已损伤, 其余检查照跑供一次看全) ----
    for sig in MOJIBAKE_SIGNATURES:
        if sig in text:
            _v("a3", f"乱码签名 {sig!r} —— 文本已损伤不可逆, 重写消息")
            break

    # ---- b1/b2 gitmoji ----
    norm = cluster.replace("\ufe0f", "")
    if norm in GITMOJIS:
        pass
    elif cluster and _is_emoji_like(cluster[0]):
        _v("b2", f"首行 emoji {cluster} 不在 gitmoji 标准集 —— 换标准集内的(全集与选法见 gitmoji skill)")
    else:
        _v("b1", f"首行不以 gitmoji 开头: {subject.lstrip()[:16]!r}… —— 口径 <gitmoji> <中文一句话概述>(选法见 gitmoji skill)")

    # ---- b4 首行无中文(明细截断展示 —— 超长首行不刷终端, 收口评审实测 5MB 回显) ----
    after = subject[len(cluster):] if cluster else subject
    if not any("\u4e00" <= c <= "\u9fff" for c in after):
        subj_strip = subject.strip()
        disp = subj_strip[:40] + ("…" if len(subj_strip) > 40 else "")
        _v("b4", f"首行无中文: {disp!r} —— 口径要求中文一句话概述(技术 token 混排不受影响)")

    # ---- c2(警告)/a5/c5 段落(基于修后文本; C1 已保证首行后有分隔) ----
    paras: list[list[str]] = []
    cur: list[str] = []
    for ln in lines[si + 1:]:
        if ln.strip():
            cur.append(ln)
        elif cur:
            paras.append(cur)
            cur = []
    if cur:
        paras.append(cur)
    for idx, para in enumerate(paras, 1):
        head = para[0].lstrip()
        if _LABEL_HEAD_RE.match(head):
            if _LABEL_FULLWIDTH_RE.match(head):
                warnings.append(f"第 {idx} 段标签用了全角冒号: {head[:14]!r} —— 语料口径是半角(a5, 标点不代改)")
        else:
            warnings.append(
                f"第 {idx} 段不以已知标签词(动机/取舍/影响面/实测)开头: {head[:20]!r} —— "
                "建议正文段落带标签(c2, 警告不拦 —— 语料回测后降档, 见计划 §06)"
            )
        if head.startswith("实测"):
            # 数字检测必须剥掉标签本体再查 —— 标签自带时间戳「实测(26-11-06):」, 整段扫日期会永远命中
            rest = "\n".join([_LABEL_RE.sub("", head)] + para[1:])
            if not re.search(r"\d", rest):
                warnings.append(f"实测段(第 {idx} 段)没有任何数字 —— 规模数字要提交那一刻实测(c5)")

    # ---- d1/d1w 占位符 ----
    for ph in PLACEHOLDER_STRONG:
        if ph in text:
            _v("d1", f"模板占位符残留 {ph!r} —— 骨架没填完")
            break
    if _SLOT_LINE_RE.search(text):
        _v("d1", "行首 SLOT 模板槽残留 —— 骨架没填完(句中引用 SLOT 不拦)")
    for ph in PLACEHOLDER_SOFT:
        if ph in text:
            warnings.append(f"疑似占位符词面 {ph!r} —— 若是合法引用请忽略(d1w)")
            break

    # ---- d2/d3 粘贴残骸 ----
    if "Traceback (most recent call last)" in text:
        _v("d2", "消息里粘贴了 traceback —— 提交消息不是日志存放处")
    if any(ln.lstrip().startswith("diff --git ") for ln in lines):
        _v("d3", "消息里粘贴了 diff —— git 自带 diff, 别复制进消息")

    # ---- a4w 不可见字符(正文零代改, 只报位置; ZWJ 在 emoji 组合里合法) ----
    for li, ln in enumerate(lines, 1):
        hits: list[str] = []
        for ci, ch in enumerate(ln):
            if ch not in INVISIBLE:
                continue
            if ch == "\u200d":
                prev_ok = ci > 0 and ord(ln[ci - 1]) >= 0x1F000
                next_ok = ci + 1 < len(ln) and ord(ln[ci + 1]) >= 0x1F000
                if prev_ok or next_ok:  # 🧑‍💻 类组合 emoji 的合法连接符
                    continue
            if INVISIBLE[ch] not in hits:
                hits.append(INVISIBLE[ch])
        if hits:
            warnings.append(f"第 {li} 行有不可见字符 {'/'.join(hits)} —— 正文零代改, 请自行清理(a4w)")

    # ---- d5/d6 模板残留(警告: 污染但内容落地) ----
    if any(ln.lstrip().startswith("#") for ln in lines):
        warnings.append("存在 # 开头的行 —— -F 下不会被当注释剥掉, 会原样入库(d5)")
    # 标准 scissors 行以 # 开头(commit -v 模板), 不能锚定行首 —— 按特征组合认(收口评审 minor)
    if any(">8" in ln and "----" in ln for ln in lines):
        warnings.append("存在 scissors 剪裁线(>8) —— 疑似 commit -v 模板残留(d6)")

    return report


def check_message_file(path: Path, allow: frozenset[str] = frozenset()) -> MsgReport:
    """文件层入口: strict UTF-8 读(a2 —— 非 UTF-8 字节会被 git 原样落库成乱码),其余交 review_text。

    读取做与 consume_message_file 同款的小步重试 —— Windows 上刚写完的消息文件会被编辑器/杀软
    瞬时占锁(在库实证), 读路径不重试会产生偶发假失败。重试后仍失败按 "io" 违规处理(环境问题,
    不是检查器误报, 不进白名单词表)。
    """
    raw: bytes | None = None
    last: OSError | None = None
    for attempt in range(3):
        try:
            raw = path.read_bytes()
            break
        except OSError as exc:
            last = exc
            time.sleep(0.2 * (attempt + 1))
    if raw is None:
        return MsgReport(violations=[("io", f"消息文件读取失败: {last} —— 瞬时占锁(编辑器/杀软)时稍后重跑")], text="")
    try:
        text = raw.decode("utf-8")  # strict —— UTF-16LE BOM / GBK 中文在这里就炸
    except UnicodeDecodeError as exc:
        return MsgReport(
            violations=[
                (
                    "a2", f"消息文件不是合法 UTF-8(字节 {exc.start}~{exc.end}) —— "
                    "多半是 PowerShell >/cmd echo 写出(GBK/UTF-16); 用 UTF-8 重写"
                )
            ],
            text="",
        )
    return review_text(text, allow)
