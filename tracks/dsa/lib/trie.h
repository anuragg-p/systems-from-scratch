/*
 * trie.h - a trie: a set of words kept a letter at a time down a tree
 * (lib/trie.c). Only the letters a-z can be stored.
 */
#ifndef TRIE_H
#define TRIE_H

#include "ds.h"

#define TRIE_LETTERS 26

/* One node: the letters on the path from the root to it. child[c] is the
 * node for the letter 'a' + c coming next, or 0 when no word goes on that
 * way (node 0 is the root, which is no one's child). */
typedef struct {
    int32_t child[TRIE_LETTERS];
    uint8_t word;        /* 1 when a word ends here */
} TrieNode;

/* The nodes in one growable array, node 0 the root; children are indexes
 * into it, which stay good when the array moves. */
typedef struct {
    Array  nodes;        /* TrieNode */
    size_t words;        /* different words added */
} Trie;

/* What trie_each and trie_near call for each word they find: the word is
 * the len bytes at w, good only until the call returns. */
typedef void (*TrieFn)(const char *w, size_t len, void *ctx);

void   trie_init(Trie *t);
int    trie_add(Trie *t, const char *w, size_t len);    /* 1 if new, 0 if there, -1 if not a-z */
int    trie_has(Trie *t, const char *w, size_t len);    /* 1 if w is one of the words */
long   trie_find(Trie *t, const char *prefix, size_t len); /* prefix's node, or -1 */
/* Every word below node (whose path is prefix), node's own first, a to z. */
void   trie_each(Trie *t, long node, const char *prefix, size_t len, TrieFn fn, void *ctx);
size_t trie_bytes(const Trie *t);                       /* the nodes' block, room to spare too */
void   trie_free(Trie *t);

// @from 05.03
/* Every word within maxd edits of w (lib/edit.c): fn gets each one, a to
 * z, with its distance. */
typedef void (*TrieNearFn)(const char *word, size_t len, int dist, void *ctx);
void   trie_near(Trie *t, const char *w, size_t len, int maxd, TrieNearFn fn, void *ctx);
// @end

#endif
