"""Syntax highlighting without dependencies: one pass per line, state carried across lines.

    highlight_lines(text, lang) -> one HTML string per source line (len == text.split("\\n"))
    language_for(filename)      -> "c" | "asm" | "python" | "make" | "ld" | "perl" | "sh" | "plain"
    fence_lang(info)            -> the same, from a markdown fence info string

Every character of the source is escaped; tokens become <span class="tk-?"> (CSS in app.css):
k keyword, t type, s string/char, n number, c comment, p preprocessor/directive,
f function name, r register, i instruction mnemonic, l label, v CONSTANT or macro.
"""

import html
import re

C_KEYWORDS = set("""auto break case continue default do else enum extern for goto if inline register restrict
return sizeof static struct switch typedef union volatile while const asm __asm__ __volatile__ __attribute__
_Static_assert _Alignas true false""".split())
C_TYPES = set("""void char short int long float double unsigned signed bool size_t ssize_t uint uchar ushort
uint8 uint16 uint32 uint64 int8 int16 int32 int64 uint8_t uint16_t uint32_t uint64_t int8_t int16_t int32_t
int64_t uintptr_t intptr_t pte_t pde_t pagetable_t""".split())
LD_KEYWORDS = set("""ENTRY SECTIONS OUTPUT_ARCH OUTPUT_FORMAT PROVIDE PROVIDE_HIDDEN ALIGN KEEP MEMORY AT BYTE
SHORT LONG QUAD ORIGIN LENGTH INCLUDE NOCROSSREFS ASSERT FILL SORT NOLOAD AT_ALIGN""".split())
PY_KEYWORDS = set("""and as assert async await break class continue def del elif else except finally for from
global if import in is lambda nonlocal not or pass raise return try while with yield True False None""".split())
PY_TYPES = set("int str float bool bytes list dict set tuple object type bytearray".split())
SH_KEYWORDS = set("if then else elif fi for while until do done case esac in function return exit local export set unset".split())
PERL_KEYWORDS = set("""my our local sub if elsif else unless while until for foreach return use no package print
printf die warn last next redo exit defined undef shift push pop split join keys values open close""".split())
MAKE_KEYWORDS = set("ifeq ifneq ifdef ifndef else endif include sinclude define endef export unexport override vpath".split())

ASM_REGS = set("zero ra sp gp tp fp".split()) | {f"t{i}" for i in range(7)} | {f"s{i}" for i in range(12)} \
    | {f"a{i}" for i in range(8)} | {f"x{i}" for i in range(32)} | {f"f{i}" for i in range(32)} \
    | {f"ft{i}" for i in range(12)} | {f"fs{i}" for i in range(12)} | {f"fa{i}" for i in range(8)}
ASM_CSRS = set("""mstatus misa medeleg mideleg mie mtvec mcounteren mscratch mepc mcause mtval mip mhartid mvendorid
marchid mimpid menvcfg mcycle minstret sstatus sie stvec scounteren senvcfg sscratch sepc scause stval sip satp
stimecmp scycle sinstret time cycle instret pmpcfg0 pmpaddr0 pmpcfg1 pmpaddr1 pmpcfg2 pmpaddr2 pmpcfg3 pmpaddr3
mseccfg fflags frm fcsr hstatus""".split())

NUMBER = r"(?<![\w.])(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|\d[\d_]*\.?\d*(?:[eE][+-]?\d+)?)[uUlLfF]*(?![\w.])"
IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
CAPS = re.compile(r"^[A-Z][A-Z0-9_]+$")


def language_for(filename):
    base = filename.rsplit("/", 1)[-1]
    low = base.lower()
    if base == "Makefile" or low == "makefile" or low.endswith(".mk"):
        return "make"
    ext = base.rsplit(".", 1)[-1] if "." in base else ""
    return {"c": "c", "h": "c", "S": "asm", "s": "asm", "py": "python", "ld": "ld", "pl": "perl", "sh": "sh"}.get(ext, "plain")


def fence_lang(info):
    return {"c": "c", "h": "c", "cpp": "c", "asm": "asm", "s": "asm", "riscv": "asm", "sh": "sh", "bash": "sh",
            "shell": "sh", "console": "sh", "python": "python", "py": "python", "make": "make",
            "makefile": "make", "perl": "perl", "pl": "perl", "ld": "ld"}.get((info or "").lower(), "plain")


