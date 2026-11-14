# kilo - a text editor in one C file.
#
#   make          build ./kilo
#   make clean    remove it
#
# The flags are the original kilo's: C99, every warning, libc and nothing else.

all: kilo

kilo: kilo.c
	$(CC) -o kilo kilo.c -Wall -W -pedantic -std=c99

clean:
	rm -f kilo

.PHONY: all clean
