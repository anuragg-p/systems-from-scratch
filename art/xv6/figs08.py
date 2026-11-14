"""Inline lesson figures for xv6 module 08 (the network).

Writes tracks/xv6/lessons/08-network/figures/08.LL-name.svg. The bytes are real:
frames recorded with make qemu PCAP=net.pcap (QEMU's filter-dump) while running
nslookup example.com, read back with tcpdump and a hex dump. Checksums were
recomputed from those bytes.
"""
from figlib import Fig, write

MOD = "08-network"

# The ARP request xv6 sent for 10.0.2.3 (42 bytes) and the IP/UDP/DNS query that
# followed it, from the recording.
ARP_REQ = bytes.fromhex("ffffffffffff525400123456080600010800060400015254001234560a00020f0000000000000a000203")
QUERY_IP = bytes.fromhex("4500003900000000401162a30a00020f0a000203c00000350025fb20")
QUERY_DNS = bytes.fromhex("5cce01000001000000000000076578616d706c6503636f6d0000010001")
ANSWER_DNS = bytes.fromhex("5cce81800001000200000000076578616d706c6503636f6d0000010001"
                           "c00c00010001000000740004ac4293f3c00c000100010000007400046814179a")


def hx(b):
    return " ".join(f"{x:02x}" for x in b)


def cell(f, x, y, w, h, top, val, cls="s f", acc=False, sub=None, vsize=11):
    """A field box: name on top (small, muted), value in mono below."""
    f.rect(x, y, w, h, cls, 0)
    f.text(x + w / 2, y + 14, top, "ta" if acc else "tm", 9.5, "middle")
    f.text(x + w / 2, y + (31 if sub else 34), val, "ta" if acc else "t", vsize, "middle", 600 if acc else None, True)
    if sub:
        f.text(x + w / 2, y + 45, sub, "ta" if acc else "tm", 9.5, "middle")


# ================================================================== 08.01

def queues():
    f = Fig("f0801a", "The receive queue and the transmit queue", 312)
    x0, cw, gap = 150, 54, 4

    def row(y, label, sub, states, legend):
        f.text(24, y + 16, label, "t", 11.5, "start", 600, True)
        f.text(24, y + 31, sub, "tm", 10.5)
        for i, st in enumerate(states):
            x = x0 + i * (cw + gap)
            card = st in ("card", "sending", "filled")
            cls = {"card": "a af", "sending": "a af", "filled": "a fa", "free": "s f", "driver": "s fs"}[st]
            f.rect(x, y, cw, 34, cls, 4)
            f.text(x + cw / 2, y - 5, f"buf[{i}]", "tm", 9.5, "middle", None, True)
            word = {"card": "empty", "sending": "frame", "filled": "frame", "free": "free", "driver": "frame"}[st]
            f.text(x + cw / 2, y + 21, word, "t" if st != "filled" else "f", 10.5, "middle", 600 if st == "filled" else None)
        f.text(x0, y + 50, legend, "tm", 10.5)

    row(26, "queue 0", "receive", ["card", "card", "filled", "card", "card", "card", "card", "card"],
        "all eight belong to the card from init on: it fills one per arriving frame")
    steps = [("1", "frame arrives: the card writes buf[2], puts 2 in the used ring, raises irq 2"),
             ("2", "virtio_net_intr: net_rx(buf[2] + 12, len - 12), the stack takes what it needs"),
             ("3", "2 goes back in the avail ring; QUEUE_NOTIFY = 0: the card has it again")]
    for i, (n, s) in enumerate(steps):
        y = 108 + i * 19
        f.circle(158, y - 4, 7, "a af")
        f.text(158, y - 0.5, n, "ta", 9.5, "middle", 600, True)
        f.text(172, y, s, "t", 10.5)
    f.line(24, 170, 616, 170, "m", dash=True)
    row(196, "queue 1", "transmit", ["free", "sending", "free", "free", "free", "free", "free", "free"],
        "a buffer is the card's only while txbusy[i] is 1")
    steps = [("1", "virtio_net_send: header and frame copied into a free buffer, txbusy[1] = 1"),
             ("2", "1 in the avail ring; QUEUE_NOTIFY = 1; the card sends it, no interrupt"),
             ("3", "the next send finds 1 in the used ring and sets txbusy[1] = 0")]
    for i, (n, s) in enumerate(steps):
        y = 274 + i * 17
        f.circle(158, y - 4, 7, "s f")
        f.text(158, y - 0.5, n, "t", 9.5, "middle", 600, True)
        f.text(172, y, s, "t", 10.5)
    return f


