// @from 09.04
// The drawing library: what a program needs to put
// rectangles, lines and text on the screen and to hear the keyboard and
// the mouse. Include it after kernel/types.h, kernel/fb.h,
// kernel/input.h and user/user.h, and link with user/gui.c and
// user/font.c (the Makefile's GUIPROGS).
//
// Everything is drawn into a surface, an array of pixels in ordinary
// memory, and nothing appears until present() copies the whole picture to
// the screen at once. A pixel is 0x00RRGGBB (kernel/fb.h).
// @else
// // The GUI library: what a program needs to hear the keyboard and the
// // mouse. Include it after kernel/types.h, kernel/input.h and
// // user/user.h, and link with user/gui.c (the Makefile's GUIPROGS).
// @end

// @from 09.04
struct surface {
  uint *px;       // pixel (x, y) is px[y * w + x]
  int w;
  int h;
};

// The screen. screen_open() maps it (fbmap) and makes back, a surface the
// size of the screen, to draw in. present() copies back to the screen.
// screen_open returns -1 if there is no screen.
int   screen_open(struct surface *back);
void  present(struct surface *back);

// Drawing. Each call draws only the part that falls inside s.
void  fillrect(struct surface *s, int x, int y, int w, int h, uint color);
void  line(struct surface *s, int x0, int y0, int x1, int y1, uint color);
void  drawchar(struct surface *s, int x, int y, int c, uint color);
int   drawtext(struct surface *s, int x, int y, char *text, uint color);
void  blit(struct surface *dst, int x, int y, struct surface *src);

// The font (user/font.c): characters 32 to 126, 8 x 8 pixels each.
#define FONT_W 8
#define FONT_H 8
extern uchar font[95][8];
// @end

// Input. input_open() returns a file descriptor on the input device,
// making its file, /input, the first time. read() it into an array of
// struct inputevent. keychar() is the character a key types (shift
// says whether a shift key is down), or 0 for a key that types none.
int   input_open(void);
int   keychar(int code, int shift);
char *keyname(int code);
