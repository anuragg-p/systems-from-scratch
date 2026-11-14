// Every function one kernel file calls in another. Reading this file top
// to bottom is a fair map of the kernel.

struct buf;  // @from 05.01
struct context;  // @from 04.02
struct file;  // @from 05.07
struct inode;  // @from 05.05
struct pipe;  // @from 06.06
struct proc;  // @from 04.01
struct spinlock;  // @from 01.03
struct sleeplock;  // @from 05.02
struct sock;  // @from 08.04
struct stat;  // @from 05.05
struct superblock;  // @from 05.04

// @from 05.02
// bio.c - the buffer cache
void            binit(void);
struct buf*     bread(uint, uint);
void            brelse(struct buf*);
void            bwrite(struct buf*);
void            bpin(struct buf*);
void            bunpin(struct buf*);
// @end

// console.c - the console @from 01.03
void            consoleinit(void);  // @from 01.03
void            consoleintr(int);  // @from 03.03
void            consputc(int);  // @from 01.03

// @from 08.02
// ether.c - Ethernet frames and ARP
void            arpinit(void);
int             arp_resolve(uint32, uint8*);
void            arp_rx(char*, int);
int             eth_send(char*, int, uint16, uint8*);
void            net_rx(char*, int);
// @end

// @from 06.03
// exec.c
int             kexec(char*, char**);
// @end

// @from 05.07
// file.c - open files
struct file*    filealloc(void);
void            fileclose(struct file*);
struct file*    filedup(struct file*);
void            fileinit(void);
int             fileread(struct file*, uint64, int n);
int             filestat(struct file*, uint64 addr);
int             filewrite(struct file*, uint64, int n);
// @end

// @from 09.01
// fb.c - the screen
void            fbinit(void);
void            fb_rect(int, int, int, int, uint32);
void            fbunmap(pagetable_t);  // @from 09.02
// @end

// fs.c - the file system @from 05.03
void            fsinit(int);  // @from 05.03
int             dirlink(struct inode*, char*, uint);  // @from 05.06
struct inode*   dirlookup(struct inode*, char*, uint*);  // @from 05.06
struct inode*   ialloc(uint, short);  // @from 05.05
struct inode*   idup(struct inode*);  // @from 05.05
void            iinit(void);  // @from 05.05
void            ilock(struct inode*);  // @from 05.05
void            iput(struct inode*);  // @from 05.05
void            iunlock(struct inode*);  // @from 05.05
void            iunlockput(struct inode*);  // @from 05.05
void            iupdate(struct inode*);  // @from 05.05
int             namecmp(const char*, const char*);  // @from 05.06
struct inode*   namei(char*);  // @from 05.06
struct inode*   nameiparent(char*, char*);  // @from 05.06
int             readi(struct inode*, int, uint64, uint, uint);  // @from 05.05
void            stati(struct inode*, struct stat*);  // @from 05.05
int             writei(struct inode*, int, uint64, uint, uint);  // @from 05.05
void            itrunc(struct inode*);  // @from 05.05
// @internal
uint            balloc_count_free(int);
// @end

// @from 08.03
// ip.c - IPv4 and UDP
uint16          in_cksum(void*, int, uint32);
void            ip_rx(char*, int);
int             ip_send(char*, int, uint8, uint32);
void            udp_rx(char*, int, uint32, uint32);
int             udp_send(char*, int, uint16, uint32, uint16);
// @end

// @from 02.02
// kalloc.c - physical page allocator
void*           kalloc(void);
void            kfree(void *);
void            kinit(void);
// @internal
int             kfreecount(void);
// @end
// @end

// @from 05.04
// log.c - write-ahead log
void            initlog(int, struct superblock*);
void            log_write(struct buf*);
void            begin_op(void);
void            end_op(void);
// @end

// @from 06.06
// pipe.c
int             pipealloc(struct file**, struct file**);
void            pipeclose(struct pipe*, int);
int             piperead(struct pipe*, uint64, int);
int             pipewrite(struct pipe*, uint64, int);
// @end

// printf.c @from 01.03
int             printf(char*, ...) __attribute__ ((format (printf, 1, 2)));  // @from 01.03
void            panic(char*) __attribute__((noreturn));  // @from 01.03
void            printfinit(void);  // @from 02.03

// proc.c @from 01.03
int             cpuid(void);  // @from 01.03
void            kexit(int);  // @from 06.01
int             kfork(void);  // @from 06.04
int             growproc(int);  // @from 06.05
void            proc_mapstacks(pagetable_t);  // @from 04.01
pagetable_t     proc_pagetable(struct proc *);  // @from 04.01
void            proc_freepagetable(pagetable_t, uint64);  // @from 04.01
int             kkill(int);  // @from 06.04
int             killed(struct proc*);  // @from 05.07
void            setkilled(struct proc*);  // @from 05.07
struct cpu*     mycpu(void);  // @from 01.03
struct proc*    myproc(void);  // @from 04.01
void            procinit(void);  // @from 04.01
void            scheduler(void) __attribute__((noreturn));  // @from 04.02
void            sched(void);  // @from 04.02
void            sleep(void*, struct spinlock*);  // @from 04.03
void            userinit(void);  // @from 07.02
int             kwait(uint64);  // @from 06.04
void            wakeup(void*);  // @from 04.03
void            yield(void);  // @from 04.02
int             either_copyout(int user_dst, uint64 dst, void *src, uint64 len);  // @from 05.05
int             either_copyin(void *dst, int user_src, uint64 src, uint64 len);  // @from 05.05
void            procdump(void);  // @from 04.01
// @internal
int             kthread(char *name, void (*fn)(void*), void *arg);
// @end

