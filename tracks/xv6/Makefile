# xv6 from scratch - build system.
#
# @from 05.03
#   make            build build/kernel/kernel and build/fs.img
# @else
# #   make            build build/kernel/kernel
# @end
#   make qemu       boot it (Ctrl-a x quits QEMU)
# @from 08.01
#                   UDPFWD=port, PCAP=file: see the network card below
# @end
# @from 09.01
#                   SCREEN=none: no window for the screen (module 09)
# @end
# @internal
#   make test       (authors) internal checks: ./learn test xv6
# @end
#
# BUILD picks the output directory: build/ unless told otherwise.
# @internal
# A normal kernel and a SELFTEST kernel never share object files.
# @end

K := kernel
U := user
BUILD ?= build
B := $(BUILD)

# Find a RISC-V cross compiler. Homebrew calls it riscv64-elf-, most Linux
# distributions call it riscv64-linux-gnu- or riscv64-unknown-elf-.
TOOLPREFIX ?= $(shell for p in riscv64-elf- riscv64-unknown-elf- riscv64-linux-gnu-; do \
	if command -v $${p}gcc >/dev/null 2>&1; then echo $$p; exit 0; fi; done; \
	echo "***" 1>&2; echo "*** no riscv64 gcc found; set TOOLPREFIX" 1>&2; echo "***" 1>&2)

CC := $(TOOLPREFIX)gcc
LD := $(TOOLPREFIX)ld
OBJCOPY := $(TOOLPREFIX)objcopy
OBJDUMP := $(TOOLPREFIX)objdump
QEMU := qemu-system-riscv64

