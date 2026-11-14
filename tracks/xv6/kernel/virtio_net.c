// The virtio network card driver.
//
// The card is a virtio device like the disk, one mmio slot further on
// (VIRTIO1, interrupt 2), with two queues. Queue 0 receives: the driver
// hands the card empty buffers ahead of time, and the card fills one with
// each frame that arrives. Queue 1 transmits: the driver posts a buffer
// holding a frame. Every buffer is a 12-byte struct virtio_net_hdr and
// then the Ethernet frame, and descriptor i always points at buffer i.

#include "kernel/types.h"
#include "kernel/riscv.h"
#include "kernel/defs.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/spinlock.h"
#include "kernel/virtio.h"
#include "kernel/net.h"

// the address of virtio mmio register r of the network card.
#define R(r) ((volatile uint32 *)(VIRTIO1 + (r)))

#define RXQ 0          // queue numbers
#define TXQ 1
#define BUFSZ 2048     // one buffer: header and a full frame (12 + 1514), rounded up

uint8 net_mac[ETHADDR_LEN];
int net_up;

// One virtqueue: the three tables shared with the card (as for the disk), and
// the NUM buffers its descriptors point at.
struct vq {
  struct virtq_desc *desc;
  struct virtq_avail *avail;
  struct virtq_used *used;
  uint16 used_idx;     // how far we have looked in used->ring
  char *buf[NUM];      // desc[i] always points at buf[i]
};

static struct {
  struct vq rx;
  struct vq tx;
  char txbusy[NUM];    // the card has tx.buf[i] and may not have sent it yet
  struct spinlock txlock;
} net;

// Allocate queue q's tables and buffers and tell the card where they are.
static void
vq_init(struct vq *vq, int q)
{
  *R(VIRTIO_MMIO_QUEUE_SEL) = q;
  if(*R(VIRTIO_MMIO_QUEUE_READY))
    panic("virtio net queue should not be ready");
  if(*R(VIRTIO_MMIO_QUEUE_NUM_MAX) < NUM)
    panic("virtio net queue too short");

  vq->desc = kalloc();
  vq->avail = kalloc();
  vq->used = kalloc();
  if(!vq->desc || !vq->avail || !vq->used)
    panic("virtio net kalloc");
  memset(vq->desc, 0, PGSIZE);
  memset(vq->avail, 0, PGSIZE);
  memset(vq->used, 0, PGSIZE);

  // two buffers per page.
  for(int i = 0; i < NUM; i += 2){
    char *page = kalloc();
    if(page == 0)
      panic("virtio net kalloc");
    vq->buf[i] = page;
    vq->buf[i+1] = page + BUFSZ;
  }
  for(int i = 0; i < NUM; i++){
    vq->desc[i].addr = (uint64)vq->buf[i];
    vq->desc[i].len = BUFSZ;
  }

  *R(VIRTIO_MMIO_QUEUE_NUM) = NUM;
  *R(VIRTIO_MMIO_QUEUE_DESC_LOW) = (uint64)vq->desc;
  *R(VIRTIO_MMIO_QUEUE_DESC_HIGH) = (uint64)vq->desc >> 32;
  *R(VIRTIO_MMIO_DRIVER_DESC_LOW) = (uint64)vq->avail;
  *R(VIRTIO_MMIO_DRIVER_DESC_HIGH) = (uint64)vq->avail >> 32;
  *R(VIRTIO_MMIO_DEVICE_DESC_LOW) = (uint64)vq->used;
  *R(VIRTIO_MMIO_DEVICE_DESC_HIGH) = (uint64)vq->used >> 32;
  *R(VIRTIO_MMIO_QUEUE_READY) = 0x1;
}