// @from 04.02
// swtch.S
void            swtch(struct context*, struct context*);
// @end

// @from 01.02
// start.c
void            early_puts(char*);
// @end

// @from 08.04
// sock.c - UDP sockets
void            sockinit(void);
struct sock*    sockalloc(int);
void            sockclose(struct sock*);
void            sock_deliver(uint16, uint32, uint16, char*, int);
int             sockrecv(struct sock*, uint64, int, uint64, uint64);
int             socksend(struct sock*, uint64, int, uint32, uint16);
// @end

// @from 02.03
// spinlock.c
void            acquire(struct spinlock*);
int             holding(struct spinlock*);
void            initlock(struct spinlock*, char*);
void            release(struct spinlock*);
void            push_off(void);
void            pop_off(void);
// @end

// @from 05.02
// sleeplock.c
void            acquiresleep(struct sleeplock*);
void            releasesleep(struct sleeplock*);
int             holdingsleep(struct sleeplock*);
void            initsleeplock(struct sleeplock*, char*);
// @end

// @from 02.02
// string.c
int             memcmp(const void*, const void*, uint);
void*           memmove(void*, const void*, uint);
void*           memset(void*, int, uint);
void*           memcpy(void*, const void*, uint);
char*           safestrcpy(char*, const char*, int);
int             strlen(const char*);
int             strncmp(const char*, const char*, uint);
char*           strncpy(char*, const char*, int);
// @end

// @from 06.02
// syscall.c
void            argint(int, int*);
int             argstr(int, char*, int);
void            argaddr(int, uint64 *);
int             fetchstr(uint64, char*, int);
int             fetchaddr(uint64, uint64*);
void            syscall(void);
// @end

// trap.c @from 03.01
extern uint     ticks;  // @from 03.02
extern struct spinlock tickslock;  // @from 03.02
void            trapinit(void);  // @from 03.02
void            trapinithart(void);  // @from 03.01
void            prepare_return(void);  // @from 06.01

// uart.c @from 01.03
void            uartinit(void);  // @from 01.03
void            uartintr(void);  // @from 03.03
void            uartputc(int);  // @from 05.07
void            uartputc_sync(int);  // @from 01.03
int             uartgetc(void);  // @from 03.03

// vm.c - page tables @from 02.04
void            kvminit(void);  // @from 02.04
void            kvminithart(void);  // @from 02.04
void            kvmmap(pagetable_t, uint64, uint64, uint64, int);  // @from 02.04
int             mappages(pagetable_t, uint64, uint64, uint64, int);  // @from 02.04
pagetable_t     uvmcreate(void);  // @from 04.01
uint64          uvmalloc(pagetable_t, uint64, uint64, int);  // @from 06.03
uint64          uvmdealloc(pagetable_t, uint64, uint64);  // @from 06.03
int             uvmcopy(pagetable_t, pagetable_t, uint64);  // @from 06.04
void            uvmfree(pagetable_t, uint64);  // @from 04.01
void            uvmunmap(pagetable_t, uint64, uint64, int);  // @from 04.01
void            uvmclear(pagetable_t, uint64);  // @from 06.03
pte_t *         walk(pagetable_t, uint64, int);  // @from 02.04
uint64          walkaddr(pagetable_t, uint64);  // @from 02.04
int             copyout(pagetable_t, uint64, char *, uint64);  // @from 05.05
int             copyin(pagetable_t, char *, uint64, uint64);  // @from 05.05
int             copyinstr(pagetable_t, char *, uint64, uint64);  // @from 06.02
extern pagetable_t kernel_pagetable;  // @from 02.04

// @from 03.03
// plic.c
void            plicinit(void);
void            plicinithart(void);
int             plic_claim(void);
void            plic_complete(int);
// @end

// @from 05.01
// virtio_disk.c
void            virtio_disk_init(void);
void            virtio_disk_rw(struct buf *, int);
void            virtio_disk_intr(void);
// @end

// @from 09.03
// virtio_input.c - the keyboard and the mouse
void            virtio_input_init(void);
void            virtio_input_intr(int);
// @end

// @from 08.01
// virtio_net.c - the network card
void            virtio_net_init(void);
void            virtio_net_intr(void);
int             virtio_net_send(void*, int);
// @end

// @internal
// selftest.c - only does anything in a SELFTEST=1 build
void            selftest_early(void);
void            selftest_harts(void);
void            selftest_start(void);
int             selftest_trap(uint64 scause, uint64 stval, uint64 *sepc);
void            selftest_log_crashpoint(int point);
// @end

// @from 04.01
// number of elements in fixed-size array
#define NELEM(x) (sizeof(x)/sizeof((x)[0]))
// @end
