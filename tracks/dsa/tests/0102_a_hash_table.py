"""01.02 A hash table

freq --algo=table gives the pipeline's counts, every word of the book and of a generated text. It
finds each word by its hash: with the first table (the bytes summed, 1024 buckets that never grow)
the book takes under a hundredth of the probes the list takes. Each word is one lookup, and each new
word one more to add it: lookups = words + distinct, inserts = distinct.
"""


def test(t):
    T = t.track
    fx = T.fixtures("freq")
    book = T.data(t, "book.txt")
    first = ["--algo=table", "--hash=sum", "--no-grow"]      # the table as 01.02 builds it
    text = T.gen(t, "text", 50000)
    for args in (first, ["--algo=table"]):
        fx.check(t, book, args + ["--top=select"], n=0)
        fx.check(t, text, args + ["--top=select"], n=0)
        fx.check(t, book, args)

    lst = T.stats(T.run(t, "freq", ["--algo=list", book], env={"DS_STATS": "1"}).err)
    tab = T.stats(T.run(t, "freq", first + [book], env={"DS_STATS": "1"}).err)
    f, s = tab["freq"], tab["table"]
    t.check(s["lookups"] == f["words"] + f["distinct"] and s["inserts"] == f["distinct"],
            f"one lookup a word, one more and an insert for each new one: {tab}")
    t.check(s["probes"] * 100 < lst["freq"]["list probes"],
            f"the table should look at under a hundredth of what the list does: table {s}, list {lst['freq']}")
    t.check(s["resizes"] == 0, f"the first table never grows: {s}")
    t.check(f["list probes"] == 0 and "table" not in lst, f"each way does only its own work: {tab} {lst}")
