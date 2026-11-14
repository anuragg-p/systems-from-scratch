"""08.04 Sockets

On QEMU's user-mode network, with real sockets on the host. Datagrams
from a host socket reach an xv6 server bound with socket() and come back
in order, including ones that arrive while the server still sleeps in
recvfrom and ones that wait in the queue. An xv6 client's datagram
reaches a host socket on 127.0.0.1, and the reply wakes the client
sleeping in read(). A port can be bound only once, and the socket's
file descriptor frees it when the process holding it exits.
"""

import socket
import time


def test(t):
    tr = t.track
    host_port = tr.free_port()
    s = tr.shell(t, udpfwd=[(host_port, 2000)])
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c.settimeout(10)
    to_guest = ("127.0.0.1", host_port)

    def roundtrip(msg):
        c.sendto(msg, to_guest)
        try:
            data, _ = c.recvfrom(4096)
        except socket.timeout:
            t.check(False, f"no echo of {msg!r} from the guest")
        t.check(data == msg, f"sent {msg!r}, the echo was {data!r}")

    # host -> guest, and back.
    s.sendline("udpecho 2000 6")
    s.expect(r"udpecho: listening on port 2000", timeout=10)
    roundtrip(b"first")
    time.sleep(1.0)                 # the server sleeps in recvfrom meanwhile
    roundtrip(b"a second later")
    # three at once: they wait in the socket's queue, and come back in order
    for i in range(3):
        c.sendto(b"queued %d" % i, to_guest)
    got = []
    for i in range(3):
        try:
            got.append(c.recvfrom(4096)[0])
        except socket.timeout:
            break
    t.check(got == [b"queued 0", b"queued 1", b"queued 2"], f"queued datagrams came back as {got}")
    roundtrip(b"x" * 1472)          # the largest that fits in one frame
    s.expect(r"\$ ", timeout=10)

    # guest -> host: a client on an ephemeral port, sleeping in read().
    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.bind(("127.0.0.1", 0))
    srv.settimeout(10)
    port = srv.getsockname()[1]
    s.sendline(f"udpecho 10.0.2.2 {port} hello-from-xv6")
    try:
        data, peer = srv.recvfrom(4096)
    except socket.timeout:
        t.check(False, "the host socket got nothing from the guest's client")
    t.check(data == b"hello-from-xv6", f"the host socket got {data!r}")
    time.sleep(0.5)
    srv.sendto(b"hello-from-the-host", peer)
    s.expect(r"\nhello-from-the-host\r?\n", timeout=10)
    s.expect(r"\$ ", timeout=10)

    # One port, one socket. A server in the background holds port 2000...
    s.sendline("udpecho 2000 1 &")
    # the whole line: user printf writes a byte at a time, and the next
    # command's echo must not land in the middle of it
    s.expect(r"udpecho: listening on port 2000\r?\n", timeout=10)
    out = tr.run(s, "udpecho 2000 1")
    t.check("cannot bind port 2000" in out, f"a second socket on port 2000 should fail: {out!r}")
    # ...until it exits, and exit closes its file descriptors.
    roundtrip(b"to the background server")
    time.sleep(0.5)
    s.sendline("udpecho 2000 1")
    s.expect(r"udpecho: listening on port 2000", timeout=10)
    roundtrip(b"port 2000 is free again")
    s.expect(r"\$ ", timeout=10)
    c.close()
    srv.close()