def span(kind, text):
    return f'<span class="tk-{kind}">{html.escape(text)}</span>'


def plain(text):
    return html.escape(text)


def highlight_lines(text, lang):
    lines = text.split("\n")
    if lang not in LEXERS:
        return [plain(l) for l in lines]
    state = {}
    out = []
    for line in lines:
        out.append(LEXERS[lang](line, state))
    return out


# ---------------------------------------------------------------- C family (c, ld)

C_TOKEN = re.compile(
    r"(?P<lc>//.*)"
    r"|(?P<bc>/\*)"
    r"|(?P<str>\"(?:\\.|[^\"\\])*\"?)"
    r"|(?P<chr>'(?:\\.|[^'\\])*'?)"
    r"|(?P<num>" + NUMBER + r")"
    r"|(?P<id>" + IDENT + r")")


def _c_like(line, state, keywords, types, pp=True):
    out, pos = [], 0
    if state.get("block"):
        end = line.find("*/")
        if end < 0:
            return span("c", line)
        out.append(span("c", line[:end + 2]))
        pos = end + 2
        state["block"] = False
    if pp:
        m = re.match(r"(\s*)(#\s*[a-z]+)", line[pos:])
        if m:
            out.append(plain(m.group(1)) + span("p", m.group(2)))
            pos += m.end()
            inc = re.match(r"(\s*)(<[^>\n]*>)", line[pos:])
            if inc:
                out.append(plain(inc.group(1)) + span("s", inc.group(2)))
                pos += inc.end()
    prev = ""  # last identifier, to catch "struct name"
    while pos < len(line):
        m = C_TOKEN.search(line, pos)
        if not m:
            out.append(plain(line[pos:]))
            break
        out.append(plain(line[pos:m.start()]))
        kind, tok = m.lastgroup, m.group()
        pos = m.end()
        if kind == "lc":
            out.append(span("c", tok))
        elif kind == "bc":
            end = line.find("*/", pos)
            if end < 0:
                out.append(span("c", tok + line[pos:]))
                state["block"] = True
                pos = len(line)
            else:
                out.append(span("c", tok + line[pos:end + 2]))
                pos = end + 2
        elif kind in ("str", "chr"):
            out.append(span("s", tok))
        elif kind == "num":
            out.append(span("n", tok))
        else:
            nxt = line[pos:].lstrip()[:1]
            if tok in keywords:
                out.append(span("k", tok))
            elif tok in types or tok.endswith("_t") and len(tok) > 2:
                out.append(span("t", tok))
            elif prev in ("struct", "union", "enum"):
                out.append(span("t", tok))
            elif nxt == "(" and not CAPS.match(tok):
                out.append(span("f", tok))
            elif CAPS.match(tok):
                out.append(span("v", tok))
            else:
                out.append(plain(tok))
            prev = tok
            continue
        prev = ""
    return "".join(out)


def lex_c(line, state):
    return _c_like(line, state, C_KEYWORDS, C_TYPES)


def lex_ld(line, state):
    return _c_like(line, state, LD_KEYWORDS, set(), pp=False)


# ---------------------------------------------------------------- RISC-V assembly

ASM_TOKEN = re.compile(
    r"(?P<lc>//.*|#.*)"
    r"|(?P<bc>/\*)"
    r"|(?P<str>\"(?:\\.|[^\"\\])*\"?)"
    r"|(?P<num>" + NUMBER + r")"
    r"|(?P<dir>(?<![\w.])\.[A-Za-z_]\w*)"
    r"|(?P<id>[A-Za-z_$][\w$.]*)")


