// @from 09.04
// The drawing library: rectangles, lines and text in a surface, double
// buffering onto the screen, and the input device. See user/gui.h.
// @else
// // The GUI library: the input device, and what each key types and is
// // called. See user/gui.h.
// @end

#include "kernel/types.h"
#include "kernel/fcntl.h"
#include "kernel/fb.h"
#include "kernel/input.h"
#include "user/user.h"
#include "user/gui.h"

// @from 09.04
static uint *screen;   // the screen, mapped by fbmap(): FB_WIDTH x FB_HEIGHT pixels

int
screen_open(struct surface *back)
{
  screen = fbmap();
  if(screen == (uint *)-1)
    return -1;
  back->w = FB_WIDTH;
  back->h = FB_HEIGHT;
  back->px = malloc(FB_SIZE);
  if(back->px == 0)
    return -1;
  memset(back->px, 0, FB_SIZE);
  return 0;
}

// Copy the back buffer to the screen, 8 bytes at a time.
void
present(struct surface *back)
{
  uint64 *from = (uint64 *)back->px;
  uint64 *to = (uint64 *)screen;
  for(int i = 0; i < FB_SIZE / 8; i++)
    to[i] = from[i];
}

// One pixel, if it is inside s.
static void
putpixel(struct surface *s, int x, int y, uint color)
{
  if(x >= 0 && x < s->w && y >= 0 && y < s->h)
    s->px[y * s->w + x] = color;
}
// @end

// Fill the rectangle w wide and h high whose top left corner is (x, y).
void
fillrect(struct surface *s, int x, int y, int w, int h, uint color)
{
  // @build 09.04 fillrect
  // Clip the rectangle to s: it may hang off any side, or miss s
  // entirely. Then fill what is left, row by row. Pixel (x, y) is
  // s->px[y * s->w + x]. Do not call putpixel for each pixel: a full
  // screen is 307200 of them, and the check is the same for a whole row.
  // @stub fprintf(2, "09.04: fillrect not written yet\n"); exit(1);
  if(x < 0){
    w += x;
    x = 0;
  }
  if(y < 0){
    h += y;
    y = 0;
  }
  if(x + w > s->w)
    w = s->w - x;
  if(y + h > s->h)
    h = s->h - y;
  for(int j = 0; j < h; j++){
    uint *row = s->px + (y + j) * s->w + x;
    for(int i = 0; i < w; i++)
      row[i] = color;
  }
  // @end
}

// A line one pixel wide from (x0, y0) to (x1, y1), both ends included.
void
line(struct surface *s, int x0, int y0, int x1, int y1, uint color)
{
  // @build 09.04 line
  // Bresenham's algorithm, which needs only integer additions: step
  // along the line one pixel at a time, from (x0, y0) to (x1, y1), and
  // keep an error term that says how far the pixels have drifted from
  // the true line, so you know when to step sideways as well. Every
  // direction must work: steep or shallow, left or right, up or down,
  // and a line from a point to itself is one pixel. Plot with putpixel,
  // which leaves out what falls outside s. Each step moves to one of the
  // 8 neighbours, and a line covers max(|dx|, |dy|) + 1 pixels.
  // @stub fprintf(2, "09.04: line not written yet\n"); exit(1);
  int dx = x1 > x0 ? x1 - x0 : x0 - x1;
  int dy = y1 > y0 ? y0 - y1 : y1 - y0;   // minus the height
  int sx = x0 < x1 ? 1 : -1;
  int sy = y0 < y1 ? 1 : -1;
  int err = dx + dy;
  for(;;){
    putpixel(s, x0, y0, color);
    if(x0 == x1 && y0 == y1)
      break;
    int e2 = 2 * err;
    if(e2 >= dy){
      err += dy;
      x0 += sx;
    }
    if(e2 <= dx){
      err += dx;
      y0 += sy;
    }
  }
  // @end
}

// Character c with its top left corner at (x, y), in color. Only the
// character's own pixels are drawn: what is behind it shows through.
void
drawchar(struct surface *s, int x, int y, int c, uint color)
{
  // @build 09.04 drawchar
  // font[c - 32] holds character c, for c from 32 to 126; draw any other
  // c as '?'. Its 8 bytes are the rows, top first, and in each byte bit
  // 7 (0x80) is the leftmost pixel. Plot (putpixel) the pixel at
  // (x + col, y + row) for each bit that is 1, and leave the others
  // alone.
  // @stub fprintf(2, "09.04: drawchar not written yet\n"); exit(1);
  if(c < 32 || c > 126)
    c = '?';
  uchar *glyph = font[c - 32];
  for(int row = 0; row < FONT_H; row++)
    for(int col = 0; col < FONT_W; col++)
      if(glyph[row] & (0x80 >> col))
        putpixel(s, x + col, y + row, color);
  // @end
}

// @from 09.04
// A line of text, one character every FONT_W pixels. Returns the x just
// past its end.
int
drawtext(struct surface *s, int x, int y, char *text, uint color)
{
  for(; *text; text++){
    drawchar(s, x, y, *text, color);
    x += FONT_W;
  }
  return x;
}

// Copy all of src into dst with src's top left corner at (x, y).
void
blit(struct surface *dst, int x, int y, struct surface *src)
{
  for(int j = 0; j < src->h; j++){
    if(y + j < 0 || y + j >= dst->h)
      continue;
    for(int i = 0; i < src->w; i++)
      if(x + i >= 0 && x + i < dst->w)
        dst->px[(y + j) * dst->w + x + i] = src->px[j * src->w + i];
  }
}
// @end

int
input_open(void)
{
  int fd = open("/input", O_RDONLY);
  if(fd < 0){
    mknod("/input", INPUT, 0);
    fd = open("/input", O_RDONLY);
  }
  return fd;
}

// What the keys of a US keyboard type, by key code (kernel/input.h):
// code 2 is the 1 key, 16 is q, 30 is a, 44 is z, 57 the space bar.
static char plain[58] =
  "\0\0331234567890-=\b\tqwertyuiop[]\n\0asdfghjkl;'`\0\\zxcvbnm,./\0*\0 ";
static char shifted[58] =
  "\0\033!@#$%^&*()_+\b\tQWERTYUIOP{}\n\0ASDFGHJKL:\"~\0|ZXCVBNM<>?\0*\0 ";

int
keychar(int code, int shift)
{
  if(code < 0 || code >= sizeof(plain))
    return 0;
  return shift ? shifted[code] : plain[code];
}

// A name for a key or button, for printing.
char *
keyname(int code)
{
  static char one[2];
  switch(code){
  case KEY_ESC: return "esc";
  case KEY_BACKSPACE: return "backspace";
  case KEY_ENTER: return "enter";
  case KEY_LEFTSHIFT: return "left shift";
  case KEY_RIGHTSHIFT: return "right shift";
  case KEY_SPACE: return "space";
  case BTN_LEFT: return "left button";
  case BTN_RIGHT: return "right button";
  case BTN_MIDDLE: return "middle button";
  }
  one[0] = keychar(code, 0);
  if(one[0] > ' ' && one[0] <= '~')
    return one;
  return "?";
}
