# Four targets that need nothing, each a second of work: four seconds one
# at a time, one second with make -j 4.

all: one two three four
one:
	sleep 1; touch one
two:
	sleep 1; touch two
three:
	sleep 1; touch three
four:
	sleep 1; touch four

.PHONY: all