def buffer():
    f = Fig("f0801b", "One buffer: the virtio header, then the Ethernet frame", 196)
    y, h = 58, 44
    segs = [(24, 116, "virtio_net_hdr", "12 bytes, all 0", "a af"),
            (140, 66, "dst", "6", "s f"), (206, 66, "src", "6", "s f"), (272, 44, "type", "2", "s f"),
            (316, 194, "payload: ARP or IP", "up to 1500 bytes", "s fs"), (510, 106, "unused", "to 2047", "m f")]
    for x, w, name, sub, cls in segs:
        f.rect(x, y, w, h, cls, 0, dash=cls == "m f")
        acc = cls.startswith("a")
        f.text(x + w / 2, y + 19, name, "ta" if acc else ("tm" if cls == "m f" else "t"), 10.5 if w < 80 else 11, "middle",
               600 if acc else None, name in ("virtio_net_hdr", "dst", "src", "type"))
        f.text(x + w / 2, y + 34, sub, "ta" if acc else "tm", 9.5, "middle")
    for x, off in ((24, "0"), (140, "12"), (206, "18"), (272, "24"), (316, "26"), (510, "1526")):
        f.line(x, y + h, x, y + h + 8, "m")
        f.text(x, y + h + 20, off, "tm", 10, "middle", None, True)
    f.brace_h(140, 510, 40, "s", up=True)
    f.text(325, 30, "the Ethernet frame: at most 14 + 1500 = 1514 bytes", "t", 10.5, "middle")
    f.brace_h(24, 140, 132, "a")
    f.text(24, 154, "flags gso_type hdr_len gso_size csum_start csum_offset num_buffers", "ta", 10, "start", None, True)
    f.text(24, 172, "no offload features were accepted, so the driver writes zeroes and skips it on receive", "tm", 10.5)
    f.text(616, 154, "net_rx(buf + 12, len - 12)", "t", 10.5, "end", 600, True)
    f.text(616, 172, "2048 bytes: two buffers per page", "tm", 10.5, "end")
    return f


# ================================================================== 08.02

def arp_packet():
    f = Fig("f0802a", "An ARP request inside an Ethernet frame", 282)
    bw = 38
    x0 = 70
    b = ARP_REQ

    def field(row, start, n, name, val, sub=None, acc=False, cls=None):
        x = x0 + (start - row * 14) * bw
        y = 30 + row * 74
        cell(f, x, y, n * bw, 54, name, val, cls or ("a af" if acc else "s f"), acc, sub, 10.5 if n > 1 else 10.5)
        f.text(x + 3, y + 66, str(start), "tm", 9, "start", None, True)

    for r, label, sub in ((0, "0", "Ethernet"), (1, "14", "ARP"), (2, "28", "ARP")):
        f.text(x0 - 10, 30 + r * 74 + 24, sub, "tm", 10.5, "end")
        f.text(x0 - 10, 30 + r * 74 + 39, f"+{label}", "tm", 9.5, "end", None, True)
    field(0, 0, 6, "destination", "ff:ff:ff:ff:ff:ff", "broadcast")
    field(0, 6, 6, "source", "52:54:00:12:34:56", "this card")
    field(0, 12, 2, "type", "08 06", "ARP")
    field(1, 14, 2, "hrd", "00 01", "Ethernet")
    field(1, 16, 2, "pro", "08 00", "IPv4")
    field(1, 18, 1, "hln", "06")
    field(1, 19, 1, "pln", "04")
    field(1, 20, 2, "op", "00 01", "request", acc=True)
    field(1, 22, 6, "sha: sender's card", "52:54:00:12:34:56")
    field(2, 28, 4, "sip: sender's IP", hx(b[28:32]), "10.0.2.15")
    field(2, 32, 6, "tha: target's card", "00:00:00:00:00:00", "unknown: the question")
    field(2, 38, 4, "tip: target's IP", hx(b[38:42]), "10.0.2.3", acc=True)
    f.text(24, 272, "42 bytes. The answer swaps the pairs: sender 10.0.2.3 at 52:55:0a:00:02:03, op 00 02.", "tm", 10.5)
    return f


