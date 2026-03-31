import numpy as np

LSB_MODES = {
    '111': {'r': 1, 'g': 1, 'b': 1, 'total': 3},
    '222': {'r': 2, 'g': 2, 'b': 2, 'total': 6},
    '332': {'r': 3, 'g': 3, 'b': 2, 'total': 8},
}

def get_lsb_config(mode='332'):
    if mode not in LSB_MODES:
        raise ValueError(f"Invalid LSB mode: {mode}. Valid modes: {list(LSB_MODES.keys())}")
    return LSB_MODES[mode]

def merge(rbit, gbit, bbit, mode='332'):
    if mode == '332':
        return (rbit << 5) | (gbit << 2) | bbit
    elif mode == '222':
        return (rbit << 4) | (gbit << 2) | bbit
    elif mode == '111':
        return (rbit << 2) | (gbit << 1) | bbit
    raise ValueError(f"Invalid LSB mode: {mode}")

def put(pixel, rbit, gbit, bbit, mode='332'):
    b, g, r = int(pixel[0]), int(pixel[1]), int(pixel[2])
    config = get_lsb_config(mode)
    
    r_mask = 0xFF << config['r']
    g_mask = 0xFF << config['g']
    b_mask = 0xFF << config['b']
    
    new_r = (r & r_mask) | (rbit & ((1 << config['r']) - 1))
    new_g = (g & g_mask) | (gbit & ((1 << config['g']) - 1))
    new_b = (b & b_mask) | (bbit & ((1 << config['b']) - 1))
    
    return np.array([new_b, new_g, new_r], dtype=np.uint8)

def extract_from_pixel(pixel, mode='332'):
    b, g, r = int(pixel[0]), int(pixel[1]), int(pixel[2])
    config = get_lsb_config(mode)
    
    r_extracted = r & ((1 << config['r']) - 1)
    g_extracted = g & ((1 << config['g']) - 1)
    b_extracted = b & ((1 << config['b']) - 1)
    
    return r_extracted, g_extracted, b_extracted

def bytes_to_bits(data):
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits

def bits_to_bytes(bits):
    pad = (8 - len(bits) % 8) % 8
    bits = bits + [0] * pad
    
    result = bytearray()
    for i in range(0, len(bits), 8):
        byte_bits = bits[i:i+8]
        byte_val = 0
        for bit in byte_bits:
            byte_val = (byte_val << 1) | bit
        result.append(byte_val)
    return bytes(result)

def file_to_bits(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    return bytes_to_bits(data)

def bits_to_file(bits, filepath):
    data = bits_to_bytes(bits)
    with open(filepath, 'wb') as f:
        f.write(data)

def int_to_bits(value, num_bits):
    bits = []
    for i in range(num_bits - 1, -1, -1):
        bits.append((value >> i) & 1)
    return bits

def bits_to_int(bits):
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value

def create_header(payload_length, extension, use_encryption, use_random, lsb_mode, original_filename=''):
    header_bits = []
    
    header_bits.extend(int_to_bits(payload_length, 32))
    
    ext_bytes = extension.encode('utf-8') if extension else b''
    header_bits.extend(int_to_bits(len(ext_bytes), 8))
    
    header_bits.extend(bytes_to_bits(ext_bytes))
    
    filename_bytes = original_filename.encode('utf-8') if original_filename else b''
    header_bits.extend(int_to_bits(len(filename_bytes), 8))
    
    header_bits.extend(bytes_to_bits(filename_bytes))
    
    header_bits.extend(int_to_bits(1 if use_encryption else 0, 8))
    
    header_bits.extend(int_to_bits(1 if use_random else 0, 8))
    
    mode_map = {'111': 1, '222': 2, '332': 3}
    header_bits.extend(int_to_bits(mode_map.get(lsb_mode, 3), 8))
    
    return header_bits

def parse_header(header_bits):
    idx = 0
    
    payload_length = bits_to_int(header_bits[idx:idx+32])
    idx += 32
    
    ext_len = bits_to_int(header_bits[idx:idx+8])
    idx += 8
    
    if ext_len > 0:
        ext_bits = header_bits[idx:idx + ext_len * 8]
        extension = bits_to_bytes(ext_bits).decode('utf-8')
        idx += ext_len * 8
    else:
        extension = ''
    
    filename_len = bits_to_int(header_bits[idx:idx+8])
    idx += 8
    
    if filename_len > 0:
        filename_bits = header_bits[idx:idx + filename_len * 8]
        original_filename = bits_to_bytes(filename_bits).decode('utf-8')
        idx += filename_len * 8
    else:
        original_filename = ''
    
    use_encryption = bits_to_int(header_bits[idx:idx+8]) == 1
    idx += 8
    
    use_random = bits_to_int(header_bits[idx:idx+8]) == 1
    idx += 8
    
    mode_val = bits_to_int(header_bits[idx:idx+8])
    idx += 8
    mode_map = {1: '111', 2: '222', 3: '332'}
    lsb_mode = mode_map.get(mode_val, '332')
    
    return payload_length, extension, use_encryption, use_random, lsb_mode, original_filename, idx

def get_bits_per_pixel(mode='332'):
    return LSB_MODES[mode]['total']