void
virtio_net_init(void)
{
  uint32 status = 0;

  initlock(&net.txlock, "virtio_net");

  // The card is optional. Without -device virtio-net-device the slot is
  // empty, and the kernel runs without a network (net_up stays 0).
  if(*R(VIRTIO_MMIO_MAGIC_VALUE) != 0x74726976 ||
     *R(VIRTIO_MMIO_VERSION) != 2 ||
     *R(VIRTIO_MMIO_DEVICE_ID) != 1 ||
     *R(VIRTIO_MMIO_VENDOR_ID) != 0x554d4551)
    return;

  // reset, then ACKNOWLEDGE and DRIVER, as for the disk.
  *R(VIRTIO_MMIO_STATUS) = status;
  status |= VIRTIO_CONFIG_S_ACKNOWLEDGE;
  *R(VIRTIO_MMIO_STATUS) = status;
  status |= VIRTIO_CONFIG_S_DRIVER;
  *R(VIRTIO_MMIO_STATUS) = status;

  // Feature bits come in banks of 32, picked with the _SEL registers.
  // Accept two: the card's address in config space, and VERSION_1, which
  // a modern device offers and a driver must accept (with it the header
  // is 12 bytes). The rest - checksum offload, segmentation, merged
  // receive buffers - stay off, so every frame fits in one buffer and
  // goes out exactly as the stack built it.
  *R(VIRTIO_MMIO_DEVICE_FEATURES_SEL) = 0;
  uint32 features = *R(VIRTIO_MMIO_DEVICE_FEATURES);
  *R(VIRTIO_MMIO_DRIVER_FEATURES_SEL) = 0;
  *R(VIRTIO_MMIO_DRIVER_FEATURES) = features & (1 << VIRTIO_NET_F_MAC);
  *R(VIRTIO_MMIO_DEVICE_FEATURES_SEL) = 1;
  features = *R(VIRTIO_MMIO_DEVICE_FEATURES);
  *R(VIRTIO_MMIO_DRIVER_FEATURES_SEL) = 1;
  *R(VIRTIO_MMIO_DRIVER_FEATURES) = features & (1 << (VIRTIO_F_VERSION_1 - 32));

  status |= VIRTIO_CONFIG_S_FEATURES_OK;
  *R(VIRTIO_MMIO_STATUS) = status;
  status = *R(VIRTIO_MMIO_STATUS);
  if(!(status & VIRTIO_CONFIG_S_FEATURES_OK))
    panic("virtio net FEATURES_OK unset");

  vq_init(&net.rx, RXQ);
  vq_init(&net.tx, TXQ);

  // Receive: every buffer goes to the card now, for it to write into.
  for(int i = 0; i < NUM; i++){
    net.rx.desc[i].flags = VRING_DESC_F_WRITE;
    net.rx.avail->ring[i] = i;
  }
  __sync_synchronize();
  net.rx.avail->idx = NUM;

  // Transmit: we notice finished buffers when we need one, in
  // virtio_net_send(), so the card need not interrupt for them.
  net.tx.avail->flags = VRING_AVAIL_F_NO_INTERRUPT;

  // Our Ethernet address, from the card's config space.
  volatile uint8 *config = (volatile uint8 *)R(VIRTIO_MMIO_CONFIG);
  for(int i = 0; i < ETHADDR_LEN; i++)
    net_mac[i] = config[i];

  status |= VIRTIO_CONFIG_S_DRIVER_OK;
  *R(VIRTIO_MMIO_STATUS) = status;

  // the receive buffers are waiting; the card may fill them now.
  *R(VIRTIO_MMIO_QUEUE_NOTIFY) = RXQ;
  net_up = 1;

  // plic.c and trap.c arrange for interrupts from VIRTIO1_IRQ.
}

