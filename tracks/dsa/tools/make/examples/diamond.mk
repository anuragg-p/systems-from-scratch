# app needs two libraries, and both need the same header: a diamond.

app: liba libb
	touch app
liba: common.h
	touch liba
libb: common.h
	touch libb
common.h:
	touch common.h
