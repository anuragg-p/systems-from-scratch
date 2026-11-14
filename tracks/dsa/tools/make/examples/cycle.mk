# a needs b, b needs c, and c needs a: there is no order to build them in.

all: a
a: b
	touch a
b: c
	touch b
c: a
	touch c

.PHONY: all
