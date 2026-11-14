from figlib import Fig, write, tw

MOD = "05-storage"


def desc_chain():
    f = Fig("f0501a", "One disk request: three chained descriptors", 300)
    f.text(24, 20, "reading block 1, the superblock: descriptors 0, 1 and 2 of disk.desc[8]", "tm", 11)
    cards = [
        (24, "desc[0]", [("addr", "&disk.ops[0]"), ("len", "16"), ("flags", "NEXT"), ("next", "1")]),
        (228, "desc[1]", [("addr", "b->data"), ("len", "1024"), ("flags", "NEXT | WRITE"), ("next", "2")]),
        (432, "desc[2]", [("addr", "&disk.info[0].status"), ("len", "1"), ("flags", "WRITE"), ("next", "0")]),
    ]
    W = 184
    for x, title, rows in cards:
        f.rect(x, 34, W, 106, "s f", 8)
        f.text(x + 12, 54, title, "t", 12, None, 600, True)
        for i, (k, v) in enumerate(rows):
            y = 76 + i * 18
            f.text(x + 12, y, k, "tm", 10.5, None, None, True)
            f.text(x + 54, y, v, "t", 10 if len(v) > 16 else 10.5, None, None, True)
    for x in (24, 228):
        f.line(x + W, 130, x + W + 18, 130, "s", arrow=True)
    targets = [
        (24, "a af", "struct virtio_blk_req", ["type     0 (IN, a read)", "reserved 0", "sector   2 = 1 * 2"], "16 bytes"),
        (228, "s fs", "b->data", ["the 1024 bytes of", "block 1; WRITE: the", "device fills them in"], "1024 bytes"),
        (432, "s fs", "info[0].status", ["0xff until the", "device writes 0", "for success"], "1 byte"),
    ]
    for x, cls, title, lines, size in targets:
        acc = cls.startswith("a")
        f.line(x + W / 2, 140, x + W / 2, 174, "a" if acc else "s", arrow=True)
        f.text(x + W / 2 + 8, 162, "addr", "ta" if acc else "tm", 10, None, None, True)
        f.rect(x, 176, W, 92, cls, 8)
        f.text(x + 12, 196, title, "ta" if acc else "t", 11.5, None, 600, True)
        for i, l in enumerate(lines):
            f.text(x + 12, 216 + i * 17, l, "ta" if acc else "t", 10.5, None, None, acc)
    f.text(24, 290, "desc[3] to desc[7] stay free, so a second request can be in flight", "tm", 10.5)
    return f


