import cv2
import os
import subprocess
import tempfile
import shutil

class VideoProcessor:
    def __init__(self, path):
        self.path = path
        self.cap = None
        self.w = 0
        self.h = 0
        self.fps = 0
        self.total_frames = 0
        self._open()
    
    def _open(self):
        self.cap = cv2.VideoCapture(self.path)
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video: {self.path}")
        
        self.w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    def get_info(self):
        return self.w, self.h, self.fps, self.total_frames
    
    def get_total_pixels(self):
        return self.total_frames * self.w * self.h
    
    def read_frame(self, frame_idx=None):
        """Read a specific frame or next frame."""
        if frame_idx is not None:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame
    
    def reset(self):
        """Reset to beginning of video."""
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    def release(self):
        if self.cap:
            self.cap.release()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class VideoWriter:
    def __init__(self, path, w, h, fps):
        self.path = path
        self.w = w
        self.h = h
        self.fps = fps
        fourcc = cv2.VideoWriter_fourcc(*'FFV1')
        self.out = cv2.VideoWriter(path, fourcc, fps, (w, h))
        if not self.out.isOpened():
            raise ValueError(f"Cannot create video writer for: {path}")
    
    def write_frame(self, frame):
        self.out.write(frame)
    
    def release(self):
        if self.out:
            self.out.release()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def check_ffmpeg():
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def extract_audio(video_path, audio_path):
    """Extract audio from video using ffmpeg."""
    if not check_ffmpeg():
        return False
    
    try:
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-vn', '-acodec', 'copy', audio_path
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return result.returncode == 0 and os.path.exists(audio_path)
    except Exception:
        return False


def has_audio(video_path):
    if not check_ffmpeg():
        return False
    
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'a',
            '-show_entries', 'stream=codec_type', '-of', 'csv=p=0',
            video_path
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return b'audio' in result.stdout
    except Exception:
        return False


def mux_audio_video(video_path, audio_path, output_path):
    if not check_ffmpeg():
        return False
    
    try:
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0',
            output_path
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return result.returncode == 0
    except Exception:
        return False


def process_video_with_audio(input_path, output_path, frame_processor_func, progress_callback=None):
    temp_dir = tempfile.mkdtemp()
    temp_video = os.path.join(temp_dir, 'temp_video.avi')
    temp_audio = os.path.join(temp_dir, 'temp_audio.aac')
    
    try:
        video_has_audio = has_audio(input_path)
        if video_has_audio:
            extract_audio(input_path, temp_audio)
        
        with VideoProcessor(input_path) as reader:
            w, h, fps, total = reader.get_info()
            
            with VideoWriter(temp_video, w, h, fps) as writer:
                for frame_idx in range(total):
                    frame = reader.read_frame()
                    if frame is None:
                        break
                    
                    processed = frame_processor_func(frame, frame_idx)
                    writer.write_frame(processed)
                    
                    if progress_callback:
                        progress_callback(frame_idx + 1, total)
        
        if video_has_audio and os.path.exists(temp_audio):
            success = mux_audio_video(temp_video, temp_audio, output_path)
            if not success:
                shutil.copy(temp_video, output_path)
        else:
            shutil.copy(temp_video, output_path)
        
        return True
        
    except Exception as e:
        raise e
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def load_video(path):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return None, 0, 0, 0
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    return frames, w, h, fps


def save_video(frames, w, h, fps, path):
    out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'FFV1'), fps, (w, h))
    for f in frames: out.write(f)
    out.release()


def get_video_capacity(path, lsb_mode='332'):
    from function import get_bits_per_pixel
    
    with VideoProcessor(path) as vp:
        total_pixels = vp.get_total_pixels()
        bits_per_pixel = get_bits_per_pixel(lsb_mode)
        return total_pixels * bits_per_pixel