def exchange():
    f = Fig("f0802b", "ARP in both directions", 350)
    lx, rx = 160, 540
    f.text(lx, 20, "xv6", "t", 12, "middle", 600)
    f.text(lx, 35, "10.0.2.15", "tm", 10, "middle", None, True)
    f.text(rx, 20, "QEMU's network", "t", 12, "middle", 600)
    f.text(rx, 35, "10.0.2.2, 10.0.2.3", "tm", 10, "middle", None, True)
    f.line(lx, 44, lx, 340, "m")
    f.line(rx, 44, rx, 340, "m")

    def msg(y, right, text, sub, cls="s"):
        x1, x2 = (lx + 4, rx - 4) if right else (rx - 4, lx + 4)
        f.line(x1, y, x2, y, cls, arrow=True)
        f.text((lx + rx) / 2, y - 6, text, "ta" if cls == "a" else "t", 10.5, "middle", None, True)
        if sub:
            f.text((lx + rx) / 2, y + 13, sub, "tm", 9.5, "middle")

    def note(y, lines):
        for i, t in enumerate(lines):
            f.text(lx - 10, y + i * 13, t, "ta", 10, "end")

    f.text(24, 62, "nslookup", "tm", 10.5, "start", 600)
    msg(80, True, "who-has 10.0.2.3? tell 10.0.2.15", "to ff:ff:ff:ff:ff:ff, 42 bytes", "a")
    msg(120, False, "10.0.2.3 is-at 52:55:0a:00:02:03", "to 52:54:00:12:34:56 only")
    note(124, ["cache 10.0.2.3"])
    msg(160, True, "UDP to 10.0.2.3:53, the DNS question", "to 52:55:0a:00:02:03")
    f.line(24, 186, 616, 186, "m", dash=True)
    f.text(24, 206, "udpecho 2000", "tm", 10.5, "start", 600)
    f.text(rx + 10, 210, "the host", "tm", 10, "start")
    f.text(rx + 10, 223, "sent hello", "tm", 10, "start")
    msg(226, False, "who-has 10.0.2.15? tell 10.0.2.2", "to ff:ff:ff:ff:ff:ff")
    note(230, ["cache 10.0.2.2", "(the merge)"])
    msg(270, True, "10.0.2.15 is-at 52:54:00:12:34:56", "to 52:55:0a:00:02:02 only", "a")
    msg(306, False, "UDP hello, 10.0.2.2 > 10.0.2.15:2000", None)
    msg(334, True, "UDP hello back: no request of its own", None)
    return f


# ================================================================== 08.03

