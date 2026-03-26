from video import load_video, save_video
from function import *
from seed import coordinates, random_seed
from metric import metrics
from a51 import A51

def main():
    menu = input("Menu\n 1: Embed\n 2: Extract\n ")
    video_path = input("path: ")
    frames, w, h, fps = load_video(video_path)
    h, w, _ = frames[0].shape
    total_pixels = len(frames) * w * h

    if menu == '1':
        message = input("pesan: ")
        use_enc = input("enkripsi (y/n): ").lower() == 'y'
        if use_enc:
            a5_key = input("A51 key:")
            message_bits = A51(a5_key).transform(char_to_bits(message))
        else:
            message_bits = char_to_bits(message)

        if len(message_bits) > total_pixels * 8:
            print("kepanjangan")
            return
 
        header_bits = format(len(message_bits), '030b')
        all_bits = [int(bit) for bit in header_bits] + message_bits
        insert_mode = input("Penyisipan\n 1.Random\n 2.Sequential\n")
        
        if insert_mode == '1':
            stego_key = input("Stego Key: ")
            seed = random_seed(stego_key, len(all_bits), total_pixels)
        else:
            seed = list(range(len(all_bits)))
        stego_frames = [f.copy() for f in frames]
        
        header_bits = all_bits[:30]
        payload_bits = all_bits[30:]
        payload_pixels = (len(payload_bits) + 7) // 8
        
        for i in range(4 + payload_pixels):
            idx = seed[i]
            f_idx, y, x = coordinates(idx, w, h)
            pixel = stego_frames[f_idx][y, x]
            
            if i < 4: 
                start = i * 8
                end = start + 8 if i < 3 else start + 6
                part = header_bits[start:end]
                val = int("".join(map(str, part)), 2)
                if i == 3:
                    val = val << 2
                r_b, g_b, b_b = split(val)
                stego_frames[f_idx][y, x] = put(pixel, r_b, g_b, b_b)
                
            else: 
                p_idx = i - 4
                part = payload_bits[p_idx*8 : (p_idx+1)*8]
                if not part:
                    break
                val = int("".join(map(str, part)), 2)
                r_b, g_b, b_b = split(val)
                stego_frames[f_idx][y, x] = put(pixel, r_b, g_b, b_b)

        save_video(stego_frames, w, h, fps, 'stego_result.avi')
        mse, psnr = metrics(frames, stego_frames)
        print(f"MSE: {mse:.4f} \nPSNR: {psnr:.2f} dB")

    elif menu == '2': 
        insert_mode = input("Penyisipan\n 1.Random\n 2.Sequential\n")
        if insert_mode == '1':
            stego_key = input("Stego Key: ")
            seed_h = random_seed(stego_key, 4, total_pixels)
        else:
            seed_h = list(range(4))

        h_bin = ""
        for idx in seed_h:
            f_idx, y, x = coordinates(idx, w, h)
            b, g, r = frames[f_idx][y, x]
            h_bin += format(r & 7, '03b') + format(g & 7, '03b')
            if len(h_bin) < 30: 
                h_bin += format(b & 3, '02b')

        total_msg = int(h_bin[:30], 2)
        payload_pixels = (total_msg + 7) // 8

        if insert_mode == '1':
            seed_all = random_seed(stego_key, 4 + payload_pixels, total_pixels)
        else:
            seed_all = list(range(4 + payload_pixels))

        extracted_bits = []
        for i in range(4, 4 + payload_pixels):
            idx = seed_all[i]
            f_idx, y, x = coordinates(idx, w, h)
            b, g, r = frames[f_idx][y, x]
            res_byte = (r & 7) << 5 | (g & 7) << 2 | (b & 3)
            extracted_bits.extend([int(bit) for bit in format(res_byte, '08b')])

        extracted_bits = extracted_bits[:total_msg]
        use_enc = input("enskripsi 9y/n): ").lower() == 'y'
        if use_enc:
            a5_key = input("A51 key ")
            extracted_bits = A51(a5_key).transform(extracted_bits)

        final_msg = "".join(chr(int("".join(map(str, extracted_bits[i:i+8])), 2)) for i in range(0, len(extracted_bits), 8))
        print(f"\nPesan Rahasia: {final_msg}")

if __name__ == "__main__":
    main()