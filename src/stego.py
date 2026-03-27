import os
import tempfile
import shutil
from video import VideoProcessor, VideoWriter, extract_audio, mux_audio_video, has_audio
from function import (
    bytes_to_bits, bits_to_bytes, file_to_bits, bits_to_file,
    create_header, parse_header, put, extract_from_pixel, merge,
    get_bits_per_pixel, get_lsb_config, int_to_bits, bits_to_int
)
from seed import FramePixelGenerator
from a51 import A51, generate_key_from_password


class StegoError(Exception):
    pass


class VideoSteganography:
    HEADER_FRAME = 0
    PAYLOAD_START_FRAME = 1
    
    def __init__(self, lsb_mode='332'):
        self.lsb_mode = lsb_mode
        self.bits_per_pixel = get_bits_per_pixel(lsb_mode)
    
    def _embed_bits_in_frame(self, frame, bits, pixel_coords):
        config = get_lsb_config(self.lsb_mode)
        bits_per_pix = config['total']
        
        bit_idx = 0
        for i, (y, x) in enumerate(pixel_coords):
            if bit_idx >= len(bits):
                break
            
            chunk = bits[bit_idx:bit_idx + bits_per_pix]
            if len(chunk) < bits_per_pix:
                chunk = chunk + [0] * (bits_per_pix - len(chunk))
            
            value = bits_to_int(chunk)
            
            if self.lsb_mode == '332':
                r_bits = (value >> 5) & 0x07
                g_bits = (value >> 2) & 0x07
                b_bits = value & 0x03
            elif self.lsb_mode == '222':
                r_bits = (value >> 4) & 0x03
                g_bits = (value >> 2) & 0x03
                b_bits = value & 0x03
            elif self.lsb_mode == '111':
                r_bits = (value >> 2) & 0x01
                g_bits = (value >> 1) & 0x01
                b_bits = value & 0x01
            
            frame[y, x] = put(frame[y, x], r_bits, g_bits, b_bits, self.lsb_mode)
            bit_idx += bits_per_pix
        
        return bit_idx
    
    def _extract_bits_from_frame(self, frame, num_bits, pixel_coords):
        config = get_lsb_config(self.lsb_mode)
        bits_per_pix = config['total']
        
        extracted = []
        for i, (y, x) in enumerate(pixel_coords):
            if len(extracted) >= num_bits:
                break
            
            r_bits, g_bits, b_bits = extract_from_pixel(frame[y, x], self.lsb_mode)
            value = merge(r_bits, g_bits, b_bits, self.lsb_mode)
            
            value_bits = int_to_bits(value, bits_per_pix)
            extracted.extend(value_bits)
        
        return extracted[:num_bits]
    
    def calculate_capacity(self, video_path):
        with VideoProcessor(video_path) as vp:
            w, h, fps, total_frames = vp.get_info()
            
            pixels_per_frame = w * h
            
            header_bits = pixels_per_frame * 3
            payload_frames = total_frames - 1
            payload_bits = payload_frames * pixels_per_frame * self.bits_per_pixel
            
            return {
                'total_frames': total_frames,
                'width': w,
                'height': h,
                'fps': fps,
                'header_capacity_bits': header_bits,
                'payload_capacity_bits': payload_bits,
                'payload_capacity_bytes': payload_bits // 8,
                'bits_per_pixel': self.bits_per_pixel
            }
    
    def embed(self, video_path, output_path, payload_data, extension='', use_encryption=False, encryption_key=None, use_random=False, stego_key=None, progress_callback=None):
        if isinstance(payload_data, str):
            payload_data = payload_data.encode('utf-8')
        
        capacity = self.calculate_capacity(video_path)
        payload_bytes = len(payload_data)
        
        estimated_total_bytes = 100 + payload_bytes
        if estimated_total_bytes > capacity['payload_capacity_bytes']:
            raise StegoError(
                f"Payload too large. Needed: {payload_bytes:,} bytes, "
                f"Available: {capacity['payload_capacity_bytes']:,} bytes"
            )
        
        payload_bits = bytes_to_bits(payload_data)
        
        
        if use_encryption and encryption_key:
            if len(encryption_key) < 16:
                encryption_key = generate_key_from_password(encryption_key)
            a51 = A51(encryption_key)
            payload_bits = a51.transform(payload_bits)
        
        header_bits = create_header(
            len(payload_bits), extension, use_encryption, use_random, self.lsb_mode
        )
        
        temp_dir = tempfile.mkdtemp()
        temp_video = os.path.join(temp_dir, 'temp_stego.avi')
        temp_audio = os.path.join(temp_dir, 'temp_audio.aac')
        
        try:
            video_has_audio = has_audio(video_path)
            audio_extracted = False
            if video_has_audio:
                audio_extracted = extract_audio(video_path, temp_audio)
                if not audio_extracted:
                    print("Warning: Audio extraction failed, output will have no audio")
            
            with VideoProcessor(video_path) as reader:
                w, h, fps, total_frames = reader.get_info()
                
                header_pixel_gen = FramePixelGenerator(w, h, stego_key=None, use_random=False)
                payload_pixel_gen = FramePixelGenerator(w, h, stego_key, use_random)
                
                pixels_per_frame = w * h
                
                payload_bit_idx = 0
                
                with VideoWriter(temp_video, w, h, fps) as writer:
                    for frame_idx in range(total_frames):
                        frame = reader.read_frame()
                        if frame is None:
                            break
                        
                        if frame_idx == self.HEADER_FRAME:
                            bits_per_pixel_header = 3
                            pixels_needed = (len(header_bits) + bits_per_pixel_header - 1) // bits_per_pixel_header
                            header_coords = header_pixel_gen.get_indices_for_frame(0, pixels_needed)
                            old_mode = self.lsb_mode
                            old_bpp = self.bits_per_pixel
                            self.lsb_mode = '111'
                            self.bits_per_pixel = 3
                            self._embed_bits_in_frame(frame, header_bits, header_coords)
                            self.lsb_mode = old_mode
                            self.bits_per_pixel = old_bpp
                        
                        elif payload_bit_idx < len(payload_bits):
                            remaining = len(payload_bits) - payload_bit_idx
                            bits_this_frame = min(remaining, pixels_per_frame * self.bits_per_pixel)
                            
                            chunk = payload_bits[payload_bit_idx:payload_bit_idx + bits_this_frame]
                            pixels_needed = (bits_this_frame + self.bits_per_pixel - 1) // self.bits_per_pixel
                            
                            coords = payload_pixel_gen.get_indices_for_frame(frame_idx, pixels_needed)
                            self._embed_bits_in_frame(frame, chunk, coords)
                            
                            payload_bit_idx += bits_this_frame
                        
                        writer.write_frame(frame)
                        
                        if progress_callback:
                            status = "Embedding" if payload_bit_idx < len(payload_bits) else "Finalizing"
                            progress_callback(frame_idx + 1, total_frames, status)
            
            if audio_extracted and os.path.exists(temp_audio):
                success = mux_audio_video(temp_video, temp_audio, output_path)
                if not success:
                    print("Muxing failed, copying video without audio")
                    shutil.copy(temp_video, output_path)
            else:
                shutil.copy(temp_video, output_path)
            
            return {
                'success': True,
                'output_path': output_path,
                'payload_size_bits': len(payload_bits),
                'payload_size_bytes': len(payload_data),
                'frames_used': (len(payload_bits) + pixels_per_frame * self.bits_per_pixel - 1) // (pixels_per_frame * self.bits_per_pixel) + 1,
                'total_frames': total_frames,
                'has_audio': video_has_audio
            }
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def embed_file(self, video_path, output_path, file_path,
                   use_encryption=False, encryption_key=None,
                   use_random=False, stego_key=None, progress_callback=None):
        with open(file_path, 'rb') as f:
            payload_data = f.read()
        
        extension = os.path.splitext(file_path)[1]
        
        return self.embed(
            video_path, output_path, payload_data,
            extension, use_encryption, encryption_key,
            use_random, stego_key, progress_callback
        )
    
    def extract(self, video_path, encryption_key=None, stego_key=None, progress_callback=None):
        with VideoProcessor(video_path) as reader:
            w, h, fps, total_frames = reader.get_info()
            
            header_frame = reader.read_frame(self.HEADER_FRAME)
            if header_frame is None:
                raise StegoError("Cannot read header frame")
            
            header_pixel_gen = FramePixelGenerator(w, h, stego_key=None, use_random=False)
            
            max_header_bits = 600
            bits_per_pixel_header = 3
            pixels_needed = (max_header_bits + bits_per_pixel_header - 1) // bits_per_pixel_header
            
            header_coords = header_pixel_gen.get_indices_for_frame(0, pixels_needed)
            
            old_mode = self.lsb_mode
            old_bpp = self.bits_per_pixel
            self.lsb_mode = '111'
            self.bits_per_pixel = 3
            header_bits = self._extract_bits_from_frame(header_frame, max_header_bits, header_coords)
            
            try:
                payload_length, extension, use_encryption, use_random, lsb_mode, header_size = parse_header(header_bits)
            except Exception as e:
                self.lsb_mode = old_mode
                self.bits_per_pixel = old_bpp
                raise StegoError(f"Invalid header: {e}")
            
            pixels_per_frame = w * h
            max_capacity_bits = (total_frames - 1) * pixels_per_frame * get_bits_per_pixel(lsb_mode)
            
            if payload_length < 0 or payload_length > max_capacity_bits:
                self.lsb_mode = old_mode
                self.bits_per_pixel = old_bpp
                raise StegoError(
                    f"Video ini tidak mengandung pesan steganografi yang valid (Header Corrupt). "
                    f"Payload length: {payload_length} bits, Max capacity: {max_capacity_bits} bits"
                )
            
            self.lsb_mode = lsb_mode
            self.bits_per_pixel = get_bits_per_pixel(lsb_mode)
            
            if progress_callback:
                progress_callback(1, total_frames, "Header parsed")
            
            payload_pixel_gen = FramePixelGenerator(w, h, stego_key if use_random else None, use_random)
            
            bits_per_frame = pixels_per_frame * self.bits_per_pixel
            
            extracted_bits = []
            reader.reset()
            
            for frame_idx in range(total_frames):
                frame = reader.read_frame()
                if frame is None:
                    break
                
                if frame_idx < self.PAYLOAD_START_FRAME:
                    continue
                
                if len(extracted_bits) >= payload_length:
                    break
                
                remaining = payload_length - len(extracted_bits)
                bits_this_frame = min(remaining, bits_per_frame)
                pixels_needed = (bits_this_frame + self.bits_per_pixel - 1) // self.bits_per_pixel
                
                coords = payload_pixel_gen.get_indices_for_frame(frame_idx, pixels_needed)
                frame_bits = self._extract_bits_from_frame(frame, bits_this_frame, coords)
                extracted_bits.extend(frame_bits)
                
                if progress_callback:
                    progress_callback(frame_idx + 1, total_frames, "Extracting")
            
            extracted_bits = extracted_bits[:payload_length]
            
            if use_encryption:
                if not encryption_key:
                    raise StegoError("Encrypted payload requires encryption key")
                if len(encryption_key) < 16:
                    encryption_key = generate_key_from_password(encryption_key)
                a51 = A51(encryption_key)
                extracted_bits = a51.transform(extracted_bits)
            
            payload_data = bits_to_bytes(extracted_bits)
            
            self.lsb_mode = old_mode
            self.bits_per_pixel = old_bpp
            
            return {
                'success': True,
                'data': payload_data,
                'extension': extension,
                'size_bytes': len(payload_data),
                'was_encrypted': use_encryption,
                'was_random': use_random,
                'lsb_mode': lsb_mode
            }
    
    def extract_to_file(self, video_path, output_dir, encryption_key=None, stego_key=None, output_filename=None, progress_callback=None):
        result = self.extract(video_path, encryption_key, stego_key, progress_callback)
        
        if not result['success']:
            return result
        
        if output_dir and os.path.splitext(output_dir)[1]:
            output_path = output_dir
            output_base_dir = os.path.dirname(output_path) or '.'
            if not os.path.exists(output_base_dir):
                os.makedirs(output_base_dir, exist_ok=True)
        else:
            if output_filename:
                filename = output_filename
            else:
                extension = result['extension'] if result['extension'] else '.bin'
                filename = f"extracted{extension}"
            
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            output_path = os.path.join(output_dir, filename)
            
            counter = 1
            base, ext = os.path.splitext(output_path)
            while os.path.exists(output_path):
                output_path = f"{base}_{counter}{ext}"
                counter += 1
        
        with open(output_path, 'wb') as f:
            f.write(result['data'])
        
        result['output_path'] = output_path
        return result


def quick_embed(video_path, output_path, message, lsb_mode='332', use_encryption=False, encryption_key=None, use_random=False, stego_key=None):
    stego = VideoSteganography(lsb_mode)
    return stego.embed(
        video_path, output_path, message.encode('utf-8'),
        '.txt', use_encryption, encryption_key, use_random, stego_key
    )


def quick_extract(video_path, encryption_key=None, stego_key=None):
    stego = VideoSteganography()
    result = stego.extract(video_path, encryption_key, stego_key)
    if result['success']:
        try:
            result['message'] = result['data'].decode('utf-8')
        except:
            result['message'] = None
    return result
