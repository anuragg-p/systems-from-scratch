// System call numbers. The user side (user/usys.pl) puts
// one of these in a7 before ecall; syscall() uses it to index syscalls[].
#define SYS_fork    1  // @from 06.04
#define SYS_exit    2  // @from 06.04
#define SYS_wait    3  // @from 06.04
#define SYS_pipe    4  // @from 06.07
#define SYS_read    5  // @from 06.02
#define SYS_kill    6  // @from 06.04
#define SYS_exec    7  // @from 06.03
#define SYS_fstat   8  // @from 06.02
#define SYS_chdir   9  // @from 06.07
#define SYS_dup    10  // @from 06.07
#define SYS_getpid 11  // @from 06.04
#define SYS_sbrk   12  // @from 06.05
#define SYS_sleep  13  // @from 06.04
#define SYS_uptime 14  // @from 06.04
#define SYS_open   15  // @from 06.07
#define SYS_write  16  // @from 06.02
#define SYS_mknod  17  // @from 06.07
#define SYS_unlink 18  // @from 06.07
#define SYS_link   19  // @from 06.07
#define SYS_mkdir  20  // @from 06.07
#define SYS_close  21  // @from 06.02
#define SYS_socket   22  // module 08 @from 08.04
#define SYS_sendto   23  // @from 08.04
#define SYS_recvfrom 24  // @from 08.04
#define SYS_fbmap    25  // module 09 @from 09.02
