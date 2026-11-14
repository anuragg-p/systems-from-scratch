// nslookup: ask DNS for the IPv4 addresses of a name.
//
//   nslookup NAME
//
// Sends one query to QEMU's resolver at 10.0.2.3, port 53, which asks
// the host's own DNS server, and prints each address in the answer.
//
// A DNS message (RFC 1035, section 4) is a 12-byte header and then
// records. The header holds an id, which the answer repeats, flags, and
// four counts: questions, answers, authority and additional records. A
// question is a name, a type and a class. An answer record is a name, a
// type, a class, a time to live, and data: for a type A record, the four
// bytes of an IPv4 address. Every number is big-endian.

#include "kernel/types.h"
#include "user/user.h"

#define DNS_SERVER 0x0a000203   // 10.0.2.3
#define DNS_PORT   53
#define MAXMSG     512          // the largest DNS message over UDP
#define MAXADDR    16

#define DNS_RD     0x0100       // flags: recursion desired
#define DNS_QR     0x8000       // flags: this is a response
#define DNS_NXDOMAIN 3          // response code: no such name
#define TYPE_A     1
#define CLASS_IN   1

uchar msg[MAXMSG];

static int
get16(uchar *p)
{
  return (p[0] << 8) | p[1];
}

static void
put16(uchar *p, int v)
{
  p[0] = v >> 8;
  p[1] = v;
}

// Return the offset just past the name that starts at off in a message
// of len bytes, or -1. A name is a run of labels (a length byte, then
// that many characters) ending either in a 0 byte or in a two-byte
// pointer whose top two bits are set: the rest of the name is elsewhere
// in the message. Answers use these pointers to avoid repeating the name
// in the question (RFC 1035, 4.1.4, "message compression").
static int
skipname(uchar *buf, int len, int off)
{
  while(off < len){
    int n = buf[off];
    if(n == 0)
      return off + 1;
    if((n & 0xc0) == 0xc0)
      return off + 2 <= len ? off + 2 : -1;
    off += 1 + n;
  }
  return -1;
}

// Build a query for the type A records of name in msg, with the given
// id. Returns its length, or -1 if name is not a valid DNS name.
int
dns_query(char *name, int id, uchar *msg)
{
  // @build 08.05 dns_query
  // The header: id, flags with only DNS_RD set (please resolve it all the
  // way), one question, zero of the other three; six big-endian 16-bit
  // numbers (put16). Then the question. The name goes as labels, one per
  // dot-separated part, each a length byte and then its characters, and a
  // 0 byte at the end: "www.mit.edu" is 3www3mit3edu0. A label is 1 to 63
  // characters; return -1 for anything else, an empty name, or a query
  // longer than MAXMSG. A trailing dot ("mit.edu.") is allowed. After the
  // name, TYPE_A and CLASS_IN, 16 bits each.
  // @stub fprintf(2, "08.05: dns_query not written yet\n"); exit(1);
  put16(msg, id);
  put16(msg + 2, DNS_RD);
  put16(msg + 4, 1);
  put16(msg + 6, 0);
  put16(msg + 8, 0);
  put16(msg + 10, 0);

  int off = 12;
  char *s = name;
  while(*s){
    char *dot = strchr(s, '.');
    int n = dot ? dot - s : strlen(s);
    if(n < 1 || n > 63 || off + 1 + n + 5 > MAXMSG)
      return -1;
    msg[off++] = n;
    memmove(msg + off, s, n);
    off += n;
    s += n;
    if(*s == '.')
      s++;
  }
  if(off == 12)
    return -1;
  msg[off++] = 0;
  put16(msg + off, TYPE_A);
  put16(msg + off + 2, CLASS_IN);
  return off + 4;
  // @end
}

