/*
 * undo.c - undo and redo: two stacks of edits.
 *
 * Every change the editor makes to the text is noted as an Edit: an
 * insert or an erase, where, and the bytes themselves (an erase keeps the
 * bytes it took out, so they can be put back). The edits made go on one
 * stack, the last on top. Undo takes the top one off, does its opposite
 * to the text (what was inserted is erased, what was erased is inserted
 * again) and puts it on the other stack; redo takes the top one off that
 * stack, does it again, and puts it back on the first. A new edit empties
 * the redo stack: what was undone can no longer be redone, because the
 * text it was made to is gone.
 *
 * The stacks are growable arrays (01.01): a push and a pop at the end
 * cost the same however deep the stack is. Undo works through text.h, so
 * it works on whichever structure holds the text.
 *
 * Typing is one edit, not one a key: a typed byte that goes where the
 * last typed one ended is added to that edit, and Backspace pressed again
 * and again gathers what it takes into one erase. Anything else (moving
 * the cursor, a paste, an undo) ends the edit being typed. Backspace takes
 * the bytes from the end backwards, so an erase that is typed keeps them
 * in reverse order, each new one pushed on the end, and turns them round
 * once, when it is undone.
 *
 * DS_STATS=1 prints "stats: undo: edits E, undos U, redos R, bytes kept
 * B": the edits noted, how many times each way, and the bytes the two
 * stacks hold at the end.
 *
 * DS_TRACE=1 prints each call, and how deep the stacks are after it:
 *
 *   trace: undo: note insert 3 "abc": a new edit | done 1, undone 0
 *   trace: undo: undo insert 3 "abc": erased | done 0, undone 1
 */
#include <stdlib.h>
#include <string.h>

#include "undo.h"

static struct {
    long edits, undos, redos, bytes;
} st;

static void print_stats(void)
{
    ds_stats_print("undo", "edits %ld, undos %ld, redos %ld, bytes kept %ld", st.edits, st.undos, st.redos,
                   st.bytes);
}

static void trace(Undo *u, const char *what, Edit *e, const char *how)
{
    if (!text_tracing())
        return;
    text_trace("trace: undo: %s %s %zu ", what, e->erase ? "erase" : "insert", e->pos);
    if (e->backwards) {                 /* show it the right way round */
        char *s = xmalloc(e->bytes.len + 1);
        for (size_t i = 0; i < e->bytes.len; i++)
            s[i] = e->bytes.data[e->bytes.len - 1 - i];
        text_trace_bytes(s, e->bytes.len);
        free(s);
    } else {
        text_trace_bytes(e->bytes.data, e->bytes.len);
    }
    text_trace(": %s | done %zu, undone %zu\n", how, u->done.len, u->undone.len);
}

static void push_bytes(Edit *e, const char *s, size_t n, int backwards)
{
    for (size_t i = 0; i < n; i++)
        *(char *)array_push(&e->bytes) = backwards ? s[n - 1 - i] : s[i];
    st.bytes += (long)n;
}

/* An edit's bytes in their own order again. */
static void straighten(Edit *e)
{
    if (!e->backwards)
        return;
    for (size_t i = 0, j = e->bytes.len; i + 1 < j; i++, j--) {
        char c = e->bytes.data[i];
        e->bytes.data[i] = e->bytes.data[j - 1];
        e->bytes.data[j - 1] = c;
    }
    e->backwards = 0;
}

static void forget(Edit *e)
{
    st.bytes -= (long)e->bytes.len;
    array_free(&e->bytes);
}

void undo_init(Undo *u)
{
    // @build 03.03 two empty stacks
    array_init(&u->done, sizeof(Edit));
    array_init(&u->undone, sizeof(Edit));
    u->typing = 0;
    ds_stats_at_exit(print_stats);
    // @end
}

void undo_note(Undo *u, int erase, size_t pos, const char *s, size_t n, int typed)
{
    // @build 03.03 note an edit: more of the one being typed, or a new one on top
    while (u->undone.len > 0)           /* a new edit: what was undone is gone for good */
        forget(array_pop(&u->undone));
    Edit *top = u->done.len > 0 ? array_at(&u->done, u->done.len - 1) : NULL;
    if (typed && u->typing && top != NULL && top->erase == erase &&
        (erase ? pos + n == top->pos : top->pos + top->bytes.len == pos)) {
        push_bytes(top, s, n, erase);   /* Backspace: these bytes come before the edit's */
        if (erase)
            top->pos = pos;
        trace(u, "note", top, "more of the same edit");
    } else {
        Edit *e = array_push(&u->done);
        e->erase = erase;
        e->pos = pos;
        e->backwards = typed && erase;
        array_init(&e->bytes, 1);
        push_bytes(e, s, n, e->backwards);
        st.edits++;
        trace(u, "note", e, "a new edit");
    }
    u->typing = typed;
    // @end
}

void undo_break(Undo *u)
{
    u->typing = 0;
}

int undo_undo(Undo *u, Text *t, Change *c)
{
    // @build 03.03 undo: the top edit off, its opposite done, onto the other stack
    u->typing = 0;
    Edit *e = array_pop(&u->done);
    if (e == NULL)
        return 0;
    straighten(e);
    if (e->erase)
        text_insert(t, e->pos, e->bytes.data, e->bytes.len);
    else
        text_erase(t, e->pos, e->bytes.len);
    Edit *moved = array_push(&u->undone);
    *moved = *e;
    c->erased = !moved->erase;
    c->pos = moved->pos;
    c->bytes = moved->bytes.data;
    c->n = moved->bytes.len;
    c->cursor = moved->erase ? moved->pos + moved->bytes.len : moved->pos;
    st.undos++;
    trace(u, "undo", moved, moved->erase ? "inserted again" : "erased");
    return 1;
    // @end
}

int undo_redo(Undo *u, Text *t, Change *c)
{
    // @build 03.03 redo: the top undone edit off, done again, back onto the first stack
    u->typing = 0;
    Edit *e = array_pop(&u->undone);
    if (e == NULL)
        return 0;
    if (e->erase)
        text_erase(t, e->pos, e->bytes.len);
    else
        text_insert(t, e->pos, e->bytes.data, e->bytes.len);
    Edit *moved = array_push(&u->done);
    *moved = *e;
    c->erased = moved->erase;
    c->pos = moved->pos;
    c->bytes = moved->bytes.data;
    c->n = moved->bytes.len;
    c->cursor = moved->erase ? moved->pos : moved->pos + moved->bytes.len;
    st.redos++;
    trace(u, "redo", moved, moved->erase ? "erased again" : "inserted again");
    return 1;
    // @end
}

void undo_free(Undo *u)
{
    while (u->done.len > 0)
        forget(array_pop(&u->done));
    while (u->undone.len > 0)
        forget(array_pop(&u->undone));
    array_free(&u->done);
    array_free(&u->undone);
}
