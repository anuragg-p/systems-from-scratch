// Input events, as user programs read them from the input device
// (module 09).
//
// The keyboard and the mouse each report what happened as a series of
// events, and an EV_SYN event ends each group: a key going down is
// EV_KEY then EV_SYN; the mouse moving is EV_ABS for x, EV_ABS for y,
// then EV_SYN. The format is the virtio input device's, which is
// Linux's evdev format, with one change: the kernel turns mouse
// positions into screen pixels.

struct inputevent {
  ushort type;    // EV_SYN, EV_KEY or EV_ABS
  ushort code;    // which key, button or axis
  int value;      // EV_KEY: 1 down, 0 up, 2 held down (repeat)
                  // EV_ABS: the position on that axis, in pixels
};

#define EV_SYN 0x00      // end of a group of events
#define EV_KEY 0x01      // a key or a mouse button
#define EV_ABS 0x03      // a position

#define ABS_X 0x00
#define ABS_Y 0x01

// a few key codes (Linux's numbering, which is the PC keyboard's)
#define KEY_ESC        1
#define KEY_BACKSPACE 14
#define KEY_ENTER     28
#define KEY_LEFTSHIFT 42
#define KEY_RIGHTSHIFT 54
#define KEY_SPACE     57

#define BTN_LEFT   0x110
#define BTN_RIGHT  0x111
#define BTN_MIDDLE 0x112

// the input device's major number: mknod("input", INPUT, 0) makes a
// file whose read() returns these events.
#define INPUT 2
