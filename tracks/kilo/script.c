/* script.c: Lua inside kilo.
 *
 * Lua is a language made to live inside a program written in C: a library
 * with a C API, through which the program hands it values, runs its code,
 * and is called back. kilo starts one Lua state and keeps it to the end:
 * the user's init.lua runs in it, and each line typed at the "lua: "
 * prompt.
// @from 09.02
 *
 * kilo.c knows nothing of Lua. What a script may do to the editor is the
 * API (api.h): a table of C functions that kilo.c defines and this file
 * hands to Lua as kilo.api, each through one dispatcher that turns Lua's
 * values into the API's and back.
// @end
 */

// @from 09.08
/* access(), poll() and read() are POSIX, not C99: on Linux, ask for them.
 * macOS shows them anyway. */
// @else
// /* access() is POSIX, not C99: on Linux, ask for it. macOS shows it
//  * anyway. */
// @end
#ifdef __linux__
#define _POSIX_C_SOURCE 200809L
#endif

#include <errno.h>
#include <poll.h>           // @from 09.08
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include "api.h"            // @from 09.02
#include "script.h"

/* ================================ The state =============================== */

/* The one Lua state, and what kilo keeps beside it. */
static struct {
    lua_State *L;       /* NULL before scriptStart(), or when Lua could not start */
    int depth;          /* calls into Lua going on now, one inside another */
    int screen;         /* 1: the editor; 0: kilo -l, no screen and no keys @from 09.09 */
    size_t used;        /* bytes Lua holds now @from 09.08 */
    int interrupted;    /* Ctrl-C was typed while a script ran @from 09.08 */
    int panic;          /* @internal the test aid kilo.test_panic() asked for a panic */
} S;

static void scriptStop(void);
static void scriptHook(lua_State *L, lua_Debug *ar);           // @from 09.08

// @from 09.08
/* Lua asks for all of its memory here: ptr is a block of osize bytes, to
 * become nsize bytes (nsize 0: freed). This one counts what Lua holds, and
 * refuses to let it grow past SCRIPT_MAX_MEMORY: Lua then raises "not
 * enough memory", which the protected call around the script catches. */
static void *scriptAlloc(void *ud, void *ptr, size_t osize, size_t nsize) {
    // @build 09.08 count the memory
    // ptr NULL is a new block, and osize then says what the block is for,
    // not a size: count it as 0. nsize 0: free the block. Otherwise refuse
    // (return NULL) a growth that would take S.used past the limit, and
    // realloc(). Keep S.used to what really happened. Never refuse to
    // shrink: Lua counts on that.
    void *p;

    (void)ud;
    if (ptr == NULL) osize = 0;
    if (nsize == 0) {
        free(ptr);
        S.used -= osize;
        return NULL;
    }
    if (nsize > osize && S.used-osize+nsize > SCRIPT_MAX_MEMORY) return NULL;
    p = realloc(ptr,nsize);
    if (p) S.used = S.used-osize+nsize;
    return p;
    // @end
}

/* Lua calls this for an error that no protected call catches, and would
 * abort() after it. Every way into Lua here is protected, so nothing should
 * come here. If something does: put the terminal back, say the error, and
 * exit, without closing a state that is in no shape to be closed. */
static int scriptPanic(lua_State *L) {
    // @build 09.08 a panic
    // Take the error on top of the stack if it is a string. Forget the state
    // (S.L NULL, so scriptStop() leaves it), leave raw mode, write
    // "kilo: Lua panic: " and the error on standard error, and exit(1).
    const char *msg = lua_type(L,-1) == LUA_TSTRING ? lua_tostring(L,-1) : "(not a string)";

    S.L = NULL;
    disableRawMode(STDIN_FILENO);
    fprintf(stderr,"kilo: Lua panic: %s\n",msg);
    exit(1);
    // @end
}

// @end
/* =========================== Calling into Lua ============================ */

/* Say the error on top of the stack, and pop it: its first line only, in
 * the message line (under kilo -l on standard error: kilo.c decides). An
 * error is most often a string; anything else is named by its type, as
 * Lua's own lua.c does, since making it into a string could fail too. */