def rings():
    f = Fig("f0501b", "The avail and used rings", 296)
    x0, cw = 128, 48

    def ring(y, name, sub, vals):
        f.text(24, y + 14, name, "t", 11.5, None, 600, True)
        f.text(24, y + 29, sub, "tm", 10.5)
        heads = ["flags", "idx"] + [f"ring[{i}]" for i in range(8)]
        for i, h in enumerate(heads):
            x = x0 + i * cw
            f.text(x + cw / 2, y - 6, h, "tm", 9.5, "middle", None, True)
            v = vals.get(i, "")
            f.rect(x, y, cw, 30, "s f" if v else "m f", 0)
            if v:
                f.text(x + cw / 2, y + 19, v, "t", 11, "middle", None, True)
        return y
    ya = ring(40, "disk.avail", "driver writes", {0: "0", 1: "1", 2: "0"})
    # driver steps
    steps = [("1", "ring[idx % 8] = 0", "the head of the chain", x0 + 2 * cw + cw / 2),
             ("2", "__sync_synchronize()", "the entry lands first", None),
             ("3", "idx += 1", "now the device may look", x0 + cw + cw / 2),
             ("4", "fence, QUEUE_NOTIFY = 0", "poke the device", None)]
    for i, (n, code, why, tx) in enumerate(steps):
        x = 128 + (i % 2) * 250
        y = 100 + (i // 2) * 36
        acc = n == "2"
        f.circle(x + 8, y - 4, 8, "a af" if acc else "s f")
        f.text(x + 8, y, n, "ta" if acc else "t", 10, "middle", 600, True)
        f.text(x + 22, y, code, "ta" if acc else "t", 11, None, 600 if acc else None, True)
        f.text(x + 22, y + 15, why, "ta" if acc else "tm", 10.5)
    f.line(x0 + 2 * cw + cw / 2, 88, x0 + 2 * cw + cw / 2, 74, "m", arrow=True)
    f.line(x0 + cw + cw / 2, 88, x0 + cw + cw / 2, 74, "m", arrow=True)
    yu = ring(196, "disk.used", "device writes", {0: "0", 1: "1", 2: "id 0"})
    f.text(24, 260, "the device", "tm", 10.5)
    f.text(128, 260, "fills ring[0] with the finished head, bumps idx, raises irq 1", "t", 11)
    f.text(24, 282, "the driver", "tm", 10.5)
    f.text(128, 282, "virtio_disk_intr(): disk.used_idx 0 -> 1, info[0].b: b->disk = 0, wakeup(b)", "t", 11)
    return f


def lru():
    f = Fig("f0502a", "brelse moves a buffer to the front", 290)
    bw, bh, gap = 62, 40, 30

    def row(y, bufs, moved=None, label=""):
        f.text(24, y - 14, label, "tm", 11)
        f.rect(24, y, 52, bh, "s fs", 8)
        f.text(50, y + 25, "head", "t", 11, "middle", None, True)
        x = 24 + 52 + gap
        xs = []
        for i, b in enumerate(bufs):
            if b is None:
                f.text(x + 10, y + 25, "...", "tm", 12, "middle")
                x += 20 + gap
                xs.append(None)
                continue
            blk, ref = b
            acc = moved == blk
            f.rect(x, y, bw, bh, "a af" if acc else "s f", 6)
            f.text(x + bw / 2, y + 17, f"blk {blk}", "ta" if acc else "t", 11, "middle", 600 if acc else None, True)
            f.text(x + bw / 2, y + 32, f"ref {ref}", "ta" if acc else "tm", 10, "middle", None, True)
            xs.append(x)
            x += bw + gap
        # links
        prev = 24 + 52
        for xx in xs:
            if xx is None:
                prev += 20 + gap
                continue
            f.line(prev + 4, y + bh / 2, xx - 4, y + bh / 2, "m", start=True, arrow=True)
            prev = xx + bw
        last = [xx for xx in xs if xx is not None][-1]
        f.path(f"M{last + bw / 2} {y + bh} L{last + bw / 2} {y + bh + 14} L50 {y + bh + 14} L50 {y + bh + 2}", "m", arrow=True)
        return xs
    before = [(33, 1), (47, 0), (48, 1), None, (2, 0), (46, 0)]
    xs = row(46, before, None, "before")
    x48 = xs[2]
    f.path(f"M{x48 + bw / 2} 44 C {x48 + bw / 2} 16, {76 + gap / 2} 16, {76 + gap / 2} 42", "a", arrow=True)
    f.text(x48 + bw / 2 + 10, 26, "brelse: ref 1 -> 0, so move it to head.next", "ta", 10.5)
    f.text(50, 122, "head.next: the most recently used", "tm", 10.5)
    f.text(xs[-1] + bw / 2, 122, "head.prev: the least", "tm", 10.5, "end")
    after = [(48, 0), (33, 1), (47, 0), None, (2, 0), (46, 0)]
    xs2 = row(176, after, 48, "after")
    xl = xs2[-1]
    f.text(xl + bw, 252, "bget's victim: from head.prev, the first ref 0", "tm", 10.5, "end")
    f.line(xl + bw / 2, 238, xl + bw / 2, 220, "m", arrow=True)
    f.text(24, 280, "30 buffers in all; a buffer with ref above 0 is never recycled", "tm", 10.5)
    return f


def buflocks():
    f = Fig("f0502b", "Which lock guards which field of struct buf", 262)
    fields = [("valid", "b"), ("disk", "d"), ("dev", "c"), ("blockno", "c"), ("lock", None), ("refcnt", "c"),
              ("prev", "c"), ("next", "c"), ("data[1024]", "b")]
    x, w, y0, rh = 60, 150, 34, 22
    f.text(x, 22, "struct buf", "t", 11.5, None, 600, True)
    ys = {}
    for i, (name, g) in enumerate(fields):
        y = y0 + i * rh
        acc = g == "b"
        f.rect(x, y, w, rh, "a af" if acc else ("s fs" if g is None else "s f"), 0)
        f.text(x + 12, y + 15, name, "ta" if acc else ("tm" if g is None else "t"), 11, None, 600 if acc else None, True)
        ys[name] = y + rh / 2
    locks = [("c", 50, "bcache.lock", "spinlock: the list, refcnt, and which", "block the buffer holds"),
             ("b", 132, "b->lock", "sleep lock: held from bread() to", "brelse(), across the disk I/O"),
             ("d", 204, "disk.vdisk_lock", "b->disk is 1 while the device", "owns the buffer (05.01)")]
    lx = 360
    for g, y, name, l1, l2 in locks:
        acc = g == "b"
        f.rect(lx, y, 256, 52, "a af" if acc else "s f", 8)
        f.text(lx + 12, y + 18, name, "ta" if acc else "t", 11.5, None, 600, True)
        f.text(lx + 12, y + 33, l1, "ta" if acc else "tm", 10.5)
        f.text(lx + 12, y + 46, l2, "ta" if acc else "tm", 10.5)
        for name2, g2 in fields:
            if g2 == g:
                yy = ys[name2]
                f.path(f"M{x + w} {yy} C {x + w + 70} {yy}, {lx - 70} {y + 26}, {lx} {y + 26}", "a" if acc else "m")
    return f


def bitmap():
    # The finished system's disk, as the lesson's worked example says: mkfs.log "first 789
    # blocks have been allocated", byte 98 of block 46 is 0x1f.
    f = Fig("f0503a", "The free bitmap, bit by bit", 262)
    f.text(24, 20, "block 46, the bitmap, on the finished system's disk: one bit per block, 8 blocks per byte", "tm", 11)
    y, h = 46, 30
    cells = [("0", "0xff", "0-7"), ("1", "0xff", "8-15"), None, ("97", "0xff", "776-783"), ("98", "0x1f", "784-791"),
             ("99", "0x00", "792-799"), None, ("249", "0x00", "1992-1999")]
    x = 24
    pos = {}
    for c in cells:
        if c is None:
            f.text(x + 14, y + 20, "...", "tm", 12, "middle")
            x += 28
            continue
        idx, val, blocks = c
        f.rect(x, y, 56, h, "s f" if val != "0x00" else "m f", 0)
        f.text(x + 28, y + 20, val, "t" if val != "0x00" else "tm", 11, "middle", None, True)
        f.text(x + 28, y - 6, f"byte {idx}", "tm", 9.5, "middle", None, True)
        f.text(x + 28, y + h + 14, blocks, "tm", 9.5, "middle", None, True)
        pos[idx] = x
        x += 56
    f.rect(x + 8, y, 616 - x - 8, h, "m", 0, dash=True)
    f.text((x + 8 + 616) / 2, y + 13, "bytes 250-1023", "tm", 10, "middle", None, True)
    f.text((x + 8 + 616) / 2, y + 25, "past sb.size: unused", "tm", 10, "middle")
    # zoom on byte 98
    bx = pos["98"]
    zx, zy, zw = 96, 140, 56
    f.line(bx, y + h + 22, zx, zy - 18, "m", dash=True)
    f.line(bx + 56, y + h + 22, zx + 8 * zw, zy - 18, "m", dash=True)
    bits = [1, 1, 1, 1, 1, 0, 0, 0]
    for i, v in enumerate(bits):
        xx = zx + i * zw
        acc = i == 5
        f.text(xx + zw / 2, zy - 4, f"bit {i}", "tm", 9.5, "middle", None, True)
        f.rect(xx, zy, zw, 34, "a af" if acc else ("s fs" if v else "s f"), 0)
        f.text(xx + zw / 2, zy + 22, str(v), "ta" if acc else "t", 13, "middle", 600 if acc else None, True)
        f.text(xx + zw / 2, zy + 50, str(784 + i), "ta" if acc else "tm", 10.5, "middle", 600 if acc else None, True)
    f.text(zx - 10, zy + 22, "0x1f", "t", 11, "end", None, True)
    f.text(zx - 10, zy + 50, "block", "tm", 10.5, "end")
    f.text(zx + 5 * zw + zw / 2, zy + 72, "the first 0: the next balloc() returns 789", "ta", 11, "middle")
    f.text(24, 250, "block b lives in bitmap block b / BPB + sb.bmapstart, byte (b % BPB) / 8, mask 1 << (b % 8)", "t", 10.5, mono=True)
    return f


def logsteps():
    f = Fig("f0504a", "The log on disk through one commit", 326)
    # columns
    hx, hw = 172, 92
    lx, lw = 276, 50
    mx = lx + 3 * lw + 22
    f.text(hx + hw / 2, 18, "header", "t", 11, "middle", 600)
    f.text(lx + 1.5 * lw, 18, "log", "t", 11, "middle", 600)
    f.text(mx + 1.5 * lw, 18, "home", "t", 11, "middle", 600)
    f.text(hx + hw / 2, 34, "2", "tm", 10, "middle", None, True)
    for i, b in enumerate(("3", "4", "5")):
        f.text(lx + i * lw + lw / 2, 34, b, "tm", 10, "middle", None, True)
    homes = ("34", "47", "33")
    for i, b in enumerate(homes):
        f.text(mx + i * lw + lw / 2, 34, b, "tm", 10, "middle", None, True)
    rows = [
        ("before", "", "n = 0", ["", "", ""], ["old"] * 3, False),
        ("1", "write_log()", "n = 0", homes, ["old"] * 3, False),
        ("2", "write_head()", "n = 3", homes, ["old"] * 3, True),
        ("3", "install_trans(0)", "n = 3", homes, ["new"] * 3, False),
        ("4", "write_head()", "n = 0", homes, ["new"] * 3, False),
    ]
    ys = [44, 88, 152, 216, 260]
    for (n, call, head, logs, home, commit), y in zip(rows, ys):
        h = 32
        if n == "before":
            f.text(24, y + 20, "in the cache only", "tm", 10.5)
        else:
            f.text(24, y + 14, n, "ta" if commit else "t", 11, None, 600, True)
            f.text(38, y + 14, call, "ta" if commit else "t", 10.5, None, 600 if commit else None, True)
            if commit:
                f.text(24, y + 28, "the commit point", "ta", 10.5)
            if n == "4":
                f.text(38, y + 28, "after n = 0", "tm", 10.5)
        f.rect(hx, y, hw, h, "a af" if commit else "s f", 0)
        f.text(hx + hw / 2, y + (14 if head != "n = 0" else 20), head, "ta" if commit else "t", 11, "middle", 600 if commit else None, True)
        if head != "n = 0":
            f.text(hx + hw / 2, y + 27, "34 47 33", "ta" if commit else "t", 10, "middle", None, True)
        stale = n == "4"
        for i, v in enumerate(logs):
            x = lx + i * lw
            if v:
                f.rect(x, y, lw, h, "m fs" if stale else "s fs", 0)
                f.text(x + lw / 2, y + 20, v, "tm" if stale else "t", 11, "middle", None, True)
            else:
                f.rect(x, y, lw, h, "m f", 0)
        for i, v in enumerate(home):
            x = mx + i * lw
            f.rect(x, y, lw, h, "s fs" if v == "new" else "m f", 0)
            f.text(x + lw / 2, y + 20, v, "t" if v == "new" else "tm", 10.5, "middle")
    # crash markers
    for y, text in ((136, "crash here: the header says n = 0; recovery copies nothing, so a never existed"),
                    (200, "crash here: the header says n = 3; recovery copies all three blocks home")):
        f.line(24, y, 160, y, "m", dash=True)
        f.text(hx, y + 4, text, "tm", 10.5)
    # The lesson's Break it creates a on the 07.03 disk: inode 16 (console is 15), in block
    # 33 + 16 / 16 = 34; the root directory's data is block 47 and its inode is in block 33.
    f.text(24, 316, "creating a on the 07.03 disk: 34 holds the new inode 16, 47 is the root directory's data, 33 its inode", "tm", 10.5)
    return f


def inode():
    f = Fig("f0505a", "An inode's twelve direct pointers and its indirect block", 314)
    x, w = 24, 196
    # cat on the finished system's disk, as the lesson says: inode 3, addrs 49..60, indirect 61
    # holding 62..85 (checked on build/at/xv6/finished's fs.img). The size is the lesson's.
    f.text(x, 20, "inode 3 (cat) on the finished system's disk, in block 33", "tm", 11)
    rows = [("type", "2 (T_FILE)"), ("nlink", "1"), ("size", "36176"), ("addrs[0]", "49"), ("addrs[1]", "50"),
            ("...", ""), ("addrs[11]", "60"), ("addrs[12]", "61")]
    y0, rh = 30, 26
    ry = {}
    for i, (k, v) in enumerate(rows):
        y = y0 + i * rh
        acc = k == "addrs[12]"
        if k == "...":
            f.text(x + 16, y + 17, "...", "tm", 12)
            ry[k] = y + rh / 2
            continue
        f.rect(x, y, w, rh, "a af" if acc else "s f", 0)
        f.text(x + 12, y + 17, k, "ta" if acc else "tm", 10.5, None, 600 if acc else None, True)
        f.text(x + w - 12, y + 17, v, "ta" if acc else "t", 11, "end", 600 if acc else None, True)
        ry[k] = y + rh / 2
    # direct data group
    gx, gw = 300, 156
    f.rect(gx, 64, gw, 52, "s fs", 8)
    f.text(gx + 12, 85, "blocks 49 to 60", "t", 11, None, 600, True)
    f.text(gx + 12, 103, "file blocks 0-11", "tm", 10.5)
    for k in ("addrs[0]", "addrs[1]", "addrs[11]"):
        f.path(f"M{x + w} {ry[k]} C {x + w + 40} {ry[k]}, {gx - 40} 90, {gx - 2} 90", "m", arrow=True)
    f.text(gx + gw / 2, 52, "direct: one lookup", "tm", 10.5, "middle")
    # indirect block
    ix, iw = 300, 156
    iy = 158
    f.text(ix, iy - 8, "block 61: 256 block numbers", "ta", 10.5, None, 600)
    irows = [("[0]", "62"), ("[1]", "63"), ("...", ""), ("[23]", "85"), ("[24]", "0"), ("...", ""), ("[255]", "0")]
    irh = 17
    for i, (k, v) in enumerate(irows):
        y = iy + i * irh
        if k == "...":
            f.text(ix + 14, y + 13, "...", "tm", 11)
            continue
        zero = v == "0"
        f.rect(ix, y, iw, irh, "m f" if zero else "s f", 0)
        f.text(ix + 10, y + 13, k, "tm", 10, None, None, True)
        f.text(ix + iw - 10, y + 13, v, "tm" if zero else "t", 10.5, "end", None, True)
    f.rect(ix - 1, iy - 1, iw + 2, len(irows) * irh + 2, "a", 2)
    f.path(f"M{x + w} {ry['addrs[12]']} C {x + w + 40} {ry['addrs[12]']}, {ix - 40} {iy + 20}, {ix - 3} {iy + 20}", "a", arrow=True)
    # indirect data group
    hx, hw = 496, 120
    f.rect(hx, iy, hw, 52, "s fs", 8)
    f.text(hx + 10, iy + 21, "blocks 62 to 85", "t", 10.5, None, 600, True)
    f.text(hx + 10, iy + 39, "file blocks 12-35", "tm", 10.5)
    f.path(f"M{ix + iw} {iy + 8} C {ix + iw + 20} {iy + 8}, {hx - 20} {iy + 26}, {hx - 2} {iy + 26}", "m", arrow=True)
    f.path(f"M{ix + iw} {iy + 3 * irh + 8} C {ix + iw + 20} {iy + 3 * irh + 8}, {hx - 20} {iy + 26}, {hx - 2} {iy + 26}", "m", arrow=True)
    f.text(hx, iy + 72, "via the indirect block:", "tm", 10.5)
    f.text(hx, iy + 87, "one more disk read", "tm", 10.5)
    f.text(24, 268, "36176 bytes is 36 blocks: 12 direct,", "tm", 10.5)
    f.text(24, 283, "24 through the indirect block", "tm", 10.5)
    f.text(24, 304, "bmap(ip, bn): bn < 12 is addrs[bn]; bn 12 to 267 is entry bn - 12 of the indirect block", "t", 10.5, mono=True)
    return f


def chunks():
    f = Fig("f0505b", "readi in block-sized pieces", 240)
    x0, s = 40, 0.18
    y = 70

    def X(b):
        return x0 + b * s
    f.text(24, 20, "a 2500-byte file, and readi(ip, 0, dst, 900, 2000)", "tm", 11)
    for i in range(3):
        xa = X(i * 1024)
        f.rect(xa, y, 1024 * s, 30, "s f", 0)
        f.text(xa + 6, y + 19, f"block {i}", "tm", 10.5)
        f.text(xa, y + 44, str(i * 1024), "tm", 9.5, "middle", None, True)
    f.text(X(3072), y + 44, "3072", "tm", 9.5, "middle", None, True)
    # past size
    f.add(f'<rect class="fs" x="{X(2500):.1f}" y="{y + 1}" width="{(3072 - 2500) * s - 1:.1f}" height="28"/>')
    f.text((X(2500) + X(3072)) / 2, y + 19, "past size", "tm", 10, "middle")
    f.line(X(2500), y - 8, X(2500), y + 36, "s")
    f.text(X(2500), y + 52, "size 2500", "t", 10, "middle", None, True)
    # request
    f.brace_h(X(900), min(X(2900), 612), y - 14, "m", up=True)
    f.text(X(900), y - 22, "asked: off 900, n 2000", "tm", 10.5, None, None, True)
    f.text(min(X(2900), 612), y - 22, "2900", "tm", 9.5, "end", None, True)
    # clamped chunks
    cy = 146
    chunks_ = [(900, 1024, "m = 124"), (1024, 2048, "m = 1024"), (2048, 2500, "m = 452")]
    for a, b, lab in chunks_:
        f.rect(X(a) + 1, cy, (b - a) * s - 2, 24, "s fs", 4)
        if b - a < 300:
            f.text(X(a) - 6, cy + 16, lab, "t", 10.5, "end", None, True)
        else:
            f.text((X(a) + X(b)) / 2, cy + 16, lab, "t", 10.5, "middle", None, True)
        f.line(X(a), y + (30 if a == 900 else 50), X(a), cy, "m", dash=True)
    f.line(X(2500), y + 58, X(2500), cy, "m", dash=True)
    f.text(X(2500) + 8, cy + 16, "n clamped to", "ta", 10.5)
    f.text(X(2500) + 8, cy + 31, "size - off = 1600", "ta", 10.5, None, 600, True)
    f.text(24, 210, "each pass copies m = min(n - tot, BSIZE - off % BSIZE) bytes from block off / BSIZE;", "tm", 10.5)
    f.text(24, 226, "the first and the last piece are partial", "tm", 10.5)
    return f


def pathwalk():
    f = Fig("f0506a", "namex walking /d/../README", 250)
    f.text(24, 24, "/d/../README", "t", 15, None, 600, True)
    f.text(160, 24, "starts at the root, inode 1; skipelem() hands out d, .., README", "tm", 11)
    cols = [
        # mkdir d needs the shell, so the 07.03 disk: wc is inode 14 at 224, console 15 at 240,
        # and d becomes inode 16 at 256 (07.03's Run it: ls d shows ". 1 16 32").
        (24, "inode 1, look up d", [("0", ".", "1"), ("16", "..", "1"), ("32", "README", "2"), ("48", "cat", "3"),
                                     ("...", "", ""), ("240", "console", "15"), ("256", "d", "16")], 6),
        (232, "inode 16, look up ..", [("0", ".", "16"), ("16", "..", "1")], 1),
        (440, "inode 1, look up README", [("0", ".", "1"), ("16", "..", "1"), ("32", "README", "2")], 2),
    ]
    W, rh, y0 = 176, 20, 78
    for i, (x, title, ents, hit) in enumerate(cols):
        f.circle(x + 9, 52, 9, "s f")
        f.text(x + 9, 56, str(i + 1), "t", 10.5, "middle", 600, True)
        f.text(x + 24, 56, title, "t", 11)
        f.text(x + 4, y0 - 6, "off", "tm", 9, None, None, True)
        for j, (off, name, inum) in enumerate(ents):
            y = y0 + j * rh
            if off == "...":
                f.text(x + 44, y + 14, "...", "tm", 11)
                continue
            acc = i == 1 and j == hit
            m = j == hit
            f.rect(x + 30, y, W - 30, rh, "a af" if acc else ("s fs" if m else "s f"), 0)
            f.text(x + 4, y + 14, off, "tm", 9.5, None, None, True)
            f.text(x + 40, y + 14, name, "ta" if acc else "t", 11, None, 600 if m else None, True)
            f.text(x + W - 10, y + 14, inum, "ta" if acc else "t", 11, "end", 600 if m else None, True)
        f.text(x + 30, y0 + len(ents) * rh + 18, f"iunlockput(inode {title.split()[1].rstrip(',')})", "tm", 10, None, None, True)
    # arrows between columns
    f.path(f"M{24 + W} {y0 + 6 * rh + 10} C {24 + W + 20} {y0 + 6 * rh + 10}, 214 52, 226 52", "s", arrow=True)
    f.path(f"M{232 + W} {y0 + 1 * rh + 10} C {232 + W + 20} {y0 + rh + 10}, 422 52, 434 52", "a", arrow=True)
    yr = y0 + 2 * rh + 10
    f.path(f"M{440 + W - 12} {yr + 10} L{440 + W - 12} 186", "s", arrow=True)
    f.rect(470, 188, 146, 30, "s f", 8)
    f.text(543, 207, "returns inode 2", "t", 11, "middle", 600, True)
    f.text(262, 176, "'..' is an ordinary entry:", "tm", 10.5)
    f.text(262, 192, "three lookups, one inode", "tm", 10.5)
    f.text(262, 208, "lock held at a time", "tm", 10.5)
    return f


def dirent():
    f = Fig("f0506b", "Two directory entries, byte by byte", 194)
    x0, cw = 116, 32
    f.text(x0 + cw, 22, "inum", "tm", 10.5, "middle")
    f.text(x0 + 2 * cw + 7 * cw, 22, "name[DIRSIZ]: 14 bytes", "tm", 10.5, "middle")
    for i in range(16):
        f.text(x0 + i * cw + cw / 2, 40, str(i), "tm", 9, "middle", None, True)

    def row(y, label, inum, name, acc):
        f.text(24, y + 20, label, "t", 11, None, None, True)
        f.rect(x0, y, 2 * cw, 30, "s fs", 0)
        f.text(x0 + cw, y + 20, inum, "t", 11.5, "middle", 600, True)
        for i in range(14):
            x = x0 + (2 + i) * cw
            c = name[i] if i < len(name) else None
            a = acc and i == 13
            f.rect(x, y, cw, 30, "a af" if a else ("s f" if c else "m f"), 0)
            if c:
                f.text(x + cw / 2, y + 20, c, "ta" if a else "t", 12, "middle", 600 if a else None, True)
            else:
                f.text(x + cw / 2, y + 19, "\\0", "tm", 9.5, "middle", None, True)
    row(52, "README", "2", "README", False)
    row(108, "abcdefghij...", "16", "abcdefghijklmn", True)  # a new file on the 07.03 disk
    f.text(x0 + 15 * cw + cw, 168, "14 characters fill the field: no NUL, so namecmp uses strncmp(s, t, DIRSIZ)", "ta", 10.5, "end")
    f.text(x0 + 15 * cw + cw, 186, "16 bytes an entry, 64 to a block; inum 0 marks a free slot", "tm", 10.5, "end")
    return f


def openfiles():
    f = Fig("f0507a", "Descriptors, open files and an inode", 330)
    f.text(24, 20, "open(\"a\") as fd 3, dup(3) as fd 4, fork(), write 6 bytes; then the parent opens a again as fd 5", "tm", 10.5)
    px, pw, rh = 24, 150, 21

    def proc(y, title, fds):
        f.text(px, y - 8, title, "t", 11.5, None, 600)
        f.text(px + pw, y - 8, "ofile[]", "tm", 10, "end", None, True)
        ys = {}
        for i, (fd, target) in enumerate(fds):
            yy = y + i * rh
            f.rect(px, yy, pw, rh, "s f" if target != "console" else "m f", 0)
            f.text(px + 10, yy + 15, f"[{fd}]", "tm", 10.5, None, None, True)
            if target == "console":
                f.text(px + pw - 10, yy + 15, "console", "tm", 10.5, "end")
            ys[fd] = (yy + rh / 2, target)
        return ys
    p = proc(52, "parent", [(0, "console"), (1, "console"), (2, "console"), (3, "F1"), (4, "F1"), (5, "F2")])
    c = proc(212, "child", [(0, "console"), (1, "console"), (2, "console"), (3, "F1"), (4, "F1")])
    # struct files
    fx, fw = 286, 150
    files = {"F1": (60, [("type", "FD_INODE"), ("ref", "4"), ("off", "6"), ("ip", "")]),
             "F2": (218, [("type", "FD_INODE"), ("ref", "1"), ("off", "0"), ("ip", "")])}
    fy = {}
    f.text(fx, 44, "ftable: struct file", "tm", 10.5)
    for name, (y, rows) in files.items():
        f.rect(fx, y, fw, 4 * 22 + 8, "s f", 8)
        for i, (k, v) in enumerate(rows):
            yy = y + 20 + i * 22
            acc = name == "F1" and k == "off"
            if acc:
                f.rect(fx + 6, yy - 15, fw - 12, 21, "a af", 4)
            f.text(fx + 12, yy, k, "ta" if acc else "tm", 10.5, None, 600 if acc else None, True)
            f.text(fx + fw - 12, yy, v, "ta" if acc else "t", 10.5, "end", 600 if acc else None, True)
        fy[name] = (y, y + 20 + 3 * 22 - 4)
        f.text(fx + fw + 8, y + 16, name, "t", 11.5, None, 600, True)
    # fd arrows
    k = {"F1": 0, "F2": 0}
    for ys in (p, c):
        for fd, (yy, target) in ys.items():
            if target in fy:
                ty = fy[target][0] + 16 + k[target] * 18
                k[target] += 1
                f.path(f"M{px + pw} {yy} C {px + pw + 50} {yy}, {fx - 50} {ty}, {fx - 2} {ty}", "s", arrow=True)
    # inode
    ix, iw = 488, 128
    iy = 140
    f.text(ix, iy - 8, "itable: struct inode", "tm", 10.5)
    f.rect(ix, iy, iw, 74, "s fs", 8)
    for i, (k, v) in enumerate((("inum", "16"), ("ref", "2"), ("size", "6"))):
        yy = iy + 20 + i * 20
        f.text(ix + 12, yy, k, "tm", 10.5, None, None, True)
        f.text(ix + iw - 12, yy, v, "t", 10.5, "end", None, True)
    for name, (y, ipy) in fy.items():
        f.path(f"M{fx + fw - 30} {ipy - 4} L{fx + fw + 14} {ipy - 4} C {fx + fw + 34} {ipy - 4}, {ix - 20} {iy + 37}, {ix - 2} {iy + 37}", "s", arrow=True)
    f.text(494, 240, "fds 3 and 4 in both", "ta", 10.5)
    f.text(494, 256, "processes move one off;", "ta", 10.5)
    f.text(494, 272, "fd 5 has its own", "ta", 10.5)
    return f


FIGS = [
    ("05.01-descriptor-chain", desc_chain),
    ("05.01-rings", rings),
    ("05.02-lru", lru),
    ("05.02-buf-locks", buflocks),
    ("05.03-bitmap", bitmap),
    ("05.04-commit", logsteps),
    ("05.05-inode-blocks", inode),
    ("05.05-readi-pieces", chunks),
    ("05.06-path-walk", pathwalk),
    ("05.06-dirent", dirent),
    ("05.07-fd-file-inode", openfiles),
]

if __name__ == "__main__":
    for name, fn in FIGS:
        print(write(MOD, name, fn()))
