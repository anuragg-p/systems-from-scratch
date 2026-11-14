/*
 * ptree.h - a piece table, its pieces in a balanced tree (ptree.c).
 */
#ifndef PTREE_H
#define PTREE_H

#include "pieces.h"

/* The text of the file at path, as one piece: all of the original buffer,
 * mapped as pieces.c maps it. */
Text *ptree_open(const char *path);

#endif
