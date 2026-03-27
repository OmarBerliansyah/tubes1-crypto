import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stego import VideoSteganography, StegoError
from video import VideoProcessor, check_ffmpeg
from metric import (
    metrics_streaming, plot_histogram_comparison, 
    plot_histogram_overlay, compare_histograms
)


class StegoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Steganography - A5/1 & LSB")
        self.root.geometry("800x700")
        self.root.minsize(700, 600)
        
        self.video_path = tk.StringVar()
        self.payload_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.stego_video_path = tk.StringVar()
        self.extract_output_dir = tk.StringVar()
        
        self.lsb_mode = tk.StringVar(value='332')
        self.use_encryption = tk.BooleanVar(value=False)
        self.encryption_key = tk.StringVar()
        self.use_random = tk.BooleanVar(value=False)
        self.stego_key = tk.StringVar()
        
        self.use_text_message = tk.BooleanVar(value=True)
        
        self.is_processing = False
        
        self._create_widgets()
        self._check_dependencies()
    
    def _create_widgets(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        embed_frame = ttk.Frame(notebook, padding=10)
        extract_frame = ttk.Frame(notebook, padding=10)
        analysis_frame = ttk.Frame(notebook, padding=10)
        
        notebook.add(embed_frame, text="Embed")
        notebook.add(extract_frame, text="Extract")
        notebook.add(analysis_frame, text="Analysis")
        
        self._create_embed_tab(embed_frame)
        self._create_extract_tab(extract_frame)
        self._create_analysis_tab(analysis_frame)
        
        self.status_frame = ttk.Frame(self.root, padding=5)
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.progress = ttk.Progressbar(self.status_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=2)
        
        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.pack(anchor=tk.W)
    
    def _create_embed_tab(self, parent):
        video_frame = ttk.LabelFrame(parent, text="Cover Video", padding=10)
        video_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(video_frame, textvariable=self.video_path, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(video_frame, text="Browse", command=self._browse_video).pack(side=tk.LEFT, padx=5)
        
        self.video_info_label = ttk.Label(video_frame, text="")
        self.video_info_label.pack(anchor=tk.W, pady=5)
        
        payload_frame = ttk.LabelFrame(parent, text="Payload", padding=10)
        payload_frame.pack(fill=tk.X, pady=5)
        
        type_frame = ttk.Frame(payload_frame)
        type_frame.pack(fill=tk.X)
        ttk.Radiobutton(type_frame, text="Text Message", variable=self.use_text_message, 
                       value=True, command=self._toggle_payload_type).pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="File", variable=self.use_text_message, 
                       value=False, command=self._toggle_payload_type).pack(side=tk.LEFT, padx=20)
        
        self.text_frame = ttk.Frame(payload_frame)
        self.text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.message_text = scrolledtext.ScrolledText(self.text_frame, height=4, width=60)
        self.message_text.pack(fill=tk.BOTH, expand=True)
        
        self.file_frame = ttk.Frame(payload_frame)
        file_row = ttk.Frame(self.file_frame)
        file_row.pack(fill=tk.X)
        ttk.Entry(file_row, textvariable=self.payload_path, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(file_row, text="Browse", command=self._browse_payload).pack(side=tk.LEFT, padx=5)
        self.payload_info_label = ttk.Label(self.file_frame, text="")
        self.payload_info_label.pack(anchor=tk.W)
        
        config_frame = ttk.LabelFrame(parent, text="Configuration", padding=10)
        config_frame.pack(fill=tk.X, pady=5)
        
        lsb_frame = ttk.Frame(config_frame)
        lsb_frame.pack(fill=tk.X, pady=5)
        ttk.Label(lsb_frame, text="LSB Mode:").pack(side=tk.LEFT)
        for mode, label in [('111', '1-1-1 (3 bits/pixel)'), 
                           ('222', '2-2-2 (6 bits/pixel)'), 
                           ('332', '3-3-2 (8 bits/pixel)')]:
            ttk.Radiobutton(lsb_frame, text=label, variable=self.lsb_mode, value=mode).pack(side=tk.LEFT, padx=10)
        
        enc_frame = ttk.Frame(config_frame)
        enc_frame.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(enc_frame, text="Enable A5/1 Encryption", 
                       variable=self.use_encryption, command=self._toggle_encryption).pack(side=tk.LEFT)
        self.enc_key_frame = ttk.Frame(enc_frame)
        ttk.Label(self.enc_key_frame, text="Key:").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Entry(self.enc_key_frame, textvariable=self.encryption_key, width=30, show="*").pack(side=tk.LEFT)
        
        spread_frame = ttk.Frame(config_frame)
        spread_frame.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(spread_frame, text="Random Pixel Spreading", 
                       variable=self.use_random, command=self._toggle_random).pack(side=tk.LEFT)
        self.stego_key_frame = ttk.Frame(spread_frame)
        ttk.Label(self.stego_key_frame, text="Stego Key:").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Entry(self.stego_key_frame, textvariable=self.stego_key, width=30).pack(side=tk.LEFT)
        
        output_frame = ttk.LabelFrame(parent, text="Output", padding=10)
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(output_frame, textvariable=self.output_path, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="Browse", command=self._browse_output).pack(side=tk.LEFT, padx=5)
        
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=10)
        self.embed_btn = ttk.Button(btn_frame, text="Embed", command=self._start_embed)
        self.embed_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Calculate Capacity", command=self._show_capacity).pack(side=tk.LEFT, padx=5)
    
    def _create_extract_tab(self, parent):
        stego_frame = ttk.LabelFrame(parent, text="Stego Video", padding=10)
        stego_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(stego_frame, textvariable=self.stego_video_path, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(stego_frame, text="Browse", command=self._browse_stego_video).pack(side=tk.LEFT, padx=5)
        
        key_frame = ttk.LabelFrame(parent, text="Keys (if required)", padding=10)
        key_frame.pack(fill=tk.X, pady=5)
        
        enc_row = ttk.Frame(key_frame)
        enc_row.pack(fill=tk.X, pady=5)
        ttk.Label(enc_row, text="A5/1 Encryption Key:").pack(side=tk.LEFT)
        self.extract_enc_key = ttk.Entry(enc_row, width=40, show="*")
        self.extract_enc_key.pack(side=tk.LEFT, padx=10)
        
        stego_row = ttk.Frame(key_frame)
        stego_row.pack(fill=tk.X, pady=5)
        ttk.Label(stego_row, text="Stego Key:").pack(side=tk.LEFT)
        self.extract_stego_key = ttk.Entry(stego_row, width=40)
        self.extract_stego_key.pack(side=tk.LEFT, padx=10)
        
        output_frame = ttk.LabelFrame(parent, text="Output Directory", padding=10)
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(output_frame, textvariable=self.extract_output_dir, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="Browse", command=self._browse_extract_output).pack(side=tk.LEFT, padx=5)
        
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=10)
        self.extract_btn = ttk.Button(btn_frame, text="Extract", command=self._start_extract)
        self.extract_btn.pack(side=tk.LEFT, padx=5)
        
        result_frame = ttk.LabelFrame(parent, text="Extraction Result", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.result_text = scrolledtext.ScrolledText(result_frame, height=10, width=60)
        self.result_text.pack(fill=tk.BOTH, expand=True)
    
    def _create_analysis_tab(self, parent):
        files_frame = ttk.LabelFrame(parent, text="Compare Videos", padding=10)
        files_frame.pack(fill=tk.X, pady=5)
        
        orig_row = ttk.Frame(files_frame)
        orig_row.pack(fill=tk.X, pady=5)
        ttk.Label(orig_row, text="Original Video:").pack(side=tk.LEFT)
        self.analysis_orig = ttk.Entry(orig_row, width=50)
        self.analysis_orig.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        ttk.Button(orig_row, text="Browse", command=lambda: self._browse_for_entry(self.analysis_orig)).pack(side=tk.LEFT)
        
        stego_row = ttk.Frame(files_frame)
        stego_row.pack(fill=tk.X, pady=5)
        ttk.Label(stego_row, text="Stego Video:").pack(side=tk.LEFT)
        self.analysis_stego = ttk.Entry(stego_row, width=50)
        self.analysis_stego.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        ttk.Button(stego_row, text="Browse", command=lambda: self._browse_for_entry(self.analysis_stego)).pack(side=tk.LEFT)
        
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="Calculate MSE/PSNR", command=self._calculate_metrics).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Show Histogram Comparison", command=self._show_histogram).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Show Histogram Overlay", command=self._show_histogram_overlay).pack(side=tk.LEFT, padx=5)
        
        result_frame = ttk.LabelFrame(parent, text="Analysis Results", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.analysis_result = scrolledtext.ScrolledText(result_frame, height=15, width=60)
        self.analysis_result.pack(fill=tk.BOTH, expand=True)
    
    def _toggle_payload_type(self):
        if self.use_text_message.get():
            self.file_frame.pack_forget()
            self.text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        else:
            self.text_frame.pack_forget()
            self.file_frame.pack(fill=tk.X, pady=5)
    
    def _toggle_encryption(self):
        if self.use_encryption.get():
            self.enc_key_frame.pack(side=tk.LEFT)
        else:
            self.enc_key_frame.pack_forget()
    
    def _toggle_random(self):
        if self.use_random.get():
            self.stego_key_frame.pack(side=tk.LEFT)
        else:
            self.stego_key_frame.pack_forget()
    
    def _check_dependencies(self):
        if not check_ffmpeg():
            self.status_label.config(text="Warning: ffmpeg not found. Audio will not be preserved.")
    
    def _browse_video(self):
        path = filedialog.askopenfilename(
            title="Select Cover Video",
            filetypes=[("Video files", "*.avi *.mp4 *.mkv *.mov"), ("All files", "*.*")]
        )
        if path:
            self.video_path.set(path)
            self._update_video_info()
    
    def _browse_payload(self):
        path = filedialog.askopenfilename(title="Select Payload File")
        if path:
            self.payload_path.set(path)
            size = os.path.getsize(path)
            self.payload_info_label.config(text=f"Size: {size:,} bytes ({size * 8:,} bits)")
    
    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save Stego Video As",
            defaultextension=".avi",
            filetypes=[("AVI files", "*.avi"), ("All files", "*.*")]
        )
        if path:
            self.output_path.set(path)
    
    def _browse_stego_video(self):
        path = filedialog.askopenfilename(
            title="Select Stego Video",
            filetypes=[("Video files", "*.avi *.mp4 *.mkv *.mov"), ("All files", "*.*")]
        )
        if path:
            self.stego_video_path.set(path)
    
    def _browse_extract_output(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.extract_output_dir.set(path)
    
    def _browse_for_entry(self, entry):
        path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[("Video files", "*.avi *.mp4 *.mkv *.mov"), ("All files", "*.*")]
        )
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)
    
    def _update_video_info(self):
        path = self.video_path.get()
        if not path or not os.path.exists(path):
            return
        
        try:
            with VideoProcessor(path) as vp:
                w, h, fps, total = vp.get_info()
                info = f"Resolution: {w}x{h} | FPS: {fps:.2f} | Frames: {total}"
                self.video_info_label.config(text=info)
        except Exception as e:
            self.video_info_label.config(text=f"Error: {e}")
    
    def _show_capacity(self):
        path = self.video_path.get()
        if not path or not os.path.exists(path):
            messagebox.showwarning("Warning", "Please select a video first.")
            return
        
        try:
            stego = VideoSteganography(self.lsb_mode.get())
            cap = stego.calculate_capacity(path)
            
            msg = f"""Video Capacity Analysis
========================
Resolution: {cap['width']}x{cap['height']}
Total Frames: {cap['total_frames']}
FPS: {cap['fps']:.2f}

LSB Mode: {self.lsb_mode.get()} ({cap['bits_per_pixel']} bits/pixel)

Header Capacity: {cap['header_capacity_bits']:,} bits
Payload Capacity: {cap['payload_capacity_bits']:,} bits
                 = {cap['payload_capacity_bytes']:,} bytes
                 = {cap['payload_capacity_bytes'] / 1024:.2f} KB
                 = {cap['payload_capacity_bytes'] / (1024*1024):.4f} MB
"""
            messagebox.showinfo("Capacity", msg)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _update_progress(self, current, total, status=""):
        self.progress['value'] = (current / total) * 100
        self.status_label.config(text=f"{status}: {current}/{total} frames")
        self.root.update_idletasks()
    
    def _start_embed(self):
        if self.is_processing:
            return
        
        video_path = self.video_path.get()
        output_path = self.output_path.get()
        
        if not video_path or not os.path.exists(video_path):
            messagebox.showwarning("Warning", "Please select a valid cover video.")
            return
        
        if not output_path:
            messagebox.showwarning("Warning", "Please specify output path.")
            return
        
        if self.use_text_message.get():
            message = self.message_text.get("1.0", tk.END).strip()
            if not message:
                messagebox.showwarning("Warning", "Please enter a message.")
                return
            payload_data = message.encode('utf-8')
            extension = '.txt'
        else:
            payload_path = self.payload_path.get()
            if not payload_path or not os.path.exists(payload_path):
                messagebox.showwarning("Warning", "Please select a payload file.")
                return
            with open(payload_path, 'rb') as f:
                payload_data = f.read()
            extension = os.path.splitext(payload_path)[1]
        
        use_enc = self.use_encryption.get()
        enc_key = self.encryption_key.get() if use_enc else None
        use_random = self.use_random.get()
        stego_key = self.stego_key.get() if use_random else None
        
        if use_enc and not enc_key:
            messagebox.showwarning("Warning", "Please enter encryption key.")
            return
        
        if use_random and not stego_key:
            messagebox.showwarning("Warning", "Please enter stego key.")
            return
        
        self.is_processing = True
        self.embed_btn.config(state=tk.DISABLED)
        
        def embed_thread():
            try:
                stego = VideoSteganography(self.lsb_mode.get())
                result = stego.embed(
                    video_path, output_path, payload_data, extension,
                    use_enc, enc_key, use_random, stego_key,
                    progress_callback=self._update_progress
                )
                
                self.root.after(0, lambda: self._embed_complete(result))
            except Exception as e:
                self.root.after(0, lambda: self._embed_error(str(e)))
        
        threading.Thread(target=embed_thread, daemon=True).start()
    
    def _embed_complete(self, result):
        self.is_processing = False
        self.embed_btn.config(state=tk.NORMAL)
        self.progress['value'] = 100
        self.status_label.config(text="Embedding complete!")
        
        msg = f"""Embedding Successful!
========================
Output: {result['output_path']}
Payload Size: {result['payload_size_bytes']:,} bytes
Frames Used: {result['frames_used']}/{result['total_frames']}
Audio Preserved: {'Yes' if result['has_audio'] else 'No'}
"""
        messagebox.showinfo("Success", msg)
    
    def _embed_error(self, error):
        self.is_processing = False
        self.embed_btn.config(state=tk.NORMAL)
        self.progress['value'] = 0
        self.status_label.config(text=f"Error: {error}")
        messagebox.showerror("Error", error)
    
    def _start_extract(self):
        if self.is_processing:
            return
        
        stego_path = self.stego_video_path.get()
        output_dir = self.extract_output_dir.get()
        
        if not stego_path or not os.path.exists(stego_path):
            messagebox.showwarning("Warning", "Please select a stego video.")
            return
        
        if not output_dir:
            output_dir = os.path.dirname(stego_path)
            self.extract_output_dir.set(output_dir)
        
        enc_key = self.extract_enc_key.get() or None
        stego_key = self.extract_stego_key.get() or None
        
        self.is_processing = True
        self.extract_btn.config(state=tk.DISABLED)
        
        def extract_thread():
            try:
                stego = VideoSteganography()
                result = stego.extract_to_file(
                    stego_path, output_dir, enc_key, stego_key,
                    progress_callback=self._update_progress
                )
                
                self.root.after(0, lambda: self._extract_complete(result))
            except Exception as e:
                self.root.after(0, lambda: self._extract_error(str(e)))
        
        threading.Thread(target=extract_thread, daemon=True).start()
    
    def _extract_complete(self, result):
        self.is_processing = False
        self.extract_btn.config(state=tk.NORMAL)
        self.progress['value'] = 100
        self.status_label.config(text="Extraction complete!")
        
        self.result_text.delete("1.0", tk.END)
        
        info = f"""Extraction Successful!
========================
Output File: {result.get('output_path', 'N/A')}
Extension: {result['extension']}
Size: {result['size_bytes']:,} bytes
Was Encrypted: {result['was_encrypted']}
Was Random: {result['was_random']}
LSB Mode: {result['lsb_mode']}
"""
        
        if result['extension'] == '.txt' or not result['extension']:
            try:
                text = result['data'].decode('utf-8')
                info += f"\n--- Message Content ---\n{text}"
            except:
                info += "\n(Binary content - saved to file)"
        
        self.result_text.insert("1.0", info)
    
    def _extract_error(self, error):
        self.is_processing = False
        self.extract_btn.config(state=tk.NORMAL)
        self.progress['value'] = 0
        self.status_label.config(text=f"Error: {error}")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", f"Error: {error}")
    
    def _calculate_metrics(self):
        orig_path = self.analysis_orig.get()
        stego_path = self.analysis_stego.get()
        
        if not orig_path or not os.path.exists(orig_path):
            messagebox.showwarning("Warning", "Please select original video.")
            return
        
        if not stego_path or not os.path.exists(stego_path):
            messagebox.showwarning("Warning", "Please select stego video.")
            return
        
        self.analysis_result.delete("1.0", tk.END)
        self.analysis_result.insert("1.0", "Calculating metrics...")
        self.root.update_idletasks()
        
        def calc_thread():
            try:
                mse, psnr = metrics_streaming(orig_path, stego_path, self._update_progress)
                
                result = f"""MSE/PSNR Analysis
========================
Original: {orig_path}
Stego: {stego_path}

Mean Squared Error (MSE): {mse:.6f}
Peak Signal-to-Noise Ratio (PSNR): {psnr:.2f} dB

Interpretation:
- MSE closer to 0 = less distortion
- PSNR > 40 dB = excellent quality (imperceptible)
- PSNR 30-40 dB = good quality
- PSNR 20-30 dB = acceptable quality
- PSNR < 20 dB = poor quality (visible artifacts)
"""
                
                with VideoProcessor(orig_path) as vp_orig, VideoProcessor(stego_path) as vp_stego:
                    orig_frame = vp_orig.read_frame(0)
                    stego_frame = vp_stego.read_frame(0)
                    
                    if orig_frame is not None and stego_frame is not None:
                        hist_corr = compare_histograms(orig_frame, stego_frame)
                        result += f"""
Histogram Correlation (Frame 0):
- Red Channel: {hist_corr['red']:.6f}
- Green Channel: {hist_corr['green']:.6f}
- Blue Channel: {hist_corr['blue']:.6f}
- Average: {hist_corr['average']:.6f}

(Correlation 1.0 = identical histograms)
"""
                
                self.root.after(0, lambda: self._show_analysis_result(result))
            except Exception as e:
                self.root.after(0, lambda: self._show_analysis_result(f"Error: {e}"))
        
        threading.Thread(target=calc_thread, daemon=True).start()
    
    def _show_analysis_result(self, text):
        self.analysis_result.delete("1.0", tk.END)
        self.analysis_result.insert("1.0", text)
        self.progress['value'] = 100
        self.status_label.config(text="Analysis complete!")
    
    def _show_histogram(self):
        self._show_histogram_plot(plot_histogram_comparison)
    
    def _show_histogram_overlay(self):
        self._show_histogram_plot(plot_histogram_overlay)
    
    def _show_histogram_plot(self, plot_func):
        orig_path = self.analysis_orig.get()
        stego_path = self.analysis_stego.get()
        
        if not orig_path or not os.path.exists(orig_path):
            messagebox.showwarning("Warning", "Please select original video.")
            return
        
        if not stego_path or not os.path.exists(stego_path):
            messagebox.showwarning("Warning", "Please select stego video.")
            return
        
        try:
            import matplotlib.pyplot as plt
            
            with VideoProcessor(orig_path) as vp_orig, VideoProcessor(stego_path) as vp_stego:
                orig_frame = vp_orig.read_frame(0)
                stego_frame = vp_stego.read_frame(0)
                
                if orig_frame is None or stego_frame is None:
                    messagebox.showerror("Error", "Cannot read video frames")
                    return
                
                fig = plot_func(orig_frame, stego_frame)
                plt.show()
                
        except ImportError:
            messagebox.showerror("Error", "matplotlib is required for histogram visualization.\nInstall with: pip install matplotlib")
        except Exception as e:
            messagebox.showerror("Error", str(e))


def main():
    root = tk.Tk()
    app = StegoGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
