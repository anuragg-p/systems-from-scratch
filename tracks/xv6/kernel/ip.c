// IPv4 and UDP.
//
// IP (RFC 791) carries a packet from one address to another. Its header
// says who sent it, who it is for, which protocol is inside, and holds a
// checksum of the header itself. UDP (RFC 768) adds ports, so that a
// packet for 10.0.2.15 finds the one socket bound to port 2000, and a
// checksum over its data. That is the whole of it here: no options, no
// fragments, no TCP; one datagram per frame.

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/riscv.h"
#include "kernel/spinlock.h"
#include "kernel/proc.h"
#include "kernel/defs.h"
#include "kernel/net.h"

static uint32 ip_id;    // the next packet's identification

// The Internet checksum (RFC 1071) of len bytes at data, continuing from
// the partial sum `sum`.
uint16
in_cksum(void *data, int len, uint32 sum)
{
  // @build 08.03 in_cksum
  // Add the data into sum as big-endian 16-bit words; an odd last byte is
  // the high byte of a word whose low byte is 0. Fold the carries back in
  // (add the top 16 bits to the bottom 16 until the top is 0) and return
  // the complement of the result. Over bytes that include their own
  // correct checksum the answer is 0, which is how a receiver checks one.
  uint8 *p = data;

  while(len > 1){
    sum += (p[0] << 8) | p[1];
    p += 2;
    len -= 2;
  }
  if(len == 1)
    sum += p[0] << 8;
  while(sum >> 16)
    sum = (sum & 0xffff) + (sum >> 16);
  return ~sum & 0xffff;
  // @end
}

// The UDP checksum also covers a "pseudo-header" that is never sent: the
// two addresses, the protocol and the UDP length. A datagram that
// reaches the wrong host, or claims the wrong protocol, then fails its
// checksum. This is that header's partial sum, for in_cksum to go on from.
static uint32
pseudo(uint32 src, uint32 dst, int len)
{
  return (src >> 16) + (src & 0xffff) + (dst >> 16) + (dst & 0xffff) + IPPROTO_UDP + len;
}

// Send len bytes at payload as one IP packet of protocol proto to dst.
// The caller leaves room for the IP and Ethernet headers before payload.
// May sleep, in arp_resolve: process context only.
int
ip_send(char *payload, int len, uint8 proto, uint32 dst)
{
  // @build 08.03 ip_send
  // Write a struct ip just before payload: IP_VHL, the total length
  // (header and payload), a new id (ip_id, counted atomically), no
  // fragment bits, ttl 64, proto, source MYIP and destination dst, every
  // field in network byte order. Then the checksum: in_cksum over the 20
  // header bytes with sum 0 while the field itself is 0. Pick the next hop:
  // dst itself when it is on our LAN (dst and MYIP agree under NETMASK),
  // the GATEWAY when it is not. Find the next hop's card with arp_resolve
  // (return -1 if that fails) and send the packet with eth_send.
  struct ip *ip = (struct ip *)(payload - sizeof(struct ip));

  ip->vhl = IP_VHL;
  ip->tos = 0;
  ip->len = htons(sizeof(struct ip) + len);
  ip->id = htons(__sync_fetch_and_add(&ip_id, 1));
  ip->off = 0;
  ip->ttl = 64;
  ip->p = proto;
  ip->sum = 0;
  ip->src = htonl(MYIP);
  ip->dst = htonl(dst);
  ip->sum = htons(in_cksum(ip, sizeof(struct ip), 0));

  uint32 hop = (dst & NETMASK) == (MYIP & NETMASK) ? dst : GATEWAY;
  uint8 mac[ETHADDR_LEN];
  if(arp_resolve(hop, mac) < 0)
    return -1;
  return eth_send((char *)ip, sizeof(struct ip) + len, ETHTYPE_IP, mac);
  // @end
}

// An IP packet of len bytes has arrived (interrupt context).
void
ip_rx(char *pkt, int len)
{
  // @build 08.03 ip_rx
  // Check the header and pass the payload up. Drop the packet (return)
  // unless all of this holds: it has a whole struct ip; vhl is IP_VHL
  // (version 4, no options); in_cksum over the header comes out 0; the
  // total length is at least the header and at most len (believe the
  // header, not len: a short frame arrives padded); it is not a fragment
  // (no IP_MF, offset 0); it is for MYIP; it carries IPPROTO_UDP. Then
  // call udp_rx with the bytes after the header, up to the total length,
  // and the source and destination addresses in host order. Never sleep.
  if(len < sizeof(struct ip))
    return;
  struct ip *ip = (struct ip *)pkt;
  if(ip->vhl != IP_VHL)
    return;
  if(in_cksum(ip, sizeof(struct ip), 0) != 0)
    return;
  int total = ntohs(ip->len);
  if(total < sizeof(struct ip) || total > len)
    return;
  if(ntohs(ip->off) & (IP_MF | IP_OFFMASK))
    return;   // a piece of a bigger packet: we do not reassemble
  if(ntohl(ip->dst) != MYIP)
    return;
  if(ip->p != IPPROTO_UDP)
    return;
  udp_rx(pkt + sizeof(struct ip), total - sizeof(struct ip), ntohl(ip->src), ntohl(ip->dst));
  // @end
}

// Send len bytes at payload as a UDP datagram from our port sport to
// port dport of dst. The caller leaves HDRSPACE bytes before payload.
// May sleep: process context only.
int
udp_send(char *payload, int len, uint16 sport, uint32 dst, uint16 dport)
{
  // @build 08.03 udp_send
  // Write a struct udp just before payload: both ports and the length
  // (header and payload), in network byte order, and sum 0. The checksum
  // runs over the pseudo-header (pseudo(MYIP, dst, length)), then the
  // header and payload; a result of 0 goes out as 0xffff, because 0 on the
  // wire means "no checksum". Send the datagram with ip_send.
  struct udp *udp = (struct udp *)(payload - sizeof(struct udp));
  int ulen = sizeof(struct udp) + len;

  udp->sport = htons(sport);
  udp->dport = htons(dport);
  udp->ulen = htons(ulen);
  udp->sum = 0;
  uint16 sum = in_cksum(udp, ulen, pseudo(MYIP, dst, ulen));
  udp->sum = htons(sum ? sum : 0xffff);
  return ip_send((char *)udp, ulen, IPPROTO_UDP, dst);
  // @end
}

// A UDP datagram of len bytes has arrived from src for dst (interrupt
// context).
void
udp_rx(char *pkt, int len, uint32 src, uint32 dst)
{
  // @build 08.03 udp_rx
  // Check the header, then give the payload to the socket on the
  // destination port. Drop the datagram unless it holds a whole struct
  // udp and its length field is at least the header and at most len. A
  // checksum of 0 means the sender sent none; any other must come out 0
  // over pseudo(src, dst, length), the header and the payload. Then
  // sock_deliver(destination port, src, source port, payload, its
  // length), the ports in host order. Never sleep.
  if(len < sizeof(struct udp))
    return;
  struct udp *udp = (struct udp *)pkt;
  int ulen = ntohs(udp->ulen);
  if(ulen < sizeof(struct udp) || ulen > len)
    return;
  if(udp->sum != 0 && in_cksum(udp, ulen, pseudo(src, dst, ulen)) != 0)
    return;
  // @from 08.04
  sock_deliver(ntohs(udp->dport), src, ntohs(udp->sport),
               pkt + sizeof(struct udp), ulen - sizeof(struct udp));
  // @end
  // @end
}
