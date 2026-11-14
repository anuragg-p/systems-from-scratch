// udpecho: send and echo UDP datagrams (module 08).
//
//   udpecho PORT [N]          bind PORT and send every datagram that
//                             arrives straight back to its sender; stop
//                             after N of them (default: never)
//   udpecho IP PORT MESSAGE   send MESSAGE to IP:PORT and print the reply
//
// On QEMU's network the host is 10.0.2.2, so `udpecho 10.0.2.2 9000 hi`
// reaches a UDP socket listening on the host's 127.0.0.1:9000.

#include "kernel/types.h"
#include "user/user.h"

char buf[2048];

// "10.0.2.2" -> 0x0a000202, or 0 if s is not a dotted quad.
static uint
parseip(char *s)
{
  uint ip = 0;
  for(int i = 0; i < 4; i++){
    if(*s < '0' || *s > '9')
      return 0;
    int n = 0;
    while(*s >= '0' && *s <= '9')
      n = n * 10 + *s++ - '0';
    if(n > 255)
      return 0;
    ip = (ip << 8) | n;
    if(i < 3 && *s++ != '.')
      return 0;
  }
  return *s == 0 ? ip : 0;
}

// xv6 system calls have no timeouts, so a child process is the alarm
// clock: it sleeps, and unless stopalarm() kills it first, it says why
// and kills us. Returns the child's pid.
static int
alarm(int ticks, char *why)
{
  int parent = getpid();
  int pid = fork();
  if(pid == 0){
    sleep(ticks);
    fprintf(2, "%s\n", why);
    kill(parent);
    exit(1);
  }
  return pid;
}

static void
stopalarm(int pid)
{
  kill(pid);
  wait(0);
}

static void
serve(int port, int n)
{
  int fd = socket(port);
  if(fd < 0){
    fprintf(2, "udpecho: cannot bind port %d\n", port);
    exit(1);
  }
  printf("udpecho: listening on port %d\n", port);
  for(int i = 0; n == 0 || i < n; i++){
    uint ip;
    int sport;
    int len = recvfrom(fd, buf, sizeof(buf), &ip, &sport);
    if(len < 0){
      fprintf(2, "udpecho: recvfrom failed\n");
      exit(1);
    }
    printf("udpecho: %d bytes from %d.%d.%d.%d:%d\n", len,
           ip >> 24, (ip >> 16) & 0xff, (ip >> 8) & 0xff, ip & 0xff, sport);
    if(sendto(fd, buf, len, ip, sport) != len)
      fprintf(2, "udpecho: sendto failed\n");
  }
  close(fd);
}

static void
client(uint ip, int port, char *msg)
{
  int fd = socket(0);
  if(fd < 0){
    fprintf(2, "udpecho: no socket\n");
    exit(1);
  }
  int a = alarm(50, "udpecho: no reply");
  if(sendto(fd, msg, strlen(msg), ip, port) < 0){
    stopalarm(a);
    fprintf(2, "udpecho: sendto failed\n");
    exit(1);
  }
  // a socket is a file: read() takes the next datagram.
  int n = read(fd, buf, sizeof(buf) - 1);
  stopalarm(a);
  if(n < 0){
    fprintf(2, "udpecho: read failed\n");
    exit(1);
  }
  buf[n] = 0;
  printf("%s\n", buf);
  close(fd);
}

int
main(int argc, char *argv[])
{
  uint ip;

  if((argc == 2 || argc == 3) && argv[1][0] >= '0' && argv[1][0] <= '9' && !strchr(argv[1], '.')){
    serve(atoi(argv[1]), argc == 3 ? atoi(argv[2]) : 0);
  } else if(argc == 4 && (ip = parseip(argv[1])) != 0){
    client(ip, atoi(argv[2]), argv[3]);
  } else {
    fprintf(2, "usage: udpecho PORT [N] | udpecho IP PORT MESSAGE\n");
    exit(1);
  }
  exit(0);
}
