"""03.01 The tokenizer

Every kind of token reads as sqlite3 reads it: keywords in any case,
quoted names, strings with doubled quotes, blobs, numbers in every form,
two-character operators, and comments anywhere.
"""


def test(t):
    tr = t.track
    setup = ('CREATE TABLE "odd table"(id INTEGER PRIMARY KEY, [first name] TEXT, `n` REAL, "say ""hi""" TEXT);\n'
             "INSERT INTO \"odd table\" VALUES (1, 'it''s', 1.5, 'x'), (2, 'O''Brien', .25, 'y');\n")
    sql = '''sElEcT 1, 2.5, .5, 1e3, 1.5E-3, 7E+2, 0;
SELECT 'it''s', '', 'two words', x'414243', X'7a';
SELECT 1<>2, 1!=1, 2==2, 3<=3, 4>=5, 'a'||'b', 7%3, 8/2, 3*3, 5-7;
SELECT /* a comment */ 42 -- and another
;
SELECT [first name], `n`, "say ""hi""" FROM "odd table"
  WHERE id = 2;
select   id
   from"odd table"order by id;
'''
    tr.both(t, sql, setup)
    for bad in ["SELECT 'unterminated;\n", "SELECT 12abc;\n", "SELECT x'4g';\n", "SELECT 1 # 2;\n"]:
        tr.errors_alike(t, "", bad)
