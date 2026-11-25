// rt.h: reading and writing numbers from C, as the machine's routines
// getint and putint do (rt.c). A C program that includes this and is
// linked with rt.o reads and writes the way a program for the machine does.

long getint(void);      // the next whole number of the input; at its end, the program stops
void putint(long n);    // n in decimal, and a line end
