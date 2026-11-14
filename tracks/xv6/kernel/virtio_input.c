// The keyboard and the mouse: virtio input devices.
//
// QEMU's virtio-keyboard-device and virtio-tablet-device are virtio
// devices like the disk, on mmio slots 2 and 3: registers at VIRTIO2 and
// VIRTIO3, interrupts 3 and 4. Each has an event queue, and the events
// arrive whenever keys go down or the pointer moves, not when the driver
// asks: so the driver hands the device empty buffers ahead of time, and
// the device writes one event into each. (Each also has a status queue,
// for the driver to light the keyboard's LEDs; xv6 leaves it alone.)
//
// The interrupt handler moves every event into one queue that both
// devices share, and gives the buffer back to its device. A process
// reads the queue with read() on the input device file (major INPUT,
// kernel/input.h), and sleeps while it is empty.
//
// QEMU attaches them with:
//   -device virtio-keyboard-device,bus=virtio-mmio-bus.2
//   -device virtio-tablet-device,bus=virtio-mmio-bus.3
// The tablet is a mouse that reports where the pointer is (EV_ABS), not
// how far it moved, so the pointer in xv6 is where it is in the window.

#include "kernel/types.h"
#include "kernel/riscv.h"
#include "kernel/defs.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/spinlock.h"
#include "kernel/sleeplock.h"
#include "kernel/fs.h"
#include "kernel/file.h"
#include "kernel/proc.h"
#include "kernel/virtio.h"
#include "kernel/fb.h"
#include "kernel/input.h"

#define EVENTQ 0     // the event queue; queue 1 is the status queue
#define NEVQ 64      // events waiting to be read, at most

// the virtio input device's configuration space, at VIRTIO_MMIO_CONFIG:
// write select and subsel to choose what to ask, then read size and u.
#define VIRTIO_INPUT_CFG_ABS_INFO 0x12   // subsel: the axis, ABS_X or ABS_Y
struct virtio_input_config {
  uint8 select;
  uint8 subsel;
  uint8 size;          // how many bytes of u hold the answer; 0: none
  uint8 reserved[5];
  struct {             // u, for VIRTIO_INPUT_CFG_ABS_INFO
    uint32 min;
    uint32 max;
    uint32 fuzz;
    uint32 flat;
    uint32 res;
  } abs;
};

// One event as the device writes it into a buffer: the same 8 bytes as
// struct inputevent.
struct virtio_input_event {
  uint16 type;
  uint16 code;
  uint32 value;
};

// One device and its event queue. desc[i] always points at ev[i].
struct indev {
  uint64 base;         // its registers
  int irq;
  int up;              // found and set up
  struct virtq_desc *desc;
  struct virtq_avail *avail;
  struct virtq_used *used;
  uint16 used_idx;     // how far we have looked in used->ring
  struct virtio_input_event *ev;
  int absmax[2];       // EV_ABS values for ABS_X and ABS_Y run from 0 to these
};

static struct indev devs[] = {
  { VIRTIO2, VIRTIO2_IRQ },
  { VIRTIO3, VIRTIO3_IRQ },
};

// The events both devices have delivered and no process has read yet.
// q[r % NEVQ] is the oldest; r == w means none.
static struct {
  struct spinlock lock;
  struct inputevent q[NEVQ];
  uint r;
  uint w;
} input;

#define R(d, r) ((volatile uint32 *)((d)->base + (r)))

static int inputread(int user_dst, uint64 dst, int n);

// The range of axis (ABS_X or ABS_Y) from the device's config space,
// or 0 if the device has no such axis (a keyboard).
static int
absmax(struct indev *d, int axis)
{
  volatile struct virtio_input_config *c = (void *)R(d, VIRTIO_MMIO_CONFIG);
  c->select = VIRTIO_INPUT_CFG_ABS_INFO;
  c->subsel = axis;
  __sync_synchronize();
  if(c->size == 0)
    return 0;
  return c->abs.max;
}

