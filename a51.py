class A51:
    def __init__(self, key_hex):
        key_int = int(key_hex, 16)
        self.initial_x = (key_int >> 45) & 0x7FFFF
        self.initial_y = (key_int >> 23) & 0x3FFFFF
        self.initial_z = key_int & 0x7FFFFF
        self.reset()
    
    def reset(self):
        self.reg_x = self.initial_x
        self.reg_y = self.initial_y
        self.reg_z = self.initial_z
    
    def majority(self):
        x8 = (self.reg_x >> 8) & 1
        y10 = (self.reg_y >> 10) & 1
        z10 = (self.reg_z >> 10) & 1
        if (x8 + y10 + z10) >= 2:
            return 1
        else:
            return 0
        
    def step(self):
        m = self.majority()
        if ((self.reg_x >> 8) & 1) == m:
            t = ((self.reg_x >> 18) ^ (self.reg_x >> 17) ^ (self.reg_x >> 16) ^ (self.reg_x >> 13)) & 1
            self.reg_x = ((self.reg_x << 1) | t) & 0x7FFFF
        if ((self.reg_y >> 10) & 1) == m:
            t = ((self.reg_y >> 21) ^ (self.reg_y >> 20)) & 1
            self.reg_y = ((self.reg_y << 1) | t) & 0x3FFFFF
        if ((self.reg_z >> 10) & 1) == m:
            t = ((self.reg_z >> 22) ^ (self.reg_z >> 21) ^ (self.reg_z >> 20) ^ (self.reg_z >> 7)) & 1
            self.reg_z = ((self.reg_z << 1) | t) & 0x7FFFFF
        return (self.reg_x ^ self.reg_y ^ self.reg_z) & 1
    
    def transform(self, bit_list):
        self.reset()
        res = []
        for i in range(0, len(bit_list), 228):
            block = bit_list[i : i + 228]
            for b in block:
                res.append(b ^ self.step())
        return res