def headers():
    f = Fig("f0803a", "The IPv4 and UDP headers of a DNS query", 300)
    x0, bw, rh = 96, 112, 34
    q = QUERY_IP
    for i in range(4):
        f.text(x0 + i * bw + bw / 2, 20, f"byte {i}", "tm", 9.5, "middle", None, True)

    def row(r, fields):
        y = 28 + r * rh
        f.text(x0 - 10, y + 22, str(r * 4), "tm", 10, "end", None, True)
        x = x0
        for n, name, val, acc in fields:
            w = n * bw
            f.rect(x, y, w, rh, "a af" if acc else ("s fs" if r >= 5 else "s f"), 0)
            f.text(x + 8, y + 21, name, "ta" if acc else "tm", 10, "start")
            f.text(x + w - 8, y + 21, val, "ta" if acc else "t", 10.5, "end", 600 if acc else None, True)
            x += w

    row(0, [(1, "vhl", "45", False), (1, "tos", "00", False), (2, "total length", "00 39 = 57", False)])
    row(1, [(2, "id", "00 00", False), (2, "flags, fragment offset", "00 00", False)])
    row(2, [(1, "ttl", "40 = 64", False), (1, "protocol", "11 = UDP", False), (2, "header checksum", hx(q[10:12]), True)])
    row(3, [(4, "source", "0a 00 02 0f = 10.0.2.15", False)])
    row(4, [(4, "destination", "0a 00 02 03 = 10.0.2.3", False)])
    row(5, [(2, "source port", "c0 00 = 49152", False), (2, "destination port", "00 35 = 53", False)])
    row(6, [(2, "length", "00 25 = 37", False), (2, "checksum", hx(q[26:28]), True)])
    y = 28 + 7 * rh
    f.text(x0 - 10, y + 16, "28", "tm", 10, "end", None, True)
    f.rect(x0, y, 4 * bw, 22, "m", 0, dash=True)
    f.text(x0 + 2 * bw, y + 15, "29 bytes of DNS query (08.05)", "tm", 10, "middle")
    for y1, y2, name, sub in ((28, 28 + 5 * rh, "IPv4", "20 bytes"), (28 + 5 * rh, 28 + 7 * rh, "UDP", "8 bytes")):
        f.path(f"M{x0 + 4 * bw + 8} {y1 + 2} L{x0 + 4 * bw + 14} {y1 + 2} L{x0 + 4 * bw + 14} {y2 - 2} L{x0 + 4 * bw + 8} {y2 - 2}", "m")
        f.text(x0 + 4 * bw + 22, (y1 + y2) / 2 - 2, name, "t", 11, "start", 600)
        f.text(x0 + 4 * bw + 22, (y1 + y2) / 2 + 12, sub, "tm", 10)
    return f


def checksum():
    f = Fig("f0803b", "Two Internet checksums, worked by hand", 280)
    words = ["4500", "0039", "0000", "0000", "4011", "0000", "0a00", "020f", "0a00", "0203"]
    names = ["vhl tos", "length", "id", "flags", "ttl proto", "checksum", "source", "", "destination", ""]
    x, y0, lh = 132, 40, 18
    f.text(24, 20, "the IP header, 10 words", "t", 11, "start", 600)
    for i, (w, n) in enumerate(zip(words, names)):
        y = y0 + i * lh
        acc = n == "checksum"
        f.text(x, y, ("+ " if i else "  ") + w, "ta" if acc else "t", 11, "end", None, True)
        f.text(x + 12, y, n + (" (0 while summing)" if acc else ""), "ta" if acc else "tm", 10)
    yl = y0 + 10 * lh - 10
    f.line(70, yl, x + 2, yl, "s")
    f.text(x, yl + 16, "9d5c", "t", 11, "end", 600, True)
    f.text(x + 12, yl + 16, "sum, no carry", "tm", 10)
    f.text(x, yl + 36, "62a3", "ta", 11, "end", 600, True)
    f.text(x + 12, yl + 36, "complement: goes in bytes 10-11", "ta", 10)
    f.text(24, 268, "the receiver: 9d5c + 62a3 = ffff, complement 0000", "tm", 10.5)

    rx = 360
    f.text(rx, 20, "UDP: pseudo-header, header, data", "t", 11, "start", 600)
    rows = [("pseudo-header", "0a00 020f 0a00 0203", "addresses"), ("", "0011 0025", "protocol, UDP length"),
            ("UDP header", "c000 0035 0025 0000", "ports, length, sum 0"),
            ("data", "5cce 0100 0001 ...", "29 bytes, 15 words:"), ("", "... 0001 0100", "the odd last byte is 01 00")]
    for i, (a, b, c) in enumerate(rows):
        y = 44 + i * 30
        if a:
            f.text(rx, y, a, "tm", 10)
        f.text(rx, y + 14, b, "t", 10.5, "start", None, True)
        f.text(616, y + 14, c, "tm", 9.5, "end")
    yy = 44 + 5 * 30 + 6
    f.line(rx, yy - 12, 616, yy - 12, "s")
    f.text(rx, yy + 6, "3 04dc", "t", 11, "start", 600, True)
    f.text(rx + 70, yy + 6, "sum: 3 carried out of 16 bits", "tm", 10)
    f.text(rx, yy + 26, "04df", "t", 11, "start", 600, True)
    f.text(rx + 70, yy + 26, "fold: 04dc + 3", "tm", 10)
    f.text(rx, yy + 46, "fb20", "ta", 11, "start", 600, True)
    f.text(rx + 70, yy + 46, "complement: bytes 26-27", "ta", 10)
    f.line(330, 12, 330, 272, "m", dash=True)
    return f


