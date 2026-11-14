"""Track xv6: a teaching Unix kernel for RISC-V, MIT's xv6 rebuilt lesson by lesson (UPSTREAM).

Fixtures the lesson tests use:

    boot(t, ...)        build-test kernel under QEMU -> Session on the serial console
    selftest(s, id)     wait for the kernel's own check for lesson `id` to report ok
    shell(t, ...)       boot all the way to the shell prompt
    run(s, cmd)         type a shell command, return what it printed
    tool(name)          path to a cross tool, e.g. tool("objdump")

and for the network (module 08):

    boot(t, udpfwd=[(host_port, guest_port)])
                        QEMU's user-mode network (the default), forwarding UDP
                        from the host's 127.0.0.1 into the guest
    Wire(); boot(t, net=wire)
                        the test is the whole network: it sees every Ethernet
                        frame the guest sends and can send it any frame
    free_port()         a UDP port on 127.0.0.1 nothing holds right now
    arp_frame, udp_frame, parse_frame, inet_checksum
                        build and take apart Ethernet/ARP/IPv4/UDP

and for the screen, keyboard and mouse (module 09), which every boot has
unless it says gui=False:

    s.qmp               the boot's QMP socket (QEMU's machine protocol)
    s.qmp.screen()      a screenshot: shot[x, y] is the pixel, 0xRRGGBB
    s.qmp.key("a"), s.qmp.move(x, y), s.qmp.click()
                        press keys and move the mouse, in screen pixels
    wait_screen(s, what, ok)
                        screenshots until ok(shot) is true, or Fail

The test kernel is built with SELFTEST=1. That compiles kernel/selftest.c,
whose checks print lines like "[02.02] ok" or "[02.02] FAIL ...". Lessons
low in the stack (memory, traps, scheduling) are tested from inside the
kernel that way; lessons above the system-call line are tested from the
shell, the way a user would.
"""

import json
import os
import re
import select
import shutil
import socket
import struct
import sys
import subprocess
import time

from harness.core import Fail

TITLE = "A Unix kernel for RISC-V, from scratch"
KIND = "kernel"
SUMMARY = "Boot, memory, traps, processes, a crash-safe file system, and a shell."

# The industry code this track is built on (see harness/web/views.py, upstreams()). The
# site shows it on the overview, on the home card and on /credits, which prints
# licence_file whole; "derived": the code is derived from it, so every lesson page says so
# too. LICENSE comes with the project's files from the first lesson (FILES_FROM).
UPSTREAM = {
    "name": "xv6-riscv",
    "url": "https://github.com/mit-pdos/xv6-riscv",
    "licence": "MIT",
    "copyright": "Copyright (c) 2006-2024 Frans Kaashoek, Robert Morris, Russ Cox, "
                 "Massachusetts Institute of Technology",
    "owes": "The kernel taught here is MIT's xv6 for RISC-V, with this course's lessons, "
            "build-up and two extension modules.",
    "derived": True,
    "licence_file": "LICENSE",
    "chip": "based on xv6-riscv",
}

TEST_BUILD = "build-test"