static void scriptReport(lua_State *L) {
    // @build 09.01 say what went wrong
    // A string: its bytes up to the first newline. Anything else: "(error
    // object is a TYPE value)". Hand it to editorMessage() as an error.
    char buf[64];
    const char *msg = buf, *nl;
    size_t len;

    if (lua_type(L,-1) == LUA_TSTRING) {
        msg = lua_tolstring(L,-1,&len);
    } else {
        snprintf(buf,sizeof(buf),"(error object is a %s value)",luaL_typename(L,-1));
        len = strlen(buf);
    }
    if ((nl = memchr(msg,'\n',len)) != NULL) len = nl-msg;
    editorMessage(msg,len,1);
    lua_pop(L,1);
    // @end
}

/* Every way into Lua goes through here. fn runs as one of Lua's C
 * functions, with arg as its argument (a light userdata), inside
 * lua_pcall(): so whatever goes wrong in it, a script's error or no memory
 * for a string, comes back here as a status, never as a jump out of kilo.
 * Returns 0, or -1 when there was an error (said). */
static int scriptProtected(lua_CFunction fn, void *arg) {
    lua_State *L = S.L;
    int status;

    if (L == NULL) return -1;
    // @build 09.01 every way in is a protected call
    // Count the call in S.depth while it runs. Push fn and arg (neither push
    // needs memory) and lua_pcall() them; on an error, scriptReport().
    S.depth++;
    lua_pushcfunction(L,fn);
    lua_pushlightuserdata(L,arg);
    status = lua_pcall(L,1,0,0);
    S.depth--;
    if (status != LUA_OK) scriptReport(L);
    // @end
    // @build 09.08 back from a script that went wrong
    // Back at the outermost call: after an error, a full collection, so that
    // memory a script filled is given back now (after "not enough memory",
    // the next allocation would fail too); and a Ctrl-C is forgotten, the
    // hook back to its count.
    if (S.depth == 0 && status != LUA_OK) lua_gc(L,LUA_GCCOLLECT);
    if (S.depth == 0 && S.interrupted) {
        S.interrupted = 0;
        lua_sethook(L,scriptHook,LUA_MASKCOUNT,SCRIPT_HOOK_COUNT);
    }
    // @end
    if (S.depth == 0) editorScriptReturned();      // @from 09.03
    // @internal
    /* The test aid: an error raised here is outside any protected call. */
    if (S.depth == 0 && S.panic) {
        lua_pushstring(L,"a panic, on purpose");
        lua_error(L);
    }
    // @end
    return status == LUA_OK ? 0 : -1;
}

/* A file of Lua, read a block at a time by lua_load() below. */
struct scriptReader {
    FILE *fp;
    char buf[4096];
};

static const char *scriptRead(lua_State *L, void *ud, size_t *size) {
    struct scriptReader *r = ud;
    (void)L;
    *size = fread(r->buf,1,sizeof(r->buf),r->fp);
    return *size ? r->buf : NULL;
}

/* Run the file whose path is the light userdata at 1 (through
 * scriptProtected()). Its chunk is named "@" and the file's own name, which
 * is what Lua puts in front of an error in it: "init.lua:3: ...". */
static int scriptFileIn(lua_State *L) {
    // @build 09.01 run a file
    // Open the file (an error if it cannot be: luaL_error(), with
    // strerror()). lua_load() it through scriptRead(), with the chunk name
    // "@" and the part of the path after its last '/'. Close the file, and
    // if it did not compile, raise the error (lua_error()). Call the chunk.
    const char *path = lua_touserdata(L,1), *slash = strrchr(path,'/');
    struct scriptReader r;
    char name[256];
    int status;

    if ((r.fp = fopen(path,"r")) == NULL)
        return luaL_error(L,"cannot open %s: %s",path,strerror(errno));
    snprintf(name,sizeof(name),"@%s",slash ? slash+1 : path);
    status = lua_load(L,scriptRead,&r,name,NULL);
    fclose(r.fp);
    if (status != LUA_OK) return lua_error(L);
    lua_call(L,0,0);
    return 0;
    // @end
}

/* A line typed at the "lua: " prompt (through scriptProtected()). As Lua's
 * own prompt does, it is tried first as an expression, with "return " in
 * front, and the values it gives are shown, as print() shows them; if that
 * does not compile, it is run as a statement. */
