# @from 07.01
# @from 09.01
# kilo - a text editor in C, its client for a language server, and Lua.
# @else
# # kilo - a text editor in C, and its client for a language server.
# @end
# @else
# @from 09.01
# # kilo - a text editor in C, with Lua inside it.
# @else
# # # kilo - a text editor in one C file.
# @end
# @end
#
#   make          build ./kilo
# @from 09.01
#   make clean    remove it, and Lua's library
#
# The flags are the original kilo's: C99 and every warning. Lua's library
# is built once, by Lua's own Makefile in lua/src, and linked in.
# @else
# #   make clean    remove it
# #
# # The flags are the original kilo's: C99, every warning, libc and nothing else.
# @end

all: kilo

# @from 07.01
# @from 09.01
kilo: kilo.c lsp.c lsp.h json.c json.h script.c script.h api.h lua/src/liblua.a
	$(CC) -o kilo kilo.c lsp.c json.c script.c -Ilua/src lua/src/liblua.a -lm \
		-Wall -W -pedantic -std=c99
# @else
# @from 07.02
# kilo: kilo.c lsp.c lsp.h json.c json.h
# 	$(CC) -o kilo kilo.c lsp.c json.c -Wall -W -pedantic -std=c99
# @else
# # kilo: kilo.c lsp.c lsp.h
# # 	$(CC) -o kilo kilo.c lsp.c -Wall -W -pedantic -std=c99
# @end
# @end
# @else
# @from 09.01
# @from 09.02
# kilo: kilo.c script.c script.h api.h lua/src/liblua.a
# @else
# # kilo: kilo.c script.c script.h lua/src/liblua.a
# @end
# 	$(CC) -o kilo kilo.c script.c -Ilua/src lua/src/liblua.a -lm \
# 		-Wall -W -pedantic -std=c99
# @else
# # kilo: kilo.c
# # 	$(CC) -o kilo kilo.c -Wall -W -pedantic -std=c99
# @end
# @end
# @from 09.01

lua/src/liblua.a:
	$(MAKE) -C lua/src liblua.a MYCFLAGS=-DLUA_USE_POSIX
# @end

clean:
	rm -f kilo
	rm -f lua/src/*.o lua/src/liblua.a	# @from 09.01

.PHONY: all clean
