/*
 * ptree.c - a piece table with its pieces in a balanced tree, so that
 * finding a position takes log2(pieces) steps instead of a walk.
 *
 * The buffers and the pieces are those of pieces.c. What changes is how
 * the pieces are kept: as the nodes of a binary tree, in the order of the
 * text from left to right. A node's left subtree is the text before its
 * piece, its right subtree the text after it, and every node knows how
 * long the text under it is: the lengths of its pieces added up. Those
 * sums are the index. To find byte pos, start at the root: if pos is less
 * than the length on the left, it is in the left subtree; past that and
 * the node's own piece, it is in the right subtree, at pos less both;
 * otherwise it is in this node's piece. One node a level.
 *
 * That is log2(n) steps only while the tree is balanced: pieces added one
 * after another at the end would make it a list leaning right. This is an
 * AVL tree (Adelson-Velsky and Landis, 1962). Each node knows its height,
 * and the rule is that the heights of its two subtrees differ by at most
 * one. Adding or removing a node can break the rule only on the path down
 * to it, and only by one, so on the way back up each node on that path is
 * mended where it is broken, by a rotation or two. A rotation turns three
 * links round: it keeps the order of the text and moves height from the
 * heavy side to the light one. An AVL tree of n nodes is never more than
 * 1.44 log2(n) high.
 *
 * Why AVL, of the balanced trees: it has one rule, about heights, that can
 * be checked at any node by looking at its children, and one repair, the
 * rotation, made the same way after an insert and after a removal. A
 * red-black tree (Visual Studio Code's piece tree is one) is balanced less
 * strictly and rotates less often, but restoring its rules about colours
 * after a removal takes a page of cases; a treap or a splay tree is
 * balanced only on average, or over many operations, not at every step.
 *
 * An edit is then: make sure there is a boundary between pieces where it
 * starts (and where it ends, for an erase), cutting the piece there in
 * two; then add a node for the new piece, or remove the nodes between the
 * boundaries. Typing on at the end of what was just typed makes that piece
 * longer, as in pieces.c.
 *
 * DS_STATS=1 prints "stats: piece tree: bytes mapped M, bytes loaded L,
 * bytes added A, inserts I, erases E, pieces P, nodes visited V, rotations
 * R, height H": as pieces.c's, with the nodes looked at on the way down,
 * the rotations made, and how high the tree is at the end.
 *
 * DS_TRACE=1 prints each rotation as it is made, and each call with the
 * whole tree after it: a node is "(left piece right)", an empty subtree
 * ".", and a piece its buffer, start+length and bytes:
 *
 *   trace: piece tree: rotate left at orig 0+1
 *   trace: piece tree: insert 1 "X": visited 4 | ((. orig 0+1 "a" .) add 0+1 "X" (. orig 1+2 "bc" .))
 */
#include <stdlib.h>
#include <string.h>

#include "ds.h"
#include "ptree.h"

typedef struct Node {
    struct Node *left, *right;
    int          height;         /* of the subtree under it, itself included: a leaf is 1 */
    size_t       sum;            /* the length of the text in that subtree */
    Span         span;           /* its piece */
} Node;

typedef struct {
    Text    text;
    Buffers b;
    Node   *root;
} PTree;

static struct {
    long mapped, loaded, added, inserts, erases, pieces, visited, rotations;
} st;

static PTree *opened;            /* for the height DS_STATS prints at the end */

static int height(Node *n)
{
    return n != NULL ? n->height : 0;
}

static size_t sum(Node *n)
{
    return n != NULL ? n->sum : 0;
}

static void print_stats(void)
{
    ds_stats_print("piece tree", "bytes mapped %ld, bytes loaded %ld, bytes added %ld, inserts %ld, erases %ld, "
                   "pieces %ld, nodes visited %ld, rotations %ld, height %d", st.mapped, st.loaded, st.added,
                   st.inserts, st.erases, st.pieces, st.visited, st.rotations,
                   opened != NULL ? height(opened->root) : 0);
}

static const char *buf_name(Span s)
{
    return s.buf == ORIG ? "orig" : "add";
}