# Every .c and .S file in kernel/ is part of the kernel. entry.o must be
# linked first so that _entry lands at 0x80000000, where QEMU jumps.
KSRC := $(sort $(wildcard $(K)/*.c $(K)/*.S))
KOBJS := $(patsubst $(K)/%,$(B)/kernel/%.o,$(basename $(KSRC)))
OBJS := $(B)/kernel/entry.o $(filter-out $(B)/kernel/entry.o,$(KOBJS))

CFLAGS := -Wall -Werror -O -fno-omit-frame-pointer -ggdb -gdwarf-2
CFLAGS += -MD -mcmodel=medany -ffreestanding -fno-common -nostdlib -mno-relax
CFLAGS += -fno-builtin -fno-stack-protector -fno-pie -no-pie -I.
CFLAGS += -std=gnu17
# An unused helper or variable is worth a warning, not a failed build.
CFLAGS += -Wno-error=unused-function -Wno-error=unused-variable -Wno-error=unused-but-set-variable
# @internal
ifdef SELFTEST
CFLAGS += -DSELFTEST
endif
# @end
CFLAGS += $(EXTRA_CFLAGS)
LDFLAGS := -z max-page-size=4096 --no-warn-rwx-segments

# @from 05.03
all: $(B)/kernel/kernel $(B)/fs.img
# @else
# all: $(B)/kernel/kernel
# @end

$(B)/kernel/%.o: $(K)/%.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c -o $@ $<

$(B)/kernel/%.o: $(K)/%.S
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c -o $@ $<

$(B)/kernel/kernel: $(OBJS) $(K)/kernel.ld
	$(LD) $(LDFLAGS) -T $(K)/kernel.ld -o $@ $(OBJS)
	$(OBJDUMP) -S $@ > $(B)/kernel/kernel.asm
	$(OBJDUMP) -t $@ | sed '1,/SYMBOL TABLE/d; s/ .* / /; /^$$/d' > $(B)/kernel/kernel.sym

# @from 07.01
# ---------------------------------------------------------------- user space

ULIB := $(addprefix $(B)/user/,ulib.o usys.o printf.o umalloc.o)

$(B)/user/%.o: $(U)/%.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c -o $@ $<

$(B)/user/usys.S: $(U)/usys.pl
	@mkdir -p $(@D)
	perl $(U)/usys.pl > $@

$(B)/user/usys.o: $(B)/user/usys.S
	$(CC) $(CFLAGS) -c -o $@ $<

# Every user program is one .c file linked against the small user library.
$(B)/user/_%: $(B)/user/%.o $(ULIB) $(U)/user.ld
	$(LD) $(LDFLAGS) -T $(U)/user.ld -o $@ $< $(ULIB)
	$(OBJDUMP) -S $@ > $(B)/user/$*.asm

# Every user/*.c file except the libraries is a program that goes on the disk.
ULIBSRC := ulib printf umalloc
# @from 09.03
# @from 09.04
GUILIBSRC := gui font
# @else
# GUILIBSRC := gui
# @end
UPROGS := $(filter-out $(ULIBSRC) $(GUILIBSRC),$(basename $(notdir $(wildcard $(U)/*.c))))
# @else
# UPROGS := $(filter-out $(ULIBSRC),$(basename $(notdir $(wildcard $(U)/*.c))))
# @end
UBINS := $(addprefix $(B)/user/_,$(UPROGS))

# @from 09.03
# Programs that use the screen, the keyboard or the mouse (module 09) also
# link the GUI library, GUILIBSRC. The rest stay as small as they were.
GUILIB := $(addprefix $(B)/user/,$(addsuffix .o,$(GUILIBSRC)))
# @from 09.05
GUIPROGS := $(addprefix $(B)/user/_,events paint)
# @else
# GUIPROGS := $(addprefix $(B)/user/_,events)
# @end
$(GUIPROGS): $(B)/user/_%: $(B)/user/%.o $(ULIB) $(GUILIB) $(U)/user.ld
	$(LD) $(LDFLAGS) -T $(U)/user.ld -o $@ $< $(ULIB) $(GUILIB)
	$(OBJDUMP) -S $@ > $(B)/user/$*.asm

# @end
# @end
# @from 05.03
# ---------------------------------------------------------------- the disk

$(B)/mkfs/mkfs: mkfs/mkfs.c $(K)/fs.h $(K)/param.h
	@mkdir -p $(@D)
	cc -Werror -Wall -I. -o $@ mkfs/mkfs.c

# @from 07.01
$(B)/fs.img: $(B)/mkfs/mkfs README.md $(UBINS) Makefile
	cp README.md $(B)/README
	$(B)/mkfs/mkfs $@ $(B)/README $(UBINS) > $(B)/mkfs.log
# @else
# $(B)/fs.img: $(B)/mkfs/mkfs README.md Makefile
# 	cp README.md $(B)/README
# 	$(B)/mkfs/mkfs $@ $(B)/README > $(B)/mkfs.log
# @end

# @end
-include $(wildcard $(B)/kernel/*.d) $(wildcard $(B)/user/*.d)

# ---------------------------------------------------------------- running

CPUS ?= 3
QEMUOPTS = -machine virt -bios none -kernel $(B)/kernel/kernel -m 128M -smp $(CPUS) -nographic
QEMUOPTS += -global virtio-mmio.force-legacy=false
# @from 05.03
QEMUOPTS += -drive file=$(B)/fs.img,if=none,format=raw,id=x0
QEMUOPTS += -device virtio-blk-device,drive=x0,bus=virtio-mmio-bus.0
# @end

# @from 08.01
# The network card (module 08) on QEMU's user-mode network: xv6 is
# 10.0.2.15, the host is 10.0.2.2, QEMU's DNS resolver is 10.0.2.3.
# make qemu UDPFWD=2000 also sends UDP datagrams for the host's
# 127.0.0.1:2000 to xv6's port 2000.
NETDEV = user,id=net0,ipv6=off
ifdef UDPFWD
NETDEV := $(NETDEV),hostfwd=udp:127.0.0.1:$(UDPFWD)-:$(UDPFWD)
endif
QEMUOPTS += -netdev $(NETDEV)
QEMUOPTS += -device virtio-net-device,netdev=net0,bus=virtio-mmio-bus.1
# make qemu PCAP=net.pcap also records every frame the card sends or
# receives in net.pcap; read it afterwards with tcpdump -n -r net.pcap.
ifdef PCAP
QEMUOPTS += -object filter-dump,id=dump0,netdev=net0,file=$(PCAP)
endif

# @end
# @from 09.01
# @from 09.03
# The screen, the keyboard and the mouse (module 09): a ramfb framebuffer
# the kernel sets up through fw_cfg, and virtio input devices on the next
# two mmio slots.
# @else
# # The screen (module 09): a ramfb framebuffer the kernel sets up through
# # fw_cfg.
# @end
# QEMU shows the screen in a window of its own when there is a desktop to
# open one on (cocoa on macOS, gtk or sdl on Linux); the serial console
# stays in this terminal either way. make qemu SCREEN=none leaves the
# window out; SCREEN=sdl, say, picks another kind.
QEMUOPTS += -device ramfb
# @from 09.03
QEMUOPTS += -device virtio-keyboard-device,bus=virtio-mmio-bus.2
QEMUOPTS += -device virtio-tablet-device,bus=virtio-mmio-bus.3
# @end
ifndef SCREEN
  QDISPLAYS := $(shell $(QEMU) -display help 2>/dev/null)
  ifeq ($(shell uname -s),Darwin)
    ifeq ($(SSH_CONNECTION),)
      SCREEN := $(filter cocoa,$(QDISPLAYS))
    endif
  else ifneq ($(DISPLAY)$(WAYLAND_DISPLAY),)
    SCREEN := $(firstword $(filter gtk sdl,$(QDISPLAYS)))
  endif
endif
ifneq ($(SCREEN),)
QEMUOPTS += -display $(SCREEN)
endif
# @end

# @from 05.03
qemu: $(B)/kernel/kernel $(B)/fs.img
# @else
# qemu: $(B)/kernel/kernel
# @end
	$(QEMU) $(QEMUOPTS)

# Pauses at the first instruction and waits for a debugger on tcp::26000.
# @from 05.03
qemu-gdb: $(B)/kernel/kernel $(B)/fs.img
# @else
# qemu-gdb: $(B)/kernel/kernel
# @end
	@echo "*** now run a riscv64 gdb and: target remote localhost:26000"
	$(QEMU) $(QEMUOPTS) -S -gdb tcp::26000

# @internal
test:
	@python3 tests/run.py $(L)

.PHONY: test
# @end
clean:
	rm -rf build
# @internal
	rm -rf build-test build-crash* build-upstream
# @end

.PHONY: all qemu qemu-gdb clean
.PRECIOUS: $(B)/user/%.o $(B)/user/usys.S  # @from 07.01
