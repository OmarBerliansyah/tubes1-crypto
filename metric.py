import numpy as np

def metrics(original, modified):
    mse_total = []
    for ori, mod in zip(original, modified):
        ori_array = ori.astype(np.float64)
        mod_array = mod.astype(np.float64)
        mse_frame = np.mean((ori_array - mod_array) ** 2)
        mse_total.append(mse_frame)
    
    avg_mse = np.mean(mse_total)
    if avg_mse == 0:
        return 100.0, 0.0   
    max_pixel = 255.0
    psnr = 20 * np.log10(max_pixel / np.sqrt(avg_mse))
    return avg_mse, psnr