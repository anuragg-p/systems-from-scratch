// UDP sockets.
//
// A socket is the end of the stack a process holds: a local UDP port,
// and a queue of the datagrams that have arrived for it and not been
// read yet. It lives behind a file descriptor (FD_SOCK), so close(),
// dup(), fork() and exit() treat it like any other open file. The
// system calls are in sysfile.c:
//   socket(port)                       bind a port (0: any free one)
//   sendto(fd, buf, n, ip, port)       send one datagram
//   recvfrom(fd, buf, n, &ip, &port)   wait for one, and see who sent it
//
// Like a pipe, it has two sides that never meet: the interrupt
// handler adds datagrams (sock_deliver) and a process takes them off
// (sockrecv), sleeping while the queue is empty.

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/riscv.h"
#include "kernel/spinlock.h"
#include "kernel/proc.h"
#include "kernel/defs.h"
#include "kernel/net.h"

#define EPHEMERAL 49152   // ports from here up are handed out by socket(0)

static struct {
  struct spinlock lock;   // guards every socket and its queue
  struct sock sock[NSOCK];
  uint16 nextport;        // where socket(0) looks for a free port next
} socks;

void
sockinit(void)
{
  initlock(&socks.lock, "socks");
  socks.nextport = EPHEMERAL;
}

// The socket bound to port, or 0. Caller holds socks.lock.
static struct sock*
sock_find(uint16 port)
{
  for(struct sock *so = socks.sock; so < socks.sock + NSOCK; so++)
    if(so->used && so->port == port)
      return so;
  return 0;
}

// Bind a new socket to a UDP port; port 0 means any free port.
// Returns the socket, or 0 if the port is taken or there is no free
// socket.
struct sock*
sockalloc(int port)
{
  // @build 08.04 sockalloc
  // A socket is a free slot in socks.sock bound to a port no other socket
  // holds. Under socks.lock: if port is 0, pick one yourself - try
  // socks.nextport, then the ports after it, wrapping from 65535 back to
  // EPHEMERAL, until one is not in use (sock_find), and leave nextport
  // just past it. If port is already bound, fail. Take a slot that is not
  // used, mark it used, set its port and an empty queue, and return it;
  // return 0 if there is none.
  struct sock *so;

  acquire(&socks.lock);
  if(port == 0){
    for(int tries = 0; tries <= 65535 - EPHEMERAL; tries++){
      uint16 p = socks.nextport;
      socks.nextport = p == 65535 ? EPHEMERAL : p + 1;
      if(sock_find(p) == 0){
        port = p;
        break;
      }
    }
  }
  if(port == 0 || sock_find(port)){
    release(&socks.lock);
    return 0;
  }
  for(so = socks.sock; so < socks.sock + NSOCK; so++){
    if(!so->used){
      so->used = 1;
      so->port = port;
      so->head = so->tail = 0;
      so->qlen = 0;
      release(&socks.lock);
      return so;
    }
  }
  release(&socks.lock);
  return 0;
  // @end
}

// The last file descriptor for so is closed: free its port and throw
// away whatever is still queued.
void
sockclose(struct sock *so)
{
  struct dgram *d;

  acquire(&socks.lock);
  while((d = so->head) != 0){
    so->head = d->next;
    kfree(d);
  }
  so->tail = 0;
  so->qlen = 0;
  so->used = 0;
  release(&socks.lock);
}

// Send n bytes at user address addr as one datagram from so to port
// dport of dst. Returns n, or -1. May sleep (ARP).
int
socksend(struct sock *so, uint64 addr, int n, uint32 dst, uint16 dport)
{
  // @build 08.04 socksend
  // One datagram: refuse (-1) a negative n or more than UDP_MAXDATA bytes.
  // Take a page from kalloc to build the packet in, copy the n bytes from
  // the process (copyin) to HDRSPACE bytes into it, leaving the room in
  // front for the headers, and send it with udp_send from so->port. Free
  // the page whatever happens. Return n, or -1 if anything failed. Hold no
  // lock across udp_send: it may sleep.
  if(n < 0 || n > UDP_MAXDATA)
    return -1;
  char *page = kalloc();
  if(page == 0)
    return -1;
  char *payload = page + HDRSPACE;
  int r = -1;
  if(copyin(myproc()->pagetable, payload, addr, n) == 0 &&
     udp_send(payload, n, so->port, dst, dport) == 0)
    r = n;
  kfree(page);
  return r;
  // @end
}

// Wait for a datagram on so and copy up to n bytes of it to user address
// addr, and the sender's address and port to ipaddr and portaddr (user
// pointers to a uint32 and an int; 0 for "do not care"). Returns the
// number of bytes copied; the rest of a longer datagram is lost. -1 if
// the process is killed while it waits.
int
sockrecv(struct sock *so, uint64 addr, int n, uint64 ipaddr, uint64 portaddr)
{
  // @build 08.04 sockrecv
  // The process side of the queue. Under socks.lock, sleep on so while the
  // queue is empty, returning -1 if the process has been killed. Unlink
  // the oldest datagram and release the lock: it is yours now. Copy out
  // min(n, its length) bytes to addr, and, when ipaddr or portaddr is not
  // 0, the sender's address (a uint32) and port (as an int). Free the
  // datagram's page. Return the bytes copied, or -1 if a copyout failed.
  struct proc *p = myproc();
  struct dgram *d;

  acquire(&socks.lock);
  while(so->head == 0){
    if(killed(p)){
      release(&socks.lock);
      return -1;
    }
    sleep(so, &socks.lock);
  }
  d = so->head;
  so->head = d->next;
  if(so->head == 0)
    so->tail = 0;
  so->qlen--;
  release(&socks.lock);

  int m = d->len < n ? d->len : n;
  int sport = d->sport;
  int r = m;
  if(m < 0 || copyout(p->pagetable, addr, d->data, m) < 0)
    r = -1;
  if(ipaddr && copyout(p->pagetable, ipaddr, (char *)&d->src, sizeof(d->src)) < 0)
    r = -1;
  if(portaddr && copyout(p->pagetable, portaddr, (char *)&sport, sizeof(sport)) < 0)
    r = -1;
  kfree(d);
  return r;
  // @end
}

// A datagram of len bytes for port has arrived from (src, sport). Called
// by udp_rx, in interrupt context.
void
sock_deliver(uint16 port, uint32 src, uint16 sport, char *data, int len)
{
  // @build 08.04 sock_deliver
  // The interrupt side of the queue. Under socks.lock, find the socket
  // bound to port. If there is none, or it already holds SOCKQ datagrams,
  // drop this one: UDP promises nothing. Otherwise copy it into a page from
  // kalloc as a struct dgram (sender, port, length, data; drop it if kalloc
  // fails), append it to the tail of the queue, and wake up whoever sleeps
  // on the socket. Never sleep.
  struct sock *so;
  struct dgram *d;

  if(len < 0 || len > UDP_MAXDATA)
    return;
  acquire(&socks.lock);
  so = sock_find(port);
  if(so == 0 || so->qlen >= SOCKQ || (d = kalloc()) == 0){
    release(&socks.lock);
    return;   // nobody listening, or too much waiting: dropped
  }
  d->next = 0;
  d->src = src;
  d->sport = sport;
  d->len = len;
  memmove(d->data, data, len);
  if(so->tail)
    so->tail->next = d;
  else
    so->head = d;
  so->tail = d;
  so->qlen++;
  wakeup(so);
  release(&socks.lock);
  // @end
}
