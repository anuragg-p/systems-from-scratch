# Authors only: xv6's own usertests (usertests.c here, see README.md) on a disk
# image of its own. Never part of the project a reader sees: run.py passes this
# file to make next to the project's own Makefile, which defines CC, CFLAGS,
# ULIB, UBINS and the rest:
#
#   make -f Makefile -f <this file> UPSTREAM_DIR=<this dir> $(B)/upstream/fs.img
#
# The image holds the project's programs and README, as its own fs.img does,
# with xv6's usertests in place of the project's: the tests exec echo and open
# README, cat and init.

UP := $(B)/upstream
UPSTREAM_DIR ?= $(dir $(lastword $(MAKEFILE_LIST)))

$(UP)/usertests.o: $(UPSTREAM_DIR)/usertests.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c -o $@ $<

$(UP)/_usertests: $(UP)/usertests.o $(ULIB) $(U)/user.ld
	$(LD) $(LDFLAGS) -T $(U)/user.ld -o $@ $< $(ULIB)
	$(OBJDUMP) -S $@ > $(UP)/usertests.asm

UPROGS_UP := $(filter-out $(B)/user/_usertests,$(UBINS)) $(UP)/_usertests

$(UP)/fs.img: $(B)/fs.img $(UPROGS_UP)
	$(B)/mkfs/mkfs $@ $(B)/README $(UPROGS_UP) > $(UP)/mkfs.log

-include $(wildcard $(UP)/*.d)