static int scriptEvalIn(lua_State *L) {
    // @build 09.01 a line at the prompt
    // Load "return LINE;" as the chunk "=lua"; if that fails, LINE itself
    // (if that fails too, raise its error). Call it for all its results; if
    // there are any, show them with print, the global, as Lua's prompt does.
    const char *line = lua_touserdata(L,1);
    int n;

    lua_settop(L,0);
    lua_pushfstring(L,"return %s;",line);
    if (luaL_loadbuffer(L,lua_tostring(L,1),lua_rawlen(L,1),"=lua") != LUA_OK) {
        lua_settop(L,0);
        if (luaL_loadbuffer(L,line,strlen(line),"=lua") != LUA_OK) return lua_error(L);
    } else {
        lua_remove(L,1);
    }
    lua_call(L,0,LUA_MULTRET);
    if ((n = lua_gettop(L)) > 0) {
        lua_getglobal(L,"print");
        lua_insert(L,1);
        lua_call(L,n,0);
    }
    return 0;
    // @end
}

void scriptEval(const char *line) {
    scriptProtected(scriptEvalIn,(void *)line);
}

/* print(), joining its arguments as Lua's own does (each through
 * tostring(), a tab between them), but to the editor: the message line, or
 * under kilo -l a line of standard output. */
static int scriptPrint(lua_State *L) {
    // @build 09.01 print to the message line
    // Build the line in a luaL_Buffer: for each argument, a tab before all
    // but the first, then luaL_tolstring() of it and luaL_addvalue(). Push
    // the result and give its bytes to editorMessage().
    int n = lua_gettop(L), i;
    const char *s;
    size_t len;
    luaL_Buffer b;

    luaL_buffinit(L,&b);
    for (i = 1; i <= n; i++) {
        if (i > 1) luaL_addchar(&b,'\t');
        luaL_tolstring(L,i,NULL);
        luaL_addvalue(&b);
    }
    luaL_pushresult(&b);
    s = lua_tolstring(L,-1,&len);
    editorMessage(s,len,0);
    return 0;
    // @end
}

// @from 09.02
/* ============================= The API, in Lua ============================ */

/* Is the value at idx of the API's type t? If not, what it is instead goes
 * in why: its type as Lua names it ("float" for a number with a fraction),
 * and for a table, what is wrong inside it. Nothing here can raise an
 * error or needs memory. */
static int scriptCheck(lua_State *L, int idx, ApiType t, char *why, size_t size) {
    // @build 09.02 check an argument
    // Booleans, strings (not numbers) and functions by lua_type(). An
    // integer: a number lua_tointegerx() takes whole. Lines: a table whose
    // keys are 1 to #t (count them with lua_next()), each value a string.
    // A position: a table of two, both integers.
    int type = lua_type(L,idx), ok = 0, isint;
    lua_Integer n, k = 0;

    snprintf(why,size,"%s",luaL_typename(L,idx));
    switch (t) {
    case API_BOOLEAN: return type == LUA_TBOOLEAN;
    case API_STRING: return type == LUA_TSTRING;
    case API_FUNCTION: return type == LUA_TFUNCTION;   // @from 09.04
    case API_INTEGER:
        lua_tointegerx(L,idx,&isint);
        if (type == LUA_TNUMBER && !isint) snprintf(why,size,"float");
        return type == LUA_TNUMBER && isint;
    case API_LINES:
    case API_POSITION:
        if (type != LUA_TTABLE) return 0;
        n = lua_rawlen(L,idx);
        lua_pushnil(L);
        while (lua_next(L,idx)) {
            k++;
            lua_pop(L,1);
        }
        if (k != n || (t == API_POSITION && n != 2)) {
            snprintf(why,size,t == API_LINES ? "a table that is not a list" :
                     "a table that is not {row, col}");
            return 0;
        }
        for (k = 1, ok = 1; k <= n && ok; k++) {
            int item = lua_rawgeti(L,idx,k);
            lua_tointegerx(L,-1,&isint);
            ok = t == API_LINES ? item == LUA_TSTRING : item == LUA_TNUMBER && isint;
            if (!ok) snprintf(why,size,"a table with a %s at %d",
                              item == LUA_TNUMBER && !isint ? "float" : lua_typename(L,item),(int)k);
            lua_pop(L,1);
        }
        return ok;
    default:
        return 0;
    }
    // @end
}