// Send one Ethernet frame of len bytes. The frame is copied into one of
// the card's buffers, so the caller may reuse its own at once. Returns 0,
// or -1 if there is no card, the frame is too long, or every transmit
// buffer is still in flight; then the frame is dropped, which the network
// is allowed to do. Never sleeps: interrupt handlers send ARP replies.
int
virtio_net_send(void *frame, int len)
{
  // @build 08.01 virtio_net_send
  // Put one frame on the transmit queue. Return -1 if net_up is 0 or len
  // is more than an Ethernet header plus ETH_MTU. Under net.txlock: walk
  // the transmit used ring (net.tx.used_idx up to used->idx) and clear
  // txbusy[] for each buffer the card has finished with. Take a buffer that
  // is not busy; if none is free, release and return -1. Fill it with a
  // zeroed struct virtio_net_hdr and then the frame, and set its
  // descriptor's len to the two together. Mark it busy, put its index in
  // the avail ring, fence, bump avail->idx, fence, and write TXQ to
  // QUEUE_NOTIFY. Never sleep.
  if(!net_up || len < 0 || len > sizeof(struct eth) + ETH_MTU)
    return -1;

  acquire(&net.txlock);

  // take back the buffers the card has finished sending.
  while(net.tx.used_idx != net.tx.used->idx){
    __sync_synchronize();
    net.txbusy[net.tx.used->ring[net.tx.used_idx % NUM].id] = 0;
    net.tx.used_idx += 1;
  }

  int i;
  for(i = 0; i < NUM; i++)
    if(!net.txbusy[i])
      break;
  if(i == NUM){
    release(&net.txlock);
    return -1;   // all in flight: drop this frame
  }

  char *buf = net.tx.buf[i];
  memset(buf, 0, sizeof(struct virtio_net_hdr));
  memmove(buf + sizeof(struct virtio_net_hdr), frame, len);
  net.tx.desc[i].len = sizeof(struct virtio_net_hdr) + len;
  net.txbusy[i] = 1;

  // the same three steps as the disk: entry, fence, index.
  net.tx.avail->ring[net.tx.avail->idx % NUM] = i;
  __sync_synchronize();
  net.tx.avail->idx += 1;
  __sync_synchronize();
  *R(VIRTIO_MMIO_QUEUE_NOTIFY) = TXQ;

  release(&net.txlock);
  return 0;
  // @end
}

// The card raised interrupt 2: frames have arrived.
void
virtio_net_intr(void)
{
  // @build 08.01 virtio_net_intr
  // Frames have arrived. Acknowledge the interrupt (INTERRUPT_STATUS & 3
  // to INTERRUPT_ACK). Then for each new entry in the receive used ring
  // (net.rx.used_idx up to used->idx): its id names the buffer and its len
  // counts the bytes the card wrote, header included. Pass the frame after
  // the header to net_rx(), then give the buffer back to the card: its
  // index into the avail ring, fence, bump avail->idx. Once the loop is
  // done, write RXQ to QUEUE_NOTIFY so the card sees the buffers again.
  // No lock is needed: after init only this handler touches the receive
  // queue, and the PLIC never hands irq 2 to two harts at once.
  *R(VIRTIO_MMIO_INTERRUPT_ACK) = *R(VIRTIO_MMIO_INTERRUPT_STATUS) & 0x3;
  __sync_synchronize();

  int given = 0;
  while(net.rx.used_idx != net.rx.used->idx){
    __sync_synchronize();
    struct virtq_used_elem *e = &net.rx.used->ring[net.rx.used_idx % NUM];
    int id = e->id;
    int len = (int)e->len - (int)sizeof(struct virtio_net_hdr);  // @from 08.02
    // @from 08.02
    if(len > 0 && len <= BUFSZ - sizeof(struct virtio_net_hdr))
      net_rx(net.rx.buf[id] + sizeof(struct virtio_net_hdr), len);
    // @end
    net.rx.used_idx += 1;

    // the frame has been dealt with; the card may fill the buffer again.
    net.rx.avail->ring[net.rx.avail->idx % NUM] = id;
    __sync_synchronize();
    net.rx.avail->idx += 1;
    given++;
  }

  if(given){
    __sync_synchronize();
    *R(VIRTIO_MMIO_QUEUE_NOTIFY) = RXQ;
  }
  // @end
}
