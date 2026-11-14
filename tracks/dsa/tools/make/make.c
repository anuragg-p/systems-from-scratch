/*
 * make - build what a makefile says, each thing after what it needs.
 *
 *   make [-n] [-s] [-f FILE] [option ...] [NAME=VALUE ...] [TARGET ...]
 *
 * make reads FILE (makefile or Makefile without -f) into a graph: each
 * target a node, needing its prerequisites (read.c). Then it builds each
 * TARGET it is given, or the makefile's first target without one: first
 * everything the target needs, then the target itself, by running its
 * recipe, a line at a time, each line with /bin/sh -c.
 * A target is made only when it is out of date: when it is not a file,   @from 07.03
 * or something it needs is newer than it is or has just been made.        @from 07.03
 *
 *   -n          print the commands that would run, and run none
 *   -s          run the commands without printing them
 *   -f FILE     read FILE
 *   -j N        run up to N recipes at once (with --algo=queue, which it    @from 07.04
 *               picks)                                                      @from 07.04
 *   NAME=VALUE  set a variable, over what the makefile sets it to
 *   --graph     print the graph, each target and what it needs, and stop
 *   --order     print the order the targets would be built in, and stop   @from 07.03
 *   --algo=NAME   how make goes over the graph:                           @from 07.03
 *     recurse   a plain recursion: everything a target needs, then the    @from 07.03
 *               target, by every path there is to it, made every time     @from 07.03
 *     topo      once over a topological order, each target once, and      @from 07.03
 *               only if it is out of date (the default)                   @from 07.03
 *     queue     a queue of targets whose prerequisites are all finished   @from 07.04
 *               (Kahn's algorithm): with -j N, N of them at a time        @from 07.04
 *
 * DS_STATS=1 prints "stats: make: recipes run R, commands C, files checked
 * F, most at once M": the recipes run, the command lines run (or printed,
 * with -n), the files whose time was read, and the most commands that ran
 * at the same time. DS_TRACE=1 prints, on stderr, each step: the graph's
 * own (depgraph.h), and make's, "trace: EVENT NAME [: WHY]":
 *   run     a target's recipe runs
 *   check   whether a target is out of date, and why                       @from 07.03
 *   ready   everything the target needs is finished: it joins the queue    @from 07.04
 *   start   it comes off the queue, and its recipe starts                  @from 07.04
 *   skip    it comes off the queue up to date: nothing to run              @from 07.04
 *   finish  its recipe is done                                             @from 07.04
 */
#include <dirent.h>
#include <errno.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#include "make.h"
#include "readyq.h"     // @from 07.04

static Graph g;
static int dry_run, silent;
static long recipes_run, commands, files_checked, most_at_once;
static long running;            /* commands started and not yet waited for */

static void print_stats(void)
{
    ds_stats_print("make", "recipes run %ld, commands %ld, files checked %ld, most at once %ld",
                   recipes_run, commands, files_checked, most_at_once);
}

static int tracing = -1;

/* DS_TRACE=1: "trace: " and the step, on stderr. */
static void trace(const char *fmt, ...)
{
    if (tracing < 0) {
        const char *s = getenv("DS_TRACE");
        tracing = s != NULL && *s != '\0' && strcmp(s, "0") != 0;
    }
    if (!tracing)
        return;
    va_list ap;
    va_start(ap, fmt);
    fputs("trace: ", stderr);
    vfprintf(stderr, fmt, ap);
    fputc('\n', stderr);
    va_end(ap);
}

static const char *name(long n)
{
    return graph_at(&g, n)->name;
}

/* Stop the build: wait for the commands still running, as make does, then
 * say why and exit with status 2. */
