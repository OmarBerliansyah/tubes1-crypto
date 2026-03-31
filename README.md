# Video Steganography dengan A5/1 Encryption

Tugas Besar I - II4021 Kriptografi, Institut Teknologi Bandung

## Fitur

- **LSB Steganography** dengan 3 mode:
  - 1-1-1 (3 bits/pixel) - Paling subtle, kapasitas rendah
  - 2-2-2 (6 bits/pixel) - Seimbang
  - 3-3-2 (8 bits/pixel) - Kapasitas maksimum

- **A5/1 Stream Cipher** dengan implementasi standar:
  - 64-bit session key (Kc)
  - 22-bit frame number (Fn) auto-generated per 228-bit block
  - Three LFSRs (19, 22, 23 bits)

- **Frame-by-Frame Processing** - Tidak akan OOM meskipun video besar
- **Audio Preservation** - Audio video asli dipertahankan via ffmpeg
- **Random/Sequential Spreading** - Pixel spreading dengan stego key
- **Binary File Support** - Embed file apapun (.pdf, .exe, .zip, dll)
- **MSE/PSNR Metrics** - Analisis kualitas video
- **Histogram Visualization** - Perbandingan histogram RGB

## Instalasi

```bash
cd tubes1-crypto

pip install -r requirements.txt
```
### (Opsional) Install ffmpeg untuk audio preservation
### Windows: 
```bash
choco install ffmpeg
```
### atau download dari https://ffmpeg.org/download.html

### Verifikasi instalasi:
```bash
python quick_test.py
```

## Penggunaan

### GUI Mode (Recommended)
```bash
python main.py
```

### CLI Mode
```bash
python main.py --cli
```

### Quick Commands
```bash
python main.py --embed

python main.py --extract
```

## Struktur Project

```
tubes1-crypto/
├── main.py              # Entry point (GUI/CLI)
├── requirements.txt     # Dependencies
├── README.md           
└── src/
    ├── __init__.py      # Package init
    ├── gui.py           # Tkinter GUI
    ├── stego.py         # Core steganography engine
    ├── video.py         # Video I/O (frame-by-frame)
    ├── function.py      # LSB bit manipulation
    ├── a51.py           # A5/1 stream cipher
    ├── seed.py          # Pixel index generation
    └── metric.py        # MSE/PSNR/Histogram
```

## Arsitektur

### Frame Processing
- **Frame 0**: Reserved untuk metadata header (sequential, LSB 1-1-1, tanpa enkripsi)
- **Frame 1+**: Payload data (dengan enkripsi dan random spreading jika diaktifkan)

### Header Format
```
[PayloadLength: 32 bits] | [ExtLen: 8 bits] | [Extension: variable] |
[Encrypted: 8 bits] | [Random: 8 bits] | [LSBMode: 8 bits]
```

### A5/1 Implementation
Setiap 228-bit block:
1. Reset registers ke 0
2. XOR key bits ke registers
3. XOR frame number (Fn) ke registers
4. Run 100 empty clockings
5. Generate 228-bit keystream

## Catatan Penting

1. **Codec Lossless**: Video output menggunakan FFV1 codec (lossless) untuk mempertahankan LSB bits.

2. **Audio Preservation**: Membutuhkan ffmpeg. Gunakan `-c:v copy` saat muxing untuk menghindari re-encoding.

3. **Kapasitas**: Dihitung dengan formula:
   ```
   Kapasitas (bits) = (Total Frames - 1) × Width × Height × Bits per Pixel
   ```

4. **Edge Cases**:
   - Video terlalu besar: Arsitektur frame-by-frame mencegah OOM
   - Payload melebihi kapasitas: Error akan ditampilkan sebelum proses dimulai
   - Kehilangan 1 bit LSB: Seluruh data terdekripsi akan rusak (karena A5/1 adalah stream cipher)

## Dependensi

- Python 3.7+
- opencv-python >= 4.5.0
- numpy >= 1.19.0
- matplotlib >= 3.3.0
- ffmpeg (opsional, untuk audio preservation)

## License

MIT License - Copyright 2026 OmarBerliansyah