/* The value at idx, checked already, as the API's type t. A string is
 * Lua's own, borrowed for the call (it stays alive while it is on the
 * stack, or in a table there); lines get an array of such strings, which
 * scriptRelease() frees (line NULL when there was no memory for it). */
static ApiValue scriptTake(lua_State *L, int idx, ApiType t) {
    // @build 09.02 an argument as the API's value
    // Fill v.u for t: lua_toboolean(), lua_tointegerx(), lua_tolstring().
    // Lines: malloc() an ApiString for each item and point it at the
    // item's bytes. A position: items 1 and 2.
    // @from 09.04
    // A function: push it again and luaL_ref() it in the registry: the
    // reference keeps it alive after the call, until scriptUnref().
    // @end
    ApiValue v;
    size_t len;
    int k, n;

    v.type = t;
    switch (t) {
    case API_BOOLEAN: v.u.boolean = lua_toboolean(L,idx); break;
    case API_INTEGER: v.u.integer = lua_tointegerx(L,idx,NULL); break;
    case API_STRING:
        v.u.string.s = (char *)lua_tolstring(L,idx,&len);
        v.u.string.len = len;
        break;
    case API_LINES:
        n = (int)lua_rawlen(L,idx);
        v.u.lines.count = n;
        v.u.lines.line = malloc(sizeof(ApiString)*(n ? n : 1));
        for (k = 0; k < n && v.u.lines.line; k++) {
            lua_rawgeti(L,idx,k+1);
            v.u.lines.line[k].s = (char *)lua_tolstring(L,-1,&len);
            v.u.lines.line[k].len = len;
            lua_pop(L,1);
        }
        break;
    case API_POSITION:
        lua_rawgeti(L,idx,1);
        lua_rawgeti(L,idx,2);
        v.u.position.row = lua_tointegerx(L,-2,NULL);
        v.u.position.col = lua_tointegerx(L,-1,NULL);
        lua_pop(L,2);
        break;
    // @from 09.04
    case API_FUNCTION:
        lua_pushvalue(L,idx);
        v.u.function = luaL_ref(L,LUA_REGISTRYINDEX);
        break;
    // @end
    default:
        break;
    }
    return v;
    // @end
}

/* Free what scriptTake() made for n arguments.
// @from 09.04
 * failed: the function did not keep its references, so they go too. */
// @else
//  */
// @end
static void scriptRelease(ApiValue *args, int n, int failed) {
    int i;
    for (i = 0; i < n; i++) {
        if (args[i].type == API_LINES) free(args[i].u.lines.line);
        if (args[i].type == API_FUNCTION && failed) scriptUnref(args[i].u.function); // @from 09.04
    }
    (void)failed;
}

/* Push what a function returned (in a protected call of its own, from
 * scriptDispatch(): if Lua has no memory for it, the value can still be
 * freed). API_NIL pushes nothing. */
static int scriptPushIn(lua_State *L) {
    // @build 09.02 the API's value as Lua's
    // A boolean, an integer, a string as themselves; lines as a new table
    // of strings, from 1; a position as {row, col}.
    ApiValue *v = lua_touserdata(L,1);
    int k;

    switch (v->type) {
    case API_BOOLEAN: lua_pushboolean(L,v->u.boolean); break;
    case API_INTEGER: lua_pushinteger(L,v->u.integer); break;
    case API_STRING: lua_pushlstring(L,v->u.string.s,v->u.string.len); break;
    case API_LINES:
        lua_createtable(L,v->u.lines.count,0);
        for (k = 0; k < v->u.lines.count; k++) {
            lua_pushlstring(L,v->u.lines.line[k].s,v->u.lines.line[k].len);
            lua_rawseti(L,-2,k+1);
        }
        break;
    case API_POSITION:
        lua_createtable(L,2,0);
        lua_pushinteger(L,v->u.position.row);
        lua_rawseti(L,-2,1);
        lua_pushinteger(L,v->u.position.col);
        lua_rawseti(L,-2,2);
        break;
    default:
        return 0;
    }
    return 1;
    // @end
}

/* The one C function behind every kilo.api.NAME; its upvalue is the
 * function's entry in API. It checks the arguments against the entry, the
 * count and then each type, so that the function itself checks none of
 * them; turns them into the API's values; calls the function; and turns
 * what it returns into a Lua value. A function that failed becomes a Lua
 * error with its name in front: "get_lines: ...". */
