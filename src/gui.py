import os
import sys
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
from PIL import Image, ImageDraw
import cv2

from stego import VideoSteganography, StegoError
from video import VideoProcessor, check_ffmpeg
from metric import (
    metrics_streaming, plot_histogram_comparison,
    plot_histogram_overlay, plot_multiframe_residual,
    compare_histograms
)

TKDND_AVAILABLE = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    TKDND_AVAILABLE = True
except ImportError:
    pass

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

COLORS = {
    "primary": "#007AFF",
    "secondary": "#0A2540",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "bg": "#FFFFFF",
    "bg_secondary": "#F8F9FA",
    "card": "#FFFFFF",
    "border": "#E2E8F0",
    "text_primary": "#1A202C",
    "text_secondary": "#718096",
    "input_bg": "#F1F5F9",
}

FONTS = {
    "header": ("JetBrains Mono", 24, "bold"),
    "title": ("JetBrains Mono", 16, "bold"),
    "subtitle": ("JetBrains Mono", 14, "bold"),
    "body": ("JetBrains Mono", 12, "normal"),
    "body_bold": ("JetBrains Mono", 12, "bold"),
    "small": ("JetBrains Mono", 10, "normal"),
    "button": ("JetBrains Mono", 12, "bold"),
}


class ModernStegoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Steganography - A5/1 & LSB")
        self.root.geometry("1100x800")
        self.root.minsize(1000, 700)
        self.root.configure(fg_color=COLORS["bg"])

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
        self.current_tab = "embed"

        self._last_progress_update = 0
        self._last_progress_value = -1
        self._progress_update_interval_ms = 50

        self._preprocess_animating = False
        self._preprocess_animation_id = None
        self._preprocess_progress = 0.0
        self._preprocess_direction = 1

        self._create_main_layout()
        self._check_dependencies()

    def _create_main_layout(self):
        self.main_frame = ctk.CTkFrame(self.root, fg_color=COLORS["bg"], corner_radius=0)
        self.main_frame.pack(fill="both", expand=True)

        self.sidebar = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["secondary"],
            corner_radius=0,
            width=220
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self._create_sidebar()

        self.content_area = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_secondary"],
            corner_radius=0
        )
        self.content_area.pack(side="right", fill="both", expand=True)

        self._create_header()
        self._create_tab_content()
        self._create_status_bar()

    def _create_sidebar(self):
        header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", corner_radius=0)
        header_frame.pack(fill="x", padx=20, pady=(30, 40))

        title = ctk.CTkLabel(
            header_frame,
            text="Kelompok 13",
            font=FONTS["header"],
            text_color="white"
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="A5/1 & LSB Steganography",
            font=FONTS["small"],
            text_color="#94A3B8"
        )
        subtitle.pack(anchor="w", pady=(5, 0))

        separator = ctk.CTkFrame(self.sidebar, fg_color="#1E3A5F", height=1, corner_radius=0)
        separator.pack(fill="x", padx=20, pady=(0, 20))

        nav_items = [
            ("Embed", "embed", self._show_embed_tab),
            ("Extract", "extract", self._show_extract_tab),
            ("Analysis", "analysis", self._show_analysis_tab),
            ("Verify", "verify", self._show_verify_tab),
        ]

        self.nav_buttons = {}
        for label, tab_id, command in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                font=FONTS["body_bold"],
                fg_color="transparent",
                text_color="white",
                hover_color="#1E3A5F",
                corner_radius=8,
                height=45,
                anchor="w",
                command=lambda t=tab_id, c=command: self._switch_tab(t, c)
            )
            btn.pack(fill="x", padx=15, pady=5)
            self.nav_buttons[tab_id] = btn

        self.nav_buttons["embed"].configure(fg_color=COLORS["primary"])

        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", corner_radius=0)
        bottom_frame.pack(side="bottom", fill="x", padx=20, pady=20)

        version_label = ctk.CTkLabel(
            bottom_frame,
            text="II4021 - Kriptografi",
            font=FONTS["small"],
            text_color="#94A3B8"
        )
        version_label.pack(fill="x")

    def _create_header(self):
        self.header = ctk.CTkFrame(self.content_area, fg_color=COLORS["bg"], corner_radius=0, height=70)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)

        self.header_title = ctk.CTkLabel(
            self.header,
            text="Embed Message",
            font=FONTS["title"],
            text_color=COLORS["text_primary"]
        )
        self.header_title.pack(side="left", padx=30, pady=20)

    def _create_tab_content(self):
        self.tab_container = ctk.CTkFrame(
            self.content_area,
            fg_color="transparent",
            corner_radius=0
        )
        self.tab_container.pack(fill="both", expand=True, padx=30, pady=(20, 10))

        self.embed_frame = self._create_embed_view()
        self.extract_frame = self._create_extract_view()
        self.analysis_frame = self._create_analysis_view()
        self.verify_frame = self._create_verify_view()

        self.current_view = self.embed_frame
        self.extract_frame.pack_forget()
        self.analysis_frame.pack_forget()
        self.verify_frame.pack_forget()

    def _create_embed_view(self):
        frame = ctk.CTkFrame(self.tab_container, fg_color="transparent", corner_radius=0)

        self.embed_initial = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
        self.embed_initial.pack(fill="both", expand=True)

        center_frame = ctk.CTkFrame(self.embed_initial, fg_color="transparent", corner_radius=0)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        upload_icon = self._create_upload_icon()
        icon_label = ctk.CTkLabel(center_frame, image=upload_icon, text="")
        icon_label.pack()

        title = ctk.CTkLabel(
            center_frame,
            text="Select Cover Video",
            font=FONTS["subtitle"],
            text_color=COLORS["text_primary"]
        )
        title.pack(pady=(20, 10))

        desc = ctk.CTkLabel(
            center_frame,
            text="Choose a video file to embed your secret message",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        desc.pack()

        select_btn = ctk.CTkButton(
            center_frame,
            text="Browse Video",
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            text_color="white",
            hover_color="#0051D5",
            corner_radius=10,
            height=50,
            width=200,
            command=self._browse_video
        )
        select_btn.pack(pady=(30, 10))

        info_label = ctk.CTkLabel(
            center_frame,
            text="Select a video file to begin",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        info_label.pack()

        # if TKDND_AVAILABLE:
        #     center_frame.drop_target_register(DND_FILES)
        #     center_frame.dnd_bind('<<Drop>>', lambda e: self._handle_embed_drop(e))
        #     center_frame.dnd_bind('<<DropEnter>>', lambda e: or_label.configure(text="Drop video file here", text_color=COLORS["primary"], font=FONTS["body_bold"]))
        #     center_frame.dnd_bind('<<DropLeave>>', lambda e: or_label.configure(text="or drag and drop a video file here", text_color=COLORS["text_secondary"], font=FONTS["small"]))

        self.embed_config = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)

        config_card = ctk.CTkFrame(
            self.embed_config,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"]
        )
        config_card.pack(fill="both", expand=True, padx=20, pady=20)

        card_header = ctk.CTkFrame(config_card, fg_color="transparent", corner_radius=0)
        card_header.pack(fill="x", padx=30, pady=(25, 20))

        back_btn = ctk.CTkButton(
            card_header,
            text="< back to upload",
            font=FONTS["body"],
            fg_color="transparent",
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["input_bg"],
            width=80,
            height=35,
            command=self._reset_embed
        )
        back_btn.pack(side="left")

        header_title = ctk.CTkLabel(
            card_header,
            text="Configuration",
            font=FONTS["subtitle"],
            text_color=COLORS["secondary"]
        )
        header_title.pack(side="left", padx=(20, 0))

        scroll_frame = ctk.CTkScrollableFrame(
            config_card,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["primary"]
        )
        scroll_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        video_section = self._create_section_card(scroll_frame, "Video Information")
        video_section.pack(fill="x", pady=(0, 15))

        self.video_info_card = ctk.CTkFrame(video_section, fg_color=COLORS["input_bg"], corner_radius=10)
        self.video_info_card.pack(fill="x", padx=15, pady=15)

        self.video_name_label = ctk.CTkLabel(
            self.video_info_card,
            text="No video selected",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"]
        )
        self.video_name_label.pack(anchor="w", padx=15, pady=(15, 5))

        self.video_details_label = ctk.CTkLabel(
            self.video_info_card,
            text="",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        self.video_details_label.pack(anchor="w", padx=15, pady=(0, 15))

        capacity_btn = ctk.CTkButton(
            video_section,
            text="Calculate Capacity",
            font=FONTS["body"],
            fg_color=COLORS["primary"],
            text_color="white",
            hover_color="#0051D5",
            height=35,
            width=150,
            command=self._show_capacity
        )
        capacity_btn.pack(anchor="w", padx=15, pady=(0, 15))

        payload_section = self._create_section_card(scroll_frame, "Payload")
        payload_section.pack(fill="x", pady=(0, 15))

        toggle_frame = ctk.CTkFrame(payload_section, fg_color="transparent", corner_radius=0)
        toggle_frame.pack(fill="x", padx=15, pady=(15, 10))

        self.text_radio = ctk.CTkButton(
            toggle_frame,
            text="Text Message",
            font=FONTS["body"],
            fg_color=COLORS["primary"] if self.use_text_message.get() else COLORS["input_bg"],
            text_color="white" if self.use_text_message.get() else COLORS["text_secondary"],
            hover_color=COLORS["primary"],
            height=35,
            width=120,
            corner_radius=8,
            command=lambda: self._set_payload_type(True)
        )
        self.text_radio.pack(side="left", padx=(0, 10))

        self.file_radio = ctk.CTkButton(
            toggle_frame,
            text="File",
            font=FONTS["body"],
            fg_color=COLORS["input_bg"] if self.use_text_message.get() else COLORS["primary"],
            text_color=COLORS["text_secondary"] if self.use_text_message.get() else "white",
            hover_color=COLORS["primary"],
            height=35,
            width=80,
            corner_radius=8,
            command=lambda: self._set_payload_type(False)
        )
        self.file_radio.pack(side="left")

        self.text_input_frame = ctk.CTkFrame(payload_section, fg_color="transparent", corner_radius=0)
        self.text_input_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.message_text = ctk.CTkTextbox(
            self.text_input_frame,
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=10,
            height=100
        )
        self.message_text.pack(fill="x")

        self.file_input_frame = ctk.CTkFrame(payload_section, fg_color="transparent", corner_radius=0)

        file_row = ctk.CTkFrame(self.file_input_frame, fg_color="transparent", corner_radius=0)
        file_row.pack(fill="x")

        self.payload_entry = ctk.CTkEntry(
            file_row,
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            height=40
        )
        self.payload_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_payload_btn = ctk.CTkButton(
            file_row,
            text="Browse",
            font=FONTS["body"],
            fg_color=COLORS["secondary"],
            text_color="white",
            hover_color="#1A365D",
            height=40,
            width=100,
            command=self._browse_payload
        )
        browse_payload_btn.pack(side="left")

        self.payload_info_label = ctk.CTkLabel(
            self.file_input_frame,
            text="",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        self.payload_info_label.pack(anchor="w", pady=(5, 0))

        config_section = self._create_section_card(scroll_frame, "Configuration")
        config_section.pack(fill="x", pady=(0, 15))

        lsb_label = ctk.CTkLabel(
            config_section,
            text="LSB Mode",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"]
        )
        lsb_label.pack(anchor="w", padx=15, pady=(15, 10))

        lsb_frame = ctk.CTkFrame(config_section, fg_color="transparent", corner_radius=0)
        lsb_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.lsb_buttons = {}
        for mode, label in [('111', '1-1-1'), ('222', '2-2-2'), ('332', '3-3-2')]:
            btn = ctk.CTkButton(
                lsb_frame,
                text=f"{label}\n({mode[0]} bits/pixel)",
                font=FONTS["small"],
                fg_color=COLORS["primary"] if self.lsb_mode.get() == mode else COLORS["input_bg"],
                text_color="white" if self.lsb_mode.get() == mode else COLORS["text_secondary"],
                hover_color=COLORS["primary"],
                height=50,
                width=100,
                corner_radius=10,
                command=lambda m=mode: self._set_lsb_mode(m)
            )
            btn.pack(side="left", padx=(0, 10))
            self.lsb_buttons[mode] = btn

        security_section = self._create_section_card(scroll_frame, "Security")
        security_section.pack(fill="x", pady=(0, 15))

        enc_frame = ctk.CTkFrame(security_section, fg_color="transparent", corner_radius=0)
        enc_frame.pack(fill="x", padx=15, pady=(15, 10))

        self.enc_switch = ctk.CTkSwitch(
            enc_frame,
            text="Enable A5/1 Encryption",
            font=FONTS["body"],
            text_color=COLORS["text_primary"],
            fg_color=COLORS["border"],
            progress_color=COLORS["primary"],
            button_color="white",
            button_hover_color=COLORS["primary"],
            command=self._toggle_encryption_ui
        )
        self.enc_switch.pack(side="left")

        self.enc_key_frame = ctk.CTkFrame(security_section, fg_color="transparent", corner_radius=0)

        enc_key_label = ctk.CTkLabel(
            self.enc_key_frame,
            text="Encryption Key:",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        enc_key_label.pack(side="left", padx=(0, 10))

        self.enc_key_entry = ctk.CTkEntry(
            self.enc_key_frame,
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            height=35,
            width=250,
            show="*"
        )
        self.enc_key_entry.pack(side="left", padx=(0, 10))

        self.enc_key_entry.insert(0, self.encryption_key.get())
        self.enc_key_entry.bind("<KeyRelease>", lambda e: self.encryption_key.set(self.enc_key_entry.get()))

        show_enc_btn = ctk.CTkButton(
            self.enc_key_frame,
            text="Show",
            font=FONTS["small"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["border"],
            height=30,
            width=60,
            command=lambda: self._toggle_password_visibility(self.enc_key_entry)
        )
        show_enc_btn.pack(side="left")

        spread_frame = ctk.CTkFrame(security_section, fg_color="transparent", corner_radius=0)
        spread_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.spread_switch = ctk.CTkSwitch(
            spread_frame,
            text="Random Pixel Spreading",
            font=FONTS["body"],
            text_color=COLORS["text_primary"],
            fg_color=COLORS["border"],
            progress_color=COLORS["primary"],
            button_color="white",
            button_hover_color=COLORS["primary"],
            command=self._toggle_random_ui
        )
        self.spread_switch.pack(side="left")

        self.spread_key_frame = ctk.CTkFrame(security_section, fg_color="transparent", corner_radius=0)

        spread_key_label = ctk.CTkLabel(
            self.spread_key_frame,
            text="Stego Key:",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        spread_key_label.pack(side="left", padx=(0, 10))

        self.spread_key_entry = ctk.CTkEntry(
            self.spread_key_frame,
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            height=35,
            width=250
        )
        self.spread_key_entry.pack(side="left")
        self.spread_key_entry.insert(0, self.stego_key.get())
        self.spread_key_entry.bind("<KeyRelease>", lambda e: self.stego_key.set(self.spread_key_entry.get()))

        output_section = self._create_section_card(scroll_frame, "Output")
        output_section.pack(fill="x", pady=(0, 15))

        output_row = ctk.CTkFrame(output_section, fg_color="transparent", corner_radius=0)
        output_row.pack(fill="x", padx=15, pady=15)

        self.output_entry = ctk.CTkEntry(
            output_row,
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            height=40,
            placeholder_text="Select output location..."
        )
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_output_btn = ctk.CTkButton(
            output_row,
            text="Browse",
            font=FONTS["body"],
            fg_color=COLORS["secondary"],
            text_color="white",
            hover_color="#1A365D",
            height=40,
            width=100,
            command=self._browse_output
        )
        browse_output_btn.pack(side="left")

        action_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent", corner_radius=0)
        action_frame.pack(fill="x", pady=(20, 10))

        test_btn = ctk.CTkButton(
            action_frame,
            text="Test Overflow",
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["border"],
            height=45,
            width=130,
            command=self._test_capacity_overflow
        )
        test_btn.pack(side="left", padx=(0, 15))

        self.embed_btn = ctk.CTkButton(
            action_frame,
            text="Embed Message",
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            text_color="white",
            hover_color="#0051D5",
            height=45,
            width=180,
            command=self._start_embed
        )
        self.embed_btn.pack(side="left")

        self.embed_loading = ctk.CTkFrame(frame, fg_color=COLORS["bg_secondary"], corner_radius=0)

        loading_center = ctk.CTkFrame(self.embed_loading, fg_color="transparent", corner_radius=0)
        loading_center.place(relx=0.5, rely=0.5, anchor="center")

        self.loading_title = ctk.CTkLabel(
            loading_center,
            text="Embedding Message...",
            font=FONTS["title"],
            text_color=COLORS["secondary"]
        )
        self.loading_title.pack(pady=(0, 20))

        progress_container = ctk.CTkFrame(loading_center, fg_color=COLORS["card"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        progress_container.pack(fill="x", padx=20)

        self.embed_progress_bar = ctk.CTkProgressBar(
            progress_container,
            width=350,
            height=20,
            mode="determinate",
            progress_color=COLORS["primary"],
            fg_color=COLORS["border"],
            corner_radius=10
        )
        self.embed_progress_bar.pack(padx=25, pady=25)
        self.embed_progress_bar.set(0)

        self.embed_progress_percent = ctk.CTkLabel(
            progress_container,
            text="0%",
            font=FONTS["header"],
            text_color=COLORS["primary"]
        )
        self.embed_progress_percent.pack(pady=(0, 15))

        self.loading_status = ctk.CTkLabel(
            loading_center,
            text="Preparing...",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        self.loading_status.pack(pady=(20, 0))

        self.loading_detail = ctk.CTkLabel(
            loading_center,
            text="",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        self.loading_detail.pack(pady=(5, 0))

        return frame

    def _create_extract_view(self):
        frame = ctk.CTkFrame(self.tab_container, fg_color="transparent", corner_radius=0)

        self.extract_initial = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
        self.extract_initial.pack(fill="both", expand=True)

        center_frame = ctk.CTkFrame(self.extract_initial, fg_color="transparent", corner_radius=0)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        video_icon = self._create_video_icon()
        icon_label = ctk.CTkLabel(center_frame, image=video_icon, text="")
        icon_label.pack()

        title = ctk.CTkLabel(
            center_frame,
            text="Select Stego Video",
            font=FONTS["subtitle"],
            text_color=COLORS["text_primary"]
        )
        title.pack(pady=(20, 10))

        desc = ctk.CTkLabel(
            center_frame,
            text="Choose a steganography video to extract hidden message",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        desc.pack()

        select_btn = ctk.CTkButton(
            center_frame,
            text="Browse Stego Video",
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            text_color="white",
            hover_color="#0051D5",
            corner_radius=10,
            height=50,
            width=220,
            command=self._browse_stego_video
        )
        select_btn.pack(pady=(30, 10))

        info_label = ctk.CTkLabel(
            center_frame,
            text="Select a stego video file to begin",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        info_label.pack()

        # if TKDND_AVAILABLE:
        #     center_frame.drop_target_register(DND_FILES)
        #     center_frame.dnd_bind('<<Drop>>', lambda e: self._handle_extract_drop(e))
        #     center_frame.dnd_bind('<<DropEnter>>', lambda e: info_label.configure(text="Drop stego video here", text_color=COLORS["primary"], font=FONTS["body_bold"]))
        #     center_frame.dnd_bind('<<DropLeave>>', lambda e: info_label.configure(text="Select a stego video file to begin", text_color=COLORS["text_secondary"], font=FONTS["small"]))

        self.extract_config = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)

        config_card = ctk.CTkFrame(
            self.extract_config,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"]
        )
        config_card.pack(fill="both", expand=True, padx=20, pady=20)

        card_header = ctk.CTkFrame(config_card, fg_color="transparent", corner_radius=0)
        card_header.pack(fill="x", padx=30, pady=(25, 20))

        back_btn = ctk.CTkButton(
            card_header,
            text="< back to upload",
            font=FONTS["body"],
            fg_color="transparent",
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["input_bg"],
            width=80,
            height=35,
            command=self._reset_extract
        )
        back_btn.pack(side="left")

        header_title = ctk.CTkLabel(
            card_header,
            text="Extraction Configuration",
            font=FONTS["subtitle"],
            text_color=COLORS["secondary"]
        )
        header_title.pack(side="left", padx=(20, 0))

        scroll_frame = ctk.CTkScrollableFrame(
            config_card,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["primary"]
        )
        scroll_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        video_section = self._create_section_card(scroll_frame, "Stego Video")
        video_section.pack(fill="x", pady=(0, 15))

        self.stego_info_card = ctk.CTkFrame(video_section, fg_color=COLORS["input_bg"], corner_radius=10)
        self.stego_info_card.pack(fill="x", padx=15, pady=15)

        self.stego_name_label = ctk.CTkLabel(
            self.stego_info_card,
            text="No video selected",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"]
        )
        self.stego_name_label.pack(anchor="w", padx=15, pady=(15, 5))

        self.stego_details_label = ctk.CTkLabel(
            self.stego_info_card,
            text="",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        self.stego_details_label.pack(anchor="w", padx=15, pady=(0, 15))

        keys_section = self._create_section_card(scroll_frame, "Decryption Keys (Optional)")
        keys_section.pack(fill="x", pady=(0, 15))

        enc_row = ctk.CTkFrame(keys_section, fg_color="transparent", corner_radius=0)
        enc_row.pack(fill="x", padx=15, pady=(15, 10))

        enc_label = ctk.CTkLabel(
            enc_row,
            text="A5/1 Key:",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
            width=100
        )
        enc_label.pack(side="left")

        self.extract_enc_entry = ctk.CTkEntry(
            enc_row,
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            height=40,
            show="*",
            placeholder_text="Enter if encrypted..."
        )
        self.extract_enc_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))

        stego_row = ctk.CTkFrame(keys_section, fg_color="transparent", corner_radius=0)
        stego_row.pack(fill="x", padx=15, pady=(0, 15))

        stego_label = ctk.CTkLabel(
            stego_row,
            text="Stego Key:",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
            width=100
        )
        stego_label.pack(side="left")

        self.extract_stego_entry = ctk.CTkEntry(
            stego_row,
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            height=40,
            placeholder_text="Enter if random spreading used..."
        )
        self.extract_stego_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))

        output_section = self._create_section_card(scroll_frame, "Output Directory")
        output_section.pack(fill="x", pady=(0, 15))

        output_row = ctk.CTkFrame(output_section, fg_color="transparent", corner_radius=0)
        output_row.pack(fill="x", padx=15, pady=15)

        self.extract_output_entry = ctk.CTkEntry(
            output_row,
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            height=40,
            placeholder_text="Select output directory..."
        )
        self.extract_output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_extract_btn = ctk.CTkButton(
            output_row,
            text="Browse",
            font=FONTS["body"],
            fg_color=COLORS["secondary"],
            text_color="white",
            hover_color="#1A365D",
            height=40,
            width=100,
            command=self._browse_extract_output
        )
        browse_extract_btn.pack(side="left")

        action_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent", corner_radius=0)
        action_frame.pack(fill="x", pady=(20, 10))

        cancel_btn = ctk.CTkButton(
            action_frame,
            text="Cancel",
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["border"],
            height=45,
            width=120,
            command=self._reset_extract
        )
        cancel_btn.pack(side="left", padx=(0, 15))

        self.extract_btn = ctk.CTkButton(
            action_frame,
            text="Extract Message",
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            text_color="white",
            hover_color="#0051D5",
            height=45,
            width=180,
            command=self._start_extract
        )
        self.extract_btn.pack(side="left")

        result_section = self._create_section_card(scroll_frame, "Extraction Result")
        result_section.pack(fill="both", expand=True, pady=(0, 15))

        self.result_text = ctk.CTkTextbox(
            result_section,
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=10,
            height=150
        )
        self.result_text.pack(fill="both", expand=True, padx=15, pady=15)

        self.extract_loading = ctk.CTkFrame(frame, fg_color=COLORS["bg_secondary"], corner_radius=0)

        loading_center = ctk.CTkFrame(self.extract_loading, fg_color="transparent", corner_radius=0)
        loading_center.place(relx=0.5, rely=0.5, anchor="center")

        extract_loading_title = ctk.CTkLabel(
            loading_center,
            text="Extracting Message...",
            font=FONTS["title"],
            text_color=COLORS["secondary"]
        )
        extract_loading_title.pack(pady=(0, 20))

        progress_container = ctk.CTkFrame(loading_center, fg_color=COLORS["card"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        progress_container.pack(fill="x", padx=20)

        self.extract_progress_bar_loading = ctk.CTkProgressBar(
            progress_container,
            width=350,
            height=20,
            mode="determinate",
            progress_color=COLORS["primary"],
            fg_color=COLORS["border"],
            corner_radius=10
        )
        self.extract_progress_bar_loading.pack(padx=25, pady=25)
        self.extract_progress_bar_loading.set(0)

        self.extract_progress_percent = ctk.CTkLabel(
            progress_container,
            text="0%",
            font=FONTS["header"],
            text_color=COLORS["primary"]
        )
        self.extract_progress_percent.pack(pady=(0, 15))

        self.extract_loading_status = ctk.CTkLabel(
            loading_center,
            text="Preparing...",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        self.extract_loading_status.pack(pady=(20, 0))

        self.extract_loading_detail = ctk.CTkLabel(
            loading_center,
            text="",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        self.extract_loading_detail.pack(pady=(5, 0))

        return frame

    def _create_analysis_view(self):
        frame = ctk.CTkFrame(self.tab_container, fg_color="transparent", corner_radius=0)

        header_label = ctk.CTkLabel(
            frame,
            text="Compare Original vs Stego Video",
            font=FONTS["subtitle"],
            text_color=COLORS["secondary"]
        )
        header_label.pack(anchor="w", pady=(0, 20))

        cards_frame = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
        cards_frame.pack(fill="x", pady=(0, 20))
        cards_frame.grid_columnconfigure(0, weight=1)
        cards_frame.grid_columnconfigure(1, weight=1)

        self.orig_card = self._create_file_drop_card(
            cards_frame,
            "Original Video",
            "Drop or browse original video file",
            lambda: self._browse_analysis_file("orig"),
            lambda p: self._handle_analysis_drop(p, "orig")
        )
        self.orig_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        self.stego_card = self._create_file_drop_card(
            cards_frame,
            "Stego Video",
            "Drop or browse stego video file",
            lambda: self._browse_analysis_file("stego"),
            lambda p: self._handle_analysis_drop(p, "stego")
        )
        self.stego_card.grid(row=0, column=1, padx=(10, 0), sticky="nsew")

        actions_frame = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
        actions_frame.pack(fill="x", pady=(0, 20))

        self.mse_btn = ctk.CTkButton(
            actions_frame,
            text="Calculate MSE & PSNR",
            font=FONTS["body"],
            fg_color=COLORS["primary"],
            text_color="white",
            hover_color="#0051D5",
            height=40,
            command=self._calculate_metrics
        )
        self.mse_btn.pack(side="left", padx=(0, 10))

        hist_btn = ctk.CTkButton(
            actions_frame,
            text="Compare Histogram",
            font=FONTS["body"],
            fg_color=COLORS["secondary"],
            text_color="white",
            hover_color="#1A365D",
            height=40,
            command=self._show_histogram
        )
        hist_btn.pack(side="left", padx=(0, 10))

        overlay_btn = ctk.CTkButton(
            actions_frame,
            text="Overlay Histogram",
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["border"],
            height=40,
            command=self._show_histogram_overlay
        )
        overlay_btn.pack(side="left", padx=(0, 10))

        multi_btn = ctk.CTkButton(
            actions_frame,
            text="Multi-Frame Analysis",
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["border"],
            height=40,
            command=self._show_multiframe_analysis
        )
        multi_btn.pack(side="left")

        results_frame = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
        results_frame.pack(fill="both", expand=True)
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_columnconfigure(1, weight=2)
        results_frame.grid_rowconfigure(0, weight=1)

        metrics_frame = ctk.CTkFrame(
            results_frame,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"]
        )
        metrics_frame.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        metrics_title = ctk.CTkLabel(
            metrics_frame,
            text="Metrics",
            font=FONTS["subtitle"],
            text_color=COLORS["secondary"]
        )
        metrics_title.pack(anchor="w", padx=20, pady=(20, 15))

        self.mse_card = self._create_metric_card(metrics_frame, "MSE", "--", COLORS["primary"])
        self.mse_card.pack(fill="x", padx=20, pady=(0, 10))

        self.psnr_card = self._create_metric_card(metrics_frame, "PSNR", "-- dB", COLORS["success"])
        self.psnr_card.pack(fill="x", padx=20, pady=(0, 20))

        self.analysis_result = ctk.CTkTextbox(
            metrics_frame,
            font=FONTS["small"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=10,
            height=200
        )
        self.analysis_result.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.histogram_frame = ctk.CTkFrame(
            results_frame,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.histogram_frame.grid(row=0, column=1, padx=(10, 0), sticky="nsew")

        hist_title = ctk.CTkLabel(
            self.histogram_frame,
            text="Histogram Visualization",
            font=FONTS["subtitle"],
            text_color=COLORS["secondary"]
        )
        hist_title.pack(anchor="w", padx=20, pady=(20, 15))

        self.histogram_placeholder = ctk.CTkLabel(
            self.histogram_frame,
            text="Select videos and click Compare Histogram\nto visualize data distribution",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        self.histogram_placeholder.pack(expand=True)

        self.histogram_canvas = None

        return frame

    def _create_verify_view(self):
        frame = ctk.CTkFrame(self.tab_container, fg_color="transparent", corner_radius=0)

        header_label = ctk.CTkLabel(
            frame,
            text="Verify File Integrity",
            font=FONTS["subtitle"],
            text_color=COLORS["secondary"]
        )
        header_label.pack(anchor="w", pady=(0, 20))

        desc_label = ctk.CTkLabel(
            frame,
            text="Compare file hashes to verify integrity",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        desc_label.pack(anchor="w", pady=(0, 10))

        algo_frame = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
        algo_frame.pack(anchor="w", pady=(0, 20))

        algo_label = ctk.CTkLabel(
            algo_frame,
            text="Hash Algorithm:",
            font=FONTS["body"],
            text_color=COLORS["text_primary"]
        )
        algo_label.pack(side="left", padx=(0, 10))

        self.hash_algo_var = tk.StringVar(value="sha256")
        self.hash_algo_seg = ctk.CTkSegmentedButton(
            algo_frame,
            values=["SHA-256", "MD5"],
            variable=self.hash_algo_var,
            font=FONTS["body"],
            selected_color=COLORS["primary"],
            selected_hover_color="#0051D5",
            unselected_color=COLORS["input_bg"],
            unselected_hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            command=self._on_hash_algo_change
        )
        self.hash_algo_seg.pack(side="left")

        cards_frame = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
        cards_frame.pack(fill="x", pady=(0, 20))
        cards_frame.grid_columnconfigure(0, weight=1)
        cards_frame.grid_columnconfigure(1, weight=1)

        self.verify_orig_card = self._create_file_drop_card(
            cards_frame,
            "Original File",
            "Drop or browse original embedded file",
            lambda: self._browse_verify_file("orig"),
            lambda p: self._handle_verify_drop(p, "orig")
        )
        self.verify_orig_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        self.verify_ext_card = self._create_file_drop_card(
            cards_frame,
            "Extracted File",
            "Drop or browse extracted file",
            lambda: self._browse_verify_file("ext"),
            lambda p: self._handle_verify_drop(p, "ext")
        )
        self.verify_ext_card.grid(row=0, column=1, padx=(10, 0), sticky="nsew")

        verify_btn = ctk.CTkButton(
            frame,
            text="Verify Integrity",
            font=FONTS["button"],
            fg_color=COLORS["secondary"],
            text_color="white",
            hover_color="#1A365D",
            height=50,
            width=250,
            command=self._verify_file_integrity
        )
        verify_btn.pack(pady=20)

        self.verify_result_frame = ctk.CTkFrame(
            frame,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.verify_result_frame.pack(fill="both", expand=True)

        result_title = ctk.CTkLabel(
            self.verify_result_frame,
            text="Verification Result",
            font=FONTS["subtitle"],
            text_color=COLORS["secondary"]
        )
        result_title.pack(anchor="w", padx=30, pady=(25, 20))

        self.verify_status_badge = ctk.CTkFrame(
            self.verify_result_frame,
            fg_color=COLORS["input_bg"],
            corner_radius=20,
            height=50
        )
        self.verify_status_badge.pack(fill="x", padx=30, pady=(0, 20))

        self.verify_status_label = ctk.CTkLabel(
            self.verify_status_badge,
            text="Waiting for verification...",
            font=FONTS["body_bold"],
            text_color=COLORS["text_secondary"]
        )
        self.verify_status_label.place(relx=0.5, rely=0.5, anchor="center")

        hashes_frame = ctk.CTkFrame(self.verify_result_frame, fg_color="transparent", corner_radius=0)
        hashes_frame.pack(fill="x", padx=30, pady=(0, 20))
        hashes_frame.grid_columnconfigure(0, weight=1)
        hashes_frame.grid_columnconfigure(1, weight=1)

        orig_hash_frame = ctk.CTkFrame(
            hashes_frame,
            fg_color=COLORS["input_bg"],
            corner_radius=10
        )
        orig_hash_frame.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        self.orig_hash_title = ctk.CTkLabel(
            orig_hash_frame,
            text="Original File (SHA-256)",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"]
        )
        self.orig_hash_title.pack(anchor="w", padx=15, pady=(15, 10))

        self.orig_hash_label = ctk.CTkLabel(
            orig_hash_frame,
            text="--",
            font=("JetBrains Mono", 10),
            text_color=COLORS["text_secondary"],
            wraplength=400
        )
        self.orig_hash_label.pack(anchor="w", padx=15, pady=(0, 15))

        ext_hash_frame = ctk.CTkFrame(
            hashes_frame,
            fg_color=COLORS["input_bg"],
            corner_radius=10
        )
        ext_hash_frame.grid(row=0, column=1, padx=(10, 0), sticky="nsew")

        self.ext_hash_title = ctk.CTkLabel(
            ext_hash_frame,
            text="Extracted File (SHA-256)",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"]
        )
        self.ext_hash_title.pack(anchor="w", padx=15, pady=(15, 10))

        self.ext_hash_label = ctk.CTkLabel(
            ext_hash_frame,
            text="--",
            font=("JetBrains Mono", 10),
            text_color=COLORS["text_secondary"],
            wraplength=400
        )
        self.ext_hash_label.pack(anchor="w", padx=15, pady=(0, 15))

        return frame

    def _create_section_card(self, parent, title):
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )

        title_label = ctk.CTkLabel(
            card,
            text=title,
            font=FONTS["body_bold"],
            text_color=COLORS["secondary"]
        )
        title_label.pack(anchor="w", padx=15, pady=(15, 0))

        separator = ctk.CTkFrame(card, fg_color=COLORS["border"], height=1, corner_radius=0)
        separator.pack(fill="x", padx=15, pady=(10, 0))

        return card

    def _create_file_drop_card(self, parent, title, subtitle, browse_command, drop_callback=None):
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["card"],
            corner_radius=16,
            border_width=2,
            border_color=COLORS["border"],
            height=200
        )
        card.grid_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent", corner_radius=0)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        icon = self._create_upload_icon_small()
        icon_label = ctk.CTkLabel(inner, image=icon, text="")
        icon_label.pack()

        title_label = ctk.CTkLabel(
            inner,
            text=title,
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"]
        )
        title_label.pack(pady=(10, 5))

        subtitle_label = ctk.CTkLabel(
            inner,
            text=subtitle,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        subtitle_label.pack()

        browse_btn = ctk.CTkButton(
            inner,
            text="Browse",
            font=FONTS["small"],
            fg_color=COLORS["primary"],
            text_color="white",
            hover_color="#0051D5",
            height=30,
            width=100,
            command=browse_command
        )
        browse_btn.pack(pady=(15, 0))

        # if TKDND_AVAILABLE and drop_callback:
        #     card.drop_target_register(DND_FILES)
        #     card.dnd_bind('<<Drop>>', lambda e: self._handle_drop(e, drop_callback, card))
        #     card.dnd_bind('<<DropEnter>>', lambda e: self._on_drag_enter(card))
        #     card.dnd_bind('<<DropLeave>>', lambda e: self._on_drag_leave(card))

        return card

    def _handle_drop(self, event, callback, card):
        file_path = event.data
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]
        if os.path.isfile(file_path):
            self._on_drag_leave(card)
            callback(file_path)
        else:
            self._show_modern_warning("Please drop a valid file.")

    def _on_drag_enter(self, card):
        card.configure(border_color=COLORS["primary"])

    def _on_drag_leave(self, card):
        card.configure(border_color=COLORS["border"])

    def _create_metric_card(self, parent, label, value, color):
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["input_bg"],
            corner_radius=12,
            height=80
        )
        card.pack_propagate(False)

        left = ctk.CTkFrame(card, fg_color="transparent", corner_radius=0)
        left.pack(side="left", fill="y", padx=15, pady=15)

        label_widget = ctk.CTkLabel(
            left,
            text=label,
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        label_widget.pack(anchor="w")

        value_widget = ctk.CTkLabel(
            left,
            text=value,
            font=FONTS["header"],
            text_color=color
        )
        value_widget.pack(anchor="w")

        return card

    def _create_status_bar(self):
        self.status_bar = ctk.CTkFrame(
            self.content_area,
            fg_color=COLORS["card"],
            corner_radius=0,
            height=50,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Ready",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(side="left", padx=20, pady=15)

    def _create_upload_icon(self):
        size = 80
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.ellipse([5, 5, size-5, size-5], outline="#007AFF", width=3)

        arrow_x = size // 2
        arrow_top = 25
        arrow_bottom = 50
        arrow_width = 15

        draw.polygon([
            (arrow_x, arrow_top),
            (arrow_x - arrow_width, arrow_bottom - 10),
            (arrow_x + arrow_width, arrow_bottom - 10)
        ], fill="#007AFF")

        draw.rectangle([arrow_x - 8, arrow_bottom - 10, arrow_x + 8, arrow_bottom + 5], fill="#007AFF")

        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

    def _create_video_icon(self):
        size = 80
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle([10, 20, size-10, size-20], radius=8, outline="#007AFF", width=3)

        triangle = [
            (size//2 - 8, size//2 - 10),
            (size//2 - 8, size//2 + 10),
            (size//2 + 10, size//2)
        ]
        draw.polygon(triangle, fill="#007AFF")

        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

    def _create_upload_icon_small(self):
        size = 40
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.ellipse([2, 2, size-2, size-2], outline="#007AFF", width=2)

        arrow_x = size // 2
        draw.polygon([
            (arrow_x, 12),
            (arrow_x - 6, 22),
            (arrow_x + 6, 22)
        ], fill="#007AFF")

        draw.rectangle([arrow_x - 4, 22, arrow_x + 4, 28], fill="#007AFF")

        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

    def _switch_tab(self, tab_id, command):
        for tid, btn in self.nav_buttons.items():
            if tid == tab_id:
                btn.configure(fg_color=COLORS["primary"])
            else:
                btn.configure(fg_color="transparent")

        self.current_tab = tab_id
        command()

    def _show_embed_tab(self):
        self.header_title.configure(text="Embed Message")
        self.current_view.pack_forget()
        self.current_view = self.embed_frame
        self.embed_frame.pack(fill="both", expand=True)
        self._clear_error_status()

    def _show_extract_tab(self):
        self.header_title.configure(text="Extract Message")
        self.current_view.pack_forget()
        self.current_view = self.extract_frame
        self.extract_frame.pack(fill="both", expand=True)
        self._clear_error_status()

    def _show_analysis_tab(self):
        self.header_title.configure(text="Video Analysis")
        self.current_view.pack_forget()
        self.current_view = self.analysis_frame
        self.analysis_frame.pack(fill="both", expand=True)
        self._clear_error_status()

    def _show_verify_tab(self):
        self.header_title.configure(text="Verify Integrity")
        self.current_view.pack_forget()
        self.current_view = self.verify_frame
        self.verify_frame.pack(fill="both", expand=True)
        self._clear_error_status()

    def _on_hash_algo_change(self, value):
        """Update hash algorithm display when selection changes"""
        algo = value.replace("-", "").lower()
        display_name = value

        self.orig_hash_title.configure(text=f"Original File ({display_name})")
        self.ext_hash_title.configure(text=f"Extracted File ({display_name})")

        self.orig_hash_label.configure(text="--")
        self.ext_hash_label.configure(text="--")
        self.verify_status_label.configure(text="Waiting for verification...", text_color=COLORS["text_secondary"])
        self.verify_status_badge.configure(fg_color=COLORS["input_bg"])

    def _clear_error_status(self):
        current_text = self.status_label.cget("text")
        if "Error:" in current_text:
            self.status_label.configure(text="Ready")

    def _toggle_password_visibility(self, entry):
        current = entry.cget("show")
        entry.configure(show="" if current == "*" else "*")

    def _set_payload_type(self, is_text):
        self.use_text_message.set(is_text)
        if is_text:
            self.text_radio.configure(
                fg_color=COLORS["primary"],
                text_color="white"
            )
            self.file_radio.configure(
                fg_color=COLORS["input_bg"],
                text_color=COLORS["text_secondary"]
            )
            self.file_input_frame.pack_forget()
            self.text_input_frame.pack(fill="x", padx=15, pady=(0, 15))
        else:
            self.file_radio.configure(
                fg_color=COLORS["primary"],
                text_color="white"
            )
            self.text_radio.configure(
                fg_color=COLORS["input_bg"],
                text_color=COLORS["text_secondary"]
            )
            self.text_input_frame.pack_forget()
            self.file_input_frame.pack(fill="x", padx=15, pady=(0, 15))

    def _set_lsb_mode(self, mode):
        self.lsb_mode.set(mode)
        for m, btn in self.lsb_buttons.items():
            if m == mode:
                btn.configure(fg_color=COLORS["primary"], text_color="white")
            else:
                btn.configure(fg_color=COLORS["input_bg"], text_color=COLORS["text_secondary"])

        if self.video_path.get() and os.path.exists(self.video_path.get()):
            self._update_video_info()

    def _toggle_encryption_ui(self):
        is_on = self.enc_switch.get()
        self.use_encryption.set(is_on)
        if is_on:
            self.enc_key_frame.pack(fill="x", padx=15, pady=(0, 15))
        else:
            self.enc_key_frame.pack_forget()
            self.encryption_key.set("")
            self.enc_key_entry.delete(0, "end")

    def _toggle_random_ui(self):
        is_on = self.spread_switch.get()
        self.use_random.set(is_on)
        if is_on:
            self.spread_key_frame.pack(fill="x", padx=15, pady=(0, 15))
        else:
            self.spread_key_frame.pack_forget()
            self.stego_key.set("")
            self.spread_key_entry.delete(0, "end")

    def _reset_embed(self):
        self.video_path.set("")
        self.output_path.set("")
        self.payload_path.set("")
        self.message_text.delete("0.0", "end")
        self.output_entry.delete(0, "end")
        self.payload_entry.delete(0, "end")
        self.payload_info_label.configure(text="")
        self.video_name_label.configure(text="No video selected")
        self.video_details_label.configure(text="")
        self.use_text_message.set(True)
        self._set_payload_type(True)
        self.embed_initial.pack(fill="both", expand=True)
        self.embed_config.pack_forget()
        self.embed_loading.pack_forget()

    def _reset_extract(self):
        self.stego_video_path.set("")
        self.extract_output_dir.set("")
        self.extract_output_entry.delete(0, "end")
        self.extract_enc_entry.delete(0, "end")
        self.extract_stego_entry.delete(0, "end")
        self.result_text.delete("0.0", "end")
        self.stego_name_label.configure(text="No video selected")
        self.stego_details_label.configure(text="")
        self.extract_initial.pack(fill="both", expand=True)
        self.extract_config.pack_forget()
        self.extract_loading.pack_forget()

    def _browse_video(self):
        path = filedialog.askopenfilename(
            title="Select Cover Video",
            filetypes=[("Video files", "*.avi *.mp4 *.mkv *.mov"), ("All files", "*.*")]
        )
        if path:
            self.video_path.set(path)
            self._update_video_info()
            base_dir = os.path.dirname(path)
            filename = os.path.basename(path)
            name, ext = os.path.splitext(filename)
            output_filename = f"{name}_stego.avi"
            output_path = os.path.join(base_dir, output_filename)
            self.output_path.set(output_path)
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, output_path)

            self.embed_initial.pack_forget()
            self.embed_config.pack(fill="both", expand=True)

    def _update_video_info(self):
        path = self.video_path.get()
        if not path or not os.path.exists(path):
            return

        try:
            with VideoProcessor(path) as vp:
                w, h, fps, total = vp.get_info()
                file_size = os.path.getsize(path)
                size_mb = file_size / (1024 * 1024)

                stego = VideoSteganography(self.lsb_mode.get())
                cap = stego.calculate_capacity(path)
                capacity_mb = cap['payload_capacity_bytes'] / (1024 * 1024)

                self.video_name_label.configure(text=os.path.basename(path))
                self.video_details_label.configure(
                    text=f"Resolution: {w}x{h} | FPS: {fps:.2f} | Frames: {total} | Size: {size_mb:.2f} MB | Capacity: {capacity_mb:.2f} MB"
                )
        except Exception as e:
            self.video_details_label.configure(text=f"Error: {e}")

    def _browse_payload(self):
        path = filedialog.askopenfilename(title="Select Payload File")
        if path:
            self.payload_path.set(path)
            self.payload_entry.delete(0, "end")
            self.payload_entry.insert(0, path)
            size = os.path.getsize(path)
            self.payload_info_label.configure(text=f"Size: {size:,} bytes ({size * 8:,} bits)")

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save Stego Video As",
            defaultextension=".avi",
            filetypes=[("AVI files (Recommended)", "*.avi"), ("All files", "*.*")]
        )
        if path:
            ext = os.path.splitext(path)[1].lower()
            lossy_formats = ['.mp4', '.mkv', '.mov', '.webm', '.wmv', '.flv']

            if ext in lossy_formats:
                if not self._show_lossy_format_warning(ext):
                    return

            self.output_path.set(path)
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, path)

    def _browse_stego_video(self):
        path = filedialog.askopenfilename(
            title="Select Stego Video",
            filetypes=[("Video files", "*.avi *.mp4 *.mkv *.mov"), ("All files", "*.*")]
        )
        if path:
            self.stego_video_path.set(path)
            output_dir = os.path.dirname(path)
            self.extract_output_dir.set(output_dir)
            self.extract_output_entry.delete(0, "end")
            self.extract_output_entry.insert(0, output_dir)

            try:
                with VideoProcessor(path) as vp:
                    w, h, fps, total = vp.get_info()
                    file_size = os.path.getsize(path)
                    size_mb = file_size / (1024 * 1024)
                    self.stego_name_label.configure(text=os.path.basename(path))
                    self.stego_details_label.configure(
                        text=f"Resolution: {w}x{h} | FPS: {fps:.2f} | Frames: {total} | Size: {size_mb:.2f} MB"
                    )
            except Exception as e:
                self.stego_details_label.configure(text=f"Error reading video: {e}")

            self.extract_initial.pack_forget()
            self.extract_config.pack(fill="both", expand=True)

    def _browse_extract_output(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.extract_output_dir.set(path)
            self.extract_output_entry.delete(0, "end")
            self.extract_output_entry.insert(0, path)

    def _browse_analysis_file(self, file_type):
        path = filedialog.askopenfilename(
            title=f"Select {'Original' if file_type == 'orig' else 'Stego'} Video",
            filetypes=[("Video files", "*.avi *.mp4 *.mkv *.mov"), ("All files", "*.*")]
        )
        if path:
            if file_type == "orig":
                self.analysis_orig_path = path
                self._update_drop_card(self.orig_card, os.path.basename(path), path)
            else:
                self.analysis_stego_path = path
                self._update_drop_card(self.stego_card, os.path.basename(path), path)

    def _browse_verify_file(self, file_type):
        path = filedialog.askopenfilename(title="Select File for Verification")
        if path:
            if file_type == "orig":
                self.verify_orig_path = path
                self._update_drop_card(self.verify_orig_card, os.path.basename(path), path)
            else:
                self.verify_ext_path = path
                self._update_drop_card(self.verify_ext_card, os.path.basename(path), path)

    def _update_drop_card(self, card, filename, fullpath):
        for widget in card.winfo_children():
            widget.destroy()

        inner = ctk.CTkFrame(card, fg_color="transparent", corner_radius=0)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        file_label = ctk.CTkLabel(
            inner,
            text=filename,
            font=FONTS["body_bold"],
            text_color=COLORS["primary"]
        )
        file_label.pack()

        path_label = ctk.CTkLabel(
            inner,
            text=fullpath[:50] + "..." if len(fullpath) > 50 else fullpath,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        path_label.pack()

        change_btn = ctk.CTkButton(
            inner,
            text="Change",
            font=FONTS["small"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["border"],
            height=25,
            width=80,
            command=lambda: self._reset_drop_card(card)
        )
        change_btn.pack(pady=(10, 0))

    def _reset_drop_card(self, card):
        for widget in card.winfo_children():
            widget.destroy()

        inner = ctk.CTkFrame(card, fg_color="transparent", corner_radius=0)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        icon = self._create_upload_icon_small()
        icon_label = ctk.CTkLabel(inner, image=icon, text="")
        icon_label.pack()

        is_orig = card == self.orig_card or card == self.verify_orig_card
        title_text = "Original" if is_orig else "Stego/Extracted"

        title_label = ctk.CTkLabel(
            inner,
            text=f"{title_text} File",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"]
        )
        title_label.pack(pady=(10, 5))

        subtitle_label = ctk.CTkLabel(
            inner,
            text="Drop or browse file",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        subtitle_label.pack()

        browse_btn = ctk.CTkButton(
            inner,
            text="Browse",
            font=FONTS["small"],
            fg_color=COLORS["primary"],
            text_color="white",
            hover_color="#0051D5",
            height=30,
            width=100,
            command=lambda: self._browse_analysis_file("orig") if card == self.orig_card else
                           self._browse_analysis_file("stego") if card == self.stego_card else
                           self._browse_verify_file("orig") if card == self.verify_orig_card else
                           self._browse_verify_file("ext")
        )
        browse_btn.pack(pady=(15, 0))

        if card == self.orig_card:
            self.analysis_orig_path = ""
        elif card == self.stego_card:
            self.analysis_stego_path = ""
        elif card == self.verify_orig_card:
            self.verify_orig_path = ""
        else:
            self.verify_ext_path = ""

    def _handle_analysis_drop(self, file_path, file_type):
        if file_type == "orig":
            self.analysis_orig_path = file_path
            self._update_drop_card(self.orig_card, os.path.basename(file_path), file_path)
        else:
            self.analysis_stego_path = file_path
            self._update_drop_card(self.stego_card, os.path.basename(file_path), file_path)
        self.status_label.configure(text=f"Dropped {file_type} video: {os.path.basename(file_path)}")

    def _handle_verify_drop(self, file_path, file_type):
        if file_type == "orig":
            self.verify_orig_path = file_path
            self._update_drop_card(self.verify_orig_card, os.path.basename(file_path), file_path)
        else:
            self.verify_ext_path = file_path
            self._update_drop_card(self.verify_ext_card, os.path.basename(file_path), file_path)
        self.status_label.configure(text=f"Dropped {file_type} file: {os.path.basename(file_path)}")

    def _handle_embed_drop(self, event):
        file_path = event.data
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]

        video_exts = ('.avi', '.mp4', '.mkv', '.mov', '.webm', '.flv', '.wmv')
        if file_path.lower().endswith(video_exts):
            self.video_path.set(file_path)
            self._update_video_info()
            base_dir = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            output_filename = f"{name}_stego.avi"
            output_path = os.path.join(base_dir, output_filename)
            self.output_path.set(output_path)
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, output_path)
            self.embed_initial.pack_forget()
            self.embed_config.pack(fill="both", expand=True)
            self.status_label.configure(text=f"Dropped video: {filename}")
        else:
            self._show_modern_warning("Please drop a valid video file (.avi, .mp4, .mkv, .mov)")

    def _handle_extract_drop(self, event):
        file_path = event.data
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]

        video_exts = ('.avi', '.mp4', '.mkv', '.mov', '.webm', '.flv', '.wmv')
        if file_path.lower().endswith(video_exts):
            self.stego_video_path.set(file_path)
            output_dir = os.path.dirname(file_path)
            self.extract_output_dir.set(output_dir)
            self.extract_output_entry.delete(0, "end")
            self.extract_output_entry.insert(0, output_dir)

            try:
                with VideoProcessor(file_path) as vp:
                    w, h, fps, total = vp.get_info()
                    file_size = os.path.getsize(file_path)
                    size_mb = file_size / (1024 * 1024)
                    self.stego_name_label.configure(text=os.path.basename(file_path))
                    self.stego_details_label.configure(
                        text=f"Resolution: {w}x{h} | FPS: {fps:.2f} | Frames: {total} | Size: {size_mb:.2f} MB"
                    )
            except Exception as e:
                self.stego_details_label.configure(text=f"Error reading video: {e}")

            self.extract_initial.pack_forget()
            self.extract_config.pack(fill="both", expand=True)
            self.status_label.configure(text=f"Dropped stego video: {os.path.basename(file_path)}")
        else:
            self._show_modern_warning("Please drop a valid video file (.avi, .mp4, .mkv, .mov)")

    def _show_capacity(self):
        path = self.video_path.get()
        if not path or not os.path.exists(path):
            self._show_modern_warning("Please select a video first.")
            return

        try:
            stego = VideoSteganography(self.lsb_mode.get())
            cap = stego.calculate_capacity(path)
            self._show_capacity_dialog(cap, path)
        except Exception as e:
            self._show_modern_error(str(e))

    def _show_capacity_dialog(self, cap, path):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Video Capacity Analysis")
        dialog.geometry("500x580")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        header_frame = ctk.CTkFrame(dialog, fg_color=COLORS["primary"], corner_radius=0, height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        header_icon = ctk.CTkLabel(
            header_frame,
            text="[i]",
            font=("JetBrains Mono", 28, "bold"),
            text_color="white"
        )
        header_icon.pack(side="left", padx=25, pady=15)

        header_title = ctk.CTkLabel(
            header_frame,
            text="Capacity Analysis",
            font=FONTS["title"],
            text_color="white"
        )
        header_title.pack(side="left", pady=15)

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=25, pady=25)

        filename = os.path.basename(path)
        file_card = self._create_info_card(content, "Video File", filename)
        file_card.pack(fill="x", pady=(0, 15))

        specs_grid = ctk.CTkFrame(content, fg_color="transparent", corner_radius=0)
        specs_grid.pack(fill="x", pady=(0, 15))
        specs_grid.grid_columnconfigure(0, weight=1)
        specs_grid.grid_columnconfigure(1, weight=1)
        specs_grid.grid_columnconfigure(2, weight=1)

        self._create_spec_box(specs_grid, "Resolution", f"{cap['width']}x{cap['height']}", 0, 0)
        self._create_spec_box(specs_grid, "Total Frames", f"{cap['total_frames']:,}", 0, 1)
        self._create_spec_box(specs_grid, "FPS", f"{cap['fps']:.2f}", 0, 2)

        lsb_card = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=12)
        lsb_card.pack(fill="x", pady=(0, 15))

        lsb_header = ctk.CTkLabel(
            lsb_card,
            text="LSB Configuration",
            font=FONTS["body_bold"],
            text_color=COLORS["secondary"]
        )
        lsb_header.pack(anchor="w", padx=20, pady=(15, 10))

        lsb_sep = ctk.CTkFrame(lsb_card, fg_color=COLORS["border"], height=1, corner_radius=0)
        lsb_sep.pack(fill="x", padx=20)

        lsb_content = ctk.CTkFrame(lsb_card, fg_color="transparent", corner_radius=0)
        lsb_content.pack(fill="x", padx=20, pady=(10, 15))

        lsb_mode_text = ctk.CTkLabel(
            lsb_content,
            text=f"Mode: {self.lsb_mode.get()}",
            font=FONTS["body"],
            text_color=COLORS["text_primary"]
        )
        lsb_mode_text.pack(side="left")

        lsb_bits_text = ctk.CTkLabel(
            lsb_content,
            text=f"({cap['bits_per_pixel']} bits/pixel)",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        lsb_bits_text.pack(side="left", padx=(10, 0))

        capacity_card = ctk.CTkFrame(content, fg_color=COLORS["card"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        capacity_card.pack(fill="x", pady=(0, 20))

        capacity_header = ctk.CTkLabel(
            capacity_card,
            text="Storage Capacity",
            font=FONTS["body_bold"],
            text_color=COLORS["secondary"]
        )
        capacity_header.pack(anchor="w", padx=20, pady=(15, 10))

        capacity_sep = ctk.CTkFrame(capacity_card, fg_color=COLORS["border"], height=1, corner_radius=0)
        capacity_sep.pack(fill="x", padx=20)

        capacity_items = ctk.CTkFrame(capacity_card, fg_color="transparent", corner_radius=0)
        capacity_items.pack(fill="x", padx=20, pady=15)

        items = [
            ("Header", f"{cap['header_capacity_bits']:,} bits", COLORS["text_secondary"]),
            ("Payload (Raw)", f"{cap['payload_capacity_bytes']:,} bytes", COLORS["text_primary"]),
            ("Payload (KB)", f"{cap['payload_capacity_bytes'] / 1024:.2f} KB", COLORS["primary"]),
            ("Payload (MB)", f"{cap['payload_capacity_bytes'] / (1024*1024):.4f} MB", COLORS["success"]),
        ]

        for i, (label, value, color) in enumerate(items):
            row = ctk.CTkFrame(capacity_items, fg_color="transparent" if i % 2 == 0 else COLORS["input_bg"], corner_radius=6, height=35)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            label_w = ctk.CTkLabel(row, text=label + ":", font=FONTS["body"], text_color=COLORS["text_secondary"])
            label_w.pack(side="left", padx=10)

            value_w = ctk.CTkLabel(row, text=value, font=FONTS["body_bold"], text_color=color)
            value_w.pack(side="right", padx=10)

        ok_btn = ctk.CTkButton(
            dialog,
            text="OK",
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            text_color="white",
            hover_color="#0051D5",
            height=45,
            width=120,
            corner_radius=10,
            command=dialog.destroy
        )
        ok_btn.pack(pady=(0, 25))

        dialog.focus_set()

    def _create_info_card(self, parent, label, value):
        card = ctk.CTkFrame(parent, fg_color=COLORS["input_bg"], corner_radius=10)

        label_w = ctk.CTkLabel(card, text=label, font=FONTS["small"], text_color=COLORS["text_secondary"])
        label_w.pack(anchor="w", padx=15, pady=(12, 2))

        value_w = ctk.CTkLabel(card, text=value, font=FONTS["body"], text_color=COLORS["text_primary"])
        value_w.pack(anchor="w", padx=15, pady=(0, 12))

        return card

    def _create_spec_box(self, parent, label, value, row, col):
        box = ctk.CTkFrame(parent, fg_color=COLORS["input_bg"], corner_radius=10)
        box.grid(row=row, column=col, padx=5, sticky="nsew")

        label_w = ctk.CTkLabel(box, text=label, font=FONTS["small"], text_color=COLORS["text_secondary"])
        label_w.pack(padx=15, pady=(12, 2))

        value_w = ctk.CTkLabel(box, text=value, font=FONTS["body_bold"], text_color=COLORS["text_primary"])
        value_w.pack(padx=15, pady=(0, 12))

    def _show_modern_warning(self, message):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Warning")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=30, pady=30)

        icon = ctk.CTkLabel(content, text="[!]", font=("JetBrains Mono", 36, "bold"), text_color=COLORS["warning"])
        icon.pack()

        msg = ctk.CTkLabel(content, text=message, font=FONTS["body"], text_color=COLORS["text_primary"], wraplength=340)
        msg.pack(pady=15)

        ok_btn = ctk.CTkButton(
            dialog,
            text="OK",
            font=FONTS["button"],
            fg_color=COLORS["warning"],
            text_color="white",
            hover_color="#D97706",
            height=40,
            width=100,
            corner_radius=8,
            command=dialog.destroy
        )
        ok_btn.pack(pady=(0, 20))

        dialog.focus_set()

    def _show_modern_error(self, message):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Error")
        dialog.geometry("450x220")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=30, pady=25)

        icon = ctk.CTkLabel(content, text="[X]", font=("JetBrains Mono", 36, "bold"), text_color=COLORS["error"])
        icon.pack()

        title = ctk.CTkLabel(content, text="An Error Occurred", font=FONTS["subtitle"], text_color=COLORS["error"])
        title.pack(pady=(10, 5))

        msg = ctk.CTkLabel(content, text=message[:200], font=FONTS["body"], text_color=COLORS["text_primary"], wraplength=390)
        msg.pack()

        ok_btn = ctk.CTkButton(
            dialog,
            text="OK",
            font=FONTS["button"],
            fg_color=COLORS["error"],
            text_color="white",
            hover_color="#DC2626",
            height=40,
            width=100,
            corner_radius=8,
            command=dialog.destroy
        )
        ok_btn.pack(pady=(0, 20))

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

        icon = ctk.CTkLabel(header, text="[OK]", font=("JetBrains Mono", 24, "bold"), text_color="white")
        icon.pack(side="left", padx=25, pady=15)

        title = ctk.CTkLabel(header, text="Embedding Complete", font=FONTS["title"], text_color="white")
        title.pack(side="left", pady=15)

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=25, pady=25)

        msg_text = ctk.CTkLabel(content, text="Your message has been successfully embedded into the video.", font=FONTS["body"], text_color=COLORS["text_secondary"], wraplength=470)
        msg_text.pack(anchor="w", pady=(0, 20))

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

            lbl = ctk.CTkLabel(row, text=label, font=FONTS["body"], text_color=COLORS["text_secondary"])
            lbl.pack(side="left")

            val = ctk.CTkLabel(row, text=value, font=FONTS["body_bold"], text_color=COLORS["text_primary"])
            val.pack(side="right")

        path_frame = ctk.CTkFrame(content, fg_color="transparent", corner_radius=0)
        path_frame.pack(fill="x", pady=(0, 20))

        path_label = ctk.CTkLabel(path_frame, text="Full Path:", font=FONTS["small"], text_color=COLORS["text_secondary"])
        path_label.pack(anchor="w")

        path_value = ctk.CTkLabel(path_frame, text=result['output_path'], font=FONTS["small"], text_color=COLORS["text_primary"], wraplength=470)
        path_value.pack(anchor="w")

        ok_btn = ctk.CTkButton(
            dialog,
            text="OK",
            font=FONTS["button"],
            fg_color=COLORS["success"],
            text_color="white",
            hover_color="#059669",
            height=45,
            width=120,
            corner_radius=10,
            command=dialog.destroy
        )
        ok_btn.pack(pady=(0, 25))

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

        icon = ctk.CTkLabel(content, text="[!]", font=("JetBrains Mono", 36, "bold"), text_color=COLORS["warning"])
        icon.pack()

        title = ctk.CTkLabel(content, text="File Too Large", font=FONTS["subtitle"], text_color=COLORS["warning"])
        title.pack(pady=(10, 15))

        details = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=12)
        details.pack(fill="x", pady=(0, 15))

        max_row = ctk.CTkFrame(details, fg_color="transparent", corner_radius=0)
        max_row.pack(fill="x", padx=15, pady=(12, 5))

        max_label = ctk.CTkLabel(max_row, text="Maximum Capacity:", font=FONTS["body"], text_color=COLORS["text_secondary"])
        max_label.pack(side="left")

        max_val = ctk.CTkLabel(max_row, text=f"{max_bytes:,} bytes", font=FONTS["body_bold"], text_color=COLORS["success"])
        max_val.pack(side="right")

        file_row = ctk.CTkFrame(details, fg_color="transparent", corner_radius=0)
        file_row.pack(fill="x", padx=15, pady=(5, 12))

        file_label = ctk.CTkLabel(file_row, text="Your File Size:", font=FONTS["body"], text_color=COLORS["text_secondary"])
        file_label.pack(side="left")

        file_val = ctk.CTkLabel(file_row, text=f"{file_size:,} bytes", font=FONTS["body_bold"], text_color=COLORS["error"])
        file_val.pack(side="right")

        msg = ctk.CTkLabel(content, text="The selected file exceeds the video's capacity. Please choose a smaller file or use a video with higher capacity (more frames/resolution).", font=FONTS["small"], text_color=COLORS["text_secondary"], wraplength=420)
        msg.pack()

        ok_btn = ctk.CTkButton(
            dialog,
            text="OK",
            font=FONTS["button"],
            fg_color=COLORS["warning"],
            text_color="white",
            hover_color="#D97706",
            height=40,
            width=100,
            corner_radius=8,
            command=dialog.destroy
        )
        ok_btn.pack(pady=(0, 20))

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

        icon = ctk.CTkLabel(content, text="[OK]", font=("JetBrains Mono", 36, "bold"), text_color=COLORS["success"])
        icon.pack()

        title = ctk.CTkLabel(content, text="Capacity Sufficient", font=FONTS["subtitle"], text_color=COLORS["success"])
        title.pack(pady=(10, 15))

        details = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=12)
        details.pack(fill="x", pady=(0, 15))

        max_row = ctk.CTkFrame(details, fg_color="transparent", corner_radius=0)
        max_row.pack(fill="x", padx=15, pady=(12, 5))

        max_label = ctk.CTkLabel(max_row, text="Maximum Capacity:", font=FONTS["body"], text_color=COLORS["text_secondary"])
        max_label.pack(side="left")

        max_val = ctk.CTkLabel(max_row, text=f"{max_bytes:,} bytes", font=FONTS["body_bold"], text_color=COLORS["text_primary"])
        max_val.pack(side="right")

        file_row = ctk.CTkFrame(details, fg_color="transparent", corner_radius=0)
        file_row.pack(fill="x", padx=15, pady=(5, 12))

        file_label = ctk.CTkLabel(file_row, text="Your Payload:", font=FONTS["body"], text_color=COLORS["text_secondary"])
        file_label.pack(side="left")

        file_val = ctk.CTkLabel(file_row, text=f"{payload_size:,} bytes", font=FONTS["body_bold"], text_color=COLORS["success"])
        file_val.pack(side="right")

        msg = ctk.CTkLabel(content, text=f"Available space: {max_bytes - payload_size:,} bytes remaining", font=FONTS["small"], text_color=COLORS["text_secondary"], wraplength=390)
        msg.pack()

        ok_btn = ctk.CTkButton(
            dialog,
            text="OK",
            font=FONTS["button"],
            fg_color=COLORS["success"],
            text_color="white",
            hover_color="#059669",
            height=40,
            width=100,
            corner_radius=8,
            command=dialog.destroy
        )
        ok_btn.pack(pady=(0, 20))

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

        icon = ctk.CTkLabel(header, text="[!]", font=("JetBrains Mono", 24, "bold"), text_color="white")
        icon.pack(side="left", padx=20, pady=12)

        title = ctk.CTkLabel(header, text="Lossy Format Warning", font=FONTS["subtitle"], text_color="white")
        title.pack(side="left", pady=12)

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=25, pady=20)

        warning_text = ctk.CTkLabel(
            content,
            text=f"{ext.upper()} uses lossy compression!",
            font=FONTS["body_bold"],
            text_color=COLORS["error"]
        )
        warning_text.pack(anchor="w", pady=(0, 10))

        details = ctk.CTkLabel(
            content,
            text="This will DESTROY the LSB steganographic data. The hidden message will be unrecoverable.",
            font=FONTS["body"],
            text_color=COLORS["text_primary"],
            wraplength=450
        )
        details.pack(anchor="w", pady=(0, 10))

        recommendation = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=8)
        recommendation.pack(fill="x", pady=(0, 15))

        rec_text = ctk.CTkLabel(
            recommendation,
            text="Tip: Use .AVI format for lossless steganography",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        rec_text.pack(padx=15, pady=10)

        question = ctk.CTkLabel(
            content,
            text="Do you want to continue anyway?",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"]
        )
        question.pack(anchor="w", pady=(0, 10))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        btn_frame.pack(fill="x", padx=25, pady=(0, 25))

        def on_cancel():
            result[0] = False
            dialog.destroy()

        def on_continue():
            result[0] = True
            dialog.destroy()

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            font=FONTS["button"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["border"],
            height=40,
            width=100,
            corner_radius=8,
            command=on_cancel
        )
        cancel_btn.pack(side="left", padx=(0, 10))

        continue_btn = ctk.CTkButton(
            btn_frame,
            text="Continue",
            font=FONTS["button"],
            fg_color=COLORS["warning"],
            text_color="white",
            hover_color="#D97706",
            height=40,
            width=100,
            corner_radius=8,
            command=on_continue
        )
        continue_btn.pack(side="left")

        dialog.focus_set()
        self.root.wait_window(dialog)
        return result[0]

    def _test_capacity_overflow(self):
        path = self.video_path.get()
        if not path or not os.path.exists(path):
            self._show_modern_warning("Please select a video first.")
            return

        if not self.output_path.get():
            self._show_modern_warning("Please specify output path.")
            return

        payload_size = 0
        if self.use_text_message.get():
            message = self.message_text.get("0.0", "end").strip()
            if not message:
                self._show_modern_warning("Please enter a message to test.")
                return
            payload_size = len(message.encode('utf-8'))
        else:
            payload_path = self.payload_path.get()
            if not payload_path or not os.path.exists(payload_path):
                self._show_modern_warning("Please select a payload file to test.")
                return
            payload_size = os.path.getsize(payload_path)

        try:
            stego = VideoSteganography(self.lsb_mode.get())
            cap = stego.calculate_capacity(path)

            max_bytes = cap['payload_capacity_bytes']
            estimated_total_bytes = 100 + payload_size

            if estimated_total_bytes > max_bytes:
                self.status_label.configure(text=f"Error: Payload too large")
                self._show_capacity_exceeded_dialog(max_bytes, payload_size)
                return
            else:
                self._show_capacity_ok_dialog(max_bytes, payload_size)

        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")
            self._show_modern_error(str(e))

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

        icon = ctk.CTkLabel(content, text="[!]", font=("JetBrains Mono", 36, "bold"), text_color=COLORS["warning"])
        icon.pack()

        title = ctk.CTkLabel(content, text="Capacity Exceeded", font=FONTS["subtitle"], text_color=COLORS["warning"])
        title.pack(pady=(10, 15))

        details = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=10)
        details.pack(fill="x", pady=(0, 15))

        max_label = ctk.CTkLabel(details, text=f"Maximum Capacity: {max_bytes:,} bytes", font=FONTS["body_bold"], text_color=COLORS["text_primary"])
        max_label.pack(anchor="w", padx=15, pady=(12, 5))

        input_label = ctk.CTkLabel(details, text=f"Your Input: {input_bytes:,} bytes", font=FONTS["body"], text_color=COLORS["error"])
        input_label.pack(anchor="w", padx=15, pady=(0, 12))

        msg = ctk.CTkLabel(content, text="The payload is too large for this video. Please use a larger video or reduce the payload size.", font=FONTS["small"], text_color=COLORS["text_secondary"], wraplength=390)
        msg.pack()

        ok_btn = ctk.CTkButton(
            dialog,
            text="OK",
            font=FONTS["button"],
            fg_color=COLORS["warning"],
            text_color="white",
            hover_color="#D97706",
            height=40,
            width=100,
            corner_radius=8,
            command=dialog.destroy
        )
        ok_btn.pack(pady=(0, 20))

        dialog.focus_set()

    def _start_preprocess_animation(self, progress_bar, percent_label, status_text="Preparing..."):
        """Start indeterminate animation for preprocessing phase"""
        self._preprocess_animating = True
        self._preprocess_progress = 0.0
        self._preprocess_direction = 1

        def animate():
            if not self._preprocess_animating:
                return

            self._preprocess_progress += 0.02 * self._preprocess_direction
            if self._preprocess_progress >= 0.4:
                self._preprocess_direction = -1
            elif self._preprocess_progress <= 0.1:
                self._preprocess_direction = 1

            progress_bar.set(self._preprocess_progress)
            percent_label.configure(text="...")

            self._preprocess_animation_id = self.root.after(50, animate)

        animate()

    def _stop_preprocess_animation(self):
        """Stop preprocessing animation"""
        self._preprocess_animating = False
        if self._preprocess_animation_id:
            self.root.after_cancel(self._preprocess_animation_id)
            self._preprocess_animation_id = None

    def _update_progress(self, current, total, status=""):
        progress = current / total if total > 0 else 0
        percent = int(progress * 100)

        current_time = int(time.time() * 1000)
        time_since_last = current_time - self._last_progress_update
        progress_diff = abs(int(progress * 100) - self._last_progress_value)

        if time_since_last < self._progress_update_interval_ms and progress_diff < 2:
            return

        self._last_progress_update = current_time
        self._last_progress_value = int(progress * 100)

        self.status_label.configure(text=f"{status}: {current:,}/{total:,}")

        if hasattr(self, 'embed_progress_bar') and self.embed_loading.winfo_ismapped():
            self.embed_progress_bar.set(progress)
            self.embed_progress_percent.configure(text=f"{percent}%")
            self.loading_status.configure(text=f"Processing frames...")
            self.loading_detail.configure(text=f"Frame {current:,} of {total:,}")

        if hasattr(self, 'extract_progress_bar_loading') and self.extract_loading.winfo_ismapped():
            self.extract_progress_bar_loading.set(progress)
            self.extract_progress_percent.configure(text=f"{percent}%")
            self.extract_loading_status.configure(text=f"Processing frames...")
            self.extract_loading_detail.configure(text=f"Frame {current:,} of {total:,}")

    def _start_embed(self):
        if self.is_processing:
            return

        video_path = self.video_path.get()
        output_path = self.output_path.get()

        if not video_path or not os.path.exists(video_path):
            self._show_modern_warning("Please select a valid cover video.")
            return

        if not output_path:
            self._show_modern_warning("Please specify output path.")
            return

        use_text = self.use_text_message.get()
        if use_text:
            message = self.message_text.get("0.0", "end").strip()
            if not message:
                self._show_modern_warning("Please enter a message.")
                return
        else:
            payload_path = self.payload_path.get()
            if not payload_path or not os.path.exists(payload_path):
                self._show_modern_warning("Please select a payload file.")
                return

        use_enc = self.use_encryption.get()
        enc_key = self.encryption_key.get() if use_enc else None
        use_random = self.use_random.get()
        stego_key = self.stego_key.get() if use_random else None

        if use_enc and not enc_key:
            self._show_modern_warning("Please enter encryption key.")
            return

        if use_random and not stego_key:
            self._show_modern_warning("Please enter stego key.")
            return

        self.is_processing = True
        self.embed_btn.configure(state="disabled")

        self._last_progress_update = 0
        self._last_progress_value = -1

        self.embed_config.pack_forget()
        self.embed_loading.pack(fill="both", expand=True)

        self.embed_progress_bar.set(0.1)
        self.embed_progress_percent.configure(text="...")
        self.loading_status.configure(text="Preparing...")
        self.loading_detail.configure(text="Validating inputs and calculating capacity")
        self.root.update_idletasks()

        self._start_preprocess_animation(self.embed_progress_bar, self.embed_progress_percent)

        def embed_thread():
            try:
                if use_text:
                    payload_data = message.encode('utf-8')
                    extension = '.txt'
                else:
                    self.root.after(0, lambda: self.loading_detail.configure(text="Analyzing video capacity..."))
                    stego_check = VideoSteganography(self.lsb_mode.get())
                    cap = stego_check.calculate_capacity(video_path)
                    file_size = os.path.getsize(payload_path)
                    estimated_total_bytes = 100 + file_size

                    if estimated_total_bytes > cap['payload_capacity_bytes']:
                        self.root.after(0, lambda: self._embed_capacity_error(cap['payload_capacity_bytes'], file_size))
                        return

                    self.root.after(0, lambda: self.loading_detail.configure(text=f"Reading payload file ({file_size/1024:.1f} KB)..."))
                    with open(payload_path, 'rb') as f:
                        payload_data = f.read()
                    extension = os.path.splitext(payload_path)[1]

                self.root.after(0, self._stop_preprocess_animation)
                self.root.after(0, lambda: self.loading_status.configure(text="Embedding message..."))
                self.root.after(0, lambda: self.loading_detail.configure(text="Reading video frames"))
                self.root.after(0, lambda: self.embed_progress_bar.set(0))
                self.root.after(0, lambda: self.embed_progress_percent.configure(text="0%"))

                stego = VideoSteganography(self.lsb_mode.get())
                result = stego.embed(
                    video_path, output_path, payload_data, extension,
                    use_enc, enc_key, use_random, stego_key,
                    progress_callback=self._update_progress
                )

                self.root.after(0, lambda: self._embed_complete(result))
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda msg=error_msg: self._embed_error(msg))

        threading.Thread(target=embed_thread, daemon=True).start()

    def _embed_capacity_error(self, max_bytes, file_size):
        self._stop_preprocess_animation()
        self.is_processing = False
        self.embed_btn.configure(state="normal")
        self.embed_loading.pack_forget()
        self.embed_config.pack(fill="both", expand=True)
        self.status_label.configure(text=f"Error: File too large")
        self._show_file_too_large_dialog(max_bytes, file_size)

    def _embed_complete(self, result):
        self._stop_preprocess_animation()
        self.is_processing = False
        self.embed_btn.configure(state="normal")
        self.status_label.configure(text="Embedding complete!")
        self.embed_progress_bar.set(1.0)
        self.embed_progress_percent.configure(text="100%")

        self.embed_loading.pack_forget()
        self.embed_config.pack(fill="both", expand=True)

        self._show_embed_success_dialog(result)

    def _embed_error(self, error):
        self._stop_preprocess_animation()
        self.is_processing = False
        self.embed_btn.configure(state="normal")
        self.status_label.configure(text="Error: Embedding failed")
        self.embed_progress_bar.set(0)

        self.embed_loading.pack_forget()
        self.embed_config.pack(fill="both", expand=True)

        if "Payload too large" in error or "too large" in error.lower():
            try:
                if "Needed:" in error and "Available:" in error:
                    needed_str = error.split("Needed: ")[1].split(" bytes")[0].strip()
                    available_str = error.split("Available: ")[1].split(" bytes")[0].strip()
                    needed = int(needed_str.replace(",", ""))
                    available = int(available_str.replace(",", ""))
                    simple_msg = f"Rejected, Max capacity is {available:,} bytes (input {needed:,} bytes)"
                else:
                    simple_msg = error
            except Exception:
                simple_msg = error
        else:
            simple_msg = error

        self.status_label.configure(text=f"Error: {simple_msg}")

    def _start_extract(self):
        if self.is_processing:
            return

        stego_path = self.stego_video_path.get()
        output_dir = self.extract_output_dir.get()

        if not stego_path or not os.path.exists(stego_path):
            self._show_modern_warning("Please select a stego video.")
            return

        if not output_dir:
            output_dir = os.path.dirname(stego_path)
            self.extract_output_dir.set(output_dir)
            self.extract_output_entry.delete(0, "end")
            self.extract_output_entry.insert(0, output_dir)

        enc_key = self.extract_enc_entry.get() or None
        stego_key = self.extract_stego_entry.get() or None

        self.is_processing = True
        self.extract_btn.configure(state="disabled")

        self._last_progress_update = 0
        self._last_progress_value = -1

        self.extract_config.pack_forget()
        self.extract_loading.pack(fill="both", expand=True)

        self.extract_progress_bar_loading.set(0.1)
        self.extract_progress_percent.configure(text="...")
        self.extract_loading_status.configure(text="Preparing...")
        self.extract_loading_detail.configure(text="Reading video header...")
        self.root.update_idletasks()

        self._start_preprocess_animation(self.extract_progress_bar_loading, self.extract_progress_percent)

        def extract_thread():
            try:
                self.root.after(0, self._stop_preprocess_animation)
                self.root.after(0, lambda: self.extract_loading_status.configure(text="Extracting message..."))
                self.root.after(0, lambda: self.extract_loading_detail.configure(text="Reading video frames"))
                self.root.after(0, lambda: self.extract_progress_bar_loading.set(0))
                self.root.after(0, lambda: self.extract_progress_percent.configure(text="0%"))

                stego = VideoSteganography()
                result = stego.extract_to_file(
                    stego_path, output_dir, enc_key, stego_key,
                    progress_callback=self._update_progress
                )

                self.root.after(0, lambda: self._extract_complete(result))
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda msg=error_msg: self._extract_error(msg))

        threading.Thread(target=extract_thread, daemon=True).start()

    def _extract_complete(self, result):
        self._stop_preprocess_animation()
        self.is_processing = False
        self.extract_btn.configure(state="normal")
        self.status_label.configure(text="Extraction complete!")
        self.extract_progress_bar_loading.set(1.0)
        self.extract_progress_percent.configure(text="100%")

        self.extract_loading.pack_forget()
        self.extract_config.pack(fill="both", expand=True)

        self.result_text.delete("0.0", "end")

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

        self.result_text.insert("0.0", info)

    def _extract_error(self, error):
        self._stop_preprocess_animation()
        self.is_processing = False
        self.extract_btn.configure(state="normal")
        self.extract_progress_bar_loading.set(0)

        self.extract_loading.pack_forget()
        self.extract_config.pack(fill="both", expand=True)

        self.result_text.delete("0.0", "end")
        self.result_text.insert("0.0", f"Error: {error}")
        self.status_label.configure(text=f"Error: {error}")

    def _calculate_metrics(self):
        orig_path = getattr(self, 'analysis_orig_path', '')
        stego_path = getattr(self, 'analysis_stego_path', '')

        if not orig_path or not os.path.exists(orig_path):
            self._show_modern_warning("Please select original video.")
            return

        if not stego_path or not os.path.exists(stego_path):
            self._show_modern_warning("Please select stego video.")
            return

        self.analysis_result.delete("0.0", "end")
        self.analysis_result.insert("0.0", "Calculating metrics...")
        self.mse_btn.configure(state="disabled")
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

                self.root.after(0, lambda: self._show_analysis_result(result, mse, psnr))
            except Exception as e:
                self.root.after(0, lambda: self._show_analysis_result(f"Error: {e}", 0, 0))

        threading.Thread(target=calc_thread, daemon=True).start()

    def _show_analysis_result(self, text, mse, psnr):
        self.analysis_result.delete("0.0", "end")
        self.analysis_result.insert("0.0", text)
        self.status_label.configure(text="Analysis complete!")
        self.mse_btn.configure(state="normal")

        for widget in self.mse_card.winfo_children():
            widget.destroy()

        left = ctk.CTkFrame(self.mse_card, fg_color="transparent", corner_radius=0)
        left.pack(side="left", fill="y", padx=15, pady=15)

        mse_label = ctk.CTkLabel(
            left,
            text="MSE",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        mse_label.pack(anchor="w")

        mse_value = ctk.CTkLabel(
            left,
            text=f"{mse:.6f}",
            font=FONTS["header"],
            text_color=COLORS["primary"]
        )
        mse_value.pack(anchor="w")

        for widget in self.psnr_card.winfo_children():
            widget.destroy()

        left = ctk.CTkFrame(self.psnr_card, fg_color="transparent", corner_radius=0)
        left.pack(side="left", fill="y", padx=15, pady=15)

        psnr_label = ctk.CTkLabel(
            left,
            text="PSNR",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        psnr_label.pack(anchor="w")

        color = COLORS["success"] if psnr > 40 else COLORS["warning"] if psnr > 30 else COLORS["error"]
        psnr_value = ctk.CTkLabel(
            left,
            text=f"{psnr:.2f} dB",
            font=FONTS["header"],
            text_color=color
        )
        psnr_value.pack(anchor="w")

    def _show_histogram(self):
        self._show_histogram_plot("comparison")

    def _show_histogram_overlay(self):
        self._show_histogram_plot("overlay")

    def _show_histogram_plot(self, plot_type):
        orig_path = getattr(self, 'analysis_orig_path', '')
        stego_path = getattr(self, 'analysis_stego_path', '')

        if not orig_path or not os.path.exists(orig_path):
            self._show_modern_warning("Please select original video.")
            return

        if not stego_path or not os.path.exists(stego_path):
            self._show_modern_warning("Please select stego video.")
            return

        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
            import matplotlib.pyplot as plt

            with VideoProcessor(orig_path) as vp_orig, VideoProcessor(stego_path) as vp_stego:
                orig_frame = vp_orig.read_frame(0)
                stego_frame = vp_stego.read_frame(0)

                if orig_frame is None or stego_frame is None:
                    self._show_modern_error("Cannot read video frames")
                    return

                if plot_type == "comparison":
                    fig = plot_histogram_comparison(orig_frame, stego_frame)
                else:
                    fig = plot_histogram_overlay(orig_frame, stego_frame)

                fig.patch.set_facecolor(COLORS["card"])
                for ax in fig.axes:
                    ax.set_facecolor(COLORS["card"])
                    ax.tick_params(colors=COLORS["text_secondary"])
                    ax.xaxis.label.set_color(COLORS["text_primary"])
                    ax.yaxis.label.set_color(COLORS["text_primary"])
                    ax.title.set_color(COLORS["text_primary"])
                    for spine in ax.spines.values():
                        spine.set_color(COLORS["border"])

                self.histogram_placeholder.pack_forget()
                if self.histogram_canvas:
                    self.histogram_canvas.get_tk_widget().destroy()

                self.histogram_canvas = FigureCanvasTkAgg(fig, master=self.histogram_frame)
                self.histogram_canvas.draw()
                self.histogram_canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=(0, 20))

                plt.close(fig)

        except ImportError:
            messagebox.showerror("Error", "matplotlib is required for histogram visualization.\nInstall with: pip install matplotlib")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _show_multiframe_analysis(self):
        orig_path = getattr(self, 'analysis_orig_path', '')
        stego_path = getattr(self, 'analysis_stego_path', '')

        if not orig_path or not os.path.exists(orig_path):
            self._show_modern_warning("Please select original video.")
            return

        if not stego_path or not os.path.exists(stego_path):
            self._show_modern_warning("Please select stego video.")
            return

        try:
            import matplotlib.pyplot as plt

            self.status_label.configure(text="Analyzing multiple frames...")
            self.root.update()

            fig = plot_multiframe_residual(orig_path, stego_path, sample_count=10, start_frame=3)

            if fig is not None:
                plt.show()
                self.status_label.configure(text="Multi-frame analysis complete!")
            else:
                self._show_modern_error("Could not analyze frames")
                self.status_label.configure(text="Analysis failed")

        except ImportError:
            self._show_modern_error("matplotlib is required.\nInstall with: pip install matplotlib")
        except Exception as e:
            self._show_modern_error(str(e))
            self.status_label.configure(text=f"Error: {e}")

    def _verify_file_integrity(self):
        import hashlib

        orig_file = getattr(self, 'verify_orig_path', '')
        ext_file = getattr(self, 'verify_ext_path', '')

        if not orig_file or not os.path.exists(orig_file):
            self._show_modern_warning("Please select original file.")
            return

        if not ext_file or not os.path.exists(ext_file):
            self._show_modern_warning("Please select extracted file.")
            return

        algo = self.hash_algo_var.get().lower().replace("-", "")

        try:
            if algo == "md5":
                hash_orig = hashlib.md5()
                hash_ext = hashlib.md5()
            else:
                hash_orig = hashlib.sha256()
                hash_ext = hashlib.sha256()

            with open(orig_file, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_orig.update(chunk)
            orig_hash = hash_orig.hexdigest()

            with open(ext_file, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_ext.update(chunk)
            ext_hash = hash_ext.hexdigest()

            orig_size = os.path.getsize(orig_file)
            ext_size = os.path.getsize(ext_file)

            self.orig_hash_label.configure(text=orig_hash)
            self.ext_hash_label.configure(text=ext_hash)

            if orig_hash == ext_hash:
                status = "VERIFIED"
                status_color = COLORS["success"]
                badge_color = "#D1FAE5"
            else:
                status = "INTEGRITY FAILED"
                status_color = COLORS["error"]
                badge_color = "#FEE2E2"

            self.verify_status_badge.configure(fg_color=badge_color)
            self.verify_status_label.configure(text=status, text_color=status_color)
            self.status_label.configure(text=f"{status} ({algo.upper()})")

        except Exception as e:
            self._show_modern_error(f"Hash verification failed: {str(e)}")

    def _check_dependencies(self):
        if not check_ffmpeg():
            self.status_label.configure(text="Warning: ffmpeg not found. Audio will not be preserved.")


def main():
    root = ctk.CTk()
    app = ModernStegoGUI(root)
    
    def on_closing():
        app.is_processing = False
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
