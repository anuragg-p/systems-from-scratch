# gcd.s: the greatest common divisor of two numbers, written by hand
# for the machine. i is kept in s1 and j in s2.
main:
    call getint           # a0 = the next number of the input
    mv   s1, a0           # i
    call getint
    mv   s2, a0           # j
loop:
    beq  s1, s2, done     # until i == j:
    ble  s1, s2, smaller  #   the larger one loses the smaller
    sub  s1, s1, s2       #   i = i - j
    j    loop
smaller:
    sub  s2, s2, s1       #   j = j - i
    j    loop
done:
    mv   a0, s1
    call putint           # print i
    li   a0, 0
    call exit             # status 0
