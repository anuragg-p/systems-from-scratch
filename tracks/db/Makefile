# db - a SQL database in C, from scratch.
#
#   make            build ./db
#   make clean      remove the build
#
# Plain C11 and libc, nothing else. Objects go in build/, the binary is
# ./db next to this file.

CC ?= cc
CFLAGS ?= -O2 -g
CFLAGS += -std=c11 -D_DEFAULT_SOURCE -D_DARWIN_C_SOURCE -D_POSIX_C_SOURCE=200809L
CFLAGS += -Wall -Wextra -Wno-unused-parameter
# Unused functions, variables and labels are not warned about.
CFLAGS += -Wno-unused-function -Wno-unused-variable -Wno-unused-but-set-variable -Wno-unused-label
CFLAGS += $(EXTRA_CFLAGS)

SRC := $(sort $(wildcard src/*.c))
OBJ := $(patsubst src/%.c,build/%.o,$(SRC))

db: $(OBJ)
	$(CC) $(CFLAGS) -o $@ $(OBJ) -lm

build/%.o: src/%.c src/db.h
	@mkdir -p build
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -rf build db

.PHONY: clean