def lex_asm(line, state):
    out, pos = [], 0
    if state.get("block"):
        end = line.find("*/")
        if end < 0:
            return span("c", line)
        out.append(span("c", line[:end + 2]))
        pos = end + 2
        state["block"] = False
    stmt = True  # next word is a mnemonic or directive
    m = re.match(r"(\s*)(#\s*(?:include|define|undef|if|ifdef|ifndef|else|elif|endif|pragma|error)\b)", line[pos:])
    if m:
        out.append(plain(m.group(1)) + span("p", m.group(2)))
        pos += m.end()
        stmt = False
        inc = re.match(r"(\s*)(<[^>\n]*>)", line[pos:])
        if inc:
            out.append(plain(inc.group(1)) + span("s", inc.group(2)))
            pos += inc.end()
    while pos < len(line):
        lab = re.compile(r"\s*([A-Za-z_.$][\w.$]*)(:)") if stmt else None
        if lab:
            lm = lab.match(line, pos)
            if lm:
                out.append(plain(line[pos:lm.start(1)]) + span("l", lm.group(1)) + plain(":"))
                pos = lm.end()
                continue
        m = ASM_TOKEN.search(line, pos)
        if not m:
            out.append(plain(line[pos:]))
            break
        out.append(plain(line[pos:m.start()]))
        kind, tok = m.lastgroup, m.group()
        pos = m.end()
        if kind == "lc":
            out.append(span("c", tok))
        elif kind == "bc":
            end = line.find("*/", pos)
            if end < 0:
                out.append(span("c", tok + line[pos:]))
                state["block"] = True
                pos = len(line)
            else:
                out.append(span("c", tok + line[pos:end + 2]))
                pos = end + 2
        elif kind == "str":
            out.append(span("s", tok))
        elif kind == "num":
            out.append(span("n", tok))
            stmt = False
        elif kind == "dir":
            out.append(span("p", tok))
            stmt = False
        else:
            low = tok.lower()
            nxt = line[pos:pos + 1]
            if stmt and nxt != "(":
                out.append(span("i", tok))
            elif low in ASM_REGS or low in ASM_CSRS:
                out.append(span("r", tok))
            elif nxt == "(" and not CAPS.match(tok):
                out.append(span("f", tok))
            elif CAPS.match(tok):
                out.append(span("v", tok))
            else:
                out.append(plain(tok))
            stmt = False
    return "".join(out)


# ---------------------------------------------------------------- Python

PY_TOKEN = re.compile(
    r"(?P<cm>\#.*)"
    r"|(?P<tq>(?:[rRbBuUfF]{0,2})(?:\"\"\"|'''))"
    r"|(?P<str>(?:[rRbBuUfF]{0,2})(?:\"(?:\\.|[^\"\\])*\"?|'(?:\\.|[^'\\])*'?))"
    r"|(?P<num>" + NUMBER + r")"
    r"|(?P<dec>@[A-Za-z_][\w.]*)"
    r"|(?P<id>" + IDENT + r")")


def lex_python(line, state):
    out, pos = [], 0
    tq = state.get("tq")
    if tq:
        end = line.find(tq)
        if end < 0:
            return span("s", line)
        out.append(span("s", line[:end + 3]))
        pos = end + 3
        state["tq"] = None
    prev = ""
    while pos < len(line):
        m = PY_TOKEN.search(line, pos)
        if not m:
            out.append(plain(line[pos:]))
            break
        out.append(plain(line[pos:m.start()]))
        kind, tok = m.lastgroup, m.group()
        pos = m.end()
        if kind == "cm":
            out.append(span("c", tok))
        elif kind == "tq":
            delim = tok[-3:]
            end = line.find(delim, pos)
            if end < 0:
                out.append(span("s", tok + line[pos:]))
                state["tq"] = delim
                pos = len(line)
            else:
                out.append(span("s", tok + line[pos:end + 3]))
                pos = end + 3
        elif kind == "str":
            out.append(span("s", tok))
        elif kind == "num":
            out.append(span("n", tok))
        elif kind == "dec":
            out.append(span("p", tok))
        else:
            nxt = line[pos:].lstrip()[:1]
            if tok in PY_KEYWORDS:
                out.append(span("k", tok))
            elif prev == "def":
                out.append(span("f", tok))
            elif prev == "class":
                out.append(span("t", tok))
            elif tok in PY_TYPES:
                out.append(span("t", tok))
            elif nxt == "(":
                out.append(span("f", tok))
            elif CAPS.match(tok):
                out.append(span("v", tok))
            else:
                out.append(plain(tok))
            prev = tok
            continue
        prev = ""
    return "".join(out)


# ---------------------------------------------------------------- shell, perl, make

