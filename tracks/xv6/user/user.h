// The user-space view of the system: what a user program can call.

struct stat;

// system calls
int fork(void);  // @from 06.04
int exit(int) __attribute__((noreturn));  // @from 06.04
int wait(int*);  // @from 06.04
int pipe(int*);  // @from 06.07
int write(int, const void*, int);  // @from 06.02
int read(int, void*, int);  // @from 06.02
int close(int);  // @from 06.02
int kill(int);  // @from 06.04
int exec(const char*, char**);  // @from 06.03
int open(const char*, int);  // @from 06.07
int mknod(const char*, short, short);  // @from 06.07
int unlink(const char*);  // @from 06.07
int fstat(int fd, struct stat*);  // @from 06.02
int link(const char*, const char*);  // @from 06.07
int mkdir(const char*);  // @from 06.07
int chdir(const char*);  // @from 06.07
int dup(int);  // @from 06.07
int getpid(void);  // @from 06.04
char* sbrk(int);  // @from 06.05
int sleep(int);  // @from 06.04
int uptime(void);  // @from 06.04
// UDP sockets (module 08). An IP address is a number: 10.0.2.2 is 0x0a000202. @from 08.04
int socket(int port);  // @from 08.04
int sendto(int fd, const void *buf, int n, uint ip, int port);  // @from 08.04
int recvfrom(int fd, void *buf, int n, uint *ip, int *port);  // @from 08.04
// The screen (module 09): map it into this process; (uint*)-1 if there is none. @from 09.02
uint *fbmap(void);  // @from 09.02

// @from 07.01
// ulib.c
int stat(const char*, struct stat*);
char* strcpy(char*, const char*);
void *memmove(void*, const void*, int);
char* strchr(const char*, char c);
int strcmp(const char*, const char*);
char* gets(char*, int max);
uint strlen(const char*);
void* memset(void*, int, uint);
int atoi(const char*);
int memcmp(const void *, const void *, uint);
void *memcpy(void *, const void *, uint);

// printf.c
void fprintf(int, const char*, ...) __attribute__ ((format (printf, 2, 3)));
void printf(const char*, ...) __attribute__ ((format (printf, 1, 2)));

// umalloc.c
void* malloc(uint);
void free(void*);
// @end
