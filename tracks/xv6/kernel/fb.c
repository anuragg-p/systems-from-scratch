// The screen.
//
// QEMU's ramfb is the simplest display there is: a framebuffer in
// ordinary RAM that the "graphics card" reads, over and over. The kernel
// picks the memory, the size and the pixel format, and tells QEMU about
// them once, by writing a 28-byte record into a fw_cfg file named
// "etc/ramfb". From then on, whatever is in that memory is on the screen.
// There are no commands, no interrupts and nothing to flush.
//
// fw_cfg is how QEMU hands configuration to firmware (UEFI and U-Boot
// find the kernel and ACPI tables through it). On the virt machine it is
// three registers at FW_CFG:
//   +0   data       the selected item, read one byte at a time
//   +8   selector   16 bits: which item to read or write next
//   +16  DMA        64 bits: the address of a struct fw_cfg_dma request
// Items are numbered; item 0x19 is a directory of named files. Every
// register and every number fw_cfg reads or writes is big-endian.
//
// QEMU attaches it with -device ramfb.

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/riscv.h"
#include "kernel/spinlock.h"
#include "kernel/proc.h"
#include "kernel/defs.h"
#include "kernel/fb.h"

#define FW_CFG_DATA  (FW_CFG + 0)
#define FW_CFG_SEL   (FW_CFG + 8)
#define FW_CFG_DMA   (FW_CFG + 16)

#define FW_CFG_SIGNATURE 0x0000   // the item that reads "QEMU"
#define FW_CFG_FILE_DIR  0x0019   // the item that lists the named files

// the control bits of a DMA request
#define FW_CFG_DMA_ERROR  0x01
#define FW_CFG_DMA_SELECT 0x08    // select the item in the top 16 bits first
#define FW_CFG_DMA_WRITE  0x10

// One entry of the file directory: 64 bytes, numbers big-endian.
struct fw_cfg_file {
  uint32 size;
  uint16 select;      // the item number to select for this file
  uint16 reserved;
  char name[56];      // "etc/ramfb", 0-terminated
};

// A DMA request. QEMU reads it from RAM at the address written to the
// DMA register, carries it out, and then writes control back: 0 when it
// went well, FW_CFG_DMA_ERROR when it did not.
struct fw_cfg_dma {
  uint32 control;
  uint32 length;
  uint64 address;
};

// What ramfb wants written to etc/ramfb: 28 bytes, all big-endian.
struct ramfb_cfg {
  uint64 addr;        // physical address of pixel (0, 0)
  uint32 fourcc;      // the pixel format
  uint32 flags;       // 0
  uint32 width;
  uint32 height;
  uint32 stride;      // bytes from one row to the next
} __attribute__((packed));

#define DRM_FORMAT_XRGB8888 0x34325258   // "XR24", read as a little-endian word

// The pixels: 300 pages of kernel memory. They are part of the kernel
// image's bss, below `end`, so kalloc never hands them out and kfree
// refuses them.
static char fb[FB_SIZE] __attribute__((aligned(PGSIZE)));
int fb_up;            // 1 once QEMU shows fb on the screen

// RISC-V is little-endian, fw_cfg big-endian: swap the bytes, both ways.
static uint16 be16(uint16 x) { return (x << 8) | (x >> 8); }
static uint32 be32(uint32 x) { return ((uint32)be16(x) << 16) | be16(x >> 16); }
static uint64 be64(uint64 x) { return ((uint64)be32(x) << 32) | be32(x >> 32); }

// Make item sel the one the data register reads.
static void
fw_cfg_select(uint16 sel)
{
  *(volatile uint16 *)FW_CFG_SEL = be16(sel);
}

// Read the next n bytes of the selected item into buf.
static void
fw_cfg_read(void *buf, int n)
{
  for(int i = 0; i < n; i++)
    ((char *)buf)[i] = *(volatile uint8 *)FW_CFG_DATA;
}

// Find the fw_cfg file called name. Returns its item number, or -1.
static int
fw_cfg_find(char *name)
{
  // @build 09.01 fw_cfg_find
  // Item FW_CFG_FILE_DIR is a directory: a 32-bit count of files, then
  // that many struct fw_cfg_file, numbers big-endian (be32, be16). Select
  // it, read the count, then read the entries one by one: each read
  // carries on where the last one stopped. Return the select number of
  // the entry whose name is name, or -1 if none is.
  uint32 count;
  struct fw_cfg_file f;

  fw_cfg_select(FW_CFG_FILE_DIR);
  fw_cfg_read(&count, sizeof(count));
  count = be32(count);
  for(uint32 i = 0; i < count; i++){
    fw_cfg_read(&f, sizeof(f));
    if(strncmp(f.name, name, sizeof(f.name)) == 0)
      return be16(f.select);
  }
  return -1;
  // @end
}

// Write len bytes from buf into fw_cfg item sel. Returns 0, or -1 if
// QEMU refuses. buf must be at a physical address: in the kernel's data
// or a page from kalloc, not on a process's kernel stack.
static int
fw_cfg_write(int sel, void *buf, int len)
{
  static struct fw_cfg_dma req;
  volatile struct fw_cfg_dma *d = &req;

  // @build 09.01 fw_cfg_write
  // fw_cfg accepts writes only by DMA. Fill in d, big-endian: control is
  // sel in the top 16 bits with FW_CFG_DMA_SELECT and FW_CFG_DMA_WRITE,
  // length is len, address is buf. Fence, so the request is in RAM, then
  // write d's own address, big-endian, to the 64-bit DMA register: that
  // starts the transfer. QEMU clears control when it is done, or leaves
  // FW_CFG_DMA_ERROR set. Wait until no other bit is set, and return -1
  // if the error bit is.
  d->control = be32((uint32)sel << 16 | FW_CFG_DMA_SELECT | FW_CFG_DMA_WRITE);
  d->length = be32(len);
  d->address = be64((uint64)buf);
  __sync_synchronize();
  *(volatile uint64 *)FW_CFG_DMA = be64((uint64)d);
  while(be32(d->control) & ~FW_CFG_DMA_ERROR)
    ;
  __sync_synchronize();
  return (be32(d->control) & FW_CFG_DMA_ERROR) ? -1 : 0;
  // @end
}

