// paint: draw with the mouse.
//
//   +--------------------------------------------------+
//   | paint                c clear  1 2 3 pen  esc quit |  title bar, TOP rows
//   |                                                  |
//   |                    the canvas                    |  CANVAS_H rows
//   |                                                  |
//   | [] [] [] [] [] [] [] [] [] []              pen 2 |  colour bar
//   +--------------------------------------------------+
//
// Hold the left button down in the canvas to draw; click a swatch to
// change colour. Keys: c clears the canvas, 1 2 3 pick the pen size, Esc
// quits. Everything comes in as events from the input device, and every
// batch of events ends with a whole new frame on the screen.
//
// The drawing lives in its own surface, the canvas, which only strokes
// change. Each frame is composed in the back buffer from scratch: the
// canvas, the bars, then the pointer on top, so the pointer never
// smudges the drawing underneath it.

#include "kernel/types.h"
#include "kernel/fb.h"
#include "kernel/input.h"
#include "user/user.h"
#include "user/gui.h"

#define TOP 20                            // the title bar's height
#define BAR 32                            // the colour bar's height
#define CANVAS_H (FB_HEIGHT - TOP - BAR)
#define SW_X 8                            // swatch i is at SW_X + i * SW_STEP
#define SW_STEP 40
#define SW_W 32
#define SW_H 24
#define SW_Y (FB_HEIGHT - BAR + 4)

#define WHITE 0xffffff
#define BLACK 0x000000
#define BARCOLOR 0x2b2b2b
#define DIM 0xb0b0b0

uint swatches[] = {
  0x000000, 0x808080, 0xffffff, 0xff0000, 0xff8000,
  0xffff00, 0x00c000, 0x00c0ff, 0x0000ff, 0x8000ff,
};
#define NSWATCH (sizeof(swatches) / sizeof(swatches[0]))

struct surface back;      // the frame being composed
struct surface canvas;    // the drawing: FB_WIDTH x CANVAS_H

int px = -1, py = -1;     // where the pointer is; -1 until it first moves
int nx = -1, ny = -1;     // where it is going: EV_ABS sets these, EV_SYN moves it
int drawing;              // the left button went down in the canvas and is still down
int choice;               // the chosen swatch
int pen = 1;              // the pen's radius: a stroke is 2 * pen + 1 pixels wide

struct inputevent ev[32];

// The swatch at screen position (x, y), or -1.
static int
swatch_at(int x, int y)
{
  if(y < SW_Y || y >= SW_Y + SW_H || x < SW_X)
    return -1;
  int i = (x - SW_X) / SW_STEP;
  if(i >= NSWATCH || x - SW_X - i * SW_STEP >= SW_W)
    return -1;
  return i;
}

// A stroke on the canvas from screen point (x0, y0) to (x1, y1) with the
// pen: the one-pixel line, drawn again at every offset up to pen
// pixels away, which paints a square of side 2 * pen + 1 around each of
// its pixels.
static void
stroke(int x0, int y0, int x1, int y1)
{
  for(int dy = -pen; dy <= pen; dy++)
    for(int dx = -pen; dx <= pen; dx++)
      line(&canvas, x0 + dx, y0 - TOP + dy, x1 + dx, y1 - TOP + dy, swatches[choice]);
}

static int
in_canvas(int x, int y)
{
  return x >= 0 && x < FB_WIDTH && y >= TOP && y < TOP + CANVAS_H;
}

// Act on one event. Returns 0 when it is time to quit, else 1.
static int
handle(struct inputevent *e)
{
  // @build 09.05 handle
  // EV_ABS: the new x (ABS_X) or y (ABS_Y) goes in nx or ny; the pointer
  //   moves only at the EV_SYN that ends the group.
  // EV_SYN: move the pointer (px, py) to (nx, ny). If drawing, stroke
  //   from where it was to where it is now.
  // EV_KEY BTN_LEFT, value 1: over a swatch (swatch_at), choose it; in
  //   the canvas (in_canvas), start drawing with a stroke from the
  //   pointer to itself: a dot. Before the pointer has moved (px < 0)
  //   it is nowhere: do nothing. Value 0: stop drawing.
  // EV_KEY, any other key, value 1 (down) or 2 (repeat): KEY_ESC quits;
  //   the key that types 'c' clears the canvas to white; '1', '2' and
  //   '3' set pen to 0, 1 and 2. Ignore keys going up.
  // @stub fprintf(2, "09.05: handle not written yet\n"); exit(1);
  if(e->type == EV_ABS){
    if(e->code == ABS_X)
      nx = e->value;
    else if(e->code == ABS_Y)
      ny = e->value;
  } else if(e->type == EV_SYN){
    if(nx >= 0 && ny >= 0){
      if(drawing)
        stroke(px, py, nx, ny);
      px = nx;
      py = ny;
    }
  } else if(e->type == EV_KEY && e->code == BTN_LEFT){
    if(e->value == 1 && px >= 0){
      int s = swatch_at(px, py);
      if(s >= 0){
        choice = s;
      } else if(in_canvas(px, py)){
        drawing = 1;
        stroke(px, py, px, py);
      }
    } else if(e->value == 0){
      drawing = 0;
    }
  } else if(e->type == EV_KEY && e->value != 0){
    int c = keychar(e->code, 0);
    if(e->code == KEY_ESC)
      return 0;
    if(c == 'c')
      fillrect(&canvas, 0, 0, canvas.w, canvas.h, WHITE);
    else if(c >= '1' && c <= '3')
      pen = c - '1';
  }
  return 1;
  // @end
}

