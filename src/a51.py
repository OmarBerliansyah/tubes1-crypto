class A51:
    REG_X_LEN = 19
    REG_Y_LEN = 22
    REG_Z_LEN = 23
    
    REG_X_MASK = (1 << REG_X_LEN) - 1
    REG_Y_MASK = (1 << REG_Y_LEN) - 1
    REG_Z_MASK = (1 << REG_Z_LEN) - 1
    
    REG_X_TAPS = [18, 17, 16, 13]
    REG_Y_TAPS = [21, 20]
    REG_Z_TAPS = [22, 21, 20, 7]
    
    CLOCK_BIT_X = 8
    CLOCK_BIT_Y = 10
    CLOCK_BIT_Z = 10
    
    KEYSTREAM_BITS_PER_FRAME = 228
    KEY_BITS = 64
    FRAME_BITS = 22
    
    def __init__(self, key_hex):
        self.key = self._parse_key(key_hex)
        self.reg_x = 0
        self.reg_y = 0
        self.reg_z = 0
    
    def _parse_key(self, key_hex):
        key_hex = key_hex.replace(" ", "").replace("0x", "")
        if len(key_hex) > 16:
            key_hex = key_hex[:16]
        elif len(key_hex) < 16:
            key_hex = key_hex.zfill(16)
        return int(key_hex, 16)
    
    def _reset_registers(self):
        self.reg_x = 0
        self.reg_y = 0
        self.reg_z = 0
    
    def _clock_x(self):
        feedback = 0
        for tap in self.REG_X_TAPS:
            feedback ^= (self.reg_x >> tap) & 1
        output = self.reg_x & 1
        self.reg_x = ((self.reg_x >> 1) | (feedback << (self.REG_X_LEN - 1))) & self.REG_X_MASK
        return output
    
    def _clock_y(self):
        feedback = 0
        for tap in self.REG_Y_TAPS:
            feedback ^= (self.reg_y >> tap) & 1
        output = self.reg_y & 1
        self.reg_y = ((self.reg_y >> 1) | (feedback << (self.REG_Y_LEN - 1))) & self.REG_Y_MASK
        return output
    
    def _clock_z(self):
        feedback = 0
        for tap in self.REG_Z_TAPS:
            feedback ^= (self.reg_z >> tap) & 1
        output = self.reg_z & 1
        self.reg_z = ((self.reg_z >> 1) | (feedback << (self.REG_Z_LEN - 1))) & self.REG_Z_MASK
        return output
    
    def _clock_all(self):
        self._clock_x()
        self._clock_y()
        self._clock_z()
    
    def _majority(self):
        x_bit = (self.reg_x >> self.CLOCK_BIT_X) & 1
        y_bit = (self.reg_y >> self.CLOCK_BIT_Y) & 1
        z_bit = (self.reg_z >> self.CLOCK_BIT_Z) & 1
        return 1 if (x_bit + y_bit + z_bit) >= 2 else 0
    
    def _clock_majority(self):
        maj = self._majority()
        
        if ((self.reg_x >> self.CLOCK_BIT_X) & 1) == maj:
            self._clock_x()
        if ((self.reg_y >> self.CLOCK_BIT_Y) & 1) == maj:
            self._clock_y()
        if ((self.reg_z >> self.CLOCK_BIT_Z) & 1) == maj:
            self._clock_z()
        
        return (self.reg_x & 1) ^ (self.reg_y & 1) ^ (self.reg_z & 1)
    
    def _load_key(self):
        for i in range(self.KEY_BITS):
            self._clock_all()
            key_bit = (self.key >> i) & 1
            self.reg_x ^= key_bit
            self.reg_y ^= key_bit
            self.reg_z ^= key_bit
    
    def _load_frame_number(self, frame_number):
        for i in range(self.FRAME_BITS):
            self._clock_all()
            fn_bit = (frame_number >> i) & 1
            self.reg_x ^= fn_bit
            self.reg_y ^= fn_bit
            self.reg_z ^= fn_bit
    
    def _run_empty_clocks(self, count=100):
        for _ in range(count):
            self._clock_majority()
    
    def _generate_keystream(self, num_bits):
        keystream = []
        for _ in range(num_bits):
            keystream.append(self._clock_majority())
        return keystream
    
    def setup_frame(self, frame_number):
        self._reset_registers()
        self._load_key()
        self._load_frame_number(frame_number)
        self._run_empty_clocks(100)
    
    def get_keystream_for_frame(self, frame_number, num_bits=228):
        """Get keystream for a specific frame number."""
        self.setup_frame(frame_number)
        return self._generate_keystream(num_bits)
    
    def transform(self, bit_list):
        result = []
        frame_number = 0
        
        for i in range(0, len(bit_list), self.KEYSTREAM_BITS_PER_FRAME):
            block = bit_list[i:i + self.KEYSTREAM_BITS_PER_FRAME]
            keystream = self.get_keystream_for_frame(frame_number)
            
            for j, bit in enumerate(block):
                result.append(bit ^ keystream[j])
            
            frame_number += 1
        
        return result
    
    def encrypt(self, data):
        """Encrypt bytes data and return encrypted bytes."""
        from function import bytes_to_bits, bits_to_bytes
        bits = bytes_to_bits(data)
        encrypted_bits = self.transform(bits)
        return bits_to_bytes(encrypted_bits)
    
    def decrypt(self, data):
        """Decrypt bytes data and return decrypted bytes."""
        return self.encrypt(data)


def generate_key_from_password(password):
    """Generate a 64-bit hex key from a password string using simple hash."""
    import hashlib
    hash_bytes = hashlib.sha256(password.encode('utf-8')).digest()
    return hash_bytes[:8].hex().upper()