static int scriptDispatch(lua_State *L) {
    // @build 09.02 the dispatcher
    // The entry is the light userdata in upvalue 1. Raise an error (with
    // luaL_error(), which puts the script's file and line in front) for a
    // wrong count: "NAME: expected N arguments, got M"; for a wrong type:
    // "NAME: argument I (ARGNAME): expected TYPE, got WHAT". Take the
    // arguments (no memory for lines: an error), call the function, release
    // the arguments. If it failed: "NAME: MESSAGE". Otherwise push its
    // value through scriptPushIn() in a protected call, apiFree() it, and
    // raise the push's error if it had one. Return how many values it gave.
    const ApiFunc *f = lua_touserdata(L,lua_upvalueindex(1));
    ApiValue args[API_MAX_ARGS], ret;
    ApiError err;
    char why[96];
    int n = lua_gettop(L), i, status, nret;

    if (n != f->nargs)
        return luaL_error(L,"%s: expected %d argument%s, got %d",
                          f->name,f->nargs,f->nargs == 1 ? "" : "s",n);
    for (i = 0; i < n; i++)
        if (!scriptCheck(L,i+1,f->args[i],why,sizeof(why)))
            return luaL_error(L,"%s: argument %d (%s): expected %s, got %s",
                              f->name,i+1,f->argnames[i],apiTypeName(f->args[i]),why);
    for (i = 0; i < n; i++) {
        args[i] = scriptTake(L,i+1,f->args[i]);
        if (args[i].type == API_LINES && args[i].u.lines.line == NULL) {
            scriptRelease(args,i+1,1);
            return luaL_error(L,"%s: not enough memory",f->name);
        }
    }
    err.set = 0;
    err.msg[0] = '\0';
    ret = f->fn(args,n,&err);
    scriptRelease(args,n,err.set);
    if (err.set) return luaL_error(L,"%s: %s",f->name,err.msg);
    nret = ret.type != API_NIL;
    lua_pushcfunction(L,scriptPushIn);
    lua_pushlightuserdata(L,&ret);
    status = lua_pcall(L,1,nret,0);
    apiFree(&ret);
    if (status != LUA_OK) return lua_error(L);
    return nret;
    // @end
}

// @end
// @from 09.04
/* ======================== Functions kept for later ======================== */

/* Call fn (through scriptProtected()), the function behind a reference,
 * with arg as its one argument (NULL: none); keep whether it returned a
 * true value. */
struct scriptCallArgs {
    int ref;
    const char *arg;
    int result;
};

static int scriptCallIn(lua_State *L) {
    // @build 09.04 call a function kept as a reference
    // Push the function (lua_rawgeti() of the registry) and arg if there is
    // one; call it for one result; note lua_toboolean() of it.
    struct scriptCallArgs *c = lua_touserdata(L,1);

    lua_rawgeti(L,LUA_REGISTRYINDEX,c->ref);
    if (c->arg) lua_pushstring(L,c->arg);
    lua_call(L,c->arg != NULL,1);
    c->result = lua_toboolean(L,-1);
    return 0;
    // @end
}

/* Call the function behind a reference. Returns 1 if it returned a true
 * value, 0 if not, -1 if it failed (said). */
int scriptCall(int ref, const char *arg) {
    struct scriptCallArgs c;

    c.ref = ref;
    c.arg = arg;
    c.result = 0;
    if (scriptProtected(scriptCallIn,&c) == -1) return -1;
    return c.result;
}

/* Let go of a reference: the function it kept can be collected now. Called
 * by the API's functions, so from inside Lua: never from anywhere else. */
void scriptUnref(int ref) {
    if (S.L) luaL_unref(S.L,LUA_REGISTRYINDEX,ref);
}

/* The Lua on top of the API: kilo's own functions written in Lua, run once
 * at start, as much of Neovim's vim.* is written in Lua on top of its API. */
static const char SCRIPT_LUA[] =
    "local api = kilo.api\n"
    "\n"
    "-- kilo.keymap.set(keys, fn): map a key, or each of a list of keys, to fn.\n"
    "kilo.keymap = {}\n"
    "function kilo.keymap.set(keys, fn)\n"
    "  if type(keys) ~= 'table' then keys = {keys} end\n"
    "  for _, key in ipairs(keys) do api.set_keymap(key, fn) end\n"
    "end\n"
    "\n"
    "-- for row, line in kilo.lines() do ... end: each row of the file, from\n"
    "-- row 0, as the file was when the loop began.\n"
    "function kilo.lines()\n"
    "  local lines, i = api.get_lines(0, api.line_count()), 0\n"
    "  return function()\n"
    "    i = i + 1\n"
    "    if lines[i] then return i - 1, lines[i] end\n"
    "  end\n"
    "end\n";