// The pointer: a cross with a gap in the middle, so you can see the
// pixel it points at. Black arms, outlined in white, to show on any
// colour.
static void
pointer(int x, int y)
{
  fillrect(&back, x - 9, y - 1, 7, 3, WHITE);
  fillrect(&back, x + 3, y - 1, 7, 3, WHITE);
  fillrect(&back, x - 1, y - 9, 3, 7, WHITE);
  fillrect(&back, x - 1, y + 3, 3, 7, WHITE);
  line(&back, x - 8, y, x - 3, y, BLACK);
  line(&back, x + 3, y, x + 8, y, BLACK);
  line(&back, x, y - 8, x, y - 3, BLACK);
  line(&back, x, y + 3, x, y + 8, BLACK);
}

// Compose a whole frame in the back buffer, then show it.
static void
redraw(void)
{
  // @build 09.05 redraw
  // Back to front, so later things cover earlier ones: the canvas
  // (blit it to row TOP); the title bar, BARCOLOR, with "paint" in WHITE
  // at (8, 6) and the help text in DIM, ending 8 pixels from the right
  // edge; the colour bar, BARCOLOR, with each swatch SW_W x SW_H at
  // (SW_X + i * SW_STEP, SW_Y), the chosen one inside a WHITE frame 2
  // pixels wide, and "pen N" (N is 1, 2 or 3) in DIM at the right end,
  // also 8 pixels in; and last the pointer, if it has been anywhere yet.
  // Then present(): the screen goes from one whole frame to the next.
  // @stub fprintf(2, "09.05: redraw not written yet\n"); exit(1);
  char *help = "c clear  1 2 3 pen  esc quit";
  char pentext[] = "pen 1";

  blit(&back, 0, TOP, &canvas);

  fillrect(&back, 0, 0, FB_WIDTH, TOP, BARCOLOR);
  drawtext(&back, 8, 6, "paint", WHITE);
  drawtext(&back, FB_WIDTH - 8 - (int)strlen(help) * FONT_W, 6, help, DIM);

  fillrect(&back, 0, FB_HEIGHT - BAR, FB_WIDTH, BAR, BARCOLOR);
  for(int i = 0; i < NSWATCH; i++){
    int x = SW_X + i * SW_STEP;
    if(i == choice)
      fillrect(&back, x - 2, SW_Y - 2, SW_W + 4, SW_H + 4, WHITE);
    fillrect(&back, x, SW_Y, SW_W, SW_H, swatches[i]);
  }
  pentext[4] = '1' + pen;
  drawtext(&back, FB_WIDTH - 8 - (int)strlen(pentext) * FONT_W, SW_Y + 8, pentext, DIM);

  if(px >= 0)
    pointer(px, py);
  present(&back);
  // @end
}

int
main(void)
{
  if(screen_open(&back) < 0){
    fprintf(2, "paint: no screen\n");
    exit(1);
  }
  canvas.w = FB_WIDTH;
  canvas.h = CANVAS_H;
  canvas.px = malloc(FB_WIDTH * CANVAS_H * sizeof(uint));
  int fd = input_open();
  if(canvas.px == 0 || fd < 0){
    fprintf(2, "paint: out of memory, or no /input\n");
    exit(1);
  }
  fillrect(&canvas, 0, 0, canvas.w, canvas.h, WHITE);
  printf("paint: draw in the window; Esc there quits\n");
  redraw();

  for(;;){
    int n = read(fd, ev, sizeof(ev));
    if(n <= 0)
      break;
    for(int i = 0; i < n / sizeof(ev[0]); i++){
      if(handle(&ev[i]) == 0){
        // leave a black screen: nobody is drawing on it any more.
        fillrect(&back, 0, 0, back.w, back.h, BLACK);
        present(&back);
        exit(0);
      }
    }
    redraw();
  }
  exit(1);
}