static void trace_tree(PTree *p, Node *n)
{
    if (n == NULL) {
        text_trace(".");
        return;
    }
    text_trace("(");
    trace_tree(p, n->left);
    text_trace(" %s %zu+%zu ", buf_name(n->span), n->span.start, n->span.len);
    text_trace_bytes(span_bytes(&p->b, n->span), n->span.len);
    text_trace(" ");
    trace_tree(p, n->right);
    text_trace(")");
}

static void trace(PTree *p, long visited)
{
    text_trace(": visited %ld | ", visited);
    trace_tree(p, p->root);
    text_trace("\n");
}

static void trace_rotation(const char *dir, Node *n)
{
    if (text_tracing())
        text_trace("trace: piece tree: rotate %s at %s %zu+%zu\n", dir, buf_name(n->span), n->span.start,
                   n->span.len);
}

static Node *new_node(Span s)
{
    Node *n = xmalloc(sizeof *n);
    n->left = n->right = NULL;
    n->height = 1;
    n->sum = s.len;
    n->span = s;
    st.pieces++;
    return n;
}

/* A node's height and sum, worked out again from its children's. */
static void update(Node *n)
{
    int l = height(n->left), r = height(n->right);
    n->height = 1 + (l > r ? l : r);
    n->sum = sum(n->left) + n->span.len + sum(n->right);
}

// @internal
/* A test aid: with DS_CHECK=1, the whole tree is checked after every
 * change (the AVL rule, every height and sum, no empty piece), and the
 * first thing wrong stops the program. */
static int checking = -1;

static int check_node(Node *n, size_t *total)
{
    if (n == NULL) {
        *total = 0;
        return 0;
    }
    size_t l, r;
    int hl = check_node(n->left, &l), hr = check_node(n->right, &r);
    if (n->span.len == 0)
        die("piece tree: an empty piece");
    if (hl - hr > 1 || hr - hl > 1)
        die("piece tree: subtrees of heights %d and %d under one node", hl, hr);
    if (n->height != 1 + (hl > hr ? hl : hr) || n->sum != l + n->span.len + r)
        die("piece tree: a node with the wrong height or sum");
    *total = n->sum;
    return n->height;
}

static void check_tree(PTree *p)
{
    if (checking < 0) {
        const char *s = getenv("DS_CHECK");
        checking = s != NULL && *s != '\0' && strcmp(s, "0") != 0;
    }
    size_t total;
    if (checking && (check_node(p->root, &total), total != p->text.len))
        die("piece tree: the pieces add up to %zu bytes, the text is %zu", total, p->text.len);
}
// @end

/* Rotate right at n: its left child l takes its place, and n becomes l's
 * right child. l's right subtree, the text between l's piece and n's,
 * moves across to be n's left. */
static Node *rotate_right(Node *n)
{
    // @build 03.05 rotate right: the left child up, the node down to its right
    Node *l = n->left;
    trace_rotation("right", n);
    n->left = l->right;
    l->right = n;
    update(n);
    update(l);
    st.rotations++;
    return l;
    // @end
}

/* Rotate left at n: the mirror image. */
static Node *rotate_left(Node *n)
{
    // @build 03.05 rotate left: the right child up, the node down to its left
    Node *r = n->right;
    trace_rotation("left", n);
    n->right = r->left;
    r->left = n;
    update(n);
    update(r);
    st.rotations++;
    return r;
    // @end
}

/* n, its subtrees balanced but their heights now maybe two apart, made to
 * keep the rule again: the subtree of n's new root. When the heavy side's
 * own heavy side is its inner one, one rotation would only move the
 * problem across, so that child is rotated first: two rotations. */
static Node *balance(Node *n)
{
    // @build 03.05 balance: a rotation, or two, where the heights are two apart
    update(n);
    int b = height(n->left) - height(n->right);
    if (b > 1) {
        if (height(n->left->left) < height(n->left->right))
            n->left = rotate_left(n->left);
        return rotate_right(n);
    }
    if (b < -1) {
        if (height(n->right->right) < height(n->right->left))
            n->right = rotate_right(n->right);
        return rotate_left(n);
    }
    return n;
    // @end
}