// @end
// @from 09.08
/* ========================== Scripts that go wrong ========================= */

/* The count hook: Lua calls it every SCRIPT_HOOK_COUNT instructions of a
 * script, in the editor. It looks at the keyboard without waiting: a Ctrl-C
 * among the bytes there stops the script with the error "interrupted".
 * Other keys typed while a script runs are dropped. Once interrupted, the
 * error is raised again at every instruction until the script is back in
 * the editor, so a pcall() in it cannot catch the error and carry on. */
static void scriptHook(lua_State *L, lua_Debug *ar) {
    // @build 09.08 Ctrl-C stops a script
    // Unless already interrupted: while poll() with no wait says standard
    // input has bytes, read() them, and note a 3 among them in
    // S.interrupted. None: return. Then lua_sethook() to a count of 1. Raise
    // "interrupted", with where the script was in front: a hook runs inside
    // the function it stops, so that is level 0 for luaL_where().
    struct pollfd pfd;
    char buf[64];
    ssize_t n, i;

    (void)ar;
    if (!S.interrupted) {
        pfd.fd = STDIN_FILENO;
        pfd.events = POLLIN;
        while (poll(&pfd,1,0) == 1 && (pfd.revents & POLLIN) &&
               (n = read(STDIN_FILENO,buf,sizeof(buf))) > 0)
            for (i = 0; i < n; i++)
                if (buf[i] == 3) S.interrupted = 1;
        if (!S.interrupted) return;
        lua_sethook(L,scriptHook,LUA_MASKCOUNT,1);
    }
    luaL_where(L,0);
    lua_pushliteral(L,"interrupted");
    lua_concat(L,2);
    lua_error(L);
    // @end
}

/* os.exit, in the editor: it would leave with the changes unsaved and no
 * question asked. kilo.api.quit() is the way out. */
static int scriptNoExit(lua_State *L) {
    return luaL_error(L,"os.exit is taken away in the editor: kilo.api.quit() leaves");
}

// @end
// @internal
/* The test aid: ask for an error outside any protected call (raised in
 * scriptProtected() once this returns), the one way to reach the panic
 * function. */
static int scriptTestPanic(lua_State *L) {
    (void)L;
    S.panic = 1;
    return 0;
}

// @end
/* ============================= Starting it up ============================= */

/* Lua's libraries and the table kilo, in a new state (run by scriptNew(),
 * in a protected call: any step may run out of memory). */
static int scriptOpen(lua_State *L) {
    // @build 09.01 the libraries and the table kilo
    // Open Lua's standard libraries. Set the global kilo to a new table, and
    // the global print to scriptPrint().
    luaL_openlibs(L);
    lua_newtable(L);
    lua_setglobal(L,"kilo");
    lua_pushcfunction(L,scriptPrint);
    lua_setglobal(L,"print");
    // @end
    // @build 09.02 kilo.api
    // kilo.api: a table with a function for each entry of API, each the same
    // C function, scriptDispatch(), with its entry as an upvalue (a light
    // userdata), so that it knows which one it is.
    const ApiFunc *f;

    lua_getglobal(L,"kilo");
    lua_newtable(L);
    for (f = API; f->name; f++) {
        lua_pushlightuserdata(L,(void *)f);
        lua_pushcclosure(L,scriptDispatch,1);
        lua_setfield(L,-2,f->name);
    }
    lua_setfield(L,-2,"api");
    // @end
    // @internal
    lua_pushcfunction(L,scriptTestPanic);
    lua_setfield(L,-2,"test_panic");
    // @end
    // @build 09.04 the Lua on top
    // Load SCRIPT_LUA, kilo's functions written in Lua, as the chunk
    // "=kilo.lua", and run it (an error if it does not load).
    if (luaL_loadbuffer(L,SCRIPT_LUA,strlen(SCRIPT_LUA),"=kilo.lua") != LUA_OK)
        return lua_error(L);
    lua_call(L,0,0);
    // @end
    // @build 09.08 no os.exit in the editor
    // Replace os.exit with scriptNoExit().
    // @from 09.09
    // Under kilo -l there is no editor to lose: os.exit stays.
    if (S.screen) {
        lua_getglobal(L,"os");
        lua_pushcfunction(L,scriptNoExit);
        lua_setfield(L,-2,"exit");
    }
    // @else
    // lua_getglobal(L,"os");
    // lua_pushcfunction(L,scriptNoExit);
    // lua_setfield(L,-2,"exit");
    // @end
    // @end
    return 0;
}

