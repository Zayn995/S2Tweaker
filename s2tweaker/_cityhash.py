"""CityHash64 for native Unreal localization identities.

Algorithm adapted from https://github.com/google/cityhash/blob/master/src/city.cc
Copyright (c) 2011 Google, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
import struct

MASK = (1 << 64) - 1
K0 = 0xc3a5c85c97cb3127
K1 = 0xb492b66fbe98f273
K2 = 0x9ae16a3b2f90404f


def rotate(n, shift):
    n &= MASK
    return ((n >> shift) | (n << (64 - shift))) & MASK


def mix(n):
    n &= MASK
    return n ^ (n >> 47)


def hash16(u, v, mul=0x9ddfea08eb382d69):
    a = mix(((u & MASK) ^ (v & MASK)) * mul)
    b = mix(((v & MASK) ^ a) * mul)
    return (b * mul) & MASK


def city64(data):
    length = len(data)
    f64 = lambda at: struct.unpack_from('<Q', data, at)[0]
    f32 = lambda at: struct.unpack_from('<I', data, at)[0]
    swap = lambda n: int.from_bytes((n & MASK).to_bytes(8, 'little'), 'big')
    mul = (K2 + length * 2) & MASK

    def weak(at, a, b):
        w, x, y, z = (f64(at+i) for i in (0, 8, 16, 24))
        a = (a + w) & MASK
        b = rotate(b + a + z, 21)
        c = a
        a = (a + x + y) & MASK
        b = (b + rotate(a, 44)) & MASK
        return (a + z) & MASK, (b + c) & MASK

    if length <= 16:
        if length >= 8:
            a, b = (f64(0) + K2) & MASK, f64(length-8)
            return hash16(rotate(b, 37) * mul + a, (rotate(a, 25) + b) * mul, mul)
        if length >= 4:
            return hash16(length + (f32(0) << 3), f32(length-4), mul)
        if length:
            y = data[0] + (data[length >> 1] << 8)
            z = length + (data[-1] << 2)
            return (mix((y * K2) ^ (z * K0)) * K2) & MASK
        return K2
    if length <= 32:
        a, b = f64(0) * K1, f64(8)
        c, d = f64(length-8) * mul, f64(length-16) * K2
        return hash16(rotate(a+b, 43) + rotate(c, 30) + d,
                      a + rotate(b + K2, 18) + c, mul)
    if length <= 64:
        a, b = f64(0) * K2, f64(8)
        c, d = f64(length-24), f64(length-32)
        e, f = f64(16) * K2, f64(24) * 9
        g, h = f64(length-8), f64(length-16) * mul
        u = rotate(a+g, 43) + (rotate(b, 30) + c) * 9
        v = (((a+g) & MASK) ^ d) + f + 1
        w = swap((u+v) * mul) + h
        x = rotate(e+f, 42) + c
        y = (swap((v+w) * mul) + g) * mul
        z = e + f + c
        a = swap((x+z) * mul + y) + b
        b = mix((z+a) * mul + d + h) * mul
        return (b+x) & MASK
    x = f64(length-40)
    y = (f64(length-16) + f64(length-56)) & MASK
    z = hash16(f64(length-48) + length, f64(length-24))
    v = weak(length-64, length, z)
    w = weak(length-32, y + K1, x)
    x = (x * K1 + f64(0)) & MASK
    for at in range(0, (length-1) & ~63, 64):
        x = (rotate(x+y+v[0]+f64(at+8), 37) * K1) & MASK
        y = (rotate(y+v[1]+f64(at+48), 42) * K1) & MASK
        x ^= w[1]
        y = (y + v[0] + f64(at+40)) & MASK
        z = (rotate(z+w[0], 33) * K1) & MASK
        v = weak(at, v[1] * K1, x+w[0])
        w = weak(at+32, z+w[1], y+f64(at+16))
        z, x = x, z
    return hash16(hash16(v[0], w[0]) + mix(y) * K1 + z,
                  hash16(v[1], w[1]) + x)


def key_hash(text):
    if not text:
        return 0
    h = city64(text.encode('utf-16-le'))
    return ((h & 0xffffffff) + (h >> 32) * 23) & 0xffffffff
