// Fixed sizes. xv6 allocates every kernel table statically, so these
// numbers are the whole capacity plan of the system.

#define NPROC        64  // maximum number of processes @from 04.01
#define NCPU          8  // maximum number of CPUs (harts)
#define NOFILE       16  // open files per process @from 04.01
#define NFILE       100  // open files per system @from 05.07
#define NINODE       50  // maximum number of active i-nodes @from 05.05
#define NDEV         10  // maximum major device number @from 05.07
#define ROOTDEV       1  // device number of file system root disk @from 05.06
#define MAXARG       32  // max exec arguments @from 06.03
#define MAXOPBLOCKS  10  // max # of blocks any FS op writes @from 05.02
#define LOGBLOCKS    (MAXOPBLOCKS*3)  // max data blocks in on-disk log @from 05.03
#define NBUF         (MAXOPBLOCKS*3)  // size of disk block cache @from 05.02
#define FSSIZE       2000  // size of file system in blocks @from 05.03
#define MAXPATH      128   // maximum file path name @from 06.03
#define USERSTACK    1     // user stack pages @from 06.03
