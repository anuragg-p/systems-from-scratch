# Builds the compiler, ./cc, with this machine's own C compiler (HOSTCC).
# What ./cc writes is RISC-V assembly, for the RISC-V toolchain's as and ld.
#
#   make          build ./cc
#   make clean    remove it, and build/
#
# The flags hold the compiler's source to plain C11, with every warning on:
# it has to compile itself one day, so it may use only what it will know.

HOSTCC ?= cc
CFLAGS = -std=c11 -Wall -Wextra -pedantic -g

SRCS = main.c
SRCS += tokenize.c # @from 01.01
SRCS += parse.c # @from 02.01
SRCS += codegen.c # @from 02.03
HDRS =
HDRS += cc.h # @from 01.01

cc: $(SRCS) $(HDRS)
	$(HOSTCC) $(CFLAGS) -o cc $(SRCS)

clean:
	rm -rf cc cc.dSYM build

.PHONY: clean
