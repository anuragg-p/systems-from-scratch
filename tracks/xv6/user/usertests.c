// usertests: exercise the whole system from user space.
//
//   usertests          run everything
//   usertests NAME     run one test
//
// Each test runs in its own child process, so a test that crashes or
// gets killed fails alone. Prints "NAME: OK" or "NAME: FAILED", and at
// the end "ALL TESTS PASSED" or "SOME TESTS FAILED".

#include "kernel/param.h"
#include "kernel/types.h"
#include "kernel/stat.h"
#include "kernel/fcntl.h"
#include "kernel/fs.h"
#include "user/user.h"

#define BUFSZ  (MAXOPBLOCKS+2)*BSIZE
char buf[BUFSZ];

static void
fail(char *name, char *why)
{
  printf("%s: %s\n", name, why);
  exit(1);
}

// fork as many children as the process table allows, then reap them.
void
forkfull(char *s)
{
  int n, pid;
  for(n = 0; n < NPROC + 5; n++){
    pid = fork();
    if(pid < 0)
      break;
    if(pid == 0){
      sleep(5);
      exit(0);
    }
  }
  if(n == NPROC + 5)
    fail(s, "fork never ran out of processes");
  for(; n > 0; n--)
    if(wait(0) < 0)
      fail(s, "wait stopped early");
  if(wait(0) != -1)
    fail(s, "wait got too many");
}

// exit statuses reach the parent through wait.
void
exitwait(char *s)
{
  for(int i = 0; i < 50; i++){
    int pid = fork();
    if(pid < 0)
      fail(s, "fork failed");
    if(pid == 0)
      exit(i);
    int xstate;
    if(wait(&xstate) != pid)
      fail(s, "wait returned the wrong pid");
    if(xstate != i)
      fail(s, "wrong exit status");
  }
}

// a child gets a copy of memory, not a shared one.
void
forkcopy(char *s)
{
  static int x = 1;
  int pid = fork();
  if(pid == 0){
    x = 2;
    exit(x == 2 ? 0 : 1);
  }
  int xstate;
  wait(&xstate);
  if(xstate != 0 || x != 1)
    fail(s, "parent saw the child's write");
}

// grow and shrink memory with sbrk.
void
sbrkbasic(char *s)
{
  char *a = sbrk(0);
  char *b = sbrk(10 * 4096);
  if(b != a)
    fail(s, "sbrk returned the wrong old break");
  for(int i = 0; i < 10 * 4096; i += 4096)
    b[i] = i / 4096;
  for(int i = 0; i < 10 * 4096; i += 4096)
    if(b[i] != i / 4096)
      fail(s, "new memory did not hold a value");
  if(sbrk(-10 * 4096) != b + 10 * 4096)
    fail(s, "shrinking returned the wrong break");
  if(sbrk(0) != a)
    fail(s, "break did not go back");
  if(sbrk(0x7fffffff) != (char*)-1)
    fail(s, "an impossible sbrk succeeded");
}

// touching memory past the break kills the process.
void
sbrkfault(char *s)
{
  int pid = fork();
  if(pid == 0){
    char *p = sbrk(0);
    *(p + 8192) = 1;   // nothing is mapped there
    exit(0);
  }
  int xstate;
  wait(&xstate);
  if(xstate != -1)
    fail(s, "a fault did not kill the child");
}

// malloc and free many blocks.
void
mallocmany(char *s)
{
  char *p[200];
  for(int i = 0; i < 200; i++){
    p[i] = malloc(1 + (i * 37) % 3000);
    if(p[i] == 0)
      fail(s, "malloc failed");
    memset(p[i], i, 1 + (i * 37) % 3000);
  }
  for(int i = 0; i < 200; i++){
    if(p[i][0] != (char)i)
      fail(s, "a block was overwritten");
    free(p[i]);
  }
}