def path():
    f = Fig("f0803c", "One datagram down the stack and back up", 392)
    lx, rx, w, h, step = 24, 376, 240, 36, 50
    down = [("sendto()", "user space: fd, buf, n, ip, port"), ("socksend", "copyin the data to page + 42"),
            ("udp_send", "8-byte UDP header at + 34"), ("ip_send", "20-byte IP header at + 14, arp_resolve"),
            ("eth_send", "14-byte Ethernet header at + 0"), ("virtio_net_send", "copy header and frame to the card")]
    up = [("recvfrom()", "the process wakes with the data"), ("sock_deliver", "destination port: queue, wakeup"),
          ("udp_rx", "checksum and length"), ("ip_rx", "checksum, MYIP, protocol 17"),
          ("net_rx", "our card or broadcast, ethertype"), ("virtio_net_intr", "irq 2: frame at buffer + 12")]
    f.text(lx, 18, "sending", "t", 11, "start", 600)
    f.text(rx + w, 18, "receiving", "t", 11, "end", 600)
    for i, ((a, b), (c, d)) in enumerate(zip(down, up)):
        y = 28 + i * step
        user = i == 0
        for x, name, sub in ((lx, a, b), (rx, c, d)):
            f.rect(x, y, w, h, "s fs" if user else "s f", 6)
            f.text(x + 10, y + 15, name, "t", 11, "start", 600, True)
            f.text(x + 10, y + 29, sub, "tm", 9.5, "start")
        if i < 5:
            f.line(lx + w / 2, y + h, lx + w / 2, y + step - 1, "s", arrow=True)
            f.line(rx + w / 2, y + step, rx + w / 2, y + h + 1, "s", arrow=True)
    yw = 28 + 5 * step + h / 2
    f.line(lx + w + 2, yw, rx - 2, yw, "a", arrow=True)
    f.text((lx + w + rx) / 2, yw - 7, "the wire", "ta", 10, "middle")
    # the page
    py, ph = 344, 26
    f.text(24, py - 10, "the page socksend fills, back to front", "tm", 10)
    segs = [(24, 70, "eth", "0"), (94, 100, "ip", "14"), (194, 40, "udp", "34"), (234, 230, "data", "42"), (464, 152, "", "")]
    for x, ww, name, off in segs:
        if not name:
            f.rect(x, py, ww, ph, "m", 0, dash=True)
            continue
        acc = name == "data"
        f.rect(x, py, ww, ph, "a af" if acc else "s f", 0)
        f.text(x + ww / 2, py + 17, name, "ta" if acc else "t", 10.5, "middle", 600 if acc else None, True)
        f.text(x, py + ph + 13, off, "tm", 9.5, "middle", None, True)
    f.text(540, py + 17, "rest of the page", "tm", 10, "middle")
    return f