// Read the answer to query id in msg (len bytes) and store the IPv4
// addresses of its type A records in addrs, at most max of them.
// Returns how many; 0 if the name has none or does not exist; -1 if msg
// is not a good answer to this query.
int
dns_answer(uchar *msg, int len, int id, uint *addrs, int max)
{
  // @build 08.05 dns_answer
  // Check the header first: at least 12 bytes, the same id, DNS_QR set,
  // and a response code (the low 4 bits of the flags) of 0, or of
  // DNS_NXDOMAIN, which means "no such name": return 0. Skip each question:
  // its name (skipname), then 4 bytes of type and class. Each answer
  // record is a name, then TYPE, CLASS (16 bits each), TTL (32), RDLENGTH
  // (16) and RDLENGTH bytes of data. Keep the data of TYPE_A, CLASS_IN
  // records with 4 bytes of it, as a host-order number (big-endian on the
  // wire); skip every other record (a CNAME, say). Never read past len:
  // return -1 for a message that ends early.
  // @stub fprintf(2, "08.05: dns_answer not written yet\n"); exit(1);
  if(len < 12 || get16(msg) != id)
    return -1;
  int flags = get16(msg + 2);
  if(!(flags & DNS_QR))
    return -1;
  if((flags & 0xf) == DNS_NXDOMAIN)
    return 0;
  if((flags & 0xf) != 0)
    return -1;
  int qdcount = get16(msg + 4);
  int ancount = get16(msg + 6);

  int off = 12;
  for(int i = 0; i < qdcount; i++){
    off = skipname(msg, len, off);
    if(off < 0 || off + 4 > len)
      return -1;
    off += 4;
  }

  int n = 0;
  for(int i = 0; i < ancount; i++){
    off = skipname(msg, len, off);
    if(off < 0 || off + 10 > len)
      return -1;
    int type = get16(msg + off);
    int class = get16(msg + off + 2);
    int rdlen = get16(msg + off + 8);
    off += 10;
    if(off + rdlen > len)
      return -1;
    if(type == TYPE_A && class == CLASS_IN && rdlen == 4 && n < max)
      addrs[n++] = (msg[off] << 24) | (msg[off+1] << 16) | (msg[off+2] << 8) | msg[off+3];
    off += rdlen;
  }
  return n;
  // @end
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

int
main(int argc, char *argv[])
{
  uint addrs[MAXADDR];

  if(argc != 2){
    fprintf(2, "usage: nslookup NAME\n");
    exit(1);
  }
  char *name = argv[1];
  int id = (getpid() * 7919 + uptime()) & 0xffff;   // any number will do

  int len = dns_query(name, id, msg);
  if(len < 0){
    fprintf(2, "nslookup: %s is not a valid name\n", name);
    exit(1);
  }
  int fd = socket(0);
  if(fd < 0){
    fprintf(2, "nslookup: no network\n");
    exit(1);
  }
  int a = alarm(50, "nslookup: no answer from 10.0.2.3");
  if(sendto(fd, msg, len, DNS_SERVER, DNS_PORT) != len){
    stopalarm(a);
    fprintf(2, "nslookup: cannot send to 10.0.2.3\n");
    exit(1);
  }

  // wait for the server's answer; anything from anyone else is not it.
  uint src;
  int sport;
  do {
    len = recvfrom(fd, msg, sizeof(msg), &src, &sport);
  } while(len >= 0 && (src != DNS_SERVER || sport != DNS_PORT));
  stopalarm(a);
  close(fd);

  int n = len < 0 ? -1 : dns_answer(msg, len, id, addrs, MAXADDR);
  if(n < 0){
    fprintf(2, "nslookup: bad answer from 10.0.2.3\n");
    exit(1);
  }
  if(n == 0)
    printf("%s has no address\n", name);
  for(int i = 0; i < n; i++)
    printf("%s has address %d.%d.%d.%d\n", name, addrs[i] >> 24,
           (addrs[i] >> 16) & 0xff, (addrs[i] >> 8) & 0xff, addrs[i] & 0xff);
  exit(0);
}
