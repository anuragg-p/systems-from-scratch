// Ethernet frames and ARP.
//
// The card moves Ethernet frames: a 14-byte header (destination
// address, source address, type) and up to 1500 bytes of payload. An
// Ethernet address names a card, not a host on the internet, so to send
// an IP packet to 10.0.2.2 we must first learn which card 10.0.2.2 is.
// ARP (RFC 826) asks the whole LAN: a broadcast "who has 10.0.2.2? tell
// 10.0.2.15", which the owner answers with "10.0.2.2 is at
// 52:55:0a:00:02:02". A small cache keeps the answers, so we ask once
// per neighbour, and we answer the same question about ourselves.

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/riscv.h"
#include "kernel/spinlock.h"
#include "kernel/proc.h"
#include "kernel/defs.h"
#include "kernel/net.h"

#define NARP 8          // cache entries
#define ARP_RETRY 10    // ticks between requests for the same address
#define ARP_WAIT 30     // ticks before arp_resolve gives up: 3 seconds

static uint8 broadcast[ETHADDR_LEN] = { 0xff, 0xff, 0xff, 0xff, 0xff, 0xff };
static uint8 zeroes[ETHADDR_LEN];

struct arpent {
  uint32 ip;            // 0: a free entry
  uint8 mac[ETHADDR_LEN];
  uint when;            // ticks at the last update, to find the oldest
};

static struct {
  struct spinlock lock;
  struct arpent ent[NARP];
} arpcache;

void
arpinit(void)
{
  initlock(&arpcache.lock, "arp");
}

// The cache entry for ip, or 0. Caller holds arpcache.lock.
static struct arpent*
arp_find(uint32 ip)
{
  for(struct arpent *e = arpcache.ent; e < arpcache.ent + NARP; e++)
    if(e->ip == ip)
      return e;
  return 0;
}

// Remember that ip is at mac: update ip's entry, or fill a free one, or
// replace the oldest. Caller holds arpcache.lock.
static void
arp_insert(uint32 ip, uint8 *mac)
{
  struct arpent *e = arp_find(ip);
  if(e == 0){
    e = arpcache.ent;
    for(struct arpent *x = arpcache.ent; x < arpcache.ent + NARP; x++){
      if(x->ip == 0){
        e = x;
        break;
      }
      if(x->when < e->when)
        e = x;
    }
  }
  e->ip = ip;
  memmove(e->mac, mac, ETHADDR_LEN);
  e->when = ticks;
}

// Send one ARP packet from us: op (ARP_REQUEST or ARP_REPLY) about the
// target (tha, tip), in a frame addressed to the card eth_dst.
static int
arp_send(uint16 op, uint8 *eth_dst, uint8 *tha, uint32 tip)
{
  char frame[sizeof(struct eth) + sizeof(struct arp)];
  struct arp *a = (struct arp *)(frame + sizeof(struct eth));

  a->hrd = htons(ARP_HRD_ETHER);
  a->pro = htons(ETHTYPE_IP);
  a->hln = ETHADDR_LEN;
  a->pln = sizeof(uint32);
  a->op = htons(op);
  memmove(a->sha, net_mac, ETHADDR_LEN);
  a->sip = htonl(MYIP);
  memmove(a->tha, tha, ETHADDR_LEN);
  a->tip = htonl(tip);
  return eth_send((char *)a, sizeof(struct arp), ETHTYPE_ARP, eth_dst);
}

// Sleep until the next clock tick, a tenth of a second. Returns -1 if
// this process has been killed meanwhile.
static int
tick_wait(void)
{
  acquire(&tickslock);
  uint t0 = ticks;
  while(ticks == t0){
    if(killed(myproc())){
      release(&tickslock);
      return -1;
    }
    sleep(&ticks, &tickslock);
  }
  release(&tickslock);
  return 0;
}

// Send len bytes at payload as one Ethernet frame of the given type to
// the card dst. The caller leaves room for the header just before
// payload. Returns what virtio_net_send returns.
int
eth_send(char *payload, int len, uint16 type, uint8 *dst)
{
  // @build 08.02 eth_send
  // Write a struct eth in the bytes just before payload: destination dst,
  // source net_mac (this card), and type in network byte order. Hand the
  // whole frame, header included, to virtio_net_send.
  struct eth *eth = (struct eth *)(payload - sizeof(struct eth));

  memmove(eth->dst, dst, ETHADDR_LEN);
  memmove(eth->src, net_mac, ETHADDR_LEN);
  eth->type = htons(type);
  return virtio_net_send(eth, sizeof(struct eth) + len);
  // @end
}

