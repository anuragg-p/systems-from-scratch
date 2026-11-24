/* script.h: kilo's Lua (script.c), and what it uses of kilo.
 *
 * kilo.c includes this file and calls the first group of functions; script.c
 * calls the second group, which are kilo.c's. Nothing here mentions Lua:
 * only script.c includes Lua's headers. */

#ifndef KILO_SCRIPT_H
#define KILO_SCRIPT_H

#include <stddef.h>

/* ================================= Limits ================================= */

#define SCRIPT_PROMPT_MAX 256       /* bytes in a line typed at a prompt */
#define AUTOCMD_MAX 64              /* autocommands at once */ // @from 09.05
// @from 09.06
#define NAMESPACE_MAX 64            /* namespaces for highlights */
#define HIGHLIGHT_MAX 10000         /* highlights at once, in all namespaces */
// @end
// @from 09.08
#define SCRIPT_MAX_MEMORY (64*1024*1024)    /* bytes Lua may hold */
#define SCRIPT_HOOK_COUNT 100000    /* instructions between looks at the keyboard */
// @end

/* What kilo.c calls. */
void scriptStart(void);
void scriptEval(const char *line);
// @from 09.04
int scriptCall(int ref, const char *arg);
void scriptUnref(int ref);
// @end
int scriptRun(const char *path);                            // @from 09.09

/* What script.c calls in kilo.c. */
void editorMessage(const char *s, size_t len, int error);
void editorScriptReturned(void);                            // @from 09.03
void disableRawMode(int fd);

// @internal
/* Stands in for code a workspace has cut out (see kilo.c). */
__attribute__((noreturn)) void kiloTodo(const char *lesson, const char *what);
// @end
#endif