# Files that may hold "@build NN.LL" regions (see harness/workspace.py),
# and what replaces a region's code when a learner's workspace cuts it.
SOURCES = ["kernel/*.c", "kernel/*.S", "user/*.c", "mkfs/*.c"]
# Built into the kernel but not part of the course: the internal self-tests.
# The web UI leaves these out of the file tree.
HIDDEN = ["kernel/selftest.c"]
# When each file comes into the project the site shows, lesson by lesson (see
# harness/timeline.py): a file with @build regions comes with its first region's
# lesson unless it is named here; every file without regions must be named. A file
# belongs to the first lesson that needs it to build or run, and the project at every
# lesson builds and boots (./learn check-timeline xv6). What later lessons add to a
# file outside their regions is marked "@from NN.LL" in the file itself.
FILES_FROM = {
    "Makefile": "00.01",
    "LICENSE": "00.01",          # xv6's licence goes with every copy of the project
    "kernel/kernel.ld": "01.01",
    "kernel/param.h": "01.01",
    "kernel/start.c": "01.01",
    "kernel/types.h": "01.01",
    "kernel/defs.h": "01.02",
    "kernel/main.c": "01.02",
    "kernel/memlayout.h": "01.02",
    "kernel/riscv.h": "01.02",
    "kernel/console.c": "01.03",
    "kernel/proc.c": "01.03",
    "kernel/proc.h": "01.03",
    "kernel/spinlock.h": "01.03",
    "kernel/uart.c": "01.03",
    "kernel/string.c": "02.02",
    "kernel/buf.h": "05.01",
    "kernel/fs.h": "05.01",
    "kernel/virtio.h": "05.01",
    "kernel/sleeplock.h": "05.02",
    "kernel/stat.h": "05.03",
    "mkfs/mkfs.c": "05.03",
    "README.md": "05.03",
    "kernel/file.h": "05.05",
    "kernel/syscall.h": "06.02",
    "kernel/sysfile.c": "06.02",
    "user/user.h": "06.02",
    "user/usys.pl": "06.02",
    "kernel/elf.h": "06.03",
    "kernel/sysproc.c": "06.04",
    "user/user.ld": "06.03",
    "kernel/fcntl.h": "06.07",
    "user/echo.c": "07.01",
    "user/printf.c": "07.01",
    "user/ulib.c": "07.01",
    "user/init.c": "07.02",
    "user/grep.c": "07.03",
    "user/kill.c": "07.03",
    "user/ln.c": "07.03",
    "user/mkdir.c": "07.03",
    "user/rm.c": "07.03",
    "user/usertests.c": "07.03",
    "kernel/net.h": "08.01",
    "user/udpecho.c": "08.04",
    "kernel/fb.h": "09.01",
    "user/colors.c": "09.02",
    "kernel/input.h": "09.03",
    "user/events.c": "09.03",
    "user/gui.c": "09.03",
    "user/gui.h": "09.03",
    "user/font.c": "09.04",
}
STUBS = {
    ".c": 'panic("{id}: {title} not written yet");',
    ".S": "unimp  # {id}: {title} not written yet",
}


def tool(name):
    for prefix in ("riscv64-elf-", "riscv64-unknown-elf-", "riscv64-linux-gnu-"):
        p = shutil.which(prefix + name)
        if p:
            return p
    raise Fail(f"no riscv64 {name} on PATH")


def make(t, build=TEST_BUILD, extra_cflags="", targets=None):
    """Build a SELFTEST kernel (and disk image, once the track has one)."""
    if targets is None:
        targets = [f"{build}/kernel/kernel"]
        if os.path.exists(os.path.join(t.root, "mkfs", "mkfs.c")):
            targets.append(f"{build}/fs.img")
    argv = ["make", "-s", f"BUILD={build}", "SELFTEST=1"]
    if extra_cflags:
        argv.append(f"EXTRA_CFLAGS={extra_cflags}")
    t.run(argv + targets)
    return os.path.join(t.root, build)


def build(t):
    make(t)


def boot(t, cpus=3, build=TEST_BUILD, image=None, disk=True, net="user", udpfwd=(),
         gui=True, qemu_args=(), name="qemu"):
    """Boot a kernel under QEMU and return a Session on its serial console.

    Each boot gets its own copy of the disk image, so tests cannot see each
    other's files. Pass image= to reuse one on purpose (a reboot).
    The network card is on QEMU's user-mode network (net="user"), with
    udpfwd's (host port, guest port) pairs forwarded; net=a Wire puts the
    test itself on the other end of the cable; net=None leaves the card out.
    The screen, keyboard and mouse are there unless gui=False; there is
    never a window. s.qmp is the boot's QMP socket either way.
    """
    kernel = os.path.join(t.root, build, "kernel", "kernel")
    argv = ["qemu-system-riscv64", "-machine", "virt", "-bios", "none",
            "-kernel", kernel, "-m", "128M", "-smp", str(cpus), "-nographic",
            "-global", "virtio-mmio.force-legacy=false"]
    fresh = os.path.join(t.root, build, "fs.img")
    if disk and (image or os.path.exists(fresh)):
        if image is None:
            image = os.path.join(t.tmp, "fs.img")
            shutil.copyfile(fresh, image)
        argv += ["-drive", f"file={image},if=none,format=raw,id=x0",
                 "-device", "virtio-blk-device,drive=x0,bus=virtio-mmio-bus.0"]
    if isinstance(net, Wire):
        argv += net.qemu_args()
    elif net:
        argv += netdev(udpfwd)
    if gui:
        argv += GUI_DEVICES
    qmp = Qmp(t.tmp, name)
    argv += qmp.qemu_args()
    argv += list(qemu_args)
    s = t.spawn(argv, name=name, fail_on=[r"panic: "])
    s.image = image
    s.qmp = qmp
    qmp.session = s
    if isinstance(net, Wire):
        net.session = s
    return s


