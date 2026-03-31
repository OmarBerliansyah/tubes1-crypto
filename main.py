#!/usr/bin/env python3

import os
import argparse
from src import gui_main, VideoSteganography, StegoError, metrics_streaming


def run_gui():
    gui_main()


def run_cli():
    print("=" * 60)
    print("Video Steganography - A5/1 & LSB")
    print("II4021 - Kriptografi, ITB")
    print("=" * 60)

    while True:
        print("\nMenu:")
        print("  1. Embed (hide message/file in video)")
        print("  2. Extract (retrieve hidden data from video)")
        print("  3. Calculate Capacity")
        print("  4. Compare Videos (MSE/PSNR)")
        print("  0. Exit")

        choice = input("\nPilih menu [0-4]: ").strip()

        if choice == '0':
            print("Goodbye!")
            break
        elif choice == '1':
            cli_embed()
        elif choice == '2':
            cli_extract()
        elif choice == '3':
            cli_capacity()
        elif choice == '4':
            cli_metrics()
        else:
            print("Invalid choice. Please try again.")


def cli_embed():
    print("\n--- EMBED MODE ---")

    video_path = input("Cover video path: ").strip().strip('"')
    if not os.path.exists(video_path):
        print(f"Error: Video not found: {video_path}")
        return

    print("\nLSB Mode:")
    print("  1. 1-1-1 (3 bits/pixel) - Most subtle")
    print("  2. 2-2-2 (6 bits/pixel) - Balanced")
    print("  3. 3-3-2 (8 bits/pixel) - Maximum capacity")
    lsb_choice = input("Choose LSB mode [1-3, default=3]: ").strip() or '3'
    lsb_map = {'1': '111', '2': '222', '3': '332'}
    lsb_mode = lsb_map.get(lsb_choice, '332')

    stego = VideoSteganography(lsb_mode)
    cap = stego.calculate_capacity(video_path)
    print(f"\nCapacity: {cap['payload_capacity_bytes']:,} bytes ({cap['payload_capacity_bytes']/1024:.2f} KB)")

    print("\nPayload type:")
    print("  1. Text message")
    print("  2. File")
    payload_type = input("Choose [1-2]: ").strip()

    if payload_type == '1':
        print("Enter message (press Enter twice to finish):")
        lines = []
        while True:
            line = input()
            if line == '':
                break
            lines.append(line)
        message = '\n'.join(lines)
        payload_data = message.encode('utf-8')
        extension = '.txt'
        original_filename = 'message.txt'
    else:
        file_path = input("File path: ").strip().strip('"')
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            return
        with open(file_path, 'rb') as f:
            payload_data = f.read()
        extension = os.path.splitext(file_path)[1]
        original_filename = os.path.basename(file_path)
        print(f"File size: {len(payload_data):,} bytes")

    if len(payload_data) * 8 > cap['payload_capacity_bits']:
        print(f"Error: Payload too large! Max: {cap['payload_capacity_bytes']:,} bytes")
        return

    use_enc = input("\nEnable A5/1 encryption? [y/n]: ").lower() == 'y'
    enc_key = None
    if use_enc:
        enc_key = input("Encryption key (hex or password): ").strip()

    use_random = input("Enable random pixel spreading? [y/n]: ").lower() == 'y'
    stego_key = None
    if use_random:
        stego_key = input("Stego key: ").strip()

    output_path = input("\nOutput video path [default: stego_output.avi]: ").strip() or 'stego_output.avi'

    print("\nEmbedding...")

    def progress(current, total, status):
        pct = (current / total) * 100
        print(f"\r{status}: {current}/{total} ({pct:.1f}%)", end='', flush=True)

    try:
        result = stego.embed(
            video_path, output_path, payload_data, extension,
            use_enc, enc_key, use_random, stego_key, original_filename, progress
        )
        print(f"\n\nSuccess!")
        print(f"Output: {result['output_path']}")
        print(f"Payload: {result['payload_size_bytes']:,} bytes")
        print(f"Frames used: {result['frames_used']}/{result['total_frames']}")
        print(f"Audio preserved: {result['has_audio']}")
    except StegoError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")


