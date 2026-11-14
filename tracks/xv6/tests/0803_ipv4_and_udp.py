"""08.03 IPv4 and UDP

The guest runs a UDP echo server on port 2000 and the test sends it
datagrams, good and bad. A good one comes back with every IP and UDP
header field right, both checksums included. A broken IP checksum, a
broken UDP checksum, the wrong port, another host's address, a fragment
and a protocol that is not UDP are all dropped. A datagram sent with no
UDP checksum, and one in a padded frame, are accepted. The echo to a
host off the LAN goes to the gateway's card.
"""

import struct

PORT = 2000


def test(t):
    tr = t.track
    gw, me = tr.GATEWAY_IP, tr.GUEST_IP
    w = tr.Wire(answer_arp=[gw])
    s = tr.shell(t, net=w)
    s.sendline(f"udpecho {PORT} 4")
    s.expect(rf"udpecho: listening on port {PORT}", timeout=10)

    def echoed(what, frame, data):
        w.send(frame)
        return w.expect(f"the echo of {what}", lambda p: p.get("udp") and p["data"] == data)

    def dropped(what, frame, data):
        w.send(bytes(frame))
        w.quiet(0.7, lambda p: p.get("udp") and p["data"] == data)

    def fix_ip_sum(f):
        f[24:26] = b"\0\0"
        f[24:26] = struct.pack("!H", tr.inet_checksum(bytes(f[14:34])))

    # A good datagram, and every field of its echo.
    p = echoed("a good datagram", tr.udp_frame(gw, 5001, me, PORT, b"good"), b"good")
    t.check(p["vhl"] == 0x45, f"version/header length {p['vhl']:#x}, expected 0x45")
    t.check(p["tlen"] == 20 + 8 + 4, f"IP total length {p['tlen']}, expected 32")
    t.check(p["off"] & 0x3fff == 0, f"the echo should not be a fragment: off {p['off']:#x}")
    t.check(p["ttl"] > 0 and p["proto"] == 17, f"ttl {p['ttl']} protocol {p['proto']}")
    t.check(p["ip_src"] == me and p["ip_dst"] == gw, f"addresses {p['ip_src']} -> {p['ip_dst']}")
    t.check(p["ip_ok"], f"IP header checksum {p['ip_sum']:#06x} is wrong")
    t.check((p["sport"], p["dport"], p["ulen"]) == (PORT, 5001, 12),
            f"UDP ports/length {(p['sport'], p['dport'], p['ulen'])}, expected (2000, 5001, 12)")
    t.check(p["udp_sum"] != 0, "the guest should send a UDP checksum")
    t.check(p["udp_ok"], f"UDP checksum {p['udp_sum']:#06x} is wrong (pseudo-header included?)")
    first_id = p["ip_id"]

    # Broken IP header checksum.
    f = bytearray(tr.udp_frame(gw, 5002, me, PORT, b"bad ip sum"))
    f[25] ^= 0x01
    dropped("a bad IP checksum", f, b"bad ip sum")

    # Broken UDP checksum: the data changed after the sum was made.
    f = bytearray(tr.udp_frame(gw, 5003, me, PORT, b"bad udp sum"))
    f[-1] ^= 0x01
    dropped("a bad UDP checksum", f, b"bad udp sul")

    # Nobody on port 2001.
    dropped("the wrong port", tr.udp_frame(gw, 5004, me, PORT + 1, b"wrong port"), b"wrong port")

    # For another host.
    f = bytearray(tr.udp_frame(gw, 5005, "10.0.2.16", PORT, b"not for us"))
    dropped("another host's packet", f, b"not for us")

    # The first fragment of a bigger packet (more fragments flag).
    dropped("a fragment", tr.udp_frame(gw, 5006, me, PORT, b"fragment", ip_off=0x2000), b"fragment")

    # Protocol 6 (TCP) with UDP inside.
    f = bytearray(tr.udp_frame(gw, 5007, me, PORT, b"not udp"))
    f[23] = 6
    fix_ip_sum(f)
    dropped("a TCP packet", f, b"not udp")

    # No UDP checksum at all: allowed in IPv4.
    echoed("a datagram with no checksum", tr.udp_frame(gw, 5008, me, PORT, b"no sum", udp_sum=False), b"no sum")

    # A frame with 20 bytes of padding after the IP packet: the IP
    # header's length counts, not the frame's.
    p = echoed("a padded frame", tr.udp_frame(gw, 5009, me, PORT, b"padded", pad=20), b"padded")
    t.check(p["ulen"] == 8 + 6 and p["tlen"] == 20 + 8 + 6, "the padding must not end up in the echo")
    t.check(p["ip_id"] != first_id, "each packet should get its own IP id")

    # From off the LAN: the echo goes back through the gateway.
    p = echoed("a datagram from 8.8.8.8", tr.udp_frame("8.8.8.8", 5010, me, PORT, b"far away",
                                                       src_mac=tr.mac_of(gw)), b"far away")
    t.check(p["ip_dst"] == "8.8.8.8" and p["dst"] == tr.mac_of(gw),
            f"the echo to 8.8.8.8 should go to the gateway's card, went to {p['dst'].hex(':')}")

    s.expect(r"\$ ", timeout=10)
    t.check(s.output.count("bytes from") == 4, "the server should have seen exactly the 4 good datagrams")