/* A new state, with Lua's libraries and kilo's table. Returns 0, or -1
 * when it could not be made (said: the editor goes on without Lua). */
static int scriptNew(void) {
    // @build 09.01 a state for the scripts
    // A new state (luaL_newstate()); none: say "lua: cannot start: not
    // enough memory" and return -1. Have scriptStop() run at exit, and run
    // scriptOpen() through scriptProtected().
    // @from 09.08
    // With lua_newstate() and scriptAlloc(), and scriptPanic() for Lua's
    // panic function.
    // @end
    static const char nomem[] = "lua: cannot start: not enough memory";

    // @from 09.08
    S.L = lua_newstate(scriptAlloc,NULL);
    // @else
    // S.L = luaL_newstate();
    // @end
    if (S.L == NULL) {
        editorMessage(nomem,sizeof(nomem)-1,1);
        return -1;
    }
    lua_atpanic(S.L,scriptPanic);   // @from 09.08
    atexit(scriptStop);
    return scriptProtected(scriptOpen,NULL);
    // @end
}

/* Start Lua for the editor, and run the user's init file: $KILO_INIT when
 * it is set (set and empty: none), else $XDG_CONFIG_HOME/kilo/init.lua,
 * else $HOME/.config/kilo/init.lua. No file there: not a word. An error in
 * it is said in the message line, and the editor goes on. */
void scriptStart(void) {
    // @build 09.01 the init file
    // scriptNew(); if it fails, that is all. Make the path from the first
    // of the three that is set (XDG_CONFIG_HOME only if not empty). If
    // there is none, or it is empty, or access() says no file is there,
    // return. Run it: scriptFileIn() through scriptProtected().
    const char *init = getenv("KILO_INIT"), *xdg = getenv("XDG_CONFIG_HOME");
    const char *home = getenv("HOME");
    char path[4096];

    S.screen = 1;                   // @from 09.09
    if (scriptNew() == -1) return;
    lua_sethook(S.L,scriptHook,LUA_MASKCOUNT,SCRIPT_HOOK_COUNT);  // @from 09.08
    if (init) snprintf(path,sizeof(path),"%s",init);
    else if (xdg && xdg[0]) snprintf(path,sizeof(path),"%s/kilo/init.lua",xdg);
    else if (home) snprintf(path,sizeof(path),"%s/.config/kilo/init.lua",home);
    else return;
    if (path[0] == '\0' || access(path,F_OK) != 0) return;
    scriptProtected(scriptFileIn,path);
    // @end
}

// @from 09.09
/* kilo -l: start Lua with no screen (no keyboard to watch, os.exit kept)
 * and run the script at path. Returns 0, or -1 when it failed (said: kilo.c
 * puts it on standard error). */
int scriptRun(const char *path) {
    // @build 09.09 run a script with no screen
    // scriptNew() (S.screen stays 0), then scriptFileIn() through
    // scriptProtected().
    if (scriptNew() == -1) return -1;
    return scriptProtected(scriptFileIn,(void *)path);
    // @end
}

// @end
/* At exit: put the terminal back first, then close the state. Closing runs
 * the finalizers (__gc) of what scripts left, and Lua runs those with its
 * hooks off: one that never ended would hang kilo here, and with the
 * terminal back in its own mode Ctrl-C is a signal again, which ends it.
 * Nothing is closed while Lua is running (exit() from inside a script):
 * the process is going anyway. */
static void scriptStop(void) {
    // @build 09.01 at exit
    // disableRawMode() on standard input; then lua_close() the state, if
    // there is one and S.depth is 0; and forget it.
    disableRawMode(STDIN_FILENO);
    if (S.L && S.depth == 0) lua_close(S.L);
    S.L = NULL;
    // @end
}
