"""08.02 Ethernet and ARP

The test plays the LAN. Asked "who has 10.0.2.15?", the guest answers
with its own address, straight to whoever asked; it ignores a question
about another address and a frame for another card. The question also
teaches it the asker's address (RFC 826's merge), so it sends to that
host without asking back. For a host it does not know it broadcasts a
request, sends to the address in the answer, and asks only once. When
nobody answers it asks again, then gives up and sendto fails.
"""

import time

ZERO = bytes(6)


def test(t):
    tr = t.track
    gw, dns, me = tr.GATEWAY_IP, tr.DNS_IP, tr.GUEST_IP
    gw_mac, dns_mac = tr.mac_of(gw), tr.mac_of(dns)
    w = tr.Wire()
    s = tr.shell(t, net=w)

    # Frames that are not for us get no answer.
    w.send(tr.arp_frame(1, gw_mac, gw, ZERO, me, dst=bytes.fromhex("525400abcdef")))
    w.quiet(0.6)
    w.send(tr.arp_frame(1, gw_mac, gw, ZERO, "10.0.2.99"))
    w.quiet(0.6)

    # The question about us.
    w.send(tr.arp_frame(1, gw_mac, gw, ZERO, me))
    p = w.expect("an answer to who-has 10.0.2.15", lambda p: p.get("arp"))
    t.check(p["op"] == 2, f"expected an ARP reply (op 2): {tr.describe(p)}")
    t.check(p["dst"] == gw_mac, f"the reply should go to the asker's card, not {p['dst'].hex(':')}")
    t.check(p["src"] == tr.GUEST_MAC and p["type"] == 0x0806, "Ethernet header of the reply")
    t.check((p["hrd"], p["pro"], p["hln"], p["pln"]) == (1, 0x0800, 6, 4),
            f"hrd/pro/hln/pln should be 1/0x0800/6/4: {(p['hrd'], hex(p['pro']), p['hln'], p['pln'])}")
    t.check(p["sha"] == tr.GUEST_MAC and p["sip"] == me, f"the reply should say 10.0.2.15 is at 52:54:00:12:34:56: {tr.describe(p)}")
    t.check(p["tha"] == gw_mac and p["tip"] == gw, "the reply's target should be the asker")
    t.check(p["len"] == 42, f"the reply frame is {p['len']} bytes, expected 14 + 28")

    def exchange(ip, port, msg):
        s.sendline(f"udpecho {ip} {port} {msg}")
        p = w.expect(f"something for {ip}", lambda p: p.get("udp") or p.get("arp"))
        return p

    def answer(p, msg):
        w.send(tr.udp_frame(p["ip_dst"], p["dport"], me, p["sport"], msg.encode()))
        s.expect(r"\n" + msg + r"\r?\n", timeout=10)
        s.expect(r"\$ ", timeout=10)

    # It learned the gateway's address from the question.
    p = exchange(gw, 7, "one")
    t.check(p.get("udp"), f"the guest should know 10.0.2.2 from its question, but sent {tr.describe(p)}")
    t.check(p["dst"] == gw_mac, f"datagram for 10.0.2.2 went to card {p['dst'].hex(':')}")
    answer(p, "one")

    # A host it has never heard of: ask, by broadcast.
    p = exchange(dns, 53, "two")
    t.check(p.get("arp") and p["op"] == 1, f"expected an ARP request for 10.0.2.3, got {tr.describe(p)}")
    t.check(p["dst"] == tr.BROADCAST, "an ARP request goes to the broadcast address")
    t.check(p["sha"] == tr.GUEST_MAC and p["sip"] == me and p["tip"] == dns and p["tha"] == ZERO,
            f"request fields: {tr.describe(p)}, tha {p['tha'].hex(':')}")
    w.send(tr.arp_frame(2, dns_mac, dns, tr.GUEST_MAC, me, dst=tr.GUEST_MAC))
    p = w.expect("the datagram for 10.0.2.3", lambda p: p.get("udp"))
    t.check(p["dst"] == dns_mac, "the datagram should go to the card named in the answer")
    answer(p, "two")

    # Asked once: the cache answers the second time.
    p = exchange(dns, 53, "three")
    t.check(p.get("udp"), f"10.0.2.3 should be cached, but the guest sent {tr.describe(p)}")
    answer(p, "three")

    # Nobody answers: ask again, then give up.
    s.sendline("udpecho 10.0.2.77 9 four")
    asked = 0
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        f = w.recv(0.5)
        if f is None:
            continue
        q = tr.parse_frame(f)
        if q.get("arp") and q["op"] == 1 and q["tip"] == "10.0.2.77":
            asked += 1
        t.check(not q.get("udp"), f"a datagram went out with no address for 10.0.2.77: {tr.describe(q)}")
        if "sendto failed" in s.output:
            break
    s.expect(r"udpecho: sendto failed", timeout=5)
    t.check(2 <= asked <= 4, f"the guest asked for 10.0.2.77 {asked} times in 3 seconds, expected about 3")
