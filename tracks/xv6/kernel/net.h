// The network stack's headers and constants (module 08, optional).
//
// A packet on the wire is a stack of headers, outermost first:
//
//   Ethernet (14 bytes) | IPv4 (20) | UDP (8) | payload (up to 1472)
//
// or, for address resolution, Ethernet | ARP (28).
// @from 08.04
// Each layer reads its own header and hands what follows to the layer
// above (ether.c -> ip.c -> sock.c); sending goes the other way.
// @end
// @from 08.02
//
// Every multi-byte field on the wire is big-endian ("network byte
// order") and RISC-V is little-endian, so a header field is converted
// with htons/htonl when it is written and ntohs/ntohl when it is read.
// Inside the kernel, IP addresses and ports are plain host-order numbers.
// @end

// @from 08.02
// QEMU's user-mode network (slirp) is a fixed little LAN: we are
// 10.0.2.15, the host is the gateway 10.0.2.2, and QEMU answers DNS
// queries at 10.0.2.3. There is no DHCP; the address is wired in.
#define MKIP(a, b, c, d) (((uint32)(a) << 24) | ((uint32)(b) << 16) | ((uint32)(c) << 8) | (uint32)(d))
#define MYIP     MKIP(10, 0, 2, 15)
#define GATEWAY  MKIP(10, 0, 2, 2)
#define NETMASK  MKIP(255, 255, 255, 0)

static inline uint16 htons(uint16 x) { return (x << 8) | (x >> 8); }
static inline uint16 ntohs(uint16 x) { return htons(x); }
static inline uint32 htonl(uint32 x) {
  return (x << 24) | ((x << 8) & 0xff0000) | ((x >> 8) & 0xff00) | (x >> 24);
}
static inline uint32 ntohl(uint32 x) { return htonl(x); }
// @end

// The headers are declared packed: the compiler adds no padding, and
// reads each field byte by byte, so a header may sit at any address
// inside a packet buffer.

#define ETHADDR_LEN 6

// An Ethernet frame header.
struct eth {
  uint8  dst[ETHADDR_LEN];  // ff:ff:ff:ff:ff:ff is broadcast: every card takes it
  uint8  src[ETHADDR_LEN];
  uint16 type;              // what follows: 0x0800 IPv4, 0x0806 ARP
} __attribute__((packed));

// @from 08.02
#define ETHTYPE_IP  0x0800
#define ETHTYPE_ARP 0x0806

// An ARP packet for IPv4 over Ethernet (RFC 826).
struct arp {
  uint16 hrd;               // hardware type: ARP_HRD_ETHER
  uint16 pro;               // protocol type: ETHTYPE_IP
  uint8  hln;               // hardware address length: 6
  uint8  pln;               // protocol address length: 4
  uint16 op;                // ARP_REQUEST or ARP_REPLY
  uint8  sha[ETHADDR_LEN];  // sender's Ethernet address
  uint32 sip;               // sender's IP address
  uint8  tha[ETHADDR_LEN];  // target's Ethernet address (zero in a request)
  uint32 tip;               // target's IP address
} __attribute__((packed));

#define ARP_HRD_ETHER 1
#define ARP_REQUEST   1
#define ARP_REPLY     2
// @end

// @from 08.03
// An IPv4 header without options (RFC 791).
struct ip {
  uint8  vhl;               // version (4) << 4 | header length in 32-bit words (5)
  uint8  tos;
  uint16 len;               // total length: this header and everything after it
  uint16 id;                // tells fragments of one packet apart
  uint16 off;               // flags (IP_MF) and fragment offset
  uint8  ttl;               // hops left before a router drops it
  uint8  p;                 // protocol of the payload: IPPROTO_UDP
  uint16 sum;               // checksum of this header
  uint32 src;
  uint32 dst;
} __attribute__((packed));

#define IP_VHL     0x45     // version 4, 5 words: the only header we send or take
#define IP_MF      0x2000   // more fragments follow
#define IP_OFFMASK 0x1fff   // fragment offset, in 8-byte units
#define IPPROTO_UDP 17

// A UDP header (RFC 768).
struct udp {
  uint16 sport;             // source port
  uint16 dport;             // destination port
  uint16 ulen;              // length of this header and the payload
  uint16 sum;               // checksum, over a pseudo-header too; 0 means none
} __attribute__((packed));

// Building a packet: the sender puts its payload HDRSPACE bytes into a
// buffer, and each layer on the way down writes its header just in
// front of what the layer above wrote. Nothing is copied until the
// driver copies the finished frame into the card's buffer.
#define HDRSPACE (sizeof(struct eth) + sizeof(struct ip) + sizeof(struct udp))
// @end

// The most a frame may carry after its Ethernet header (the MTU), and so
// the largest UDP payload that fits in one frame.
#define ETH_MTU 1500
#define UDP_MAXDATA (ETH_MTU - sizeof(struct ip) - sizeof(struct udp))  // @from 08.03

// @from 08.04
// sock.c: a UDP socket, and one datagram waiting in its queue.
// Each queued datagram fills one kalloc'd page.
struct dgram {
  struct dgram *next;
  uint32 src;               // who sent it
  uint16 sport;
  int len;
  char data[];              // len bytes, at most UDP_MAXDATA
};

#define NSOCK 16            // sockets in the whole system
#define SOCKQ 16            // datagrams a socket holds before it drops more

struct sock {
  int used;
  uint16 port;              // the local port it is bound to
  struct dgram *head;       // received, not yet read: oldest first
  struct dgram *tail;
  int qlen;
};
// @end

// virtio_net.c
extern uint8 net_mac[ETHADDR_LEN];  // our Ethernet address, from the card
extern int net_up;                  // 1 if a network card was found
