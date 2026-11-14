p = "gen.py"
s = open(p).read()
def swap(start, end, new):
    global s
    i, j = s.index(start), s.index(end)
    s = s[:i] + new + s[j:]

swap("def sbrk_heap():", "# ================================================================== 06.06", '''def sbrk_heap():
    a = Art("f0605", "sbrk(8192) after exec of echo: two new pages, and the call returns the old end", 250)
    pw = 52
    def strip(y, heap):
        cells = ["text", "data", "guard", "stack"]
        for i, s in enumerate(cells):
            x = 24 + i * pw
            a.cell(x, y, pw, 36, "s fs" if s == "guard" else "s f")
            a.text(x + pw / 2, y + 22, s, "tm" if s == "guard" else "t", 11, "middle")
        end = 24 + 4 * pw
        if heap:
            for k in range(2):
                x = end + k * pw
                a.cell(x, y, pw, 36, "a af")
                a.text(x + pw / 2, y + 22, "heap", "ta", 11, "middle", 600)
            end += 2 * pw
        a.cell(end, y, 440 - end, 36, "m", dash=True)
        a.text((end + 440) / 2, y + 22, "unmapped", "tm", 11, "middle")
        a.cell(440, y, 88, 36, "s fs"); a.mono(484, y + 22, "TRAPFRAME", "t", 10.5, "middle")
        a.cell(528, y, 88, 36, "s fs"); a.mono(572, y + 22, "TRAMPOLINE", "t", 10.5, "middle")
        n = 7 if heap else 5
        labels = [(24 + k * pw, "0x%x000" % k if k else "0x0") for k in range(n)]
        for x, s in labels:
            a.mono(x, y + 50, s, "tm", 10, "start" if x == 24 else "middle")
        a.mono(440, y + 50, "0x3FFFFFE000", "tm", 10)
        a.mono(528, y + 50, "0x3FFFFFF000", "tm", 10)
        return end
    a.text(24, 22, "after exec", "tm", 10.5)
    e1 = strip(36, False)
    a.line(e1, 8, e1, 32, arrow=True)
    a.mono(e1 + 6, 18, "p->sz", "t", 10.5)
    a.mono(24, 118, "sbrk(8192)", "t", 11.5, weight=600)
    a.text(24, 134, "growproc: uvmalloc two pages, zeroed, PTE_W", "tm", 10.5)
    e2 = strip(150, True)
    a.line(e2, 122, e2, 146, arrow=True)
    a.mono(e2 + 6, 132, "p->sz", "t", 10.5)
    a.line(232, 104, 232, 146, "a", arrow=True)
    a.mono(238, 112, "returns 0x4000, the old end", "ta", 10.5)
    a.text(440, 220, "growproc refuses to let", "tm", 10.5)
    a.text(440, 234, "sz + n pass TRAPFRAME", "tm", 10.5)
    return a


''')

old = '''    a.path(f"M{x1} {y + h + 22} C {x1} 232, {x0} 232, {x0} {y + h + 22}", "m", arrow=True)
    a.text(470, 196, "the next byte after data[511]", "tm", 10.5, "middle")
    a.text(470, 210, "goes to data[0]", "tm", 10.5, "middle")'''
assert old in s
s = s.replace(old, '''    a.path(f"M{x1} {y + h + 22} C {x1} 226, {x0} 226, {x0} {y + h + 22}", "m", arrow=True)
    a.text(320, 222, "the byte after data[511] goes to data[0]", "tm", 10.5, "middle")''')

swap("def free_list():", "def to_disk():", '''def free_list():
    a = Art("f0701a", "malloc(100) on a fresh heap: the 4096-unit block from morecore is split, and the caller gets the tail", 252)
    a.text(616, 18, "1 unit = sizeof(Header) = 16 bytes; not to scale", "tm", 10, "end")
    def row(y, label, split):
        a.text(24, y - 10, label, "tm", 10.5)
        a.box(24, y, 76, 40, "s fs", rx=6)
        a.mono(36, y + 17, "base", "t", 11.5, weight=600)
        a.mono(36, y + 32, "size 0", "tm", 10)
        a.cell(150, y, 56, 40, "s fs")
        a.mono(178, y + 17, "size", "tm", 10, "middle")
        a.mono(178, y + 32, "4088" if split else "4096", "t", 11, "middle")
        if split:
            a.cell(206, y, 224, 40, "s f"); a.text(318, y + 25, "free", "tm", 11, "middle")
            a.cell(430, y, 56, 40, "a af"); a.mono(458, y + 17, "size", "ta", 10, "middle"); a.mono(458, y + 32, "8", "ta", 11, "middle", 600)
            a.cell(486, y, 130, 40, "a af"); a.text(551, y + 25, "112 bytes for you", "ta", 11, "middle", 600)
        else:
            a.cell(206, y, 410, 40, "s f"); a.text(411, y + 25, "4095 free units: 65520 bytes", "tm", 11, "middle")
        a.line(100, y + 14, 148, y + 14, arrow=True)
        a.path(f"M178 {y + 40} C 178 {y + 64}, 62 {y + 64}, 62 {y + 42}", arrow=True)
        a.mono(124, y + 8, "ptr", "tm", 10, "middle")
        a.mono(120, y + 66, "ptr", "tm", 10, "middle")
    row(44, "after morecore: sbrk(65536) gave one free block, and the list is base -> block -> base", False)
    row(156, "after malloc(100): (100 + 15) / 16 + 1 = 8 units, cut off the tail", True)
    a.text(206, 212, "bytes from the start of the block:", "tm", 10)
    a.mono(430, 212, "0xff80", "tm", 10, "middle")
    a.mono(616, 212, "0x10000", "tm", 10, "end")
    a.line(486, 240, 486, 200, "a", arrow=True)
    a.text(478, 240, "malloc returns the byte after the header", "ta", 10.5, "end")
    return a


''')

old = '''    a.path("M236 44 C 262 44, 300 50, 310 77", arrow=True)
    a.path("M252 138 C 280 138, 300 128, 310 109", arrow=True)'''
assert old in s
s = s.replace(old, '''    a.path("M236 44 C 256 44, 250 86, 268 86", arrow=True)
    a.path("M252 138 C 264 138, 256 100, 268 100", arrow=True)''')
open(p, "w").write(s)
