/* lsp.h: kilo's language server client (lsp.c), and what it uses of kilo.
 *
 * kilo.c includes this file and calls the first group of functions, each
 * from one line in it; lsp.c calls the second group, which are kilo.c's. */

#ifndef KILO_LSP_H
#define KILO_LSP_H

// @from 07.06
/* The frame kilo.c builds in editorRefreshScreen(); only kilo.c needs to
 * know what is in it. */
struct abuf;

// @end
/* What kilo.c calls. */
void lspStart(const char *filename);
// @from 07.02
// @from 07.04
// @else
// void lspPump(void);
// @end
// @end
void lspWaitKey(int fd);                    // @from 07.04
// @from 07.06
void lspDrawRow(struct abuf *ab, int filerow, const char *chars, int size,
                const char *render, int rsize, int coloff, int cols);
// @end
void lspDefinition(void);                   // @from 07.07
void lspBack(void);                         // @from 07.07

// @from 07.06
/* What lsp.c calls in kilo.c: functions the editor has anyway, */
// @else
// /* What lsp.c calls in kilo.c: functions the editor has anyway. */
// @end
void editorSetStatusMessage(const char *fmt, ...);
void editorRefreshScreen(void);                             // @from 07.02
char *editorRowsToString(int *buflen);                      // @from 07.05
void abAppend(struct abuf *ab, const char *s, int len);    // @from 07.06
// @from 07.06
/* and those kilo.c keeps for it, in "The editor's side of the language
 * client" there. */
void editorCursor(int *row, int *col);
int editorJump(const char *path, int row, int col);         // @from 07.07
// @end

// @internal
/* Stands in for code a workspace has cut out (see kilo.c). */
__attribute__((noreturn)) void kiloTodo(const char *lesson, const char *what);
// @end
#endif