// a pipe carries bytes in order from a writer to a reader.
void
pipe1(char *s)
{
  int fds[2], seq = 0, total = 0, n;
  if(pipe(fds) != 0)
    fail(s, "pipe failed");
  int pid = fork();
  if(pid == 0){
    close(fds[0]);
    for(int n = 0; n < 5; n++){
      for(int i = 0; i < 1033; i++)
        buf[i] = seq++;
      if(write(fds[1], buf, 1033) != 1033)
        fail(s, "pipe write failed");
    }
    exit(0);
  }
  close(fds[1]);
  while((n = read(fds[0], buf, 500)) > 0){
    for(int i = 0; i < n; i++)
      if((buf[i] & 0xff) != (seq++ & 0xff))
        fail(s, "pipe bytes out of order");
    total += n;
  }
  close(fds[0]);
  wait(0);
  if(total != 5 * 1033)
    fail(s, "pipe lost bytes");
}

// kill makes a running process exit with status -1.
void
killstatus(char *s)
{
  int pid = fork();
  if(pid == 0){
    for(;;)
      getpid();
  }
  sleep(2);
  kill(pid);
  int xstate;
  wait(&xstate);
  if(xstate != -1)
    fail(s, "a killed child did not exit with -1");
}

// create, write, read back, unlink.
void
files(char *s)
{
  int fd = open("ut.f", O_CREATE|O_RDWR);
  if(fd < 0)
    fail(s, "create failed");
  for(int i = 0; i < 20; i++){
    memset(buf, 'a' + i, 300);
    if(write(fd, buf, 300) != 300)
      fail(s, "write failed");
  }
  close(fd);
  fd = open("ut.f", O_RDONLY);
  for(int i = 0; i < 20; i++){
    if(read(fd, buf, 300) != 300 || buf[0] != 'a' + i || buf[299] != 'a' + i)
      fail(s, "read back the wrong bytes");
  }
  if(read(fd, buf, 1) != 0)
    fail(s, "no end of file");
  close(fd);
  struct stat st;
  if(stat("ut.f", &st) < 0 || st.size != 6000 || st.type != T_FILE)
    fail(s, "stat is wrong");
  if(unlink("ut.f") < 0 || open("ut.f", O_RDONLY) >= 0)
    fail(s, "unlink did not remove it");
}

// a file large enough to need the indirect block.
void
bigfile(char *s)
{
  int n = NDIRECT + 40;
  int fd = open("ut.big", O_CREATE|O_RDWR);
  for(int i = 0; i < n; i++){
    memset(buf, i, BSIZE);
    if(write(fd, buf, BSIZE) != BSIZE)
      fail(s, "write failed");
  }
  close(fd);
  fd = open("ut.big", O_RDONLY);
  for(int i = 0; i < n; i++){
    if(read(fd, buf, BSIZE) != BSIZE || buf[0] != (char)i || buf[BSIZE-1] != (char)i)
      fail(s, "read back the wrong block");
  }
  close(fd);
  unlink("ut.big");
}

// directories: mkdir, chdir, files inside, removing.
void
dirs(char *s)
{
  if(mkdir("ut.d") < 0)
    fail(s, "mkdir failed");
  if(chdir("ut.d") < 0)
    fail(s, "chdir failed");
  int fd = open("inside", O_CREATE|O_RDWR);
  if(fd < 0)
    fail(s, "create in dir failed");
  close(fd);
  if(chdir("..") < 0)
    fail(s, "chdir .. failed");
  if(open("ut.d/inside", O_RDONLY) < 0)
    fail(s, "path through dir failed");
  if(unlink("ut.d") == 0)
    fail(s, "removed a directory that is not empty");
  unlink("ut.d/inside");
  if(unlink("ut.d") < 0)
    fail(s, "could not remove an empty directory");
  if(open("ut.d/../README", O_RDONLY) >= 0)
    fail(s, "path through a removed dir worked");
}

// two names, one file.
void
links(char *s)
{
  int fd = open("ut.l1", O_CREATE|O_RDWR);
  write(fd, "hello", 5);
  close(fd);
  if(link("ut.l1", "ut.l2") < 0)
    fail(s, "link failed");
  unlink("ut.l1");
  fd = open("ut.l2", O_RDONLY);
  if(fd < 0 || read(fd, buf, 5) != 5 || memcmp(buf, "hello", 5) != 0)
    fail(s, "the second name lost the data");
  close(fd);
  unlink("ut.l2");
}

