"""表达式词法分析: 字符串 -> Token 列表

字面量的单位解析一律复用 utils.parse_fsize / parse_time / parse_speed / parse_hm
(与 interval/cooldown/限速等配置同一口径), 单位非法(如 10GB)在此即抛 ExprSyntaxError
—— fail-fast, 不留到运行期才发现。

字面量形态(见计划第 03 节):
    100 / 1.5        num    裸数字
    10GiB / 500MiB   size   字节(必须 iB 单位, 与项目惯例一致)
    24H / 30M / 7D   time   秒
    1MiB/s           speed  字节/秒
    22:30            hhmm   当日分钟数 0-1439(配 sys.time_of_day 用)
    "HR" / 'HR'      str
    true / false     bool
"""
import re
from dataclasses import dataclass
from typing import Any, List, Tuple

from ... import utils
from .errors import ExprSyntaxError

# 运算符(两字符优先匹配)
_OPS2 = (">=", "<=", "==", "!=")
_OPS1 = (">", "<", "=", "+", "-", "*", "/", "%", "~")
# 词法关键字: 只接受小写(大写给出改写提示, 免得被当成名字报出莫名其妙的错)
_KEYWORD_OPS = frozenset(("and", "or", "not", "in"))
_KEYWORD_BOOL = {"true": True, "false": False}

_RE_HHMM = re.compile(r"(\d{1,2}):(\d{2})(?![\d:])")
_RE_NUM = re.compile(r"\d+(?:\.\d+)?")
_RE_SPEED = re.compile(r"[KMGTP]?i?B/s", re.IGNORECASE)
_RE_SIZE = re.compile(r"[KMGTP]?i?B(?![\w])", re.IGNORECASE)
_RE_TIME = re.compile(r"[SMHD](?![\w])")
_RE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")


@dataclass(frozen=True, slots=True)
class Token:
    """一个词法单元

    kind:  num/size/time/speed/hhmm/str/bool/name/op/"("/")"/"["/"]"/","/eof
    value: 字面量为已解析的值; 运算符与名字为文本; 括号/逗号为符号本身
    """

    kind: str
    text: str
    value: Any
    pos: int  # 1 起的列号, 供报错定位


def tokenize(text) -> List[Token]:
    """把表达式切分为 Token 列表(末尾恒带 eof)

    空表达式 / 非法字符 / 非法单位 / 未闭合字符串 一律抛 ExprSyntaxError。
    """
    s = str(text)
    if not s.strip():
        raise ExprSyntaxError("表达式不能为空")
    tokens: List[Token] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        pos = i + 1
        if c in "'\"":
            raw, value, i = _read_string(s, i)
            tokens.append(Token("str", raw, value, pos))
            continue
        if c.isdigit():
            token, i = _read_number(s, i)
            tokens.append(token)
            continue
        if c in "()[],":
            tokens.append(Token(c, c, c, pos))
            i += 1
            continue
        if s[i:i + 2] in _OPS2:
            tokens.append(Token("op", s[i:i + 2], s[i:i + 2], pos))
            i += 2
            continue
        if c in _OPS1:
            tokens.append(Token("op", c, c, pos))
            i += 1
            continue
        m = _RE_NAME.match(s, i)
        if m:
            word = m.group(0)
            i = m.end()
            low = word.lower()
            if low in _KEYWORD_OPS or low in _KEYWORD_BOOL:
                if word != low:
                    raise ExprSyntaxError(f"关键字必须小写: '{word}' -> '{low}'", pos)
                if low in _KEYWORD_BOOL:
                    tokens.append(Token("bool", word, _KEYWORD_BOOL[low], pos))
                else:
                    tokens.append(Token("op", word, word, pos))
                continue
            tokens.append(Token("name", word, word, pos))
            continue
        raise ExprSyntaxError(f"非法字符 '{c}'", pos)
    tokens.append(Token("eof", "", None, n + 1))
    return tokens


def _read_string(s: str, i: int) -> Tuple[str, str, int]:
    """读取引号字符串(支持 \\ 转义引号与反斜杠), 返回 (原始文本, 值, 结束下标)"""
    quote = s[i]
    start = i
    i += 1
    buf: List[str] = []
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            buf.append(s[i + 1])
            i += 2
            continue
        if c == quote:
            return s[start:i + 1], "".join(buf), i + 1
        buf.append(c)
        i += 1
    raise ExprSyntaxError(f"字符串缺少结束引号 '{quote}'", start + 1)


def _read_number(s: str, i: int) -> Tuple[Token, int]:
    """读取数字及其可选单位: hhmm / speed / size / time / 裸数字"""
    start = i
    m = _RE_HHMM.match(s, i)
    if m:
        raw = m.group(0)
        try:
            hour, minute = utils.parse_hm(raw)
        except ValueError as e:
            raise ExprSyntaxError(f"非法时间字面量 '{raw}': {e}", start + 1) from e
        return Token("hhmm", raw, hour * 60 + minute, start + 1), m.end()

    m = _RE_NUM.match(s, i)
    if not m:
        raise ExprSyntaxError(f"无法识别的数字 '{s[i]}'", start + 1)
    num_text = m.group(0)
    i = m.end()

    for regex, kind, parser in (
        (_RE_SPEED, "speed", utils.parse_speed),
        (_RE_SIZE, "size", utils.parse_fsize),
        (_RE_TIME, "time", utils.parse_time),
    ):
        um = regex.match(s, i)
        if not um:
            continue
        raw = num_text + um.group(0)
        i = um.end()
        _ensure_boundary(s, i, raw, start)
        try:
            value = parser(raw)
        except ValueError as e:
            raise ExprSyntaxError(f"非法字面量 '{raw}': {e}", start + 1) from e
        return Token(kind, raw, value, start + 1), i

    _ensure_boundary(s, i, num_text, start)
    value = float(num_text) if "." in num_text else int(num_text)
    return Token("num", num_text, value, start + 1), i


def _ensure_boundary(s: str, i: int, raw: str, start: int) -> None:
    """数字/单位后面紧跟字母数字下划线点 -> 报错(如 '24Hours' / '10GiBx' / '1.5.2')"""
    if i < len(s) and (s[i].isalnum() or s[i] in "_."):
        raise ExprSyntaxError(f"数字后紧跟非法字符: '{raw}{s[i]}'（想写单位请用合法单位, 如 KiB/H/D）", start + 1)
