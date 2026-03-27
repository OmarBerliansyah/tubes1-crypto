import numpy as np
import cv2


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
    import matplotlib.pyplot as plt
    
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


def get_video_statistics(video_path, sample_frames=10):
    from video import VideoProcessor
    
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
