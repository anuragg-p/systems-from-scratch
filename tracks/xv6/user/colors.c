// colors: draw a test card from user space.
//
// fbmap() puts the screen into this process's memory, so drawing is
// storing to an array: no system call per pixel, no copying. The top
// three quarters get eight colour bars. The bottom quarter, a ramp from
// black to white, is drawn by a child process: fork does not pass the
// mapping on, so the child maps the screen itself. Both mappings lead to
// the same pages, and the parent sees what the child drew.

#include "kernel/types.h"
#include "kernel/fb.h"
#include "user/user.h"

#define BARS_H 360

uint bars[8] = {
  0xffffff, 0xffff00, 0x00ffff, 0x00ff00,   // white, yellow, cyan, green
  0xff00ff, 0xff0000, 0x0000ff, 0x000000,   // magenta, red, blue, black
};

int
main(void)
{
  uint *fb = fbmap();
  if(fb == (uint *)-1){
    fprintf(2, "colors: no screen\n");
    exit(1);
  }
  printf("colors: the screen is at %p\n", fb);

  // pixel (x, y) is fb[y * FB_WIDTH + x]: FB_STRIDE bytes per row.
  for(int y = 0; y < BARS_H; y++)
    for(int x = 0; x < FB_WIDTH; x++)
      fb[y * FB_WIDTH + x] = bars[x / (FB_WIDTH / 8)];

  int pid = fork();
  if(pid < 0){
    fprintf(2, "colors: fork failed\n");
    exit(1);
  }
  if(pid == 0){
    uint *mine = fbmap();
    if(mine == (uint *)-1)
      exit(1);
    for(int y = BARS_H; y < FB_HEIGHT; y++)
      for(int x = 0; x < FB_WIDTH; x++){
        uint g = x * 255 / (FB_WIDTH - 1);
        mine[y * FB_WIDTH + x] = g << 16 | g << 8 | g;
      }
    exit(0);
  }
  wait(0);

  // the child's last pixel, read through our own mapping.
  if(fb[FB_HEIGHT * FB_WIDTH - 1] == 0xffffff)
    printf("colors: child %d drew the ramp; this process sees it too\n", pid);
  else
    printf("colors: the ramp is missing\n");
  exit(0);
}
