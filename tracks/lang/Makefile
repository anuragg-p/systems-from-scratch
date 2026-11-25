# Builds the programs of the project with this computer's C compiler.
#
#   make          build every program there is
#   make gcd      build one of them (here, the C version of gcd)
#   make clean    remove what make and the scripts built
#
# Every program is plain C11 with every warning on. build/ holds what the
# scripts make (motec, agree) and what the lessons write there.

CFLAGS = -std=c11 -O2 -Wall -Wextra

PROGRAMS = machine
PROGRAMS += gcd rt.o # @from 01.02
PROGRAMS += mote0 # @from 01.03
PROGRAMS += mote2c # @from 01.04
PROGRAMS += mote # @from 01.06

# @from 01.06
# The phases of the compiler, a file each, and the driver (main.c).
MOTE = main.c scan.c
MOTE += parse.c # @from 01.07
MOTE += analyze.c # @from 01.08
MOTE += interp.c # @from 01.09
MOTE += gen.c # @from 01.10
MOTE += improve.c # @from 01.11

# @end
all: $(PROGRAMS)
	@mkdir -p build

machine: machine.c
	$(CC) $(CFLAGS) -o $@ machine.c

# @from 01.02
# rt.o reads and writes numbers for programs written in C, as the
# machine's getint and putint do.
rt.o: rt.c rt.h
	$(CC) $(CFLAGS) -c -o $@ rt.c

gcd: programs/gcd.c rt.o rt.h
	$(CC) $(CFLAGS) -I. -o $@ programs/gcd.c rt.o

# @end
# @from 01.03
mote0: mote0.c
	$(CC) $(CFLAGS) -o $@ mote0.c

# @end
# @from 01.04
mote2c: mote2c.c
	$(CC) $(CFLAGS) -o $@ mote2c.c

# @end
# @from 01.06
mote: $(MOTE) mote.h
	$(CC) $(CFLAGS) -o $@ $(MOTE)

# @end
clean:
	rm -rf $(PROGRAMS) build

.PHONY: all clean