static void
indev_init(struct indev *d)
{
  uint32 status = 0;

  // An empty slot, or some other device: no keyboard or mouse there.
  if(*R(d, VIRTIO_MMIO_MAGIC_VALUE) != 0x74726976 ||
     *R(d, VIRTIO_MMIO_VERSION) != 2 ||
     *R(d, VIRTIO_MMIO_DEVICE_ID) != 18 ||
     *R(d, VIRTIO_MMIO_VENDOR_ID) != 0x554d4551)
    return;

  // reset, ACKNOWLEDGE, DRIVER, and the features: VERSION_1 alone.
  *R(d, VIRTIO_MMIO_STATUS) = status;
  status |= VIRTIO_CONFIG_S_ACKNOWLEDGE;
  *R(d, VIRTIO_MMIO_STATUS) = status;
  status |= VIRTIO_CONFIG_S_DRIVER;
  *R(d, VIRTIO_MMIO_STATUS) = status;
  *R(d, VIRTIO_MMIO_DRIVER_FEATURES_SEL) = 0;
  *R(d, VIRTIO_MMIO_DRIVER_FEATURES) = 0;
  *R(d, VIRTIO_MMIO_DEVICE_FEATURES_SEL) = 1;
  uint32 features = *R(d, VIRTIO_MMIO_DEVICE_FEATURES);
  *R(d, VIRTIO_MMIO_DRIVER_FEATURES_SEL) = 1;
  *R(d, VIRTIO_MMIO_DRIVER_FEATURES) = features & (1 << (VIRTIO_F_VERSION_1 - 32));
  status |= VIRTIO_CONFIG_S_FEATURES_OK;
  *R(d, VIRTIO_MMIO_STATUS) = status;
  if(!(*R(d, VIRTIO_MMIO_STATUS) & VIRTIO_CONFIG_S_FEATURES_OK))
    panic("virtio input FEATURES_OK unset");

  // Where the pointer can be: the tablet says 0 to 32767 on each axis.
  d->absmax[ABS_X] = absmax(d, ABS_X);
  d->absmax[ABS_Y] = absmax(d, ABS_Y);

  // The event queue: three tables and one page of NUM event buffers.
  *R(d, VIRTIO_MMIO_QUEUE_SEL) = EVENTQ;
  if(*R(d, VIRTIO_MMIO_QUEUE_READY))
    panic("virtio input queue should not be ready");
  if(*R(d, VIRTIO_MMIO_QUEUE_NUM_MAX) < NUM)
    panic("virtio input queue too short");
  d->desc = kalloc();
  d->avail = kalloc();
  d->used = kalloc();
  d->ev = kalloc();
  if(!d->desc || !d->avail || !d->used || !d->ev)
    panic("virtio input kalloc");
  memset(d->desc, 0, PGSIZE);
  memset(d->avail, 0, PGSIZE);
  memset(d->used, 0, PGSIZE);
  memset(d->ev, 0, PGSIZE);
  *R(d, VIRTIO_MMIO_QUEUE_NUM) = NUM;
  *R(d, VIRTIO_MMIO_QUEUE_DESC_LOW) = (uint64)d->desc;
  *R(d, VIRTIO_MMIO_QUEUE_DESC_HIGH) = (uint64)d->desc >> 32;
  *R(d, VIRTIO_MMIO_DRIVER_DESC_LOW) = (uint64)d->avail;
  *R(d, VIRTIO_MMIO_DRIVER_DESC_HIGH) = (uint64)d->avail >> 32;
  *R(d, VIRTIO_MMIO_DEVICE_DESC_LOW) = (uint64)d->used;
  *R(d, VIRTIO_MMIO_DEVICE_DESC_HIGH) = (uint64)d->used >> 32;
  *R(d, VIRTIO_MMIO_QUEUE_READY) = 0x1;

  // Every buffer goes to the device now, for it to write an event into.
  for(int i = 0; i < NUM; i++){
    d->desc[i].addr = (uint64)&d->ev[i];
    d->desc[i].len = sizeof(struct virtio_input_event);
    d->desc[i].flags = VRING_DESC_F_WRITE;
    d->avail->ring[i] = i;
  }
  __sync_synchronize();
  d->avail->idx = NUM;

  status |= VIRTIO_CONFIG_S_DRIVER_OK;
  *R(d, VIRTIO_MMIO_STATUS) = status;
  *R(d, VIRTIO_MMIO_QUEUE_NOTIFY) = EVENTQ;
  d->up = 1;

  // plic.c and trap.c arrange for interrupts from d->irq.
}

