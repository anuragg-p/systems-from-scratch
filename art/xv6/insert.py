"""Insert figure lines after the paragraph that contains each anchor. Idempotent."""
import os
L = os.path.expanduser("~/Documents/WORK/misc/systems-from-scratch/tracks/xv6/lessons")
F = [
 ("06-user-space/06.01-the-trampoline-and-user-traps.md", "says they are fixed.",
  "`struct trapframe` at `TRAPFRAME`: the five values `uservec` needs to enter the kernel, then the 31 user registers, each at an offset the assembly hard-codes.",
  "06.01-trapframe"),
 ("06-user-space/06.01-the-trampoline-and-user-traps.md", "may trap again and overwrite it.",
  "One trip from `ecall` and back: the kernel page table is installed only between the two `csrw satp`, and `stvec` names `kernelvec` from the start of `usertrap` until `prepare_return`.",
  "06.01-round-trip"),
 ("06-user-space/06.02-system-calls.md", "is simply what `userret` restores.",
  "`write(1, buf, 3)` as a system call: the stub puts 16 in `a7`, `syscall` uses it to pick `sys_write` from the table, and the result goes back through the trapframe's `a0`.",
  "06.02-syscall-path"),
 ("06-user-space/06.03-exec-and-the-elf-loader.md", "instead of silently overwriting data.",
  "The two LOAD headers of `_echo` become its first two pages; `kexec` then adds a guard page and a stack page above them.",
  "06.03-elf-load"),
 ("06-user-space/06.03-exec-and-the-elf-loader.md", "is where the program starts.",
  "The top of the stack page after `exec` of `echo a bb ccc`: the strings, then the `argv` array, with `sp` and `a1` both at 0x3F90.",
  "06.03-argv-stack"),
 ("06-user-space/06.04-fork-exit-and-wait.md", "one after the other in it.",
  "`init` forks its first child: every page is copied, the trapframe too except `a0`, and descriptors 0 to 2 still point at the same `struct file`.",
  "06.04-fork-copy"),
 ("06-user-space/06.04-fork-exit-and-wait.md", "if init itself tries to leave.",
  "B exits with status 3: it stays a zombie until A's `wait` collects it, and its child C is handed to `init`.",
  "06.04-exit-wait"),
 ("06-user-space/06.05-sbrk-and-the-user-heap.md", "returns real memory to the free list.",
  "`sbrk(8192)` in a process laid out like `echo`: two zeroed pages appear at the old `p->sz`, which is what the call returns.",
  "06.05-sbrk-heap"),
 ("06-user-space/06.06-pipes.md", "without a spare slot.",
  "The 512 bytes of `data` as a ring: 300 bytes are waiting, and they wrap past the end of the array.",
  "06.06-ring"),
 ("06-user-space/06.06-pipes.md", "still *could* write.",
  "One reader and one writer: each sleeps on its own counter and wakes the other's, and closing the write end is what turns an empty pipe into end of file.",
  "06.06-sleep-wake"),
 ("06-user-space/06.07-file-system-calls.md", "there is no `dup2` here.",
  "Redirection with `cmd > f`: after `close(1)` the lowest free slot is 1, so `open` puts the file there.",
  "06.07-lowest-fd"),
 ("06-user-space/06.07-file-system-calls.md", "so it commits atomically (05.04).",
  "Two names for inode 21: `link` and `unlink` move `nlink`, and the inode is freed only when it reaches 0 and no file has it open.",
  "06.07-nlink"),
 ("07-userland/07.01-the-user-library.md", "The caller gets\nthe address just after the header.",
  "`malloc(100)` on a fresh heap: 8 units are cut from the tail of the block `morecore` added, so the header the free list holds stays where it was.",
  "07.01-free-list"),
 ("07-userland/07.01-the-user-library.md", "no list to edit.",
  "`user/cat.c` is linked with the user library into `_cat`, `mkfs` stores it as `/cat`, and `exec` finds it by name in the root directory.",
  "07.01-to-disk"),
 ("07-userland/07.02-init-and-the-shell.md", "That is why the main loop runs it\nin a forked child.",
  "One command: the shell forks, the child parses the line and becomes `echo` at `exec`, and the shell sleeps in `wait` until it exits.",
  "07.02-fork-exec-wait"),
 ("07-userland/07.02-init-and-the-shell.md", "the parent closes both\nbefore `wait`.",
  "`echo hi | wc` just before the children exec: each end of the pipe is open in exactly one process.",
  "07.02-pipe-fds"),
 ("07-userland/07.03-the-utilities.md", "the type, the inode number and the size.",
  "`ls` with no arguments: it reads `.` one 16-byte entry at a time, skips empty slots, and `stat`s each name to print its line.",
  "07.03-ls-loop"),
]
for rel, anchor, cap, name in F:
    path = os.path.join(L, rel)
    text = open(path).read()
    line = f"![{cap}](figures/{name}.svg)"
    assert "]" not in cap and cap.isascii()
    if f"figures/{name}.svg" in text:
        continue
    assert text.count(anchor) == 1, (rel, anchor, text.count(anchor))
    i = text.index(anchor) + len(anchor)
    j = text.find("\n\n", i)
    assert j != -1
    text = text[:j] + "\n\n" + line + text[j:]
    open(path, "w").write(text)
    print("inserted", name)