// A frame of len bytes has arrived. Called by virtio_net_intr(), in
// interrupt context.
void
net_rx(char *frame, int len)
{
  // @build 08.02 net_rx
  // Read the Ethernet header and pass the payload up. Drop the frame
  // (return) if it is shorter than a header or not for us: its
  // destination must be net_mac or the broadcast address. Then by type:
  // ETHTYPE_ARP goes to arp_rx, ETHTYPE_IP to ip_rx, each given the bytes
  // after the header. Drop any other type. Never sleep.
  if(len < sizeof(struct eth))
    return;
  struct eth *eth = (struct eth *)frame;
  if(memcmp(eth->dst, net_mac, ETHADDR_LEN) != 0 &&
     memcmp(eth->dst, broadcast, ETHADDR_LEN) != 0)
    return;   // for another card

  char *payload = frame + sizeof(struct eth);
  len -= sizeof(struct eth);
  switch(ntohs(eth->type)){
  case ETHTYPE_ARP:
    arp_rx(payload, len);
    break;
  // @from 08.03
  case ETHTYPE_IP:
    ip_rx(payload, len);
    break;
  // @end
  }
  // @end
}

// An ARP packet of len bytes has arrived (interrupt context).
void
arp_rx(char *pkt, int len)
{
  // @build 08.02 arp_rx
  // Learn from the packet, and answer a question about us. Drop it unless
  // it is a whole struct arp for IPv4 over Ethernet (hrd, pro, hln, pln)
  // with a sender IP that is not 0. Under arpcache.lock, RFC 826's merge:
  // if the sender's IP is in the cache, update its Ethernet address; if
  // the target IP is MYIP, cache the sender either way, since it is about
  // to talk to us. Then, after releasing the lock, answer an ARP_REQUEST
  // for MYIP with an ARP_REPLY sent straight to the sender's card. Never
  // sleep.
  if(len < sizeof(struct arp))
    return;
  struct arp *a = (struct arp *)pkt;
  if(ntohs(a->hrd) != ARP_HRD_ETHER || ntohs(a->pro) != ETHTYPE_IP ||
     a->hln != ETHADDR_LEN || a->pln != sizeof(uint32))
    return;
  uint32 sip = ntohl(a->sip);
  uint32 tip = ntohl(a->tip);
  if(sip == 0)
    return;

  acquire(&arpcache.lock);
  if(tip == MYIP || arp_find(sip))
    arp_insert(sip, a->sha);
  release(&arpcache.lock);

  if(tip == MYIP && ntohs(a->op) == ARP_REQUEST)
    arp_send(ARP_REPLY, a->sha, a->sha, sip);
  // @end
}

// Find the Ethernet address of ip, a host on our LAN, and copy it to
// mac. If the cache does not know it, ask, and wait up to ARP_WAIT ticks
// for the answer. Returns 0, or -1 if nobody answered. It may sleep, so
// only a process may call it, never an interrupt handler.
int
arp_resolve(uint32 ip, uint8 *mac)
{
  // @build 08.02 arp_resolve
  // Look ip up in the cache (arp_find, under arpcache.lock); if it is
  // there, copy its address to mac and return 0. If not, broadcast an
  // ARP_REQUEST for it (target Ethernet address all zeroes: unknown) and
  // look again after every clock tick (tick_wait), repeating the request
  // every ARP_RETRY ticks in case it was lost. The answer may never come,
  // so nothing but the clock is sure to wake you. Return -1 after ARP_WAIT
  // ticks, or if tick_wait says this process was killed. Hold no lock
  // while you send or wait.
  for(int t = 0; ; t++){
    acquire(&arpcache.lock);
    struct arpent *e = arp_find(ip);
    if(e){
      memmove(mac, e->mac, ETHADDR_LEN);
      release(&arpcache.lock);
      return 0;
    }
    release(&arpcache.lock);

    if(t == ARP_WAIT)
      return -1;
    if(t % ARP_RETRY == 0)
      arp_send(ARP_REQUEST, broadcast, zeroes, ip);
    if(tick_wait() < 0)
      return -1;
  }
  // @end
}