/* The node whose piece holds byte pos of the subtree n (pos is less than
 * its length), and where in the piece: *off. */
static Node *find(Node *n, size_t pos, size_t *off)
{
    // @build 03.05 find a position: down the tree by the lengths on the left
    while (n != NULL) {
        st.visited++;
        size_t l = sum(n->left);
        if (pos < l) {
            n = n->left;
        } else if (pos < l + n->span.len) {
            *off = pos - l;
            return n;
        } else {
            pos -= l + n->span.len;
            n = n->right;
        }
    }
    return NULL;
    // @end
}

/* Add the node x so that its piece starts at byte pos of the subtree n,
 * where pos is between two pieces (or at either end). The subtree's new
 * root comes back, balanced. */
static Node *insert_at(Node *n, size_t pos, Node *x)
{
    // @build 03.05 add a node at a position, balancing on the way back up
    if (n == NULL)
        return x;
    st.visited++;
    size_t l = sum(n->left);
    if (pos <= l)
        n->left = insert_at(n->left, pos, x);
    else
        n->right = insert_at(n->right, pos - l - n->span.len, x);
    return balance(n);
    // @end
}

/* The leftmost node of n, taken out of it into *min: the subtree's new
 * root, balanced. */
static Node *remove_min(Node *n, Node **min)
{
    st.visited++;
    if (n->left == NULL) {
        *min = n;
        return n->right;
    }
    n->left = remove_min(n->left, min);
    return balance(n);
}

/* Take out, and free, the node whose piece starts at byte pos of the
 * subtree n. With two children it is replaced by the first node after it,
 * the leftmost of its right subtree. The subtree's new root comes back,
 * balanced. */
static Node *remove_at(Node *n, size_t pos)
{
    // @build 03.05 remove the node at a position, balancing on the way back up
    st.visited++;
    size_t l = sum(n->left);
    if (pos < l) {
        n->left = remove_at(n->left, pos);
    } else if (pos > l) {
        n->right = remove_at(n->right, pos - l - n->span.len);
    } else {
        Node *left = n->left, *right = n->right, *next;
        free(n);
        st.pieces--;
        if (left == NULL)
            return right;
        if (right == NULL)
            return left;
        right = remove_min(right, &next);
        next->left = left;
        next->right = right;
        n = next;
    }
    return balance(n);
    // @end
}

/* Make the piece of the node starting at byte pos of the subtree n len
 * bytes long, and the sums on the path down to it right again. */
static void set_len(Node *n, size_t pos, size_t len)
{
    // @build 03.05 a piece made shorter or longer, and the sums above it
    st.visited++;
    size_t l = sum(n->left);
    if (pos < l)
        set_len(n->left, pos, len);
    else if (pos > l)
        set_len(n->right, pos - l - n->span.len, len);
    else
        n->span.len = len;
    n->sum = sum(n->left) + n->span.len + sum(n->right);
    // @end
}

/* Make byte pos a boundary between pieces: the piece it is inside is cut
 * short there, and the rest of it is a new node just after. */
static void cut(PTree *p, size_t pos)
{
    // @build 03.05 cut the piece pos is inside in two
    size_t off = 0;
    if (pos >= p->text.len)
        return;
    Node *n = find(p->root, pos, &off);
    if (off == 0)
        return;
    Span rest = {n->span.buf, n->span.start + off, n->span.len - off};
    set_len(p->root, pos - off, off);
    p->root = insert_at(p->root, pos, new_node(rest));
    // @end
}

/* Insert: the bytes go on the end of the add buffer, and a node for them
 * goes in at pos. */