SH_TOKEN = re.compile(
    r"(?P<cm>(?<![^\s;|&(])\#.*)"
    r"|(?P<str>\"(?:\\.|[^\"\\])*\"?|'[^']*'?)"
    r"|(?P<var>\$(?:\{[^}\n]*\}?|\([^)\n]*\)?|[A-Za-z_]\w*|[@<^?!#*0-9$]))"
    r"|(?P<num>" + NUMBER + r")"
    r"|(?P<id>[A-Za-z_][\w-]*)")


def lex_sh(line, state):
    out, pos = [], 0
    first = True
    while pos < len(line):
        m = SH_TOKEN.search(line, pos)
        if not m:
            out.append(plain(line[pos:]))
            break
        out.append(plain(line[pos:m.start()]))
        kind, tok = m.lastgroup, m.group()
        pos = m.end()
        if kind == "cm":
            out.append(span("c", tok))
        elif kind == "str":
            out.append(span("s", tok))
        elif kind == "var":
            out.append(span("v", tok))
        elif kind == "num":
            out.append(span("n", tok))
        else:
            if tok in SH_KEYWORDS:
                out.append(span("k", tok))
            elif first and line[pos:pos + 1] != "=":
                out.append(span("i", tok))
            elif line[pos:pos + 2] == "()":
                out.append(span("f", tok))
            else:
                out.append(plain(tok))
        first = False if kind != "id" or tok not in ("then", "do", "else") else True
    return "".join(out)


PERL_TOKEN = re.compile(
    r"(?P<cm>\#.*)"
    r"|(?P<str>\"(?:\\.|[^\"\\])*\"?|'(?:\\.|[^'\\])*'?)"
    r"|(?P<var>[$@%]\{?[A-Za-z_]\w*\}?)"
    r"|(?P<num>" + NUMBER + r")"
    r"|(?P<id>" + IDENT + r")")


def lex_perl(line, state):
    out, pos, prev = [], 0, ""
    while pos < len(line):
        m = PERL_TOKEN.search(line, pos)
        if not m:
            out.append(plain(line[pos:]))
            break
        out.append(plain(line[pos:m.start()]))
        kind, tok = m.lastgroup, m.group()
        pos = m.end()
        if kind == "cm":
            out.append(span("c", tok))
        elif kind == "str":
            out.append(span("s", tok))
        elif kind == "var":
            out.append(span("v", tok))
        elif kind == "num":
            out.append(span("n", tok))
        else:
            if tok in PERL_KEYWORDS:
                out.append(span("k", tok))
            elif prev == "sub" or line[pos:].lstrip()[:1] == "(":
                out.append(span("f", tok))
            else:
                out.append(plain(tok))
            prev = tok
            continue
        prev = ""
    return "".join(out)


MAKE_VAR = re.compile(r"\$(?:\([^)\n]*\)?|\{[^}\n]*\}?|[@<^?*%+|])")


def lex_make(line, state):
    if line.startswith("\t"):
        return lex_sh(line, state)
    m = re.match(r"\s*#", line)
    if m:
        return span("c", line)
    km = re.match(r"(\s*-?)(" + "|".join(sorted(MAKE_KEYWORDS, key=len, reverse=True)) + r")\b", line)
    head = ""
    rest = line
    if km:
        head = plain(km.group(1)) + span("k", km.group(2))
        rest = line[km.end():]
    else:
        am = re.match(r"([A-Za-z_][\w.]*)(\s*[:?+!]?=)", line)
        tm = re.match(r"([^\s:=#][^:=#]*?)(\s*::?)(?!=)", line)
        if am:
            head = span("v", am.group(1)) + plain(am.group(2))
            rest = line[am.end():]
        elif tm:
            head = span("l", tm.group(1)) + plain(tm.group(2))
            rest = line[tm.end():]
    out, pos = [], 0
    while pos < len(rest):
        mm = re.compile(r"(?P<cm>\#.*)|(?P<var>" + MAKE_VAR.pattern + r")").search(rest, pos)
        if not mm:
            out.append(plain(rest[pos:]))
            break
        out.append(plain(rest[pos:mm.start()]))
        out.append(span("c" if mm.lastgroup == "cm" else "v", mm.group()))
        pos = mm.end()
    return head + "".join(out)


LEXERS = {"c": lex_c, "ld": lex_ld, "asm": lex_asm, "python": lex_python, "sh": lex_sh,
          "perl": lex_perl, "make": lex_make}