void
virtio_input_init(void)
{
  initlock(&input.lock, "input");
  devsw[INPUT].read = inputread;
  for(int i = 0; i < NELEM(devs); i++)
    indev_init(&devs[i]);
}

// A keyboard or mouse raised its interrupt: events have arrived.
void
virtio_input_intr(int irq)
{
  struct indev *d = 0;
  for(int i = 0; i < NELEM(devs); i++)
    if(devs[i].irq == irq && devs[i].up)
      d = &devs[i];
  if(d == 0)
    return;

  // @build 09.03 virtio_input_intr
  // Acknowledge the interrupt (INTERRUPT_STATUS & 3 to INTERRUPT_ACK).
  // For each new entry in d's used ring (d->used_idx up to used->idx),
  // the buffer d->ev[id] holds one event. Under input.lock, append it to
  // input.q as a struct inputevent, unless NEVQ events are already
  // waiting: then drop it. An EV_ABS value for ABS_X or ABS_Y is a
  // position from 0 to d->absmax[axis]; turn it into a pixel, 0 to
  // FB_WIDTH - 1 or FB_HEIGHT - 1. Give the buffer back to the device
  // (avail ring, fence, avail->idx += 1). After the loop, wake up the
  // readers sleeping on &input.r and write EVENTQ to QUEUE_NOTIFY once.
  *R(d, VIRTIO_MMIO_INTERRUPT_ACK) = *R(d, VIRTIO_MMIO_INTERRUPT_STATUS) & 0x3;
  __sync_synchronize();

  acquire(&input.lock);
  while(d->used_idx != d->used->idx){
    __sync_synchronize();
    int id = d->used->ring[d->used_idx % NUM].id;
    struct virtio_input_event *ve = &d->ev[id];
    struct inputevent e;
    e.type = ve->type;
    e.code = ve->code;
    e.value = ve->value;
    if(e.type == EV_ABS && e.code <= ABS_Y && d->absmax[e.code] > 0){
      int size = e.code == ABS_X ? FB_WIDTH : FB_HEIGHT;
      e.value = (uint64)ve->value * size / ((uint64)d->absmax[e.code] + 1);
    }
    if(input.w - input.r < NEVQ)
      input.q[input.w++ % NEVQ] = e;
    d->used_idx += 1;

    // the event is copied; the device may write into the buffer again.
    d->avail->ring[d->avail->idx % NUM] = id;
    __sync_synchronize();
    d->avail->idx += 1;
  }
  wakeup(&input.r);
  release(&input.lock);

  __sync_synchronize();
  *R(d, VIRTIO_MMIO_QUEUE_NOTIFY) = EVENTQ;
  // @end
}

// read() on the input device: copy whole events, oldest first, into the
// n bytes at dst, sleeping until there is at least one. Returns the bytes
// copied: a multiple of sizeof(struct inputevent).
static int
inputread(int user_dst, uint64 dst, int n)
{
  // @build 09.03 inputread
  // Return -1 if n cannot hold even one struct inputevent. Under
  // input.lock, sleep on &input.r while the queue is empty, returning -1
  // if the process has been killed. Then take events off the queue, oldest
  // first, copying each to dst with either_copyout, for as long as there
  // are events and room for another whole one in n. Return the bytes
  // copied (or -1 if not even the first copy worked).
  int got = 0;

  if(n < sizeof(struct inputevent))
    return -1;
  acquire(&input.lock);
  while(input.r == input.w){
    if(killed(myproc())){
      release(&input.lock);
      return -1;
    }
    sleep(&input.r, &input.lock);
  }
  while(input.r != input.w && n - got >= sizeof(struct inputevent)){
    struct inputevent e = input.q[input.r % NEVQ];
    if(either_copyout(user_dst, dst + got, &e, sizeof(e)) < 0)
      break;
    input.r++;
    got += sizeof(e);
  }
  release(&input.lock);
  return got > 0 ? got : -1;
  // @end
}
