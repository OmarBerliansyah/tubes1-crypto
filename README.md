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

## Testing

### Verifikasi Integritas (SHA-256)
```bash
certutil -hashfile file_asli.pdf SHA256
certutil -hashfile extracted_file.pdf SHA256

sha256sum file_asli.pdf
sha256sum extracted_file.pdf
```

Hash harus identik untuk memastikan ekstraksi berhasil.

### Test Matrix
1. LSB 1-1-1, Random, No Encryption
2. LSB 2-2-2, Sequential, A5/1 Encryption
3. LSB 3-3-2, Random, A5/1 Encryption

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

## Dependencies

- Python 3.7+
- opencv-python >= 4.5.0
- numpy >= 1.19.0
- matplotlib >= 3.3.0
- ffmpeg (opsional, untuk audio preservation)

## Critical Fixes Implemented

### 1. Garbage Header Protection
Program sekarang memvalidasi header dari video steganografi. Jika Anda mencoba extract dari video normal yang tidak mengandung steganografi, program akan menampilkan error yang jelas tanpa crash:
```
"Video ini tidak mengandung pesan steganografi yang valid (Header Corrupt)"
```

### 2. Capacity Validation
Sebelum proses embed, program akan memverifikasi apakah payload muat dalam video:
```python
if payload_size > video_capacity:
    raise StegoError("Payload too large...")
```

### 3. Memory Management
- **Frame-by-frame processing**: Video tidak pernah dimuat seluruhnya ke RAM
- **Audio streaming**: ffmpeg digunakan untuk demux/mux tanpa load full audio
- **Bit list limitation**: Untuk testing, batasi file payload < 5 MB

## Helper Tools

### Test Helper Script
```bash
# Calculate SHA-256 hash
python test_helper.py hash dokumen.pdf

# Compare two files by hash
python test_helper.py compare original.pdf extracted.pdf

# Create dummy file for testing
python test_helper.py dummy 1024 bigfile.bin

# Show video capacity
python test_helper.py capacity cover.avi
```

### Quick Test
```bash
python quick_test.py
```
Akan menjalankan unit tests untuk memverifikasi semua komponen bekerja dengan baik.

## Testing Guide

Lihat file `TESTING_GUIDE.md` untuk panduan lengkap testing dengan skenario:
- Kombinasi LSB modes
- Capacity overflow testing
- File integrity verification (SHA-256)
- Histogram analysis
- Edge cases (garbage header, wrong keys)

## License

MIT License - Copyright 2026 OmarBerliansyah
