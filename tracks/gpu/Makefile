# Builds the project's programs with this computer's C compiler.
#
#   make          build them all: wb, the workbench
#                 and mm, matrix multiply    @from 01.01
#   make clean    remove what make built
#
# Every program is plain C11 with every warning on. -ffp-contract=off
# keeps the compiler from fusing a multiply and an add into one
# instruction (a fused multiply-add rounds once where the two round
# twice), so the code rounds the same on every compiler and machine.

CFLAGS = -std=c11 -O2 -Wall -Wextra -pedantic -ffp-contract=off
LDLIBS = -lm
LDLIBS += -pthread # @from 01.05

# add.c is built on its own with the compiler's vectorizer off (gcc and
# clang both take these two flags). Its loops are written one float at a
# time, and that is how they are meant to run: left on, the vectorizer
# would quietly rewrite them.
# So is matmul.c, for the same reason.    @from 01.01
SCALAR = -fno-tree-vectorize -fno-tree-slp-vectorize

PROGRAMS = wb
PROGRAMS += mm # @from 01.01

WB = wb.c rng.c add.o
WB += check.c # @from 00.02
WB += bench.c # @from 00.03

all: $(PROGRAMS)

wb: $(WB) *.h
	$(CC) $(CFLAGS) -o $@ $(WB) $(LDLIBS)

add.o: add.c add.h
	$(CC) $(CFLAGS) $(SCALAR) -c -o $@ add.c

# @from 01.01
MM = mm.c rng.c check.c bench.c matmul.o
MM += matmul_simd.o # @from 01.03
MM += matmul_blocked.c # @from 01.04
MM += matmul_threads.c blas.o # @from 01.05

mm: $(MM) *.h
	$(CC) $(CFLAGS) -o $@ $(MM) $(LDLIBS) $(BLASLIBS)

matmul.o: matmul.c matmul.h
	$(CC) $(CFLAGS) $(SCALAR) -c -o $@ matmul.c

# @end
# @from 01.03
# matmul_simd.c is the one file where fusing is wanted: each a * b + c of
# its vectors may become one fused multiply-add, where the machine has
# them. On x86-64 it may also use every vector instruction this machine
# has (with AVX2, eight floats at once); on arm64, NEON is always there.
SIMD = -ffp-contract=fast
ifeq ($(shell uname -m),x86_64)
SIMD += -march=native
endif

matmul_simd.o: matmul_simd.c matmul.h
	$(CC) $(CFLAGS) $(SIMD) -c -o $@ matmul_simd.c

# @end
# @from 01.05
# matmul_blas calls the system's BLAS library: Accelerate on macOS, and
# OpenBLAS on Linux when pkg-config finds it. Without one, mm still
# builds, and says how to get one.
ifeq ($(shell uname -s),Darwin)
BLAS = -DBLAS_ACCELERATE -DACCELERATE_NEW_LAPACK
BLASLIBS = -framework Accelerate
else ifeq ($(shell pkg-config --exists openblas 2>/dev/null && echo yes),yes)
BLAS = -DBLAS_OPENBLAS $(shell pkg-config --cflags openblas)
BLASLIBS = $(shell pkg-config --libs openblas)
endif

blas.o: blas.c matmul.h
	$(CC) $(CFLAGS) $(BLAS) -c -o $@ blas.c

# @end
# @internal
# For the tests (track.py): the flags each part is built with here.
flags:
	@echo "CFLAGS $(CFLAGS)"
	@echo "SCALAR $(SCALAR)"
	@echo "SIMD $(SIMD)"
	@echo "BLAS $(BLAS)"
	@echo "BLASLIBS $(BLASLIBS)"
	@echo "LDLIBS $(LDLIBS)"

# @end
clean:
	rm -f $(PROGRAMS) *.o

.PHONY: all clean
