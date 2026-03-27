import numpy as np
import matplotlib.pyplot as plt
import cv2
from video import VideoProcessor


def calculate_mse(original_frame, modified_frame):
    """Calculate Mean Squared Error between two frames."""
    ori = original_frame.astype(np.float64)
    mod = modified_frame.astype(np.float64)
    return np.mean((ori - mod) ** 2)


def calculate_psnr(mse, max_pixel=255.0):
    """Calculate Peak Signal-to-Noise Ratio from MSE."""
    if mse == 0:
        return float('inf')
    return 20 * np.log10(max_pixel / np.sqrt(mse))


def metrics(original, modified):
    mse_values = []
    
    if isinstance(original, list) and isinstance(modified, list):
        for ori, mod in zip(original, modified):
            mse_values.append(calculate_mse(ori, mod))
    else:
        raise ValueError("Both inputs must be lists of frames")
    
    avg_mse = np.mean(mse_values) if mse_values else 0.0
    psnr = calculate_psnr(avg_mse)
    
    return avg_mse, psnr


def metrics_streaming(original_path, modified_path, progress_callback=None):
    from video import VideoProcessor
    
    mse_values = []
    
    with VideoProcessor(original_path) as orig_vp, VideoProcessor(modified_path) as mod_vp:
        total = orig_vp.total_frames
        
        for i in range(total):
            orig_frame = orig_vp.read_frame()
            mod_frame = mod_vp.read_frame()
            
            if orig_frame is None or mod_frame is None:
                break
            
            mse_values.append(calculate_mse(orig_frame, mod_frame))
            
            if progress_callback:
                progress_callback(i + 1, total)
    
    avg_mse = np.mean(mse_values) if mse_values else 0.0
    psnr = calculate_psnr(avg_mse)
    
    return avg_mse, psnr


def calculate_histogram(frame, channel):
    hist = cv2.calcHist([frame], [channel], None, [256], [0, 256])
    return hist.flatten()


def calculate_rgb_histograms(frame):
    b_hist = calculate_histogram(frame, 0)
    g_hist = calculate_histogram(frame, 1)
    r_hist = calculate_histogram(frame, 2)
    return r_hist, g_hist, b_hist


def compare_histograms(original_frame, stego_frame):
    orig_r, orig_g, orig_b = calculate_rgb_histograms(original_frame)
    stego_r, stego_g, stego_b = calculate_rgb_histograms(stego_frame)
    
    r_corr = cv2.compareHist(
        orig_r.reshape(-1, 1).astype(np.float32),
        stego_r.reshape(-1, 1).astype(np.float32),
        cv2.HISTCMP_CORREL
    )
    g_corr = cv2.compareHist(
        orig_g.reshape(-1, 1).astype(np.float32),
        stego_g.reshape(-1, 1).astype(np.float32),
        cv2.HISTCMP_CORREL
    )
    b_corr = cv2.compareHist(
        orig_b.reshape(-1, 1).astype(np.float32),
        stego_b.reshape(-1, 1).astype(np.float32),
        cv2.HISTCMP_CORREL
    )
    
    return {
        'red': r_corr,
        'green': g_corr,
        'blue': b_corr,
        'average': (r_corr + g_corr + b_corr) / 3
    }


def validate_frame(frame, name="Frame"):
    if frame is None:
        return False, f"{name} is None"
    
    mean_val = np.mean(frame)
    max_val = np.max(frame)
    
    if max_val == 0:
        return False, f"{name} is completely black (all zeros) - video may not be decoded correctly"
    
    if mean_val < 1:
        return False, f"{name} is nearly black (mean={mean_val:.2f}) - possible codec issue"
    
    return True, f"{name} OK (mean={mean_val:.1f}, max={max_val})"