# ================================================================== 08.04

def sockqueue():
    f = Fig("f0804a", "A socket's receive queue", 270)
    sx, sy, sw = 24, 56, 150
    f.text(sx, sy - 10, "socks.sock[0]", "t", 11, "start", 600, True)
    f.rect(sx, sy, sw, 112, "s f", 8)
    for i, (k, v) in enumerate((("used", "1"), ("port", "2000"), ("head", ""), ("tail", ""), ("qlen", "2"))):
        y = sy + 20 + i * 20
        f.text(sx + 12, y, k, "tm", 10.5, "start", None, True)
        f.text(sx + sw - 12, y, v, "t", 10.5, "end", None, True)
    dx, dw, dh = 236, 150, 112
    pages = [("10.0.2.2", "64407", "5", "hello"), ("10.0.2.2", "61179", "5", "world")]
    for j, (src, sp, ln, data) in enumerate(pages):
        x = dx + j * (dw + 46)
        f.text(x, sy - 10, "one kalloc'd page", "tm", 10)
        f.rect(x, sy, dw, dh, "a af", 8)
        for i, (k, v) in enumerate((("next", ""), ("src", src), ("sport", sp), ("len", ln), ("data", data))):
            y = sy + 20 + i * 20
            f.text(x + 12, y, k, "ta", 10.5, "start", None, True)
            f.text(x + dw - 12, y, v if k != "next" else ("0" if j == 1 else ""), "ta", 10.5, "end", 600 if k == "data" else None, True)
    f.path(f"M{sx + sw - 20} {sy + 56} C {sx + sw + 30} {sy + 56}, {dx - 40} {sy + 16}, {dx - 2} {sy + 16}", "s", arrow=True)
    f.path(f"M{sx + sw - 20} {sy + 76} C {sx + sw + 60} {sy + 150}, {dx + dw + 46 - 40} {sy + 150}, {dx + dw + 46 + 30} {sy + dh + 2}", "s", arrow=True)
    f.path(f"M{dx + dw - 20} {sy + 16} L{dx + dw + 44} {sy + 16}", "a", arrow=True)
    # the two sides
    f.text(24, 222, "a process: sockrecv", "t", 11, "start", 600, True)
    f.text(24, 238, "sleep(so) while head == 0; take the head;", "tm", 10.5)
    f.text(24, 254, "copyout, kfree", "tm", 10.5)
    f.text(616, 222, "the interrupt: sock_deliver", "t", 11, "end", 600, True)
    f.text(616, 238, "kalloc, copy in, append at the tail,", "tm", 10.5, "end")
    f.text(616, 254, "wakeup(so); the 17th waiting is dropped", "tm", 10.5, "end")
    f.text(320, 30, "both hold socks.lock", "tm", 10.5, "middle")
    return f


