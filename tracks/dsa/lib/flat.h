/*
 * flat.h - the text in one array (flat.c).
 */
#ifndef FLAT_H
#define FLAT_H

#include "text.h"

/* The text of the file at path, every byte of it copied into one array.
 * A file that does not exist is an empty text. */
Text *flat_open(const char *path);

#endif