def selftest(s, lesson_id, timeout=15):
    """Wait for the in-kernel check for lesson_id to say ok, or why not."""
    tag = r"\[" + re.escape(lesson_id) + r"\] "
    m = s.expect_line(tag + r"(ok|FAIL.*)", timeout=timeout)
    if m.group(1) != "ok":
        raise Fail(f"kernel check {lesson_id}: {m.group(1)}")
    return m


PROMPT = r"\$ $"


def shell(t, **kw):
    """Boot and wait for the first shell prompt."""
    s = boot(t, **kw)
    s.expect(r"init: starting sh", timeout=30)
    s.expect(r"\$ ", timeout=10)
    return s


def run(s, cmd, timeout=30):
    """Type a command at the shell and return its output (without the echo
    of the command itself and without the next prompt)."""
    s.sendline(cmd)
    s.expect(re.escape(cmd) + r"\r?\n", timeout=timeout)
    m = s.expect(r"(?s)(.*?)\$ ", timeout=timeout)
    return m.group(1)


# ---------------------------------------------------------------- run it (web UI)
#
# The track contract's optional "run it" hooks. The web UI calls them and knows
# nothing about QEMU: prepare(root) returns the command that builds the tree
# (or None), run_argv(root) returns the command that starts the system. Both
# run with cwd=root: the project as it stands at a lesson (./learn run xv6 --at
# NN.LL writes it to build/at/xv6/NN.LL/), or the finished track.

def prepare(root):
    """Command that builds the normal (not SELFTEST) kernel and disk image."""
    return ["make", "-s"]


def run_argv(root, display=None):
    """Like `make qemu`: the normal kernel with its disk, on the serial console.

    The disk is attached with snapshot=on, so a run never changes the image
    and every run starts from the same files. The network card (module 08)
    is on QEMU's user-mode network, with no ports forwarded, so any number
    of runs can share the machine. The screen (module 09) opens in a window
    when there is a desktop for one, as with make qemu; SCREEN=none in the
    environment leaves it out (display= overrides both: the -display args).
    A tree with no framebuffer yet (before 09.01) gets no window, as its
    Makefile's make qemu does not open one.
    """
    kernel = os.path.join(root, "build", "kernel", "kernel")
    argv = ["qemu-system-riscv64", "-machine", "virt", "-bios", "none",
            "-kernel", kernel, "-m", "128M", "-smp", "3", "-nographic",
            "-global", "virtio-mmio.force-legacy=false"]
    image = os.path.join(root, "build", "fs.img")
    if os.path.exists(image):
        argv += ["-drive", f"file={image},if=none,format=raw,id=x0,snapshot=on",
                 "-device", "virtio-blk-device,drive=x0,bus=virtio-mmio-bus.0"]
    if display is None:
        display = screen_args() if os.path.exists(os.path.join(root, "kernel", "fb.h")) else []
    return argv + netdev() + GUI_DEVICES + list(display)


# ---------------------------------------------------------------- the project at each lesson
#
# Internal: ./learn check-timeline xv6 builds the project as the site shows it at each
# lesson (harness/timeline.py) and boots it with these.

TIMELINE_FAIL = [r"panic: ", r"unexpected scause", r"unknown sys call", r"exec \S+ failed"]


def timeline_run(root):
    """run_argv for a boot nobody watches: never a window."""
    return run_argv(root, display=["-display", "none"])


def timeline_boot(lesson_id):
    """What the project as it stands at a lesson does when it boots: (text to type or None,
    regex to wait for) steps. Before 01.03 nothing prints (no UART code yet); the boot
    banner comes with 01.03, the lock that keeps the hart lines whole with 02.03, typed
    characters echo once console interrupts are taken (03.03), and the system boots to the
    shell from 07.02 on, which is also where every extension starts."""
    from harness.core import lesson_key
    k = lesson_key(lesson_id)
    if k >= (7, 2):
        steps = [(None, r"init: starting sh"), (None, r"\$ "), ("echo hi there", r"hi there\r?\n\$ ")]
        if k >= (7, 3):
            steps.append(("ls", r"README +2 2 \d+[\s\S]*\$ "))
        if lesson_id.startswith("09.") and k >= (9, 2):
            steps.append(("colors", r"colors: child \d+ drew the ramp; this process sees it too"))
        return steps
    if k < (1, 3):
        return []
    steps = [(None, r"xv6 kernel is booting")]
    if k >= (2, 3):
        steps += [(None, r"hart \d starting\r?\n"), (None, r"hart \d starting\r?\n")]
    if k >= (3, 3):
        steps += [("typed", r"typed")]
    return steps


