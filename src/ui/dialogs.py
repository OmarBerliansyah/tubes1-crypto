import os
import customtkinter as ctk
from .constants import COLORS, FONTS


class DialogsMixin:
    """Mixin providing all dialog/popup methods for the GUI."""

    def _show_modern_warning(self, message):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Warning")
        dialog.geometry("440x220")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=30, pady=30)

        ctk.CTkLabel(content, text="[!]", font=("JetBrains Mono", 36, "bold"),
                     text_color=COLORS["warning"]).pack()
        ctk.CTkLabel(content, text=message, font=FONTS["body"],
                     text_color=COLORS["text_primary"], wraplength=380).pack(pady=15)

        ctk.CTkButton(
            dialog, text="OK", font=FONTS["button"],
            fg_color=COLORS["warning"], text_color="white", hover_color="#D97706",
            height=40, width=100, corner_radius=8, command=dialog.destroy
        ).pack(pady=(0, 20))
        dialog.focus_set()

    def _show_modern_error(self, message):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Error")
        dialog.geometry("480x240")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=30, pady=25)

        ctk.CTkLabel(content, text="[X]", font=("JetBrains Mono", 36, "bold"),
                     text_color=COLORS["error"]).pack()
        ctk.CTkLabel(content, text="An Error Occurred", font=FONTS["subtitle"],
                     text_color=COLORS["error"]).pack(pady=(10, 5))
        ctk.CTkLabel(content, text=message[:200], font=FONTS["body"],
                     text_color=COLORS["text_primary"], wraplength=420).pack()

        ctk.CTkButton(
            dialog, text="OK", font=FONTS["button"],
            fg_color=COLORS["error"], text_color="white", hover_color="#DC2626",
            height=40, width=100, corner_radius=8, command=dialog.destroy
        ).pack(pady=(0, 20))
        dialog.focus_set()

    def _show_embed_success_dialog(self, result):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Embedding Successful")
        dialog.geometry("520x450")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        header = ctk.CTkFrame(dialog, fg_color=COLORS["success"], corner_radius=0, height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="[OK]", font=("JetBrains Mono", 24, "bold"),
                     text_color="white").pack(side="left", padx=25, pady=15)
        ctk.CTkLabel(header, text="Embedding Complete", font=FONTS["title"],
                     text_color="white").pack(side="left", pady=15)

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=25, pady=25)
        ctk.CTkLabel(content, text="Your message has been successfully embedded into the video.",
                     font=FONTS["body"], text_color=COLORS["text_secondary"],
                     wraplength=450).pack(anchor="w", pady=(0, 20))

        details = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=12)
        details.pack(fill="x", pady=(0, 20))

        items = [
            ("Output File:", os.path.basename(result['output_path'])),
            ("Payload Size:", f"{result['payload_size_bytes']:,} bytes"),
            ("Frames Used:", f"{result['frames_used']:,} / {result['total_frames']:,}"),
            ("Audio Preserved:", "Yes" if result['has_audio'] else "No"),
        ]
        for label, value in items:
            row = ctk.CTkFrame(details, fg_color="transparent", corner_radius=0, height=35)
            row.pack(fill="x", padx=15, pady=2)
            row.pack_propagate(False)
            ctk.CTkLabel(row, text=label, font=FONTS["body"],
                         text_color=COLORS["text_secondary"]).pack(side="left")
            ctk.CTkLabel(row, text=value, font=FONTS["body_bold"],
                         text_color=COLORS["text_primary"]).pack(side="right")

        path_frame = ctk.CTkFrame(content, fg_color="transparent", corner_radius=0)
        path_frame.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(path_frame, text="Full Path:", font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack(anchor="w")
        ctk.CTkLabel(path_frame, text=result['output_path'], font=FONTS["small"],
                     text_color=COLORS["text_primary"], wraplength=450).pack(anchor="w")

        ctk.CTkButton(
            dialog, text="OK", font=FONTS["button"],
            fg_color=COLORS["success"], text_color="white", hover_color="#059669",
            height=45, width=120, corner_radius=10, command=dialog.destroy
        ).pack(pady=(0, 25))
        dialog.focus_set()

    def _show_file_too_large_dialog(self, max_bytes, file_size):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("File Too Large")
        dialog.geometry("480x300")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=30, pady=30)

        ctk.CTkLabel(content, text="[!]", font=("JetBrains Mono", 36, "bold"),
                     text_color=COLORS["warning"]).pack()
        ctk.CTkLabel(content, text="File Too Large", font=FONTS["subtitle"],
                     text_color=COLORS["warning"]).pack(pady=(10, 15))

        details = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=12)
        details.pack(fill="x", pady=(0, 15))

        for label_text, val_text, color in [
            ("Maximum Capacity:", f"{max_bytes:,} bytes", COLORS["success"]),
            ("Your File Size:", f"{file_size:,} bytes", COLORS["error"]),
        ]:
            row = ctk.CTkFrame(details, fg_color="transparent", corner_radius=0)
            row.pack(fill="x", padx=15, pady=(12, 5))
            ctk.CTkLabel(row, text=label_text, font=FONTS["body"],
                         text_color=COLORS["text_secondary"]).pack(side="left")
            ctk.CTkLabel(row, text=val_text, font=FONTS["body_bold"],
                         text_color=color).pack(side="right")

        ctk.CTkLabel(content, text="The selected file exceeds the video's capacity. "
                     "Please choose a smaller file or use a video with higher capacity.",
                     font=FONTS["small"], text_color=COLORS["text_secondary"],
                     wraplength=400).pack()

        ctk.CTkButton(
            dialog, text="OK", font=FONTS["button"],
            fg_color=COLORS["warning"], text_color="white", hover_color="#D97706",
            height=40, width=100, corner_radius=8, command=dialog.destroy
        ).pack(pady=(0, 20))
        dialog.focus_set()

    def _show_capacity_ok_dialog(self, max_bytes, payload_size):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Capacity OK")
        dialog.geometry("450x280")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=30, pady=30)

        ctk.CTkLabel(content, text="[OK]", font=("JetBrains Mono", 36, "bold"),
                     text_color=COLORS["success"]).pack()
        ctk.CTkLabel(content, text="Capacity Sufficient", font=FONTS["subtitle"],
                     text_color=COLORS["success"]).pack(pady=(10, 15))

        details = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=12)
        details.pack(fill="x", pady=(0, 15))

        for label_text, val_text, color in [
            ("Maximum Capacity:", f"{max_bytes:,} bytes", COLORS["text_primary"]),
            ("Your Payload:", f"{payload_size:,} bytes", COLORS["success"]),
        ]:
            row = ctk.CTkFrame(details, fg_color="transparent", corner_radius=0)
            row.pack(fill="x", padx=15, pady=(12, 5))
            ctk.CTkLabel(row, text=label_text, font=FONTS["body"],
                         text_color=COLORS["text_secondary"]).pack(side="left")
            ctk.CTkLabel(row, text=val_text, font=FONTS["body_bold"],
                         text_color=color).pack(side="right")

        ctk.CTkLabel(content, text=f"Available space: {max_bytes - payload_size:,} bytes remaining",
                     font=FONTS["small"], text_color=COLORS["text_secondary"],
                     wraplength=380).pack()

        ctk.CTkButton(
            dialog, text="OK", font=FONTS["button"],
            fg_color=COLORS["success"], text_color="white", hover_color="#059669",
            height=40, width=100, corner_radius=8, command=dialog.destroy
        ).pack(pady=(0, 20))
        dialog.focus_set()

    def _show_capacity_exceeded_dialog(self, max_bytes, input_bytes):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Capacity Exceeded")
        dialog.geometry("450x280")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=30, pady=30)

        ctk.CTkLabel(content, text="[!]", font=("JetBrains Mono", 36, "bold"),
                     text_color=COLORS["warning"]).pack()
        ctk.CTkLabel(content, text="Capacity Exceeded", font=FONTS["subtitle"],
                     text_color=COLORS["warning"]).pack(pady=(10, 15))

        details = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=10)
        details.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(details, text=f"Maximum Capacity: {max_bytes:,} bytes",
                     font=FONTS["body_bold"], text_color=COLORS["text_primary"]
                     ).pack(anchor="w", padx=15, pady=(12, 5))
        ctk.CTkLabel(details, text=f"Your Input: {input_bytes:,} bytes",
                     font=FONTS["body"], text_color=COLORS["error"]
                     ).pack(anchor="w", padx=15, pady=(0, 12))

        ctk.CTkLabel(content, text="The payload is too large for this video. "
                     "Please use a larger video or reduce the payload size.",
                     font=FONTS["small"], text_color=COLORS["text_secondary"],
                     wraplength=380).pack()

        ctk.CTkButton(
            dialog, text="OK", font=FONTS["button"],
            fg_color=COLORS["warning"], text_color="white", hover_color="#D97706",
            height=40, width=100, corner_radius=8, command=dialog.destroy
        ).pack(pady=(0, 20))
        dialog.focus_set()

    def _show_lossy_format_warning(self, ext):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Lossy Format Warning")
        dialog.geometry("500x320")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        result = [False]

        header = ctk.CTkFrame(dialog, fg_color=COLORS["warning"], corner_radius=0, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="[!]", font=("JetBrains Mono", 24, "bold"),
                     text_color="white").pack(side="left", padx=20, pady=12)
        ctk.CTkLabel(header, text="Lossy Format Warning", font=FONTS["subtitle"],
                     text_color="white").pack(side="left", pady=12)

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=25, pady=20)

        ctk.CTkLabel(content, text=f"{ext.upper()} uses lossy compression!",
                     font=FONTS["body_bold"], text_color=COLORS["error"]).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(content, text="This will DESTROY the LSB steganographic data. "
                     "The hidden message will be unrecoverable.",
                     font=FONTS["body"], text_color=COLORS["text_primary"],
                     wraplength=440).pack(anchor="w", pady=(0, 10))

        rec = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=8)
        rec.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(rec, text="Tip: Use .AVI format for lossless steganography",
                     font=FONTS["body"], text_color=COLORS["text_secondary"]).pack(padx=15, pady=10)

        ctk.CTkLabel(content, text="Do you want to continue anyway?",
                     font=FONTS["body_bold"], text_color=COLORS["text_primary"]
                     ).pack(anchor="w", pady=(0, 10))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        btn_frame.pack(fill="x", padx=25, pady=(0, 25))

        def on_cancel():
            result[0] = False
            dialog.destroy()

        def on_continue():
            result[0] = True
            dialog.destroy()

        ctk.CTkButton(
            btn_frame, text="Cancel", font=FONTS["button"],
            fg_color=COLORS["input_bg"], text_color=COLORS["text_secondary"],
            hover_color=COLORS["border"], height=40, width=100,
            corner_radius=8, command=on_cancel
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Continue", font=FONTS["button"],
            fg_color=COLORS["warning"], text_color="white",
            hover_color="#D97706", height=40, width=100,
            corner_radius=8, command=on_continue
        ).pack(side="left")

        dialog.focus_set()
        self.root.wait_window(dialog)
        return result[0]

    def _show_capacity_dialog(self, cap, path):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Video Capacity Analysis")
        dialog.geometry("500x580")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        header = ctk.CTkFrame(dialog, fg_color=COLORS["primary"], corner_radius=0, height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="[i]", font=("JetBrains Mono", 28, "bold"),
                     text_color="white").pack(side="left", padx=25, pady=15)
        ctk.CTkLabel(header, text="Capacity Analysis", font=FONTS["title"],
                     text_color="white").pack(side="left", pady=15)

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=25, pady=25)

        file_card = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=10)
        file_card.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(file_card, text="Video File", font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack(anchor="w", padx=15, pady=(12, 2))
        ctk.CTkLabel(file_card, text=os.path.basename(path), font=FONTS["body"],
                     text_color=COLORS["text_primary"]).pack(anchor="w", padx=15, pady=(0, 12))

        specs_grid = ctk.CTkFrame(content, fg_color="transparent", corner_radius=0)
        specs_grid.pack(fill="x", pady=(0, 15))
        specs_grid.grid_columnconfigure(0, weight=1)
        specs_grid.grid_columnconfigure(1, weight=1)
        specs_grid.grid_columnconfigure(2, weight=1)

        for label, value, row, col in [
            ("Resolution", f"{cap['width']}x{cap['height']}", 0, 0),
            ("Total Frames", f"{cap['total_frames']:,}", 0, 1),
            ("FPS", f"{cap['fps']:.2f}", 0, 2),
        ]:
            box = ctk.CTkFrame(specs_grid, fg_color=COLORS["input_bg"], corner_radius=10)
            box.grid(row=row, column=col, padx=5, sticky="nsew")
            ctk.CTkLabel(box, text=label, font=FONTS["small"],
                         text_color=COLORS["text_secondary"]).pack(padx=15, pady=(12, 2))
            ctk.CTkLabel(box, text=value, font=FONTS["body_bold"],
                         text_color=COLORS["text_primary"]).pack(padx=15, pady=(0, 12))

        lsb_card = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=12)
        lsb_card.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(lsb_card, text="LSB Configuration", font=FONTS["body_bold"],
                     text_color=COLORS["secondary"]).pack(anchor="w", padx=20, pady=(15, 10))
        ctk.CTkFrame(lsb_card, fg_color=COLORS["border"], height=1, corner_radius=0
                     ).pack(fill="x", padx=20)
        lsb_row = ctk.CTkFrame(lsb_card, fg_color="transparent", corner_radius=0)
        lsb_row.pack(fill="x", padx=20, pady=(10, 15))
        ctk.CTkLabel(lsb_row, text=f"Mode: {self.lsb_mode.get()}",
                     font=FONTS["body"], text_color=COLORS["text_primary"]).pack(side="left")
        ctk.CTkLabel(lsb_row, text=f"({cap['bits_per_pixel']} bits/pixel)",
                     font=FONTS["body"], text_color=COLORS["text_secondary"]).pack(side="left", padx=(10, 0))

        cap_card = ctk.CTkFrame(content, fg_color=COLORS["card"], corner_radius=12,
                                border_width=1, border_color=COLORS["border"])
        cap_card.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(cap_card, text="Storage Capacity", font=FONTS["body_bold"],
                     text_color=COLORS["secondary"]).pack(anchor="w", padx=20, pady=(15, 10))
        ctk.CTkFrame(cap_card, fg_color=COLORS["border"], height=1, corner_radius=0
                     ).pack(fill="x", padx=20)

        cap_items = ctk.CTkFrame(cap_card, fg_color="transparent", corner_radius=0)
        cap_items.pack(fill="x", padx=20, pady=15)
        for i, (label, value, color) in enumerate([
            ("Header", f"{cap['header_capacity_bits']:,} bits", COLORS["text_secondary"]),
            ("Payload (Raw)", f"{cap['payload_capacity_bytes']:,} bytes", COLORS["text_primary"]),
            ("Payload (KB)", f"{cap['payload_capacity_bytes']/1024:.2f} KB", COLORS["primary"]),
            ("Payload (MB)", f"{cap['payload_capacity_bytes']/(1024*1024):.4f} MB", COLORS["success"]),
        ]):
            row = ctk.CTkFrame(cap_items, fg_color="transparent" if i % 2 == 0 else COLORS["input_bg"],
                               corner_radius=6, height=35)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)
            ctk.CTkLabel(row, text=label + ":", font=FONTS["body"],
                         text_color=COLORS["text_secondary"]).pack(side="left", padx=10)
            ctk.CTkLabel(row, text=value, font=FONTS["body_bold"],
                         text_color=color).pack(side="right", padx=10)

        ctk.CTkButton(
            dialog, text="OK", font=FONTS["button"],
            fg_color=COLORS["primary"], text_color="white",
            hover_color="#0051D5", height=45, width=120,
            corner_radius=10, command=dialog.destroy
        ).pack(pady=(0, 25))
        dialog.focus_set()
