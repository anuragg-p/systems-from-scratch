"""08.01 The virtio network card

The test is the other end of the cable. Every frame the guest sends is a
bare Ethernet frame from the card's own address, 52:54:00:12:34:56, with
no virtio header left in front. Receive buffers go back to the card: a
flood of more frames than the receive queue holds is followed by a
datagram that still gets through. A full-size frame (1514 bytes) makes
it in both directions, and so does a run of datagrams in a row.
"""


def test(t):
    tr = t.track
    gw = tr.GATEWAY_IP
    w = tr.Wire(answer_arp=[gw])
    s = tr.shell(t, net=w)
    s.sendline("udpecho 2000 12")
    s.expect(r"udpecho: listening on port 2000", timeout=10)

    def echo(data, sport=5555):
        w.send(tr.udp_frame(gw, sport, tr.GUEST_IP, 2000, data))
        return w.expect(f"the echo of {data[:16]!r}", lambda p: p.get("udp") and p["data"] == data)

    # Twenty broadcast frames of a type nobody handles: more than the
    # receive queue's buffers. Then a datagram, which arrives only if
    # each buffer went back to the card after its frame was handled.
    for i in range(20):
        w.send(tr.BROADCAST + tr.mac_of(gw) + b"\x88\xb5" + bytes([i]) * 46)
    p = echo(b"after the flood")

    # What the guest sent: an ARP request for the gateway, then the echo.
    # Each starts with an Ethernet header from our card, exactly as long
    # as what it carries.
    t.check(len(w.log) >= 2, f"expected an ARP request and a datagram, got {len(w.log)} frames")
    for f in w.log:
        q = tr.parse_frame(f)
        t.check(q["src"] == tr.GUEST_MAC, f"frame from {q['src'].hex(':')}, not the card's address "
                                          f"52:54:00:12:34:56 (is the virtio header still in front?): {f[:20].hex()}")
        t.check(q["type"] in (0x0800, 0x0806), f"frame of unknown type {q['type']:#x}: {f[:20].hex()}")
    arp = tr.parse_frame(w.log[0])
    t.check(arp.get("arp") and arp["len"] == 42, f"first frame should be a 42-byte ARP request: {tr.describe(arp)}")
    t.check(p["len"] == 14 + 20 + 8 + len(b"after the flood"), f"echo frame is {p['len']} bytes")
    t.check(p["dst"] == tr.mac_of(gw), "the echo should go to the gateway's card")

    # The largest frame there is, 1500 bytes after the Ethernet header.
    big = bytes((i * 7) & 0xff for i in range(1472))
    p = echo(big, 5556)
    t.check(p["len"] == 1514, f"a full-size echo should be a 1514-byte frame, got {p['len']}")

    # Ten more, one after another: the transmit buffers come back too.
    for i in range(10):
        echo(b"datagram %d" % i, 6000 + i)
    s.expect(r"\$ ", timeout=10)
    out = s.output
    t.check(out.count("bytes from 10.0.2.2") == 12, "udpecho should have seen 12 datagrams")