// exec runs a program with arguments; a bad path fails.
void
exectest(char *s)
{
  int fds[2];
  pipe(fds);
  int pid = fork();
  if(pid == 0){
    close(1);
    dup(fds[1]);
    char *argv[] = { "echo", "OK", "exec", 0 };
    exec("echo", argv);
    exit(1);
  }
  close(fds[1]);
  int n = read(fds[0], buf, 100);
  wait(0);
  if(n != 8 || memcmp(buf, "OK exec\n", 8) != 0)
    fail(s, "exec'd echo printed the wrong thing");
  char *argv[] = { "nope", 0 };
  if(exec("does-not-exist", argv) != -1)
    fail(s, "exec of a missing file did not fail");
}

// the kernel must refuse bad user pointers, not crash on them.
void
badptr(char *s)
{
  int fd = open("README", O_RDONLY);
  if(read(fd, (void*)0xffffffffff, 10) != -1)
    fail(s, "read into a kernel address worked");
  if(read(fd, (char*)sbrk(0) + 4096 * 10, 10) != -1)
    fail(s, "read into unmapped memory worked");
  close(fd);
  if(open((char*)0x7fffffff, O_RDONLY) != -1)
    fail(s, "open with a bad path pointer worked");
  fd = open("ut.bad", O_CREATE|O_RDWR);
  if(write(fd, (char*)0x7fffffff, 10) != -1)
    fail(s, "write to a file from a bad pointer worked");
  close(fd);
  unlink("ut.bad");
}

// four processes write four files at once.
void
fourfiles(char *s)
{
  char *names[] = { "ut.f0", "ut.f1", "ut.f2", "ut.f3" };
  for(int pi = 0; pi < 4; pi++){
    int pid = fork();
    if(pid == 0){
      int fd = open(names[pi], O_CREATE|O_RDWR);
      memset(buf, '0' + pi, 512);
      for(int i = 0; i < 12; i++)
        if(write(fd, buf, 500) != 500)
          exit(1);
      exit(0);
    }
  }
  for(int pi = 0; pi < 4; pi++){
    int xstate;
    wait(&xstate);
    if(xstate != 0)
      fail(s, "a writer failed");
  }
  for(int pi = 0; pi < 4; pi++){
    int fd = open(names[pi], O_RDONLY), n, total = 0;
    while((n = read(fd, buf, sizeof(buf))) > 0){
      for(int j = 0; j < n; j++)
        if(buf[j] != '0' + pi)
          fail(s, "files got mixed up");
      total += n;
    }
    close(fd);
    if(total != 12 * 500)
      fail(s, "a file has the wrong size");
    unlink(names[pi]);
  }
}

struct test {
  void (*f)(char *);
  char *s;
} tests[] = {
  {forkfull, "forkfull"},
  {exitwait, "exitwait"},
  {forkcopy, "forkcopy"},
  {sbrkbasic, "sbrkbasic"},
  {sbrkfault, "sbrkfault"},
  {mallocmany, "mallocmany"},
  {pipe1, "pipe1"},
  {killstatus, "killstatus"},
  {files, "files"},
  {bigfile, "bigfile"},
  {dirs, "dirs"},
  {links, "links"},
  {exectest, "exectest"},
  {badptr, "badptr"},
  {fourfiles, "fourfiles"},
  {0, 0},
};

int
run(struct test *t)
{
  int xstate;
  int pid = fork();
  if(pid < 0){
    printf("runtest: fork error\n");
    exit(1);
  }
  if(pid == 0){
    t->f(t->s);
    exit(0);
  }
  wait(&xstate);
  printf("%s: %s\n", t->s, xstate == 0 ? "OK" : "FAILED");
  return xstate == 0;
}

int
main(int argc, char *argv[])
{
  int ok = 1, ran = 0;
  for(struct test *t = tests; t->s; t++){
    if(argc > 1 && strcmp(argv[1], t->s) != 0)
      continue;
    ran++;
    if(!run(t))
      ok = 0;
  }
  if(ran == 0){
    printf("usertests: no test named %s\n", argv[1]);
    exit(1);
  }
  printf(ok ? "ALL TESTS PASSED\n" : "SOME TESTS FAILED\n");
  exit(ok ? 0 : 1);
}
