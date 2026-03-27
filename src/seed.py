import random
import hashlib


def coordinates(idx, w, h):
    pixels_per_frame = w * h
    f_idx = idx // pixels_per_frame
    rem = idx % pixels_per_frame
    y = rem // w
    x = rem % w
    return f_idx, y, x


def pixel_to_index(frame_idx, y, x, w, h):
    return frame_idx * (w * h) + y * w + x


def random_seed(seed, total, limit):
    if isinstance(seed, str):
        hash_val = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
        random.seed(hash_val)
    else:
        random.seed(seed)
    
    if total > limit:
        raise ValueError(f"Cannot sample {total} items from range of {limit}")
    
    return random.sample(range(limit), total)


def get_frame_pixel_indices(stego_key, num_pixels, frame_width, frame_height, use_random=True):
    total_pixels = frame_width * frame_height
    
    if num_pixels > total_pixels:
        raise ValueError(f"Cannot embed {num_pixels} pixels in frame with {total_pixels} pixels")
    
    if use_random:
        indices = random_seed(stego_key, num_pixels, total_pixels)
    else:
        indices = list(range(num_pixels))
    
    coords = []
    for idx in indices:
        y = idx // frame_width
        x = idx % frame_width
        coords.append((y, x))
    
    return coords


class FramePixelGenerator:
    def __init__(self, w, h, stego_key=None, use_random=True):
        self.w = w
        self.h = h
        self.pixels_per_frame = w * h
        self.stego_key = stego_key
        self.use_random = use_random
        self._frame_indices_cache = {}
    
    def _get_frame_seed(self, frame_idx):
        if self.stego_key is None:
            return frame_idx
        
        key_str = f"{self.stego_key}_{frame_idx}"
        return int(hashlib.sha256(key_str.encode()).hexdigest(), 16)
    
    def get_indices_for_frame(self, frame_idx, num_pixels=None):
        if num_pixels is None:
            num_pixels = self.pixels_per_frame
        
        num_pixels = min(num_pixels, self.pixels_per_frame)
        
        cache_key = (frame_idx, num_pixels)
        if cache_key in self._frame_indices_cache:
            return self._frame_indices_cache[cache_key]
        
        if self.use_random:
            seed = self._get_frame_seed(frame_idx)
            random.seed(seed)
            flat_indices = random.sample(range(self.pixels_per_frame), num_pixels)
        else:
            flat_indices = list(range(num_pixels))
        
        coords = [(idx // self.w, idx % self.w) for idx in flat_indices]
        
        self._frame_indices_cache[cache_key] = coords
        return coords
    
    def get_pixel_at_position(self, frame_idx, position_in_frame):
        indices = self.get_indices_for_frame(frame_idx)
        if position_in_frame >= len(indices):
            raise IndexError(f"Position {position_in_frame} out of range for frame {frame_idx}")
        return indices[position_in_frame]
    
    def clear_cache(self):
        self._frame_indices_cache.clear()


class EmbedPositionCalculator:
    def __init__(self, w, h, total_frames, lsb_mode='332', stego_key=None, use_random=True):
        from function import get_bits_per_pixel
        
        self.w = w
        self.h = h
        self.total_frames = total_frames
        self.pixels_per_frame = w * h
        self.bits_per_pixel = get_bits_per_pixel(lsb_mode)
        self.bits_per_frame = self.pixels_per_frame * self.bits_per_pixel
        self.total_capacity = self.bits_per_frame * total_frames
        
        self.pixel_gen = FramePixelGenerator(w, h, stego_key, use_random)
    
    def get_capacity(self):
        return self.total_capacity
    
    def get_capacity_bytes(self):
        return self.total_capacity // 8
    
    def bits_needed_for_frame(self, frame_idx, total_bits, header_frames=1):
        if frame_idx < header_frames:
            return 0
        
        payload_frame_idx = frame_idx - header_frames
        bits_before = payload_frame_idx * self.bits_per_frame
        
        if bits_before >= total_bits:
            return 0
        
        remaining = total_bits - bits_before
        return min(remaining, self.bits_per_frame)
    
    def get_pixel_coords_for_frame(self, frame_idx, num_pixels=None):
        return self.pixel_gen.get_indices_for_frame(frame_idx, num_pixels)