def plot_histogram_comparison(original_frame, stego_frame, save_path=None):
    import matplotlib.pyplot as plt
    
    orig_r, orig_g, orig_b = calculate_rgb_histograms(original_frame)
    stego_r, stego_g, stego_b = calculate_rgb_histograms(stego_frame)
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle('Histogram Comparison: Original vs Stego', fontsize=14)
    
    x = np.arange(256)
    
    axes[0, 0].fill_between(x, orig_r, alpha=0.7, color='red', label='Original')
    axes[0, 0].set_title('Original - Red Channel')
    axes[0, 0].set_xlabel('Pixel Value')
    axes[0, 0].set_ylabel('Frequency')
    
    axes[0, 1].fill_between(x, orig_g, alpha=0.7, color='green', label='Original')
    axes[0, 1].set_title('Original - Green Channel')
    axes[0, 1].set_xlabel('Pixel Value')
    
    axes[0, 2].fill_between(x, orig_b, alpha=0.7, color='blue', label='Original')
    axes[0, 2].set_title('Original - Blue Channel')
    axes[0, 2].set_xlabel('Pixel Value')
    
    axes[1, 0].fill_between(x, stego_r, alpha=0.7, color='darkred', label='Stego')
    axes[1, 0].set_title('Stego - Red Channel')
    axes[1, 0].set_xlabel('Pixel Value')
    axes[1, 0].set_ylabel('Frequency')
    
    axes[1, 1].fill_between(x, stego_g, alpha=0.7, color='darkgreen', label='Stego')
    axes[1, 1].set_title('Stego - Green Channel')
    axes[1, 1].set_xlabel('Pixel Value')
    
    axes[1, 2].fill_between(x, stego_b, alpha=0.7, color='darkblue', label='Stego')
    axes[1, 2].set_title('Stego - Blue Channel')
    axes[1, 2].set_xlabel('Pixel Value')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


