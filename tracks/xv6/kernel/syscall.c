// System call dispatch and argument fetching.
//
// A user program puts the call number in a7 and its arguments in a0-a5,
// then runs ecall. The trap lands in usertrap(), which calls syscall().
// The arguments are still in the trapframe, where uservec saved them.

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/memlayout.h"
#include "kernel/riscv.h"
#include "kernel/spinlock.h"
#include "kernel/proc.h"
#include "kernel/syscall.h"
#include "kernel/defs.h"

// Fetch the uint64 at addr from the current process.
int
fetchaddr(uint64 addr, uint64 *ip)
{
  struct proc *p = myproc();
  if(addr >= p->sz || addr+sizeof(uint64) > p->sz) // both checks needed, in case of overflow
    return -1;
  if(copyin(p->pagetable, (char *)ip, addr, sizeof(*ip)) != 0)
    return -1;
  return 0;
}

// Fetch the nul-terminated string at addr from the current process.
// Returns length of string, not including nul, or -1 for error.
int
fetchstr(uint64 addr, char *buf, int max)
{
  struct proc *p = myproc();
  if(copyinstr(p->pagetable, buf, addr, max) < 0)
    return -1;
  return strlen(buf);
}

static uint64
argraw(int n)
{
  // @build 06.02 argraw
  // The n-th system call argument (0 to 5) is in register a0+n, saved in
  // this process's trapframe when it trapped. Return it; panic for any
  // other n.
  struct proc *p = myproc();
  switch (n) {
  case 0:
    return p->trapframe->a0;
  case 1:
    return p->trapframe->a1;
  case 2:
    return p->trapframe->a2;
  case 3:
    return p->trapframe->a3;
  case 4:
    return p->trapframe->a4;
  case 5:
    return p->trapframe->a5;
  }
  panic("argraw");
  // @end
}

// Fetch the nth 32-bit system call argument.
void
argint(int n, int *ip)
{
  *ip = argraw(n);
}

// Retrieve an argument as a pointer.
// Doesn't check for legality, since
// copyin/copyout will do that.
void
argaddr(int n, uint64 *ip)
{
  *ip = argraw(n);
}

// Fetch the nth word-sized system call argument as a null-terminated string.
// Copies into buf, at most max.
// Returns string length if OK (not including nul), -1 if error.
int
argstr(int n, char *buf, int max)
{
  uint64 addr;
  argaddr(n, &addr);
  return fetchstr(addr, buf, max);
}

// Prototypes for the functions that handle system calls.
extern uint64 sys_fork(void);  // @from 06.04
extern uint64 sys_exit(void);  // @from 06.04
extern uint64 sys_wait(void);  // @from 06.04
extern uint64 sys_pipe(void);  // @from 06.07
extern uint64 sys_read(void);  // @from 06.02
extern uint64 sys_kill(void);  // @from 06.04
extern uint64 sys_exec(void);  // @from 06.03
extern uint64 sys_fstat(void);  // @from 06.02
extern uint64 sys_chdir(void);  // @from 06.07
extern uint64 sys_dup(void);  // @from 06.07
extern uint64 sys_getpid(void);  // @from 06.04
extern uint64 sys_sbrk(void);  // @from 06.05
extern uint64 sys_sleep(void);  // @from 06.04
extern uint64 sys_uptime(void);  // @from 06.04
extern uint64 sys_open(void);  // @from 06.07
extern uint64 sys_write(void);  // @from 06.02
extern uint64 sys_mknod(void);  // @from 06.07
extern uint64 sys_unlink(void);  // @from 06.07
extern uint64 sys_link(void);  // @from 06.07
extern uint64 sys_mkdir(void);  // @from 06.07
extern uint64 sys_close(void);  // @from 06.02
extern uint64 sys_socket(void);  // @from 08.04
extern uint64 sys_sendto(void);  // @from 08.04
extern uint64 sys_recvfrom(void);  // @from 08.04
extern uint64 sys_fbmap(void);  // @from 09.02

// An array mapping syscall numbers from syscall.h
// to the function that handles the system call.
static uint64 (*syscalls[])(void) = {
[SYS_fork]    sys_fork,  // @from 06.04
[SYS_exit]    sys_exit,  // @from 06.04
[SYS_wait]    sys_wait,  // @from 06.04
[SYS_pipe]    sys_pipe,  // @from 06.07
[SYS_read]    sys_read,  // @from 06.02
[SYS_kill]    sys_kill,  // @from 06.04
[SYS_exec]    sys_exec,  // @from 06.03
[SYS_fstat]   sys_fstat,  // @from 06.02
[SYS_chdir]   sys_chdir,  // @from 06.07
[SYS_dup]     sys_dup,  // @from 06.07
[SYS_getpid]  sys_getpid,  // @from 06.04
[SYS_sbrk]    sys_sbrk,  // @from 06.05
[SYS_sleep]   sys_sleep,  // @from 06.04
[SYS_uptime]  sys_uptime,  // @from 06.04
[SYS_open]    sys_open,  // @from 06.07
[SYS_write]   sys_write,  // @from 06.02
[SYS_mknod]   sys_mknod,  // @from 06.07
[SYS_unlink]  sys_unlink,  // @from 06.07
[SYS_link]    sys_link,  // @from 06.07
[SYS_mkdir]   sys_mkdir,  // @from 06.07
[SYS_close]   sys_close,  // @from 06.02
[SYS_socket]  sys_socket,  // @from 08.04
[SYS_sendto]  sys_sendto,  // @from 08.04
[SYS_recvfrom] sys_recvfrom,  // @from 08.04
[SYS_fbmap]   sys_fbmap,  // @from 09.02
};

void
syscall(void)
{
  // @build 06.02 syscall
  // The call number is in a7 (in the trapframe). If it names an entry in
  // syscalls[], call it and put its return value in the trapframe's a0 -
  // that is what the user program sees returned from ecall. Otherwise
  // print "<pid> <name>: unknown sys call <num>" and return -1.
  int num;
  struct proc *p = myproc();

  num = p->trapframe->a7;
  if(num > 0 && num < NELEM(syscalls) && syscalls[num]) {
    // Use num to lookup the system call function for num, call it,
    // and store its return value in p->trapframe->a0
    p->trapframe->a0 = syscalls[num]();
  } else {
    printf("%d %s: unknown sys call %d\n",
            p->pid, p->name, num);
    p->trapframe->a0 = -1;
  }
  // @end
}
