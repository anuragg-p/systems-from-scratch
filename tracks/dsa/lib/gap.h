/*
 * gap.h - a gap buffer (gap.c).
 */
#ifndef GAP_H
#define GAP_H

#include "text.h"

/* The text of the file at path, read into one array with a gap after it.
 * A file that does not exist is an empty text. */
Text *gap_open(const char *path);

#endif
