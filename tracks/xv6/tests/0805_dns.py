"""08.05 A DNS lookup

First with the test playing QEMU's resolver at 10.0.2.3 on the wire, so
it needs no network: nslookup's query is checked byte by byte, and an
answer with a CNAME and two A records, all named with compression
pointers, prints both addresses. A "no such name" answer prints none, and
a bad name sends nothing. Then, if this host can resolve dns.google
itself, nslookup must get an address for it through QEMU's real
resolver; with no network that part is skipped, and says so.
"""

import socket
import struct


def answer(query, flags, records=b"", ancount=0):
    """A response to query: its id and question, then the records."""
    qid = struct.unpack("!H", query[:2])[0]
    question = query[12:]
    return struct.pack("!6H", qid, flags, 1, ancount, 0, 0) + question + records


def rr(name, rtype, rdata, ttl=300):
    return name + struct.pack("!HHIH", rtype, 1, ttl, len(rdata)) + rdata


def test(t):
    tr = t.track
    w = tr.Wire(answer_arp=[tr.DNS_IP])
    s = tr.shell(t, net=w)

    def query(name):
        s.sendline(f"nslookup {name}")
        p = w.expect("a DNS query", lambda p: p.get("udp") and p["dport"] == 53)
        t.check(p["ip_dst"] == tr.DNS_IP, f"the query went to {p['ip_dst']}, not 10.0.2.3")
        return p

    # The query, byte by byte.
    p = query("www.example.com")
    q = p["data"]
    qname = b"\x03www\x07example\x03com\x00"
    t.check(len(q) == 12 + len(qname) + 4, f"query is {len(q)} bytes, expected {12 + len(qname) + 4}: {q.hex()}")
    qid, flags, qd, an, ns, ar = struct.unpack("!6H", q[:12])
    t.check(flags == 0x0100, f"query flags {flags:#06x}, expected 0x0100 (only RD)")
    t.check((qd, an, ns, ar) == (1, 0, 0, 0), f"counts {(qd, an, ns, ar)}, expected one question")
    t.check(q[12:12 + len(qname)] == qname, f"the name should be {qname!r}, got {q[12:12 + len(qname)]!r}")
    t.check(q[-4:] == b"\x00\x01\x00\x01", f"QTYPE/QCLASS should be A/IN: {q[-4:].hex()}")

    # The answer: www.example.com is a CNAME for web.example.com, which has
    # two addresses. 0xc00c points at the name in the question (offset 12),
    # 0xc010 at its "example.com" part; the A records point at the CNAME's
    # data, which starts 12 bytes into the first record.
    cname_at = 12 + len(qname) + 4 + 12
    recs = (rr(b"\xc0\x0c", 5, b"\x03web\xc0\x10") +
            rr(struct.pack("!H", 0xc000 | cname_at), 1, bytes([192, 0, 2, 1])) +
            rr(struct.pack("!H", 0xc000 | cname_at), 1, bytes([192, 0, 2, 2])))
    w.send(tr.udp_frame(tr.DNS_IP, 53, tr.GUEST_IP, p["sport"], answer(q, 0x8180, recs, 3), src_mac=tr.mac_of(tr.DNS_IP)))
    s.expect(r"www\.example\.com has address 192\.0\.2\.1\r?\n", timeout=10)
    s.expect(r"www\.example\.com has address 192\.0\.2\.2\r?\n", timeout=5)
    s.expect(r"\$ ", timeout=10)

    # No such name (response code 3).
    p = query("nosuch.example")
    w.send(tr.udp_frame(tr.DNS_IP, 53, tr.GUEST_IP, p["sport"], answer(p["data"], 0x8183)))
    s.expect(r"nosuch\.example has no address\r?\n", timeout=10)
    s.expect(r"\$ ", timeout=10)

    # A name with an empty label never leaves the machine.
    out = tr.run(s, "nslookup bad..name")
    t.check("not a valid name" in out, f"nslookup bad..name printed {out!r}")
    w.quiet(0.5, lambda p: p.get("udp"))
    s.close()

    # The real resolver, if this host has a network.
    name = "dns.google"
    try:
        host_sees = {ai[4][0] for ai in socket.getaddrinfo(name, 53, socket.AF_INET, socket.SOCK_DGRAM)}
    except OSError as e:
        print(f"      skipped the real lookup: this host cannot resolve {name} ({e})")
        return
    s = tr.shell(t, name="qemu-real")
    out = tr.run(s, f"nslookup {name}", timeout=30)
    got = set(l.split()[-1] for l in out.splitlines() if " has address " in l)
    t.check(got, f"nslookup {name} through QEMU's resolver found nothing: {out!r}")
    t.check(got & host_sees, f"xv6 says {sorted(got)}, this host says {sorted(host_sees)}")