# ---------------------------------------------------------------- ./learn verify
#
# Internal: how ./learn verify (harness/verify.py) replays the transcripts in the lessons:
# the shell's prompt and the QEMU monitor's (Control-a c) mark typed lines; Control-a x quits
# QEMU; a boot with no shell is done once it has been quiet this long.

VERIFY_PROMPTS = ["$ ", "(qemu) "]
VERIFY_QUIT = ["\x01x"]
VERIFY_QUIET = 0.5
VERIFY_SETTLE = 2.0
VERIFY_PANIC = "panic: "


def verify_tools():
    """What replaying a lesson needs: QEMU, the RISC-V cross compiler, make."""
    try:
        gcc = tool("gcc")
    except Fail:
        gcc = None
    return {"qemu-system-riscv64": shutil.which("qemu-system-riscv64"), "riscv64 gcc": gcc,
            "make": shutil.which("make")}


# ---------------------------------------------------------------- the network (module 08)
#
# The guest is 10.0.2.15 on QEMU's user-mode network ("slirp"): the host is
# the gateway 10.0.2.2, and QEMU's DNS resolver is 10.0.2.3. A datagram the
# guest sends to 10.0.2.2:P comes out of a host socket and goes to the
# host's 127.0.0.1:P; hostfwd sends datagrams for a host port to the guest.

NET_CARD = ["-device", "virtio-net-device,netdev=net0,bus=virtio-mmio-bus.1"]
GUEST_MAC = bytes.fromhex("525400123456")    # QEMU's default for the first card
GUEST_IP = "10.0.2.15"
GATEWAY_IP = "10.0.2.2"
DNS_IP = "10.0.2.3"
BROADCAST = b"\xff" * 6


def netdev(udpfwd=()):
    """QEMU arguments for the card on the user-mode network."""
    opts = "user,id=net0,ipv6=off"
    for host_port, guest_port in udpfwd:
        opts += f",hostfwd=udp:127.0.0.1:{host_port}-:{guest_port}"
    return ["-netdev", opts] + NET_CARD


def free_port():
    """A UDP port on 127.0.0.1 that nothing is bound to right now."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def mac_of(ip):
    """The Ethernet address slirp gives its own hosts: 52:55 and the IP."""
    return b"\x52\x55" + socket.inet_aton(ip)


class Wire:
    """The other end of the guest's network cable.

    QEMU's dgram netdev carries each raw Ethernet frame in one UDP datagram
    between QEMU and this object, on 127.0.0.1. Frames the guest sends
    arrive in recv(); send() puts a frame on the guest's wire. With
    answer_arp, ARP requests for those IPs are answered as they arrive, so
    a test can talk UDP without doing ARP itself.
    """

    def __init__(self, answer_arp=()):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.qemu_port = free_port()
        self.answer_arp = set(answer_arp)
        self.log = []       # every frame the guest sent, in order
        self.session = None # the guest's console, once boot() has started it

    def qemu_args(self):
        return ["-netdev", f"dgram,id=net0,local.type=inet,local.host=127.0.0.1,local.port={self.qemu_port},"
                           f"remote.type=inet,remote.host=127.0.0.1,remote.port={self.port}"] + NET_CARD

    def send(self, frame):
        self.sock.sendto(frame, ("127.0.0.1", self.qemu_port))

    def recv(self, timeout=5.0):
        """The next frame from the guest, or None after timeout seconds.
        Fails at once if the guest's kernel panics meanwhile."""
        deadline = time.monotonic() + timeout
        while True:
            if self.session is not None:
                self.session._pump(0)
                m = re.search(r"panic: [^\n]*", self.session.output)
                if m:
                    raise Fail(f"{self.session.name}: {m.group(0).strip()}")
            left = deadline - time.monotonic()
            r, _, _ = select.select([self.sock], [], [], max(0, min(left, 0.1)))
            if r:
                break
            if left <= 0:
                return None
        frame = self.sock.recv(65536)
        self.log.append(frame)
        p = parse_frame(frame)
        if p.get("arp") and p["op"] == 1 and p["tip"] in self.answer_arp:
            self.send(arp_frame(2, mac_of(p["tip"]), p["tip"], p["sha"], p["sip"], dst=p["sha"]))
        return frame

    def expect(self, what, match, timeout=5.0):
        """Wait for a frame from the guest that match(parse_frame(f)) accepts;
        return it parsed. Fail, naming what was wanted, if none comes."""
        deadline = time.monotonic() + timeout
        while True:
            left = deadline - time.monotonic()
            frame = self.recv(max(left, 0)) if left > 0 else None
            if frame is None:
                raise Fail(f"no {what} from the guest within {timeout}s; it sent "
                           f"{[describe(parse_frame(f)) for f in self.log[-6:]]}")
            p = parse_frame(frame)
            if match(p):
                return p

    def quiet(self, within=1.0, match=lambda p: True):
        """Fail if the guest sends a frame match accepts in the next `within` seconds."""
        deadline = time.monotonic() + within
        while (left := deadline - time.monotonic()) > 0:
            frame = self.recv(left)
            if frame is not None and match(parse_frame(frame)):
                raise Fail(f"the guest sent {describe(parse_frame(frame))} but should not have")

    def close(self):
        self.sock.close()