static void ptree_insert(Text *t, size_t pos, const char *s, size_t n)
{
    // @build 03.05 insert: cut at pos, and a node for the new piece there
    PTree *p = (PTree *)t;
    long visited = st.visited;
    size_t start = buffers_add(&p->b, s, n), off = 0;
    Node *before = pos > 0 ? find(p->root, pos - 1, &off) : NULL;
    if (before != NULL && off + 1 == before->span.len && before->span.buf == ADD &&
        before->span.start + before->span.len == start) {
        set_len(p->root, pos - before->span.len, before->span.len + n);   /* typing on */
    } else {
        cut(p, pos);
        p->root = insert_at(p->root, pos, new_node((Span){ADD, start, n}));
    }
    t->len += n;
    st.added += (long)n;
    st.inserts++;
    if (text_tracing()) {
        text_trace("trace: piece tree: insert %zu ", pos);
        text_trace_bytes(s, n);
        trace(p, st.visited - visited);
    }
    // @internal
    check_tree(p);
    // @end
    // @end
}

/* Erase: boundaries at both ends of the bytes, and every node between
 * them taken out. */
static void ptree_erase(Text *t, size_t pos, size_t n)
{
    // @build 03.05 erase: cut at both ends, and remove the nodes between
    PTree *p = (PTree *)t;
    long visited = st.visited;
    cut(p, pos);
    cut(p, pos + n);
    size_t left = n, off = 0;
    while (left > 0) {
        Node *x = find(p->root, pos, &off);
        left -= x->span.len;
        p->root = remove_at(p->root, pos);
    }
    t->len -= n;
    st.erases++;
    if (text_tracing()) {
        text_trace("trace: piece tree: erase %zu %zu", pos, n);
        trace(p, st.visited - visited);
    }
    // @internal
    check_tree(p);
    // @end
    // @end
}

/* Copy the bytes [from, to) of the subtree n into out, where out is the
 * place for byte from: the parts of the left subtree, of the node's own
 * piece, and of the right subtree that are in the range. */
static void copy(PTree *p, Node *n, size_t from, size_t to, char *out)
{
    // @build 03.05 read: the subtrees and pieces the bytes are in, in order
    if (n == NULL || from >= to)
        return;
    st.visited++;
    size_t l = sum(n->left), r = l + n->span.len;
    if (from < l)
        copy(p, n->left, from, to < l ? to : l, out);
    if (from < r && to > l) {
        size_t a = from > l ? from : l, b = to < r ? to : r;
        memcpy(out + (a - from), span_bytes(&p->b, n->span) + (a - l), b - a);
    }
    if (to > r)
        copy(p, n->right, from > r ? from - r : 0, to - r, out + (from > r ? 0 : r - from));
    // @end
}

static void ptree_read(Text *t, size_t pos, char *buf, size_t n)
{
    PTree *p = (PTree *)t;
    copy(p, p->root, pos, pos + n, buf);
}

static int write_node(PTree *p, Node *n, FILE *out)
{
    if (n == NULL)
        return 0;
    if (write_node(p, n->left, out) < 0 ||
        fwrite(span_bytes(&p->b, n->span), 1, n->span.len, out) != n->span.len)
        return -1;
    return write_node(p, n->right, out);
}

static int ptree_write(Text *t, FILE *out)
{
    PTree *p = (PTree *)t;
    return write_node(p, p->root, out);
}

static void free_node(Node *n)
{
    if (n == NULL)
        return;
    free_node(n->left);
    free_node(n->right);
    free(n);
    st.pieces--;
}

static void ptree_free(Text *t)
{
    PTree *p = (PTree *)t;
    free_node(p->root);
    buffers_free(&p->b);
    if (opened == p)
        opened = NULL;
    free(p);
}

static const TextOps ptree_ops = {"piece tree", ptree_insert, ptree_erase, ptree_read, ptree_write, ptree_free};

Text *ptree_open(const char *path)
{
    // @build 03.05 open: the file mapped, as the one node of the tree
    PTree *p = xmalloc(sizeof *p);
    p->text.ops = &ptree_ops;
    buffers_open(&p->b, path, &st.mapped, &st.loaded);
    p->root = p->b.origlen > 0 ? new_node((Span){ORIG, 0, p->b.origlen}) : NULL;
    p->text.len = p->b.origlen;
    opened = p;
    ds_stats_at_exit(print_stats);
    return &p->text;
    // @end
}
