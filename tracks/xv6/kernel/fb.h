// The screen, as the kernel and user programs both see it (module 09).
//
// 640 x 480 pixels, one 32-bit word each, row after row from the top
// left. A pixel is 0x00RRGGBB: blue in the lowest byte, then green, then
// red, and the top byte unused. In memory, the bytes of one pixel are
// therefore B, G, R, 0 (DRM calls this XRGB8888, fourcc "XR24").
//
// Pixel (x, y) is the word at  base + y * FB_STRIDE + x * 4.

#define FB_WIDTH   640
#define FB_HEIGHT  480
#define FB_BPP     4                      // bytes per pixel
#define FB_STRIDE  (FB_WIDTH * FB_BPP)    // bytes from one row to the next
#define FB_SIZE    (FB_STRIDE * FB_HEIGHT)
