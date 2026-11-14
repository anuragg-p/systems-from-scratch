// Formatted console output: printf and panic.
//
// The kernel cannot call the C library - there is none - so it carries
// its own small printf. It understands %d %ld %u %lu %x %lx %p %s %c %%.

#include <stdarg.h>

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/spinlock.h"
#include "kernel/riscv.h"
#include "kernel/defs.h"

volatile int panicking = 0; // printing a panic message
volatile int panicked = 0;  // spinning forever at end of a panic

// @from 02.03
// lock to avoid interleaving concurrent printf's.
static struct {
  struct spinlock lock;
} pr;
// @end

static char digits[] = "0123456789abcdef";

static void
printint(long long xx, int base, int sign)
{
  // @build 01.03 printint
  // Print xx in base 10 or 16 with consputc(). If sign is set and xx is
  // negative, print '-' and then the magnitude. Division hands you the
  // least significant digit first, so collect digits in buf and print them
  // in reverse. digits[] maps a value to its character.
  // @stub consputc('?');
  char buf[24];
  int i;
  unsigned long long x;

  if(sign && (sign = (xx < 0)))
    x = -xx;
  else
    x = xx;

  i = 0;
  do {
    buf[i++] = digits[x % base];
  } while((x /= base) != 0);

  if(sign)
    buf[i++] = '-';

  while(--i >= 0)
    consputc(buf[i]);
  // @end
}

static void
printptr(uint64 x)
{
  // @build 01.03 printptr
  // Print "0x" and then all 16 hex digits of x, most significant first,
  // leading zeros included.
  // @stub consputc('?');
  int i;
  consputc('0');
  consputc('x');
  for (i = 0; i < (sizeof(uint64) * 2); i++, x <<= 4)
    consputc(digits[x >> (sizeof(uint64) * 8 - 4)]);
  // @end
}

// Print to the console.
int
printf(char *fmt, ...)
{
  va_list ap;
  int i, cx, c0, c1;
  char *s;

  // @from 02.03
  if(panicking == 0)
    acquire(&pr.lock);
  // @end

  va_start(ap, fmt);
  for(i = 0; (cx = fmt[i] & 0xff) != 0; i++){
    if(cx != '%'){
      consputc(cx);
      continue;
    }
    i++;
    c0 = fmt[i+0] & 0xff;
    c1 = 0;
    if(c0) c1 = fmt[i+1] & 0xff;
    if(c0 == 'd'){
      printint(va_arg(ap, int), 10, 1);
    } else if(c0 == 'l' && c1 == 'd'){
      printint(va_arg(ap, uint64), 10, 1);
      i += 1;
    } else if(c0 == 'u'){
      printint(va_arg(ap, uint32), 10, 0);
    } else if(c0 == 'l' && c1 == 'u'){
      printint(va_arg(ap, uint64), 10, 0);
      i += 1;
    } else if(c0 == 'x'){
      printint(va_arg(ap, uint32), 16, 0);
    } else if(c0 == 'l' && c1 == 'x'){
      printint(va_arg(ap, uint64), 16, 0);
      i += 1;
    } else if(c0 == 'p'){
      printptr(va_arg(ap, uint64));
    } else if(c0 == 'c'){
      consputc(va_arg(ap, uint));
    } else if(c0 == 's'){
      if((s = va_arg(ap, char*)) == 0)
        s = "(null)";
      for(; *s; s++)
        consputc(*s);
    } else if(c0 == '%'){
      consputc('%');
    } else if(c0 == 0){
      break;
    } else {
      // Print unknown % sequence to draw attention.
      consputc('%');
      consputc(c0);
    }
  }
  va_end(ap);

  // @from 02.03
  if(panicking == 0)
    release(&pr.lock);
  // @end

  return 0;
}

// Something is wrong that the kernel cannot recover from. Say what, and
// stop this CPU. Setting panicked freezes output from the other CPUs, so
// the message is the last thing on the screen.
void
panic(char *s)
{
  panicking = 1;
  printf("panic: ");
  printf("%s\n", s);
  panicked = 1;
  for(;;)
    ;
}

// @from 02.03
void
printfinit(void)
{
  initlock(&pr.lock, "pr");
}
// @end