def inet_checksum(data, start=0):
    """RFC 1071: the one's complement of the one's complement sum."""
    if len(data) % 2:
        data += b"\0"
    s = start + sum(struct.unpack(f"!{len(data) // 2}H", data))
    while s >> 16:
        s = (s & 0xffff) + (s >> 16)
    return ~s & 0xffff


def _pseudo(src, dst, length):
    return sum(struct.unpack("!4H", socket.inet_aton(src) + socket.inet_aton(dst))) + 17 + length


def arp_frame(op, sha, sip, tha, tip, dst=BROADCAST, src=None):
    """An Ethernet frame holding one ARP packet (op 1 request, 2 reply)."""
    body = struct.pack("!HHBBH6s4s6s4s", 1, 0x0800, 6, 4, op, sha, socket.inet_aton(sip),
                       tha, socket.inet_aton(tip))
    return dst + (src or sha) + struct.pack("!H", 0x0806) + body


def udp_frame(src, sport, dst, dport, data, src_mac=None, dst_mac=GUEST_MAC,
              ip_id=1, ip_off=0, ttl=64, udp_sum=True, pad=0):
    """An Ethernet frame holding one IPv4/UDP datagram, checksums right
    unless udp_sum is False (send 0: no checksum)."""
    ulen = 8 + len(data)
    s = inet_checksum(struct.pack("!HHHH", sport, dport, ulen, 0) + data, _pseudo(src, dst, ulen)) if udp_sum else 0
    u = struct.pack("!HHHH", sport, dport, ulen, (s or 0xffff) if udp_sum else 0) + data
    h = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + ulen, ip_id, ip_off, ttl, 17, 0,
                    socket.inet_aton(src), socket.inet_aton(dst))
    h = h[:10] + struct.pack("!H", inet_checksum(h)) + h[12:]
    return dst_mac + (src_mac or mac_of(src)) + struct.pack("!H", 0x0800) + h + u + b"\0" * pad