static _Noreturn void stop(const char *fmt, ...)
{
    char msg[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(msg, sizeof msg, fmt, ap);
    va_end(ap);
    fflush(stdout);
    fprintf(stderr, "make: %s\n", msg);
    if (running > 0)
        fprintf(stderr, "make: *** Waiting for unfinished jobs....\n");
    while (running > 0 && wait(NULL) > 0)
        running--;
    exit(2);
}

/* ------------------------------------------------------------ files */

#ifdef __APPLE__
#define MTIME(sb) ((sb).st_mtimespec)
#else
#define MTIME(sb) ((sb).st_mtim)
#endif

/* Whether n is a file, reading its time once (again after its recipe has
 * run, which may have changed it). */
static int file_time(long n)
{
    Target *t = target(&g, n);
    if (!t->checked) {
        struct stat sb;
        files_checked++;
        t->exists = stat(name(n), &sb) == 0;
        if (t->exists)
            t->mtime = MTIME(sb);
        t->checked = 1;
    }
    return t->exists;
}

/* No file n, and no rule to make one: fatal. from: the target that needs
 * it, or -1 for one make was asked to build. */
static _Noreturn void no_rule(long n, long from)
{
    if (from < 0)
        stop("*** No rule to make target '%s'.  Stop.", name(n));
    stop("*** No rule to make target '%s', needed by '%s'.  Stop.", name(n), name(from));
}

// @from 07.03
static int newer(struct timespec a, struct timespec b)
{
    return a.tv_sec > b.tv_sec || (a.tv_sec == b.tv_sec && a.tv_nsec > b.tv_nsec);
}
// @end

/* ------------------------------------------------------------ commands */

/* Line i of n's recipe, its variables expanded, ready for the shell: the
 * blanks and any @ in front taken off (*quiet says if there was an @).
 * NULL for a line with nothing left. */
static char *command_line(long n, size_t i, int *quiet)
{
    Recipe *r = target(&g, n)->recipe;
    char *x = expand(*(char **)array_at(&r->lines, i), r->file, r->line);
    char *p = x;
    *quiet = 0;
    for (;; p++) {
        if (*p == '@')
            *quiet = 1;
        else if (*p == '-' || *p == '+')
            stop("%s:%ld: '%c' in front of a command is not supported (target '%s')", r->file, r->line,
                 *p, name(n));
        else if (*p != ' ' && *p != '\t')
            break;
    }
    if (*p == '\0') {
        free(x);
        return NULL;
    }
    memmove(x, p, strlen(p) + 1);
    return x;
}

/* Print cmd, unless it had an @ or make has -s (with -n, always), and
 * start it: /bin/sh -c cmd. Returns the shell's pid, or 0 with -n. */
static pid_t start_command(const char *cmd, int quiet)
{
    commands++;
    if (dry_run || (!quiet && !silent))
        printf("%s\n", cmd);
    if (dry_run)
        return 0;
    fflush(stdout);
    fflush(stderr);
    pid_t pid = fork();
    if (pid < 0)
        stop("cannot start a shell: %s", strerror(errno));
    if (pid == 0) {
        execl("/bin/sh", "sh", "-c", cmd, (char *)NULL);
        fprintf(stderr, "make: /bin/sh: %s\n", strerror(errno));
        _exit(127);
    }
    if (++running > most_at_once)
        most_at_once = running;
    return pid;
}

/* A command of n's recipe has ended with status: stop the build unless it
 * succeeded. */
static void check_status(long n, int status)
{
    if (WIFEXITED(status) && WEXITSTATUS(status) == 0)
        return;
    if (WIFEXITED(status))
        stop("*** [%s] Error %d", name(n), WEXITSTATUS(status));
    stop("*** [%s] killed by signal %d", name(n), WTERMSIG(status));
}

/* Run n's recipe: each line in turn, each finished before the next. */
static void run_recipe(long n)
{
    Target *t = target(&g, n);
    trace("run %s", name(n));
    recipes_run++;
    t->ran = 1;
    for (size_t i = 0; i < t->recipe->lines.len; i++) {
        int quiet;
        char *cmd = command_line(n, i, &quiet);
        if (cmd == NULL)
            continue;
        pid_t pid = start_command(cmd, quiet);
        free(cmd);
        if (pid > 0) {
            int status;
            while (waitpid(pid, &status, 0) < 0 && errno == EINTR)
                ;
            running--;
            check_status(n, status);
        }
    }
}

/* ------------------------------------------------------------ the graph */

/* --graph: each node, and the nodes it needs, in the order the makefile
 * named them; then the phony ones. The output is itself a makefile, with
 * the recipes left out. */
static void print_graph(void)
{
    // @build 07.01 print the graph: each node, and the nodes it needs
    for (size_t i = 0; i < graph_len(&g); i++) {
        Node *node = graph_at(&g, (long)i);
        printf("%s:", node->name);
        for (size_t j = 0; j < node->needs.len; j++)
            printf(" %s", name(*(long *)array_at(&node->needs, j)));
        printf("\n");
    }
    int phony = 0;
    for (size_t i = 0; i < graph_len(&g); i++) {
        if (target(&g, (long)i)->phony)
            printf("%s %s", phony++ ? "" : ".PHONY:", name((long)i));
    }
    if (phony)
        printf("\n");
    // @end
}

/* ------------------------------------------------------------ building */

/* --algo=recurse: what the walk does at each node it comes to, after
 * everything the node needs: a target with a recipe has it run, every
 * time the walk comes to it; a file with no rule must be there. */
static void make_node(Graph *graph, long n, long from, void *ctx)
{
    // @build 07.01 at each node the walk comes to: run its recipe
    Target *t = target(graph, n);
    if (!t->rule) {
        if (!t->phony && !file_time(n))
            no_rule(n, from);
        return;
    }
    if (t->recipe != NULL)
        run_recipe(n);
    // @end
}

// @from 07.02
/* A cycle: the targets that form it, each needing the next. Fatal: there
 * is no order in which to build them. */
static void report_cycle(const Array *cycle)
{
    // @build 07.02 report the cycle: each target on it, then the first again
    fflush(stdout);
    fprintf(stderr, "make: dependency cycle:");
    for (size_t i = 0; i < cycle->len; i++)
        fprintf(stderr, "%s %s", i ? " ->" : "", name(*(long *)array_at(cycle, i)));
    fprintf(stderr, "\n");
    exit(2);
    // @end
}
// @end

// @from 07.03
/* Must n be made? Everything it needs has been dealt with already, made
 * or found up to date. n must be made if it is phony, or not a file, or if
 * something it needs was made in this run or is newer than it is. A file
 * with no rule is never made: it must be there. */
static int out_of_date(long n)
{
    // @build 07.03 out of date: phony, missing, or older than something it needs
    Node *node = graph_at(&g, n);
    Target *t = target(&g, n);
    if (t->phony) {
        trace("check %s: phony", node->name);
        return 1;
    }
    if (!t->rule) {
        if (!file_time(n))
            no_rule(n, node->from);
        trace("check %s: a file with no rule", node->name);
        return 0;
    }
    if (!file_time(n)) {
        trace("check %s: missing", node->name);
        return 1;
    }
    for (size_t i = 0; i < node->needs.len; i++) {
        long m = *(long *)array_at(&node->needs, i);
        Target *u = target(&g, m);
        if (u->remade) {
            trace("check %s: %s was made", node->name, name(m));
            return 1;
        }
        if (file_time(m) && newer(u->mtime, t->mtime)) {
            trace("check %s: %s is newer", node->name, name(m));
            return 1;
        }
    }
    trace("check %s: up to date", node->name);
    return 0;
    // @end
}

/* n has been made: everything that needs it must be made too, and its
 * file's time read again. */
static void made(long n)
{
    Target *t = target(&g, n);
    t->remade = 1;
    t->checked = 0;
}

/* --algo=topo: once along order, in which each target comes after
 * everything it needs, making each target that is out of date. */
static void build_in_order(const Array *order)
{
    // @build 07.03 build in topological order: each target once, if it is out of date
    for (size_t i = 0; i < order->len; i++) {
        long n = *(long *)array_at(order, i);
        if (!out_of_date(n))
            continue;
        if (target(&g, n)->recipe != NULL)
            run_recipe(n);
        made(n);
    }
    // @end
}
// @end

// @from 07.04
/* A recipe running under -j: which target, which of its lines, and the
 * shell running that line. */
typedef struct {
    long   node;
    size_t line;
    pid_t  pid;
} Job;

/* Start the next line of j's recipe: 1, or 0 when there is none left (or
 * with -n, when they have all been printed). */
static int next_command(Job *j)
{
    Target *t = target(&g, j->node);
    if (t->recipe == NULL)
        return 0;
    while (j->line < t->recipe->lines.len) {
        int quiet;
        char *cmd = command_line(j->node, j->line++, &quiet);
        if (cmd == NULL)
            continue;
        j->pid = start_command(cmd, quiet);
        free(cmd);
        if (j->pid > 0)
            return 1;
    }
    return 0;
}

/* n is finished: one thing fewer for each target that needs it to wait
 * for, and a target with nothing left to wait for is ready. */
static void finished(ReadyQueue *q, long n)
{
    // @build 07.04 a target is finished: count it off what needs it, queue what is ready
    Node *node = graph_at(&g, n);
    trace("finish %s", node->name);
    for (size_t i = 0; i < node->needed_by.len; i++) {
        long d = *(long *)array_at(&node->needed_by, i);
        Node *dep = graph_at(&g, d);
        if (dep->state != NODE_DONE)
            continue;           /* the search did not reach it: not wanted */
        if (--dep->waiting == 0) {
            trace("ready %s", dep->name);
            readyq_push(q, d);
        }
    }
    // @end
}

/* --algo=queue: Kahn's algorithm. Each target of order waits for as many
 * targets as it needs; one that needs none is ready, and goes on the
 * queue. Up to jobs recipes run at once, each of a target taken off the
 * queue; as each one finishes, what needs it waits for one fewer. */
static void build_queue(const Array *order, long jobs)
{
    // @build 07.04 Kahn: a queue of ready targets, up to jobs of them running at once
    ReadyQueue q;
    readyq_init(&q);
    for (size_t i = 0; i < order->len; i++) {
        long n = *(long *)array_at(order, i);
        Node *node = graph_at(&g, n);
        node->waiting = (long)node->needs.len;
        if (node->waiting == 0) {
            trace("ready %s", node->name);
            readyq_push(&q, n);
        }
    }
    Job *job = xmalloc((size_t)jobs * sizeof *job);
    long njobs = 0;
    for (;;) {
        /* start ready targets, while there is room */
        while (njobs < jobs && readyq_len(&q) > 0) {
            long n = readyq_pop(&q);
            if (!out_of_date(n)) {
                trace("skip %s", name(n));
                finished(&q, n);
                continue;
            }
            trace("start %s", name(n));
            if (target(&g, n)->recipe != NULL) {
                recipes_run++;
                target(&g, n)->ran = 1;
            }
            Job j = {n, 0, 0};
            if (next_command(&j)) {
                job[njobs++] = j;
            } else {
                made(n);
                finished(&q, n);
            }
        }
        if (njobs == 0)
            break;
        /* wait for any command to end */
        int status;
        pid_t pid = wait(&status);
        if (pid < 0) {
            if (errno == EINTR)
                continue;
            stop("wait: %s", strerror(errno));
        }
        running--;
        long k = 0;
        while (k < njobs && job[k].pid != pid)
            k++;
        if (k == njobs)
            continue;
        long n = job[k].node;
        check_status(n, status);
        if (next_command(&job[k]))
            continue;
        job[k] = job[--njobs];
        made(n);
        finished(&q, n);
    }
    free(job);
    readyq_free(&q);
    // @end
}
// @end

/* ------------------------------------------------------------ main */

// @from 07.03
static const char *const algos[] = {
    "recurse",
    "topo",
    "queue",        // @from 07.04
    NULL,
};

static const char *pick_algo(const char *value)
{
    char have[200] = "";
    for (int i = 0; algos[i]; i++) {
        if (strcmp(value, algos[i]) == 0)
            return algos[i];
        strcat(strcat(have, i ? ", " : ""), algos[i]);
    }
    die("no --algo '%s' (have: %s)", value, have);
}
// @end

/* Nothing was done for goal n: say so, as make does (not with -s). */
static void nothing_done(long n)
{
    Target *t = target(&g, n);
    if (silent)
        return;
    if (t->phony || t->recipe == NULL)
        printf("make: Nothing to be done for '%s'.\n", name(n));
    else
        printf("make: '%s' is up to date.\n", name(n));
}

/* makefile if there is one, else Makefile, as make looks for them: by
 * the names in the directory, not by opening them, since a disk that
 * ignores case would open Makefile as makefile. */
static const char *default_makefile(void)
{
    int lower = 0;
    DIR *d = opendir(".");
    struct dirent *e;
    while (d != NULL && (e = readdir(d)) != NULL)
        lower |= strcmp(e->d_name, "makefile") == 0;
    if (d != NULL)
        closedir(d);
    return lower ? "makefile" : "Makefile";
}

static void usage(void)
{
    die("usage: make [-n] [-s] [-f FILE] [option ...] [NAME=VALUE ...] [TARGET ...]");
}

int main(int argc, char **argv)
{
    progname = "make";
    ds_stats_at_exit(print_stats);
    const char *file = NULL;
    int graph_mode = 0;
    // @from 07.03
    int order_mode = 0;
    const char *algo = "topo";
    // @end
    long jobs = 1;      // @from 07.04
    Array goal_names;
    array_init(&goal_names, sizeof(char *));

    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (strcmp(a, "--graph") == 0) {
            graph_mode = 1;
            continue;
        }
        // @from 07.03
        if (strcmp(a, "--order") == 0) {
            order_mode = 1;
            continue;
        }
        if (strncmp(a, "--algo=", 7) == 0) {
            algo = pick_algo(a + 7);
            continue;
        }
        // @end
        if (a[0] == '-' && a[1] == '-')
            die("unknown option '%s'", a);
        if (a[0] == '-' && a[1] != '\0') {
            for (const char *p = a + 1; *p; p++) {
                if (*p == 'n') {
                    dry_run = 1;
                } else if (*p == 's') {
                    silent = 1;
                } else if (*p == 'f') {
                    file = p[1] ? p + 1 : (i + 1 < argc ? argv[++i] : NULL);
                    if (file == NULL)
                        die("-f wants the name of a makefile");
                    break;
                // @from 07.04
                } else if (*p == 'j') {
                    const char *v = p[1] ? p + 1 : (i + 1 < argc ? argv[++i] : "");
                    char *end;
                    jobs = strtol(v, &end, 10);
                    if (*v == '\0' || *end != '\0' || jobs < 1)
                        die("-j wants a number of jobs, 1 or more, not '%s'", v);
                    algo = "queue";
                    break;
                // @end
                } else {
                    die("unknown option -%c", *p);
                }
            }
            continue;
        }
        const char *eq = strchr(a, '=');
        if (eq != NULL && eq > a) {
            char *n = xstrndup(a, (size_t)(eq - a));
            set_variable(n, eq + 1, FROM_COMMAND_LINE);
            free(n);
            continue;
        }
        if (a[0] == '\0')
            usage();
        *(const char **)array_push(&goal_names) = a;
    }
    // @from 07.04
    if (jobs > 1 && strcmp(algo, "queue") != 0)
        die("-j runs only with --algo=queue");
    // @end

    graph_init(&g);
    if (file == NULL)
        file = default_makefile();
    read_makefile(&g, file);
    if (graph_mode) {
        print_graph();
        return 0;
    }

    Array goals;
    array_init(&goals, sizeof(long));
    for (size_t i = 0; i < goal_names.len; i++)
        *(long *)array_push(&goals) = graph_node(&g, *(char **)array_at(&goal_names, i));
    if (goals.len == 0) {
        if (default_goal < 0)
            stop("*** No targets.  Stop.");
        *(long *)array_push(&goals) = default_goal;
    }
    long *goal = (long *)goals.data;

    // @from 07.02
    Array order, cycle;
    array_init(&order, sizeof(long));
    array_init(&cycle, sizeof(long));
    if (graph_search(&g, goal, goals.len, &order, &cycle) < 0)
        report_cycle(&cycle);
    // @end
    // @from 07.03
    if (order_mode) {
        for (size_t i = 0; i < order.len; i++)
            printf("%s\n", name(*(long *)array_at(&order, i)));
        return 0;
    }
    // @end

    // @from 07.03
    if (strcmp(algo, "recurse") != 0) {
        // @from 07.04
        if (strcmp(algo, "queue") == 0)
            build_queue(&order, jobs);
        else
            build_in_order(&order);
        // @else
        // build_in_order(&order);
        // @end
        /* a goal had nothing done for it if nothing ran among the targets
         * the search finished from the goal before it up to it */
        size_t from = 0;
        for (size_t i = 0; i < order.len; i++) {
            long n = *(long *)array_at(&order, i);
            for (size_t k = 0; k < goals.len; k++) {
                if (goal[k] != n)
                    continue;
                int ran = 0;
                for (size_t j = from; j <= i; j++)
                    ran |= target(&g, *(long *)array_at(&order, j))->ran;
                if (!ran)
                    nothing_done(n);
                from = i + 1;
            }
        }
        return ferror(stdout) ? 2 : 0;
    }
    // @end
    for (size_t k = 0; k < goals.len; k++) {
        long before = commands;
        if (graph_walk(&g, goal[k], make_node, NULL) < 0)
            stop("a cycle in what '%s' needs: the walk went deeper than the %zu targets there are",
                 name(goal[k]), graph_len(&g));
        if (commands == before)
            nothing_done(goal[k]);
    }
    return ferror(stdout) ? 2 : 0;
}
