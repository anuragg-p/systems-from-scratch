// The console.
//
// Output: printf() -> consputc() -> the UART.
// @from 03.03
// @from 05.07
// Input: the UART interrupts -> consoleintr() collects a line, handling
// backspace and friends -> consoleread() hands whole lines to processes.
// @else
// // Input: the UART interrupts -> consoleintr() collects a line, handling
// // backspace and friends.
// @end
// @end

#include <stdarg.h>

#include "kernel/types.h"
#include "kernel/param.h"
#include "kernel/spinlock.h"
#include "kernel/sleeplock.h"  // @from 05.07
#include "kernel/fs.h"         // @from 05.07
#include "kernel/file.h"       // @from 05.07
#include "kernel/memlayout.h"
#include "kernel/riscv.h"
#include "kernel/defs.h"
#include "kernel/proc.h"

#define BACKSPACE 0x100
#define C(x)  ((x)-'@')  // Control-x @from 03.03

// send one character to the uart, waiting until it is taken
// (uartputc_sync). the kernel's own output goes this way.
void
consputc(int c)
{
  if(c == BACKSPACE){
    // erase the character before the cursor: back up, overwrite it
    // with a space, back up again.
    uartputc_sync('\b'); uartputc_sync(' '); uartputc_sync('\b');
  } else {
    uartputc_sync(c);
  }
}

// @from 03.03
struct {
  struct spinlock lock;

  // input
#define INPUT_BUF_SIZE 128
  char buf[INPUT_BUF_SIZE];
  uint r;  // Read index
  uint w;  // Write index
  uint e;  // Edit index
} cons;
// @end

// @from 05.07
//
// writes to the console device go here, through devsw[CONSOLE].
//
int
consolewrite(int user_src, uint64 src, int n)
{
  int i;

  for(i = 0; i < n; i++){
    char c;
    if(either_copyin(&c, user_src, src+i, 1) == -1)
      break;
    uartputc(c);
  }

  return i;
}

//
// reads from the console device go here, through devsw[CONSOLE].
// copy (up to) a whole input line to dst.
// user_dst indicates whether dst is a user
// or kernel address.
//
int
consoleread(int user_dst, uint64 dst, int n)
{
  uint target;
  int c;
  char cbuf;

  target = n;
  acquire(&cons.lock);
  while(n > 0){
    // wait until interrupt handler has put some
    // input into cons.buffer.
    while(cons.r == cons.w){
      if(killed(myproc())){
        release(&cons.lock);
        return -1;
      }
      sleep(&cons.r, &cons.lock);
    }

    c = cons.buf[cons.r++ % INPUT_BUF_SIZE];

    if(c == C('D')){  // end-of-file
      if(n < target){
        // Save ^D for next time, to make sure
        // caller gets a 0-byte result.
        cons.r--;
      }
      break;
    }

    // copy the input byte to the user-space buffer.
    cbuf = c;
    if(either_copyout(user_dst, dst, &cbuf, 1) == -1)
      break;

    dst++;
    --n;

    if(c == '\n'){
      // a whole line has arrived: return it.
      break;
    }
  }
  release(&cons.lock);

  return target - n;
}
// @end

//
// the console input interrupt handler.
// uartintr() calls this for each input character.
// do erase/kill processing, append to cons.buf,
// and make the line readable once it is whole.
//
void
consoleintr(int c)
{
  // @build 03.03 consoleintr
  // One typed character, from the UART interrupt. Under cons.lock:
  //   Control-P: procdump()
  //   Control-U: erase back to the start of the line, echoing BACKSPACE
  //   Control-H or DEL: erase one character, if the line has one
  //   anything else (if cons.buf has room): turn '\r' into '\n', echo it
  //   with consputc(), and append it at cons.e. When it ends a line ('\n'
  //   or Control-D) or fills the buffer, publish the line - cons.w =
  //   cons.e - and wakeup(&cons.r) for consoleread().
  acquire(&cons.lock);

  switch(c){
  case C('P'):
    procdump();  // Print process list. @from 04.01
    break;
  case C('U'):  // Kill line.
    while(cons.e != cons.w &&
          cons.buf[(cons.e-1) % INPUT_BUF_SIZE] != '\n'){
      cons.e--;
      consputc(BACKSPACE);
    }
    break;
  case C('H'): // Backspace
  case '\x7f': // Delete key
    if(cons.e != cons.w){
      cons.e--;
      consputc(BACKSPACE);
    }
    break;
  default:
    if(c != 0 && cons.e-cons.r < INPUT_BUF_SIZE){
      c = (c == '\r') ? '\n' : c;

      // echo back to the user.
      consputc(c);

      // append it to the line being edited.
      cons.buf[cons.e++ % INPUT_BUF_SIZE] = c;

      if(c == '\n' || c == C('D') || cons.e-cons.r == INPUT_BUF_SIZE){
        // a whole line (or end-of-file) has arrived:
        // make it readable, up to cons.w.
        cons.w = cons.e;
        wakeup(&cons.r);  // @from 04.03
      }
    }
    break;
  }

  release(&cons.lock);
  // @end
}

void
consoleinit(void)
{
  initlock(&cons.lock, "cons");  // @from 03.03

  uartinit();

  // @from 05.07
  // connect reads and writes of the console device
  // to consoleread and consolewrite.
  devsw[CONSOLE].read = consoleread;
  devsw[CONSOLE].write = consolewrite;
  // @end
}