def cli_extract():
    print("\n--- EXTRACT MODE ---")

    video_path = input("Stego video path: ").strip().strip('"')
    if not os.path.exists(video_path):
        print(f"Error: Video not found: {video_path}")
        return

    enc_key = input("Encryption key (leave empty if not encrypted): ").strip() or None
    stego_key = input("Stego key (leave empty if sequential): ").strip() or None

    print("\nExtracting...")

    def progress(current, total, status):
        pct = (current / total) * 100
        print(f"\r{status}: {current}/{total} ({pct:.1f}%)", end='', flush=True)

    try:
        stego = VideoSteganography()
        result = stego.extract(video_path, enc_key, stego_key, progress_callback=progress)

        print(f"\n\nExtraction successful!")
        print(f"Original filename: {result.get('original_filename', 'N/A')}")
        print(f"Extension: {result['extension']}")
        print(f"Size: {result['size_bytes']:,} bytes")
        print(f"Was encrypted: {result['was_encrypted']}")
        print(f"Was random: {result['was_random']}")
        print(f"LSB mode: {result['lsb_mode']}")

        original_filename = result.get('original_filename', '')
        if original_filename:
            default_name = original_filename
        else:
            extension = result.get('extension', '')
            default_name = f"extracted{extension}" if extension else "extracted.bin"
        
        output_path = input(f"\nSave as [default: {default_name}]: ").strip() or default_name
        
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            f.write(result['data'])
        
        print(f"File saved to: {output_path}")

        if result['extension'] == '.txt' or not result['extension']:
            try:
                text = result['data'].decode('utf-8')
                print(f"\n--- Message ---\n{text}")
            except:
                pass

    except StegoError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")


def cli_capacity():
    print("\n--- CAPACITY CALCULATOR ---")

    video_path = input("Video path: ").strip().strip('"')
    if not os.path.exists(video_path):
        print(f"Error: Video not found: {video_path}")
        return

    print("\nCapacity by LSB mode:")
    for mode, name in [('111', '1-1-1'), ('222', '2-2-2'), ('332', '3-3-2')]:
        stego = VideoSteganography(mode)
        cap = stego.calculate_capacity(video_path)
        print(f"  {name}: {cap['payload_capacity_bytes']:,} bytes ({cap['payload_capacity_bytes']/1024:.2f} KB)")


def cli_metrics():
    print("\n--- VIDEO COMPARISON ---")
    orig_path = input("Original video path: ").strip().strip('"')
    if not os.path.exists(orig_path):
        print(f"Error: Video not found: {orig_path}")
        return

    stego_path = input("Stego video path: ").strip().strip('"')
    if not os.path.exists(stego_path):
        print(f"Error: Video not found: {stego_path}")
        return

    print("\nCalculating metrics...")

    def progress(current, total):
        pct = (current / total) * 100
        print(f"\rProgress: {current}/{total} ({pct:.1f}%)", end='', flush=True)

    mse, psnr = metrics_streaming(orig_path, stego_path, progress)

    print(f"\n\nResults:")
    print(f"  MSE: {mse:.6f}")
    print(f"  PSNR: {psnr:.2f} dB")
    print(f"\nInterpretation:")
    if psnr == float('inf'):
        print("  Videos are identical!")
    elif psnr > 40:
        print("  Excellent quality - changes are imperceptible")
    elif psnr > 30:
        print("  Good quality - minimal visible artifacts")
    elif psnr > 20:
        print("  Acceptable quality - some visible artifacts")
    else:
        print("  Poor quality - significant visible artifacts")


def main():
    parser = argparse.ArgumentParser(
        description="Video Steganography with A5/1 Encryption",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
        python main.py              # Launch GUI
        python main.py --cli        # Use CLI mode
        python main.py --embed      # Quick embed
        python main.py --extract    # Quick extract"""
    )
    parser.add_argument('--cli', action='store_true', help='Run in CLI mode')
    parser.add_argument('--embed', action='store_true', help='Quick embed mode')
    parser.add_argument('--extract', action='store_true', help='Quick extract mode')

    args = parser.parse_args()

    if args.cli:
        run_cli()
    elif args.embed:
        cli_embed()
    elif args.extract:
        cli_extract()
    else:
        run_gui()


if __name__ == "__main__":
    main()
