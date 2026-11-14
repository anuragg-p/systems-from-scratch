// events: print what the keyboard and the mouse report.
//
// Reads the input device and prints every event as it arrives: its type,
// code and value, and what they mean. Each read() returns as many whole
// events as are waiting. Press Esc in the window to stop.

#include "kernel/types.h"
#include "kernel/fb.h"
#include "kernel/input.h"
#include "user/user.h"
#include "user/gui.h"

struct inputevent ev[16];

int
main(void)
{
  int fd = input_open();
  if(fd < 0){
    fprintf(2, "events: cannot open /input\n");
    exit(1);
  }
  printf("events: reading /input; Esc in the window stops\n");
  for(;;){
    int n = read(fd, ev, sizeof(ev));
    if(n <= 0){
      fprintf(2, "events: read failed\n");
      exit(1);
    }
    for(int i = 0; i < n / sizeof(ev[0]); i++){
      struct inputevent *e = &ev[i];
      if(e->type == EV_SYN){
        printf("EV_SYN %d %d\n", e->code, e->value);
      } else if(e->type == EV_KEY){
        char *what = e->value == 1 ? "down" : e->value == 0 ? "up" : "repeat";
        printf("EV_KEY %d %d  %s %s\n", e->code, e->value, keyname(e->code), what);
        if(e->code == KEY_ESC && e->value == 1)
          exit(0);
      } else if(e->type == EV_ABS){
        printf("EV_ABS %d %d  %s = %d\n", e->code, e->value, e->code == ABS_X ? "x" : "y", e->value);
      } else {
        printf("type %d %d %d\n", e->type, e->code, e->value);
      }
    }
  }
}