def fdsock():
    f = Fig("f0804b", "A file descriptor that leads to a socket", 272)
    px, pw = 24, 120
    for j, (name, y) in enumerate((("parent", 30), ("child, after fork", 152))):
        f.text(px, y - 8, name, "t", 11, "start", 600)
        f.rect(px, y, pw, 84, "s f", 8)
        f.text(px + 12, y + 18, "ofile[]", "tm", 10.5, "start", None, True)
        for i in range(4):
            yy = y + 30 + i * 13
            acc = i == 3
            f.text(px + 14, yy + 4, str(i), "ta" if acc else "tm", 10, "start", 600 if acc else None, True)
            f.rect(px + 30, yy - 5, 76, 11, "a af" if acc else "m f", 2)
    fx, fy, fw = 222, 80, 168
    f.text(fx, fy - 8, "ftable: struct file", "t", 11, "start", 600)
    f.rect(fx, fy, fw, 112, "s f", 8)
    for i, (k, v) in enumerate((("type", "FD_SOCK"), ("ref", "2"), ("readable", "1"), ("writable", "0"), ("sock", ""))):
        y = fy + 20 + i * 20
        f.text(fx + 12, y, k, "tm", 10.5, "start", None, True)
        f.text(fx + fw - 12, y, v, "t", 10.5, "end", 600 if k == "type" else None, True)
    for y in (30 + 30 + 39, 152 + 30 + 39):
        f.path(f"M{px + 106} {y} C {px + 150} {y}, {fx - 40} {fy + 56}, {fx - 2} {fy + 56}", "a", arrow=True)
    sx, sw = 448, 168
    f.text(sx, fy - 8, "socks.sock[0]", "t", 11, "start", 600, True)
    f.rect(sx, fy, sw, 72, "a af", 8)
    f.text(sx + 12, fy + 22, "port", "ta", 10.5, "start", None, True)
    f.text(sx + sw - 12, fy + 22, "49152", "ta", 10.5, "end", 600, True)
    f.text(sx + 12, fy + 44, "queue", "ta", 10.5, "start", None, True)
    f.text(sx + sw - 12, fy + 44, "datagrams", "ta", 10.5, "end")
    f.path(f"M{fx + fw - 20} {fy + 100} C {fx + fw + 20} {fy + 100}, {sx - 30} {fy + 36}, {sx - 2} {fy + 36}", "s", arrow=True)
    f.text(sx, fy + 98, "close or exit: ref 2, 1, 0;", "tm", 10.5)
    f.text(sx, fy + 114, "the last runs fileclose_sock:", "tm", 10.5)
    f.text(sx, fy + 130, "sockclose frees the port", "tm", 10.5)
    f.text(24, 264, "socket(0) put the socket in fd 3; fork copied the descriptor, so both reach the same struct file", "tm", 10.5)
    return f


# ================================================================== 08.05

def dns_query():
    f = Fig("f0805a", "A DNS query, byte by byte", 232)
    q = QUERY_DNS
    x0, bw = 24, 49
    y = 34
    hdr = [("id", hx(q[0:2]), "any number"), ("flags", hx(q[2:4]), "RD: recurse"), ("qdcount", hx(q[4:6]), "1 question"),
           ("ancount", hx(q[6:8]), ""), ("nscount", hx(q[8:10]), ""), ("arcount", hx(q[10:12]), "")]
    f.text(x0, y - 12, "header", "t", 11, "start", 600)
    for i, (name, val, sub) in enumerate(hdr):
        x = x0 + i * 2 * bw
        acc = name == "flags"
        cell(f, x, y, 2 * bw, 54, name, val, "a af" if acc else "s f", acc, sub or None)
        f.text(x + 3, y + 66, str(2 * i), "tm", 9, "start", None, True)
    y2 = 132
    f.text(x0, y2 - 12, "question", "t", 11, "start", 600)
    name = q[12:25]
    bw2 = 34
    for i, ch in enumerate(name):
        x = x0 + i * bw2
        isl = ch < 32
        f.rect(x, y2, bw2, 36, "a af" if isl else "s f", 0)
        f.text(x + bw2 / 2, y2 + 16, f"{ch:02x}", "ta" if isl else "tm", 9.5, "middle", None, True)
        f.text(x + bw2 / 2, y2 + 30, str(ch) if isl else chr(ch), "ta" if isl else "t", 11, "middle", 600 if isl else None, True)
        if i in (0, 8, 12):
            f.text(x + 3, y2 + 48, str(12 + i), "tm", 9, "start", None, True)
    xe = x0 + 13 * bw2
    for j, (name2, val, sub) in enumerate((("QTYPE", "00 01", "A"), ("QCLASS", "00 01", "IN"))):
        x = xe + j * 75
        f.rect(x, y2, 75, 36, "s f", 0)
        f.text(x + 37.5, y2 + 16, f"{name2} {sub}", "tm", 9.5, "middle")
        f.text(x + 37.5, y2 + 30, val, "t", 11, "middle", None, True)
        f.text(x + 3, y2 + 48, str(25 + 2 * j), "tm", 9, "start", None, True)
    f.text(24, 210, "length bytes, not dots: 7 example 3 com, and a 0 for the root. 29 bytes in all.", "tm", 10.5)
    return f


