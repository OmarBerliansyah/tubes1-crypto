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
    def __init__(self, path, w, h, fps, use_ffmpeg=True):
        self.path = path
        self.w = w
        self.h = h
        self.fps = fps
        self.use_ffmpeg = use_ffmpeg and check_ffmpeg()
        self.process = None
        self.out = None
        self.frame_count = 0
        
        if self.use_ffmpeg:
            self._init_ffmpeg()
        else:
            self._init_opencv()
    
    def _init_ffmpeg(self):
        """Initialize ffmpeg pipe with FFV1 lossless codec for steganography."""
        try:
            cmd = [
                'ffmpeg',
                '-y',
                '-hide_banner',
                '-loglevel', 'error',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{self.w}x{self.h}',
                '-pix_fmt', 'bgr24',
                '-r', str(self.fps),
                '-i', '-',
                '-c:v', 'ffv1', 
                '-level', '3',   
                '-slices', '4',  
                '-f', 'avi',
                self.path
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
        except Exception as e:
            print(f"FFmpeg initialization failed: {e}. Falling back to OpenCV.")
            self.use_ffmpeg = False
            self._init_opencv()
    
    def _init_opencv(self):
        """Fallback to OpenCV VideoWriter with MJPEG."""
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.out = cv2.VideoWriter(self.path, fourcc, self.fps, (self.w, self.h))
        if not self.out.isOpened():
            raise ValueError(f"Cannot create video writer for: {self.path}")
    
    def write_frame(self, frame):
        """Write a frame to the video."""
        if self.use_ffmpeg and self.process:
            try:
                self.process.stdin.write(frame.tobytes())
                self.frame_count += 1
            except Exception as e:
                print(f"Error writing frame via ffmpeg: {e}")
        elif self.out:
            self.out.write(frame)
            self.frame_count += 1
    
    def release(self):
        """Close the video writer."""
        if self.use_ffmpeg and self.process:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=30)
            except Exception as e:
                print(f"Error closing ffmpeg process: {e}")
                try:
                    self.process.terminate()
                except:
                    pass
        elif self.out:
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
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-i', video_path,
            '-vn', '-acodec', 'aac', audio_path
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        success = result.returncode == 0 and os.path.exists(audio_path)
        if not success and result.stderr:
            print(f"Audio extraction stderr: {result.stderr.decode('utf-8', errors='ignore')}")
        return success
    except Exception as e:
        print(f"Exception in extract_audio: {e}")
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
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
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
        if result.returncode == 0:
            return True
        else:
            print(f"Mux audio/video failed: {result.stderr.decode('utf-8', errors='ignore')}")
            return False
    except Exception as e:
        print(f"Exception in mux_audio_video: {e}")
        return False
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
    """Save video using ffmpeg with FFV1 lossless codec for steganography."""
    if check_ffmpeg():
        try:
            cmd = [
                'ffmpeg',
                '-y',
                '-hide_banner',
                '-loglevel', 'error',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{w}x{h}',
                '-pix_fmt', 'bgr24',
                '-r', str(fps),
                '-i', '-',
                '-c:v', 'ffv1',
                '-level', '3',
                '-slices', '4',
                '-f', 'avi',
                path
            ]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            for frame in frames:
                process.stdin.write(frame.tobytes())
            
            process.stdin.close()
            process.wait()
            
            if process.returncode != 0:
                print(f"FFmpeg save warning: return code {process.returncode}")
        except Exception as e:
            print(f"FFmpeg save failed: {e}. Falling back to OpenCV.")
            out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'MJPG'), fps, (w, h))
            for f in frames:
                out.write(f)
            out.release()
    else:
        out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'MJPG'), fps, (w, h))
        for f in frames:
            out.write(f)
        out.release()


def get_video_capacity(path, lsb_mode='332'):
    from function import get_bits_per_pixel
    
    with VideoProcessor(path) as vp:
        total_pixels = vp.get_total_pixels()
        bits_per_pixel = get_bits_per_pixel(lsb_mode)
        return total_pixels * bits_per_pixel