// Fill the rectangle w pixels wide and h high whose top left corner is
// (x, y) with color (0x00RRGGBB). Whatever falls off the screen is left
// out.
void
fb_rect(int x, int y, int w, int h, uint32 color)
{
  // @build 09.01 fb_rect
  // Clip first: the rectangle may hang off any edge, or miss the screen
  // altogether (then draw nothing). Then set each pixel in it to color.
  // Pixel (x, y) is the uint32 at fb + y * FB_STRIDE + x * FB_BPP.
  if(x < 0){
    w += x;
    x = 0;
  }
  if(y < 0){
    h += y;
    y = 0;
  }
  if(x + w > FB_WIDTH)
    w = FB_WIDTH - x;
  if(y + h > FB_HEIGHT)
    h = FB_HEIGHT - y;
  for(int j = 0; j < h; j++){
    uint32 *row = (uint32 *)(fb + (y + j) * FB_STRIDE + x * FB_BPP);
    for(int i = 0; i < w; i++)
      row[i] = color;
  }
  // @end
}

// The boot screen: a dark background, a white border one pixel wide
// around the very edge, and a red, a green and a blue square.
#define BOOT_BG 0x202830
static void
testcard(void)
{
  fb_rect(0, 0, FB_WIDTH, FB_HEIGHT, 0xffffff);
  fb_rect(1, 1, FB_WIDTH - 2, FB_HEIGHT - 2, BOOT_BG);
  fb_rect(160, 200, 80, 80, 0xff0000);
  fb_rect(280, 200, 80, 80, 0x00ff00);
  fb_rect(400, 200, 80, 80, 0x0000ff);
}

void
fbinit(void)
{
  static struct ramfb_cfg cfg;
  char sig[4];
  int sel;

  // Is QEMU's fw_cfg there, and a ramfb on it? Without -device ramfb
  // there is no etc/ramfb, and the kernel runs without a screen.
  fw_cfg_select(FW_CFG_SIGNATURE);
  fw_cfg_read(sig, sizeof(sig));
  if(memcmp(sig, "QEMU", 4) != 0)
    return;
  if((sel = fw_cfg_find("etc/ramfb")) < 0)
    return;

  testcard();

  cfg.addr = be64((uint64)fb);
  cfg.fourcc = be32(DRM_FORMAT_XRGB8888);
  cfg.flags = 0;
  cfg.width = be32(FB_WIDTH);
  cfg.height = be32(FB_HEIGHT);
  cfg.stride = be32(FB_STRIDE);
  if(fw_cfg_write(sel, &cfg, sizeof(cfg)) < 0){
    printf("fbinit: ramfb refused the configuration\n");
    return;
  }
  fb_up = 1;
}

// ---------------------------------------------------------------- the screen in user space @from 09.02

// The fbmap() system call: map the screen into the calling process at
// FBVA, readable and writable from user mode, so that the process can
// draw by storing to memory. Returns FBVA, or -1 if there is no screen.
uint64
sys_fbmap(void)
{
  struct proc *p = myproc();

  // @build 09.02 fbmap
  // Return -1 if there is no screen (fb_up is 0). If p already has it
  // (walkaddr(p->pagetable, FBVA) is not 0), return FBVA. Otherwise map
  // the FB_SIZE bytes at fb into p->pagetable at FBVA with mappages,
  // user readable and writable. The pages stay the kernel's: p->sz does
  // not grow, so fork's uvmcopy and exit's uvmfree never see them. If
  // mappages fails part way, take back what it mapped (fbunmap) and
  // return -1. Return FBVA.
  if(!fb_up)
    return -1;
  if(walkaddr(p->pagetable, FBVA) != 0)
    return FBVA;
  if(mappages(p->pagetable, FBVA, FB_SIZE, (uint64)fb, PTE_R | PTE_W | PTE_U) < 0){
    fbunmap(p->pagetable);
    return -1;
  }
  return FBVA;
  // @end
}

// Take the screen out of a page table that is about to be freed,
// leaving its pages alone: they are fb's, not kalloc's. Called by
// proc_freepagetable() for every process that exits or execs, whether
// it mapped the screen or not.
void
fbunmap(pagetable_t pagetable)
{
  // @build 09.02 fbunmap
  // For each page of the screen, FBVA up to FBVA + FB_SIZE: if the page
  // table maps it (walk without allocating finds a valid PTE), clear the
  // PTE. Never kfree the page, and do not panic over a page that is not
  // mapped: most processes never map the screen, and a failed fbmap may
  // have mapped only part of it. With the leaves gone, freewalk() can
  // free the page-table pages.
  // @stub ;
  for(uint64 va = FBVA; va < FBVA + FB_SIZE; va += PGSIZE){
    pte_t *pte = walk(pagetable, va, 0);
    if(pte != 0 && (*pte & PTE_V))
      *pte = 0;
  }
  // @end
}