def parse_frame(f):
    """Take an Ethernet frame apart. Always has dst, src, type; plus the ARP
    fields (arp=True), or the IPv4 and UDP fields with ip_ok and udp_ok
    saying whether each checksum holds."""
    p = {"dst": f[0:6], "src": f[6:12], "type": struct.unpack("!H", f[12:14])[0] if len(f) >= 14 else None,
         "len": len(f)}
    body = f[14:]
    if p["type"] == 0x0806 and len(body) >= 28:
        hrd, pro, hln, pln, op, sha, sip, tha, tip = struct.unpack("!HHBBH6s4s6s4s", body[:28])
        p.update(arp=True, hrd=hrd, pro=pro, hln=hln, pln=pln, op=op, sha=sha, sip=socket.inet_ntoa(sip),
                 tha=tha, tip=socket.inet_ntoa(tip))
    elif p["type"] == 0x0800 and len(body) >= 20:
        vhl, tos, tlen, ipid, off, ttl, proto, csum, src, dst = struct.unpack("!BBHHHBBH4s4s", body[:20])
        p.update(ip=True, vhl=vhl, tlen=tlen, ip_id=ipid, off=off, ttl=ttl, proto=proto, ip_sum=csum,
                 ip_src=socket.inet_ntoa(src), ip_dst=socket.inet_ntoa(dst), ip_ok=inet_checksum(body[:20]) == 0)
        if proto == 17 and len(body) >= 28:
            sport, dport, ulen, usum = struct.unpack("!HHHH", body[20:28])
            seg = body[20:20 + ulen]
            p.update(udp=True, sport=sport, dport=dport, ulen=ulen, udp_sum=usum, data=seg[8:],
                     udp_ok=len(seg) == ulen and (usum == 0 or
                                                  inet_checksum(seg, _pseudo(p["ip_src"], p["ip_dst"], ulen)) == 0))
    return p


def describe(p):
    if p.get("arp"):
        what = f"who-has {p['tip']} tell {p['sip']}" if p["op"] == 1 else f"{p['sip']} is-at {p['sha'].hex(':')}"
        return f"ARP {what}"
    if p.get("udp"):
        return f"UDP {p['ip_src']}:{p['sport']} > {p['ip_dst']}:{p['dport']} {p['data'][:20]!r}"
    return f"frame type {p['type']:#06x}, {p['len']} bytes" if p["type"] is not None else f"runt {p['len']} bytes"


# ---------------------------------------------------------------- the screen (module 09)
#
# The kernel draws into a ramfb framebuffer that QEMU finds through fw_cfg;
# the keyboard and the mouse (a tablet: it reports positions) are virtio
# input devices on mmio slots 2 and 3. A test never opens a window. It
# looks at the screen and works the keyboard and mouse through QMP, QEMU's
# machine protocol: screendump writes the screen to a PPM file, and
# input-send-event delivers key, button and pointer events to the devices.

GUI_DEVICES = ["-device", "ramfb",
               "-device", "virtio-keyboard-device,bus=virtio-mmio-bus.2",
               "-device", "virtio-tablet-device,bus=virtio-mmio-bus.3"]
SCREEN_W, SCREEN_H = 640, 480
ABS_MAX = 0x7fff          # the tablet's positions run from 0 to this on each axis


def screen_args():
    """-display for a window, like the Makefile picks: cocoa on a Mac's
    desktop, gtk or sdl on Linux with $DISPLAY or $WAYLAND_DISPLAY; none
    when there is no desktop. SCREEN in the environment overrides it."""
    if os.environ.get("SCREEN"):
        return ["-display", os.environ["SCREEN"]]
    try:
        have = subprocess.run(["qemu-system-riscv64", "-display", "help"], capture_output=True,
                              text=True, timeout=10).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return []
    if sys.platform == "darwin" and not os.environ.get("SSH_CONNECTION"):
        want = ["cocoa"]
    elif os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        want = ["gtk", "sdl"]
    else:
        want = []
    for d in want:
        if d in have:
            return ["-display", d]
    return []


