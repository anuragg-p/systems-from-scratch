# @from 07.01
# kilo - a text editor in C, and its client for a language server.
# @else
# # kilo - a text editor in one C file.
# @end
#
#   make          build ./kilo
#   make clean    remove it
#
# The flags are the original kilo's: C99, every warning, libc and nothing else.

all: kilo

# @from 07.01
# @from 07.02
kilo: kilo.c lsp.c lsp.h json.c json.h
	$(CC) -o kilo kilo.c lsp.c json.c -Wall -W -pedantic -std=c99
# @else
# kilo: kilo.c lsp.c lsp.h
# 	$(CC) -o kilo kilo.c lsp.c -Wall -W -pedantic -std=c99
# @end
# @else
# kilo: kilo.c
# 	$(CC) -o kilo kilo.c -Wall -W -pedantic -std=c99
# @end

clean:
	rm -f kilo

.PHONY: all clean
