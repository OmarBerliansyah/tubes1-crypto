import numpy as np
def split(huruf):
    value = ord(huruf) if isinstance(huruf, str) else huruf
    rbit = (value >> 5) & 7
    gbit = (value >> 2) & 7
    bbit = value & 3
    return rbit, gbit, bbit

def merge(rbit, gbit, bbit):
    value = (rbit << 5) | (gbit << 2) | bbit
    return chr(value)

def put(pixel, rbit, gbit, bbit):
    b,g,r = pixel
    new_r = (r & 0b11111000) | rbit
    new_g = (g & 0b11111000) | gbit
    new_b = (b & 0b11111100) | bbit
    return new_b, new_g, new_r

def char_to_bits(text):
    bits = []
    for char in text:
        bin_str = format(ord(char), '08b')
        for bin in bin_str:
            bits.append(int(bin))
    return bits

def bits_to_int(bits):
    int_value = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        int_value.append(int("".join(map(str, byte)), 2))
    return int_value

def bits_to_bytes(bits):
    bits = []
    for i in range in range(0, len(bits), 8):
        byte = bits[i:i+8]
        bits.append(int("".join(map(str, byte)), 2))
    return bytes(bits)

