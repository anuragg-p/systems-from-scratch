/*
 * edit.h - the edit distance between two words (lib/edit.c): the fewest
 * letters to insert, delete or replace to turn one into the other.
 */
#ifndef EDIT_H
#define EDIT_H

#include "ds.h"

/* The distance between the na bytes at a and the nb bytes at b, by the
 * table: a row for each letter of b, a column for each letter of a. */
int  edit_distance(const char *a, size_t na, const char *b, size_t nb);

/* The table a row at a time, for a walk that shares rows (lib/trie.c).
 * A row has na + 1 cells. The first row is 0 1 2 ... na: the distance
 * from nothing to each start of a. edit_next_row fills row from prev, the
 * row above it, for one more letter c of b. */
void edit_first_row(int *row, size_t na);
void edit_next_row(const int *prev, int *row, const char *a, size_t na, int c);

#endif
