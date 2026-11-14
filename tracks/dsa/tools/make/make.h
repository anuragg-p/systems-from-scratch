/*
 * make.h - what the two halves of make share: read.c reads makefiles into
 * a graph, make.c builds from the graph.
 */
#ifndef MAKE_H
#define MAKE_H

#include <time.h>

#include "ds.h"
#include "depgraph.h"

/* The command lines under a rule, as written (without the tab), run one
 * after another by the shell. Their variables are expanded as they run. */
typedef struct {
    Array       lines;      /* char * */
    const char *file;       /* where the rule is, for messages */
    long        line;
} Recipe;

/* What make knows about one node of the graph, hung on its data. */
typedef struct {
    Recipe *recipe;         /* NULL: none */
    int     rule;           /* a rule names it as a target */
    int     phony;          /* .PHONY names it: never a file */
    int     ran;            /* its recipe ran (or, with -n, was printed) */
    int     checked;        /* exists and mtime have been read */
    int     exists;         /* there is a file by its name */
    struct timespec mtime;  /* when that file last changed */
    int     remade;         /* made again in this run */               // @from 07.03
} Target;

/* The Target of node n, made empty on first use. */
Target *target(Graph *g, long n);

/* Read the makefile at path, and every makefile it includes, into g. A
 * makefile that cannot be read, or that uses what this make does not
 * support, is fatal. */
void read_makefile(Graph *g, const char *path);

/* The first target of the first rule (not one whose name starts with a
 * dot, such as .PHONY): what make builds when it is not told; -1. */
extern long default_goal;

/* Where a variable's value came from: the later in this list wins. */
enum { FROM_ENVIRONMENT, FROM_MAKEFILE, FROM_COMMAND_LINE };

void set_variable(const char *name, const char *value, int origin);

/* text with each $(NAME) replaced by NAME's value, itself expanded, and
 * each $$ by $: a new string. file and line say where text is, for an
 * error. */
char *expand(const char *text, const char *file, long line);

#endif