def dns_answer():
    f = Fig("f0805b", "A DNS answer with compressed names", 358)
    a = ANSWER_DNS
    x0 = 40
    y = 30
    f.text(x0, y - 10, "header", "t", 11, "start", 600)
    hdr = [("id", hx(a[0:2])), ("flags", hx(a[2:4])), ("qd", hx(a[4:6])), ("an", hx(a[6:8])), ("ns", hx(a[8:10])), ("ar", hx(a[10:12]))]
    w = 60
    for i, (n, v) in enumerate(hdr):
        acc = n in ("flags", "an")
        cell(f, x0 + i * w, y, w, 44, n, v, "a af" if acc else "s f", acc)
    f.text(x0 + 6 * w + 14, y + 18, "81 80: a response (QR), RD and RA,", "tm", 10)
    f.text(x0 + 6 * w + 14, y + 33, "response code 0; an: 2 answers", "tm", 10)
    yq = 106
    f.text(x0, yq - 10, "question, as sent", "t", 11, "start", 600)
    f.rect(x0, yq, 250, 32, "s f", 0)
    f.text(x0 + 10, yq + 20, "07 example 03 com 00", "t", 10.5, "start", None, True)
    f.text(x0 + 3, yq + 44, "12", "tm", 9, "start", None, True)
    f.rect(x0 + 250, yq, 116, 32, "s f", 0)
    f.text(x0 + 308, yq + 20, "00 01  00 01", "t", 10.5, "middle", None, True)
    f.text(x0 + 253, yq + 44, "25", "tm", 9, "start", None, True)
    f.text(x0 + 380, yq + 13, "c0 0c: the top two bits are set,", "ta", 10)
    f.text(x0 + 380, yq + 28, "so it points to the name at offset 12", "ta", 10)
    recs = [(29, a[29:45], "172.66.147.243"), (45, a[45:61], "104.20.23.154")]
    yr0 = 186
    for k, (off, r, ip) in enumerate(recs):
        yr = yr0 + k * 84
        f.text(x0, yr - 10, f"answer {k + 1}", "t", 11, "start", 600)
        fields = [("name", hx(r[0:2]), 56, True), ("type", hx(r[2:4]), 52, False), ("class", hx(r[4:6]), 52, False),
                  ("ttl", hx(r[6:10]), 104, False), ("rdlength", hx(r[10:12]), 66, False), ("rdata: " + ip, hx(r[12:16]), 206, False)]
        x = x0
        for n, v, ww, acc in fields:
            cell(f, x, yr, ww, 44, n, v, "a af" if acc else ("s fs" if n.startswith("rdata") else "s f"), acc)
            x += ww
        f.text(x0 + 3, yr + 56, str(off), "tm", 9, "start", None, True)
        # the pointer, back to offset 12
        f.path(f"M{x0 + 4} {yr + 30} C {x0 - 26} {yr + 24}, {x0 - 26} {yq + 20}, {x0 - 2} {yq + 16}", "a", arrow=True)
    f.text(x0, 348, "type 00 01 is A, ttl 00 00 00 74 is 116 seconds, rdlength 4: one IPv4 address", "tm", 10.5)
    return f


FIGS = [
    ("08.01-queues", queues),
    ("08.01-buffer", buffer),
    ("08.02-arp-packet", arp_packet),
    ("08.02-exchange", exchange),
    ("08.03-headers", headers),
    ("08.03-checksum", checksum),
    ("08.03-path", path),
    ("08.04-queue", sockqueue),
    ("08.04-fd", fdsock),
    ("08.05-query", dns_query),
    ("08.05-answer", dns_answer),
]

if __name__ == "__main__":
    for name, fn in FIGS:
        print(write(MOD, name, fn()))
