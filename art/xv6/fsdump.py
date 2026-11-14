import struct, sys
img = open(sys.argv[1], "rb").read()
B = 1024
def blk(n): return img[n*B:(n+1)*B]
sb = struct.unpack("<8I", blk(1)[:32])
print("super", [hex(sb[0])] + list(sb[1:]))
inodestart = sb[6]
def dinode(i):
    b = blk(i // 16 + inodestart)
    o = (i % 16) * 64
    t, maj, mi, nl, size = struct.unpack("<hhhhI", b[o:o+12])
    addrs = struct.unpack("<13I", b[o+12:o+64])
    return t, nl, size, addrs
for i in range(1, 16):
    t, nl, size, addrs = dinode(i)
    if t: print(i, "type", t, "nlink", nl, "size", size, "addrs", [a for a in addrs if a], "iblock", i//16+inodestart)
t, nl, size, addrs = dinode(1)
d = blk(addrs[0])
for k in range(size // 16):
    inum, = struct.unpack("<H", d[k*16:k*16+2]); name = d[k*16+2:k*16+16].split(b"\0")[0].decode()
    print("dirent", k, "off", k*16, inum, name)
bm = blk(sb[7])
used = sum(bin(x).count("1") for x in bm)
print("bitmap bits set", used, "first bytes", bm[:8].hex(), "byte 67", hex(bm[67]), "byte 68", hex(bm[68]))