def plot_histogram_overlay(original_frame, stego_frame, save_path=None):
    orig_valid, orig_msg = validate_frame(original_frame, "Original")
    stego_valid, stego_msg = validate_frame(stego_frame, "Stego")
    
    if not orig_valid or not stego_valid:
        print(f"WARNING: {orig_msg}")
        print(f"WARNING: {stego_msg}")
    
    orig_r, orig_g, orig_b = calculate_rgb_histograms(original_frame)
    stego_r, stego_g, stego_b = calculate_rgb_histograms(stego_frame)
    
    diff_r = stego_r - orig_r
    diff_g = stego_g - orig_g
    diff_b = stego_b - orig_b
    
    fig, axes = plt.subplots(3, 3, figsize=(14, 11))
    fig.suptitle('LSB Steganography Histogram Analysis', fontsize=13, fontweight='bold', y=0.98)
    
    x = np.arange(256)
    zoom_start, zoom_end = 100, 200
    
    axes[0, 0].plot(x, orig_r, 'r-', alpha=0.7, label='Original', linewidth=1.5)
    axes[0, 0].plot(x, stego_r, 'r--', alpha=0.7, label='Stego', linewidth=1.5)
    axes[0, 0].set_title('Red (Full)', fontsize=10)
    axes[0, 0].set_xlabel('Pixel Value', fontsize=8)
    axes[0, 0].set_ylabel('Frequency', fontsize=8)
    axes[0, 0].legend(fontsize=7)
    axes[0, 0].tick_params(labelsize=7)
    
    axes[0, 1].plot(x, orig_g, 'g-', alpha=0.7, label='Original', linewidth=1.5)
    axes[0, 1].plot(x, stego_g, 'g--', alpha=0.7, label='Stego', linewidth=1.5)
    axes[0, 1].set_title('Green (Full)', fontsize=10)
    axes[0, 1].set_xlabel('Pixel Value', fontsize=8)
    axes[0, 1].legend(fontsize=7)
    axes[0, 1].tick_params(labelsize=7)
    
    axes[0, 2].plot(x, orig_b, 'b-', alpha=0.7, label='Original', linewidth=1.5)
    axes[0, 2].plot(x, stego_b, 'b--', alpha=0.7, label='Stego', linewidth=1.5)
    axes[0, 2].set_title('Blue (Full)', fontsize=10)
    axes[0, 2].set_xlabel('Pixel Value', fontsize=8)
    axes[0, 2].legend(fontsize=7)
    axes[0, 2].tick_params(labelsize=7)
    
    x_zoom = x[zoom_start:zoom_end]
    
    axes[1, 0].bar(x_zoom - 0.2, orig_r[zoom_start:zoom_end], width=0.4, 
                   color='red', alpha=0.6, label='Original')
    axes[1, 0].bar(x_zoom + 0.2, stego_r[zoom_start:zoom_end], width=0.4, 
                   color='darkred', alpha=0.6, label='Stego')
    axes[1, 0].set_title(f'Red (Zoom {zoom_start}-{zoom_end})', fontsize=10)
    axes[1, 0].set_xlabel('Pixel Value', fontsize=8)
    axes[1, 0].set_ylabel('Frequency', fontsize=8)
    axes[1, 0].legend(fontsize=7)
    axes[1, 0].set_xlim(zoom_start - 1, zoom_end + 1)
    axes[1, 0].tick_params(labelsize=7)
    
    axes[1, 1].bar(x_zoom - 0.2, orig_g[zoom_start:zoom_end], width=0.4, 
                   color='green', alpha=0.6, label='Original')
    axes[1, 1].bar(x_zoom + 0.2, stego_g[zoom_start:zoom_end], width=0.4, 
                   color='darkgreen', alpha=0.6, label='Stego')
    axes[1, 1].set_title(f'Green (Zoom {zoom_start}-{zoom_end})', fontsize=10)
    axes[1, 1].set_xlabel('Pixel Value', fontsize=8)
    axes[1, 1].legend(fontsize=7)
    axes[1, 1].set_xlim(zoom_start - 1, zoom_end + 1)
    axes[1, 1].tick_params(labelsize=7)
    
    axes[1, 2].bar(x_zoom - 0.2, orig_b[zoom_start:zoom_end], width=0.4, 
                   color='blue', alpha=0.6, label='Original')
    axes[1, 2].bar(x_zoom + 0.2, stego_b[zoom_start:zoom_end], width=0.4, 
                   color='darkblue', alpha=0.6, label='Stego')
    axes[1, 2].set_title(f'Blue (Zoom {zoom_start}-{zoom_end})', fontsize=10)
    axes[1, 2].set_xlabel('Pixel Value', fontsize=8)
    axes[1, 2].legend(fontsize=7)
    axes[1, 2].set_xlim(zoom_start - 1, zoom_end + 1)
    axes[1, 2].tick_params(labelsize=7)
    
    axes[2, 0].bar(x, diff_r, color='red', alpha=0.7, width=1.0)
    axes[2, 0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[2, 0].set_title('Red (Residual)', fontsize=10)
    axes[2, 0].set_xlabel('Pixel Value', fontsize=8)
    axes[2, 0].set_ylabel('Difference', fontsize=8)
    axes[2, 0].tick_params(labelsize=7)
    max_diff_r = max(abs(diff_r.min()), abs(diff_r.max())) * 1.1
    if max_diff_r > 0:
        axes[2, 0].set_ylim(-max_diff_r, max_diff_r)
    
    axes[2, 1].bar(x, diff_g, color='green', alpha=0.7, width=1.0)
    axes[2, 1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[2, 1].set_title('Green (Residual)', fontsize=10)
    axes[2, 1].set_xlabel('Pixel Value', fontsize=8)
    axes[2, 1].tick_params(labelsize=7)
    max_diff_g = max(abs(diff_g.min()), abs(diff_g.max())) * 1.1
    if max_diff_g > 0:
        axes[2, 1].set_ylim(-max_diff_g, max_diff_g)
    
    axes[2, 2].bar(x, diff_b, color='blue', alpha=0.7, width=1.0)
    axes[2, 2].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[2, 2].set_title('Blue (Residual)', fontsize=10)
    axes[2, 2].set_xlabel('Pixel Value', fontsize=8)
    axes[2, 2].tick_params(labelsize=7)
    max_diff_b = max(abs(diff_b.min()), abs(diff_b.max())) * 1.1
    if max_diff_b > 0:
        axes[2, 2].set_ylim(-max_diff_b, max_diff_b)
    
    total_changed = int(np.sum(np.abs(diff_r)) + np.sum(np.abs(diff_g)) + np.sum(np.abs(diff_b))) // 2
    fig.text(0.5, 0.01, f'Total pixel shifts: {total_changed:,}', 
             ha='center', fontsize=9, style='italic')
    
    plt.subplots_adjust(hspace=0.35, wspace=0.25, top=0.93, bottom=0.06)
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


def plot_histogram_simple(original_frame, stego_frame, save_path=None):
    orig_r, orig_g, orig_b = calculate_rgb_histograms(original_frame)
    stego_r, stego_g, stego_b = calculate_rgb_histograms(stego_frame)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    fig.suptitle('Histogram Overlay: Original (solid) vs Stego (dashed)', fontsize=12)
    
    x = np.arange(256)
    
    axes[0].plot(x, orig_r, 'r-', alpha=0.8, label='Original', linewidth=1)
    axes[0].plot(x, stego_r, 'r--', alpha=0.8, label='Stego', linewidth=1)
    axes[0].set_title('Red Channel')
    axes[0].set_xlabel('Pixel Value')
    axes[0].set_ylabel('Frequency')
    axes[0].legend()
    
    axes[1].plot(x, orig_g, 'g-', alpha=0.8, label='Original', linewidth=1)
    axes[1].plot(x, stego_g, 'g--', alpha=0.8, label='Stego', linewidth=1)
    axes[1].set_title('Green Channel')
    axes[1].set_xlabel('Pixel Value')
    axes[1].legend()
    
    axes[2].plot(x, orig_b, 'b-', alpha=0.8, label='Original', linewidth=1)
    axes[2].plot(x, stego_b, 'b--', alpha=0.8, label='Stego', linewidth=1)
    axes[2].set_title('Blue Channel')
    axes[2].set_xlabel('Pixel Value')
    axes[2].legend()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


def plot_histogram_residual(original_frame, stego_frame, save_path=None):
    orig_r, orig_g, orig_b = calculate_rgb_histograms(original_frame)
    stego_r, stego_g, stego_b = calculate_rgb_histograms(stego_frame)
    
    diff_r = stego_r - orig_r
    diff_g = stego_g - orig_g
    diff_b = stego_b - orig_b
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Histogram Residual Analysis (Stego - Original)', fontsize=14, fontweight='bold')
    
    x = np.arange(256)
    
    axes[0].bar(x, diff_r, color='red', alpha=0.7, width=1.0)
    axes[0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[0].set_title('Red Channel Difference')
    axes[0].set_xlabel('Pixel Value')
    axes[0].set_ylabel('Frequency Change')
    axes[0].grid(True, alpha=0.3)
    
    axes[1].bar(x, diff_g, color='green', alpha=0.7, width=1.0)
    axes[1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[1].set_title('Green Channel Difference')
    axes[1].set_xlabel('Pixel Value')
    axes[1].grid(True, alpha=0.3)
    
    axes[2].bar(x, diff_b, color='blue', alpha=0.7, width=1.0)
    axes[2].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[2].set_title('Blue Channel Difference')
    axes[2].set_xlabel('Pixel Value')
    axes[2].grid(True, alpha=0.3)
    
    total_r = int(np.sum(np.abs(diff_r))) // 2
    total_g = int(np.sum(np.abs(diff_g))) // 2
    total_b = int(np.sum(np.abs(diff_b))) // 2
    
    stats_text = f'Pixels shifted: R={total_r:,} | G={total_g:,} | B={total_b:,} | Total={total_r+total_g+total_b:,}'
    fig.text(0.5, 0.01, stats_text, ha='center', fontsize=10, style='italic')
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


def plot_multiframe_residual(orig_path, stego_path, sample_count=10, start_frame=3, save_path=None):
    total_diff_r = np.zeros(256, dtype=np.float64)
    total_diff_g = np.zeros(256, dtype=np.float64)
    total_diff_b = np.zeros(256, dtype=np.float64)
    
    pixel_changes = {'r': 0, 'g': 0, 'b': 0}
    frames_analyzed = 0
    
    with VideoProcessor(orig_path) as vp_orig, VideoProcessor(stego_path) as vp_stego:
        total_frames = min(vp_orig.total_frames, vp_stego.total_frames)
        
        if total_frames <= start_frame:
            print(f"Warning: Video only has {total_frames} frames, cannot start at frame {start_frame}")
            start_frame = 0
        
        available_frames = total_frames - start_frame
        step = max(1, available_frames // sample_count)
        
        for i in range(start_frame, total_frames, step):
            if frames_analyzed >= sample_count:
                break
            
            orig_frame = vp_orig.read_frame(i)
            stego_frame = vp_stego.read_frame(i)
            
            if orig_frame is None or stego_frame is None:
                continue
            
            if np.max(orig_frame) == 0 or np.max(stego_frame) == 0:
                continue
            
            orig_r, orig_g, orig_b = calculate_rgb_histograms(orig_frame)
            stego_r, stego_g, stego_b = calculate_rgb_histograms(stego_frame)
            
            total_diff_r += (stego_r - orig_r)
            total_diff_g += (stego_g - orig_g)
            total_diff_b += (stego_b - orig_b)
            
            pixel_diff = np.abs(stego_frame.astype(np.int16) - orig_frame.astype(np.int16))
            pixel_changes['b'] += np.sum(pixel_diff[:, :, 0] > 0)
            pixel_changes['g'] += np.sum(pixel_diff[:, :, 1] > 0)
            pixel_changes['r'] += np.sum(pixel_diff[:, :, 2] > 0)
            
            frames_analyzed += 1
    
    if frames_analyzed == 0:
        print("Error: No valid frames could be analyzed")
        return None
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle(f'Multi-Frame Residual Analysis ({frames_analyzed} frames, starting from frame {start_frame})', 
                 fontsize=14, fontweight='bold')
    
    x = np.arange(256)
    
    axes[0, 0].bar(x, total_diff_r, color='red', alpha=0.7, width=1.0)
    axes[0, 0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[0, 0].set_title('Red Channel - Aggregated Difference')
    axes[0, 0].set_xlabel('Pixel Value')
    axes[0, 0].set_ylabel('Frequency Change')
    axes[0, 0].grid(True, alpha=0.3)
    
    axes[0, 1].bar(x, total_diff_g, color='green', alpha=0.7, width=1.0)
    axes[0, 1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[0, 1].set_title('Green Channel - Aggregated Difference')
    axes[0, 1].set_xlabel('Pixel Value')
    axes[0, 1].grid(True, alpha=0.3)
    
    axes[0, 2].bar(x, total_diff_b, color='blue', alpha=0.7, width=1.0)
    axes[0, 2].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[0, 2].set_title('Blue Channel - Aggregated Difference')
    axes[0, 2].set_xlabel('Pixel Value')
    axes[0, 2].grid(True, alpha=0.3)
    
    channels = ['Red', 'Green', 'Blue']
    colors = ['red', 'green', 'blue']
    values = [pixel_changes['r'], pixel_changes['g'], pixel_changes['b']]
    
    axes[1, 0].bar(channels, values, color=colors, alpha=0.7)
    axes[1, 0].set_title('Pixels Changed per Channel')
    axes[1, 0].set_ylabel('Number of Changed Pixels')
    for i, v in enumerate(values):
        axes[1, 0].text(i, v + max(values)*0.02, f'{v:,}', ha='center', fontsize=9)
    
    with VideoProcessor(orig_path) as vp:
        total_pixels_per_frame = vp.w * vp.h
    total_pixels = total_pixels_per_frame * frames_analyzed
    total_changed = sum(values)
    change_percent = (total_changed / total_pixels) * 100 if total_pixels > 0 else 0
    
    stats_text = [
        f'Frames analyzed: {frames_analyzed}',
        f'Total pixels: {total_pixels:,}',
        f'Pixels changed: {total_changed:,}',
        f'Change ratio: {change_percent:.2f}%'
    ]
    axes[1, 1].axis('off')
    axes[1, 1].text(0.5, 0.5, '\n'.join(stats_text), transform=axes[1, 1].transAxes,
                    fontsize=12, verticalalignment='center', horizontalalignment='center',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    axes[1, 1].set_title('Statistics')
    
    lsb_bits_info = [
        'LSB Mode Info:',
        '• 1-1-1: 3 bits/pixel (max shift: 1)',
        '• 2-2-2: 6 bits/pixel (max shift: 3)',
        '• 3-3-2: 8 bits/pixel (max shift: 7/7/3)'
    ]
    axes[1, 2].axis('off')
    axes[1, 2].text(0.5, 0.5, '\n'.join(lsb_bits_info), transform=axes[1, 2].transAxes,
                    fontsize=11, verticalalignment='center', horizontalalignment='center',
                    bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
    axes[1, 2].set_title('Reference')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    
    return fig


def get_video_statistics(video_path, sample_frames=10):
    stats = {'r': [], 'g': [], 'b': []}
    
    with VideoProcessor(video_path) as vp:
        total = vp.total_frames
        step = max(1, total // sample_frames)
        
        for i in range(0, total, step):
            frame = vp.read_frame(i)
            if frame is None:
                break
            
            stats['b'].append(np.mean(frame[:, :, 0]))
            stats['g'].append(np.mean(frame[:, :, 1]))
            stats['r'].append(np.mean(frame[:, :, 2]))
    
    return {
        'r_mean': np.mean(stats['r']),
        'g_mean': np.mean(stats['g']),
        'b_mean': np.mean(stats['b']),
        'r_std': np.std(stats['r']),
        'g_std': np.std(stats['g']),
        'b_std': np.std(stats['b']),
    }