def free_tcp_port():
    """A TCP port on 127.0.0.1 that nothing listens on right now."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Screen:
    """One screenshot. shot[x, y] is the pixel at (x, y) as 0xRRGGBB."""

    def __init__(self, ppm):
        magic, size, maxval, data = ppm.split(b"\n", 3)
        if magic != b"P6" or maxval != b"255":
            raise Fail(f"screendump wrote something that is not a P6 PPM: {ppm[:20]!r}")
        self.w, self.h = map(int, size.split())
        self.data = data

    def __getitem__(self, xy):
        x, y = xy
        i = (y * self.w + x) * 3
        return self.data[i] << 16 | self.data[i + 1] << 8 | self.data[i + 2]

    def count(self, color, x0=0, y0=0, x1=None, y1=None):
        """How many pixels of color in the box from (x0, y0) up to, not including, (x1, y1)."""
        x1 = self.w if x1 is None else x1
        y1 = self.h if y1 is None else y1
        return sum(1 for y in range(y0, y1) for x in range(x0, x1) if self[x, y] == color)


class Qmp:
    """The boot's QMP socket: a unix socket in the test's scratch directory
    (or a TCP port on 127.0.0.1, when that path is too long for a socket).
    It connects on first use."""

    def __init__(self, tmp, name):
        self.tmp, self.name = tmp, name
        path = os.path.join(tmp, f"{name}.qmp")
        if len(path) < 100:
            self.address, self.arg = path, f"unix:{path},server=on,wait=off"
        else:
            port = free_tcp_port()
            self.address, self.arg = ("127.0.0.1", port), f"tcp:127.0.0.1:{port},server=on,wait=off"
        self.sock = None
        self.session = None
        self.shots = 0

    def qemu_args(self):
        return ["-qmp", self.arg]

    def _connect(self):
        deadline = time.monotonic() + 10
        while True:
            fam = socket.AF_UNIX if isinstance(self.address, str) else socket.AF_INET
            sock = socket.socket(fam, socket.SOCK_STREAM)
            try:
                sock.connect(self.address)
                break
            except OSError:
                sock.close()
                if time.monotonic() > deadline:
                    raise Fail(f"{self.name}: no QMP socket at {self.address} after 10s")
                time.sleep(0.05)
        sock.settimeout(30)
        self.sock, self.rfile = sock, sock.makefile("rb")
        self._reply()                       # the greeting
        self.sock.sendall(b'{"execute": "qmp_capabilities"}\n')
        self._reply()

    def _reply(self):
        while True:
            line = self.rfile.readline()
            if not line:
                raise Fail(f"{self.name}: QEMU closed its QMP socket")
            msg = json.loads(line)
            if "event" not in msg:         # events (SHUTDOWN, ...) come unasked
                return msg

    def cmd(self, name, **args):
        """Run one QMP command and return what it returned; Fail if QEMU says error."""
        if self.sock is None:
            self._connect()
        self.sock.sendall(json.dumps({"execute": name, "arguments": args}).encode() + b"\n")
        r = self._reply()
        if "error" in r:
            raise Fail(f"{self.name}: QMP {name} failed: {r['error'].get('desc')}")
        return r.get("return")

    def screen(self):
        """A screenshot of the guest's display, as it is right now."""
        self.shots += 1
        path = os.path.join(self.tmp, f"{self.name}-{self.shots}.ppm")
        self.cmd("screendump", filename=path, format="ppm")
        with open(path, "rb") as f:
            shot = Screen(f.read())
        os.unlink(path)
        return shot

    def _send(self, *events):
        self.cmd("input-send-event", events=list(events))
        time.sleep(0.03)    # let the guest give the device its buffers back

    def key(self, name, down=None):
        """Press and release a key (QEMU's names: "a", "esc", "ret", "1"),
        or with down=True or False, only press or only release it."""
        for d in ([True, False] if down is None else [down]):
            self._send({"type": "key", "data": {"down": d, "key": {"type": "qcode", "data": name}}})

    def button(self, down, name="left"):
        self._send({"type": "btn", "data": {"down": down, "button": name}})

    def move(self, x, y):
        """Put the pointer in the middle of screen pixel (x, y)."""
        ax = (2 * x + 1) * (ABS_MAX + 1) // (2 * SCREEN_W)
        ay = (2 * y + 1) * (ABS_MAX + 1) // (2 * SCREEN_H)
        self._send({"type": "abs", "data": {"axis": "x", "value": ax}},
                   {"type": "abs", "data": {"axis": "y", "value": ay}})

    def click(self, x, y, name="left"):
        self.move(x, y)
        self.button(True, name)
        self.button(False, name)

    def drag(self, points, name="left"):
        """Press at the first point, move through the rest, release."""
        self.move(*points[0])
        self.button(True, name)
        for p in points[1:]:
            self.move(*p)
        self.button(False, name)


def wait_screen(s, what, ok, timeout=10):
    """Take screenshots until ok(shot) is true and return that shot. Fail,
    saying what was wanted, after timeout seconds or as soon as the kernel
    panics."""
    deadline = time.monotonic() + timeout
    while True:
        shot = s.qmp.screen()
        if ok(shot):
            return shot
        s._pump(0)
        m = re.search(r"panic: [^\n]*", s.output)
        if m:
            raise Fail(f"{s.name}: {m.group(0).strip()}")
        if time.monotonic() > deadline:
            raise Fail(f"the screen never showed {what} within {timeout}s")
        time.sleep(0.1)


def hexcolor(c):
    return f"{c:06x}"
