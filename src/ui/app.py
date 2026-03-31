import os
import time
import threading
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageDraw

from ..crypto.stego import VideoSteganography, StegoError
from ..utils.video import VideoProcessor, check_ffmpeg
from ..utils.metric import (
    metrics_streaming, plot_histogram_residual,
    plot_multiframe_residual
)
from .constants import COLORS, FONTS
from .dialogs import DialogsMixin


class ModernStegoGUI(DialogsMixin):
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
        self.use_encryption = tk.BooleanVar(value=True)
        self.encryption_key = tk.StringVar()
        self.use_random = tk.BooleanVar(value=False)
        self.stego_key = tk.StringVar()
        self.use_text_message = tk.BooleanVar(value=True)
        self.analysis_frame_index = tk.IntVar(value=3)

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

        enc_label_row = ctk.CTkFrame(security_section, fg_color="transparent", corner_radius=0)
        enc_label_row.pack(fill="x", padx=15, pady=(15, 10))

        enc_label = ctk.CTkLabel(
            enc_label_row,
            text="A5/1 Encryption Key (Required):",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"]
        )
        enc_label.pack(side="left")

        enc_key_frame = ctk.CTkFrame(security_section, fg_color="transparent", corner_radius=0)
        enc_key_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.enc_key_entry = ctk.CTkEntry(
            enc_key_frame,
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            height=40,
            show="*",
            placeholder_text="Enter encryption password..."
        )
        self.enc_key_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.enc_key_entry.insert(0, self.encryption_key.get())
        self.enc_key_entry.bind("<KeyRelease>", lambda e: self.encryption_key.set(self.enc_key_entry.get()))

        show_enc_btn = ctk.CTkButton(
            enc_key_frame,
            text="Show",
            font=FONTS["small"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["border"],
            height=40,
            width=70,
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

        keys_section = self._create_section_card(scroll_frame, "Decryption Keys")
        keys_section.pack(fill="x", pady=(0, 15))

        enc_label_header = ctk.CTkLabel(
            keys_section,
            text="A5/1 Encryption Key (Required):",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"]
        )
        enc_label_header.pack(anchor="w", padx=15, pady=(15, 5))

        enc_row = ctk.CTkFrame(keys_section, fg_color="transparent", corner_radius=0)
        enc_row.pack(fill="x", padx=15, pady=(0, 15))

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
            placeholder_text="Enter encryption password..."
        )
        self.extract_enc_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        show_extract_enc_btn = ctk.CTkButton(
            enc_row,
            text="Show",
            font=FONTS["small"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["border"],
            height=40,
            width=70,
            command=lambda: self._toggle_password_visibility(self.extract_enc_entry)
        )
        show_extract_enc_btn.pack(side="left")

        stego_label_header = ctk.CTkLabel(
            keys_section,
            text="Stego Key:",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        stego_label_header.pack(anchor="w", padx=15, pady=(0, 5))

        stego_row = ctk.CTkFrame(keys_section, fg_color="transparent", corner_radius=0)
        stego_row.pack(fill="x", padx=15, pady=(0, 15))

        self.extract_stego_entry = ctk.CTkEntry(
            stego_row,
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            height=40,
            placeholder_text="Enter stego key (leave empty if sequential)..."
        )
        self.extract_stego_entry.pack(side="left", fill="x", expand=True)

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

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True)

        cards_frame = ctk.CTkFrame(scroll, fg_color="transparent", corner_radius=0)
        cards_frame.pack(fill="x", pady=(0, 15))
        cards_frame.grid_columnconfigure(0, weight=1)
        cards_frame.grid_columnconfigure(1, weight=1)

        self.orig_card = self._create_file_drop_card(
            cards_frame,
            "Original Video",
            "Browse original video file",
            lambda: self._browse_analysis_file("orig"),
            lambda p: self._handle_analysis_drop(p, "orig")
        )
        self.orig_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        self.stego_card = self._create_file_drop_card(
            cards_frame,
            "Stego Video",
            "Browse stego video file",
            lambda: self._browse_analysis_file("stego"),
            lambda p: self._handle_analysis_drop(p, "stego")
        )
        self.stego_card.grid(row=0, column=1, padx=(10, 0), sticky="nsew")

        frame_input_section = ctk.CTkFrame(scroll, fg_color="transparent", corner_radius=0)
        frame_input_section.pack(fill="x", pady=(15, 0))

        frame_label = ctk.CTkLabel(
            frame_input_section,
            text="Frame Index to Analyze:",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"]
        )
        frame_label.pack(side="left", padx=(0, 10))

        self.frame_index_entry = ctk.CTkEntry(
            frame_input_section,
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            height=35,
            width=100
        )
        self.frame_index_entry.pack(side="left")
        self.frame_index_entry.insert(0, "3")
        self.frame_index_entry.bind("<KeyRelease>", lambda e: self._update_frame_index())

        frame_info_label = ctk.CTkLabel(
            frame_input_section,
            text="(Payload starts at frame 3)",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        frame_info_label.pack(side="left", padx=(10, 0))

        actions_frame = ctk.CTkFrame(scroll, fg_color="transparent", corner_radius=0)
        actions_frame.pack(fill="x", pady=(15, 15))

        self.mse_btn = ctk.CTkButton(
            actions_frame, text="Calculate MSE & PSNR", font=FONTS["body"],
            fg_color=COLORS["primary"], text_color="white", hover_color="#0051D5",
            height=40, width=180, command=self._calculate_metrics
        )
        self.mse_btn.pack(side="left", padx=(0, 10))

        self.hist_residual_btn = ctk.CTkButton(
            actions_frame, text="Show Residual Histogram", font=FONTS["body"],
            fg_color=COLORS["secondary"], text_color="white", hover_color="#1A365D",
            height=40, width=200, command=self._show_histogram_residual
        )
        self.hist_residual_btn.pack(side="left", padx=(0, 10))

        self.multi_btn = ctk.CTkButton(
            actions_frame, text="Multi-Frame Analysis", font=FONTS["body"],
            fg_color=COLORS["input_bg"], text_color=COLORS["text_secondary"],
            hover_color=COLORS["border"], height=40, width=180, command=self._show_multiframe_analysis
        )
        self.multi_btn.pack(side="left")

        metrics_row = ctk.CTkFrame(scroll, fg_color="transparent", corner_radius=0)
        metrics_row.pack(fill="x", pady=(0, 15))
        metrics_row.grid_columnconfigure(0, weight=1)
        metrics_row.grid_columnconfigure(1, weight=1)

        self.mse_card = ctk.CTkFrame(
            metrics_row, fg_color=COLORS["card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"], height=120
        )
        self.mse_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        self.mse_card.pack_propagate(False)
        mse_inner = ctk.CTkFrame(self.mse_card, fg_color="transparent")
        mse_inner.pack(side="left", fill="y", padx=25, pady=20)
        ctk.CTkLabel(mse_inner, text="Mean Squared Error", font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack(anchor="w")
        self.mse_value_label = ctk.CTkLabel(mse_inner, text="--", font=FONTS["header"],
                                            text_color=COLORS["text_primary"])
        self.mse_value_label.pack(anchor="w")
        self.mse_desc_label = ctk.CTkLabel(mse_inner, text="Run analysis to calculate",
                                           font=FONTS["small"], text_color=COLORS["text_secondary"])
        self.mse_desc_label.pack(anchor="w")

        self.psnr_card = ctk.CTkFrame(
            metrics_row, fg_color=COLORS["card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"], height=120
        )
        self.psnr_card.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        self.psnr_card.pack_propagate(False)
        psnr_inner = ctk.CTkFrame(self.psnr_card, fg_color="transparent")
        psnr_inner.pack(side="left", fill="y", padx=25, pady=20)
        
        psnr_title_row = ctk.CTkFrame(psnr_inner, fg_color="transparent")
        psnr_title_row.pack(anchor="w")
        ctk.CTkLabel(psnr_title_row, text="Peak Signal-to-Noise Ratio", font=FONTS["small"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        
        info_btn = ctk.CTkButton(
            psnr_title_row,
            text="i",
            font=("JetBrains Mono", 10, "bold"),
            fg_color="transparent",
            text_color=COLORS["primary"],
            hover_color=COLORS["input_bg"],
            border_width=2,
            border_color=COLORS["primary"],
            width=20,
            height=20,
            corner_radius=10,
            command=self._show_psnr_info
        )
        info_btn.pack(side="left", padx=(5, 0))
        
        self.psnr_value_label = ctk.CTkLabel(psnr_inner, text="-- dB", font=FONTS["header"],
                                             text_color=COLORS["success"])
        self.psnr_value_label.pack(anchor="w")
        self.psnr_desc_label = ctk.CTkLabel(psnr_inner, text="Run analysis to calculate",
                                            font=FONTS["small"], text_color=COLORS["text_secondary"])
        self.psnr_desc_label.pack(anchor="w")

        self.analysis_viz_frame = ctk.CTkFrame(
            scroll, fg_color=COLORS["card"], corner_radius=12,
            border_width=1, border_color=COLORS["border"]
        )
        self.analysis_viz_frame.pack(fill="x", pady=(0, 15))

        self.viz_title_label = ctk.CTkLabel(
            self.analysis_viz_frame, text="Visualization",
            font=FONTS["subtitle"], text_color=COLORS["secondary"]
        )
        self.viz_title_label.pack(anchor="w", padx=25, pady=(20, 10))

        self.viz_placeholder = ctk.CTkLabel(
            self.analysis_viz_frame,
            text="Select videos and click an action button above to visualize",
            font=FONTS["body"], text_color=COLORS["text_secondary"]
        )
        self.viz_placeholder.pack(pady=(10, 30))

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

    def _update_frame_index(self):
        try:
            value = int(self.frame_index_entry.get())
            if value < 0:
                value = 0
            self.analysis_frame_index.set(value)
        except ValueError:
            pass

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
            parent_dir = os.path.dirname(path)
            if parent_dir and not os.path.exists(parent_dir):
                try:
                    os.makedirs(parent_dir, exist_ok=True)
                except Exception as e:
                    self._show_modern_error(f"Cannot create directory: {e}")
                    return

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
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                except Exception as e:
                    self._show_modern_error(f"Cannot create directory: {e}")
                    return
            
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

        parent_dir = os.path.dirname(output_path)
        if parent_dir and not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception as e:
                self._show_modern_error(f"Cannot create output directory: {e}")
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

        enc_key = self.encryption_key.get()
        if not enc_key:
            self._show_modern_warning("Encryption key is required.")
            return

        use_random = self.use_random.get()
        stego_key = self.stego_key.get() if use_random else None

        if use_random and not stego_key:
            self._show_modern_warning("Please enter stego key for random spreading.")
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
                    True, enc_key, use_random, stego_key,
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

        enc_key = self.extract_enc_entry.get()
        if not enc_key:
            self._show_modern_warning("Encryption key is required.")
            return

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

        if result.get('stego_key_ignored', False):
            info += "\n[INFO] Video was embedded sequentially.\nStego Key was ignored during extraction.\n"

        if result['extension'] == '.txt' or not result['extension']:
            try:
                text = result['data'].decode('utf-8')
                info += f"\n--- Message Content ---\n{text}"
            except UnicodeDecodeError:
                info += "\nCannot decode message.\nPossible causes:\n- Incorrect encryption key\n- Incorrect stego key (for random mode)\n- Corrupted data"

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

        self.mse_btn.configure(state="disabled")
        self.status_label.configure(text="Calculating MSE & PSNR...")
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

                self.root.after(0, lambda: self._show_analysis_result(result, mse, psnr))
            except Exception as e:
                self.root.after(0, lambda: self._show_analysis_result(f"Error: {e}", 0, 0))

        threading.Thread(target=calc_thread, daemon=True).start()

    def _show_analysis_result(self, text, mse, psnr):
        self.status_label.configure(text="Analysis complete!")
        self.mse_btn.configure(state="normal")

        self.mse_value_label.configure(text=f"{mse:.6f}")
        if mse < 0.01:
            self.mse_desc_label.configure(text="Very low distortion")
        elif mse < 0.1:
            self.mse_desc_label.configure(text="Low distortion")
        else:
            self.mse_desc_label.configure(text="Noticeable distortion")

        color = COLORS["success"] if psnr > 40 else COLORS["warning"] if psnr > 30 else COLORS["error"]
        self.psnr_value_label.configure(text=f"{psnr:.2f} dB", text_color=color)
        if psnr > 40:
            self.psnr_desc_label.configure(text="Excellent quality (> 40dB)")
        elif psnr > 30:
            self.psnr_desc_label.configure(text="Good quality (30-40dB)")
        else:
            self.psnr_desc_label.configure(text="Low quality (< 30dB)")

    def _show_histogram_residual(self):
        self._show_analysis_plot("residual")

    def _show_multiframe_analysis(self):
        self._show_analysis_plot("multiframe")

    def _validate_analysis_paths(self):
        orig_path = getattr(self, 'analysis_orig_path', '')
        stego_path = getattr(self, 'analysis_stego_path', '')
        if not orig_path or not os.path.exists(orig_path):
            self._show_modern_warning("Please select original video.")
            return None, None
        if not stego_path or not os.path.exists(stego_path):
            self._show_modern_warning("Please select stego video.")
            return None, None
        return orig_path, stego_path

    def _embed_figure_in_viz(self, fig, title):
        """Embed a matplotlib figure into the analysis visualization frame"""
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import matplotlib.pyplot as plt

        fig.patch.set_facecolor(COLORS["card"])
        for ax in fig.axes:
            ax.set_facecolor(COLORS["card"])
            ax.tick_params(colors=COLORS["text_secondary"], labelsize=8)
            ax.xaxis.label.set_color(COLORS["text_primary"])
            ax.yaxis.label.set_color(COLORS["text_primary"])
            ax.title.set_color(COLORS["text_primary"])
            for spine in ax.spines.values():
                spine.set_color(COLORS["border"])

        self.viz_title_label.configure(text=title)

        self.viz_placeholder.pack_forget()
        if self.histogram_canvas:
            self.histogram_canvas.get_tk_widget().destroy()

        self.histogram_canvas = FigureCanvasTkAgg(fig, master=self.analysis_viz_frame)
        self.histogram_canvas.draw()
        self.histogram_canvas.get_tk_widget().pack(fill="x", padx=15, pady=(0, 20))

        plt.close(fig)

    def _show_analysis_plot(self, plot_type):
        orig_path, stego_path = self._validate_analysis_paths()
        if not orig_path:
            return

        try:
            frame_idx = self.analysis_frame_index.get()
        except:
            frame_idx = 3

        try:
            import matplotlib.pyplot as plt

            if plot_type == "multiframe":
                self.status_label.configure(text="Analyzing multiple frames...")
                self.multi_btn.configure(state="disabled")
                self.root.update_idletasks()

                def multiframe_thread():
                    try:
                        fig = plot_multiframe_residual(
                            orig_path, stego_path, sample_count=10, start_frame=3
                        )
                        if fig:
                            fig.set_size_inches(10, 5.5)
                            fig.tight_layout(rect=[0, 0.02, 1, 0.95])
                            self.root.after(0, lambda: self._embed_figure_in_viz(fig, "Multi-Frame Residual Analysis"))
                            self.root.after(0, lambda: self.status_label.configure(text="Multi-frame analysis complete!"))
                        else:
                            self.root.after(0, lambda: self._show_modern_error("Could not analyze frames"))
                        self.root.after(0, lambda: self.multi_btn.configure(state="normal"))
                    except Exception as e:
                        err = str(e)
                        self.root.after(0, lambda: self._show_modern_error(err))
                        self.root.after(0, lambda: self.multi_btn.configure(state="normal"))

                threading.Thread(target=multiframe_thread, daemon=True).start()
                return

            with VideoProcessor(orig_path) as vp_orig, VideoProcessor(stego_path) as vp_stego:
                orig_frame = vp_orig.read_frame(frame_idx)
                stego_frame = vp_stego.read_frame(frame_idx)

                if orig_frame is None or stego_frame is None:
                    self._show_modern_error(f"Cannot read frame {frame_idx}. Check if frame index is valid.")
                    return

                if plot_type == "residual":
                    fig = plot_histogram_residual(orig_frame, stego_frame)
                    fig.set_size_inches(10, 4.5)
                    fig.tight_layout(rect=[0, 0.05, 1, 0.95])
                    self._embed_figure_in_viz(fig, f"Residual Histogram (Frame {frame_idx})")

        except ImportError:
            self._show_modern_error("matplotlib is required.\nInstall with: pip install matplotlib")
        except Exception as e:
            self._show_modern_error(str(e))

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

    def _show_psnr_info(self):
        info_text = """PSNR (Peak Signal-to-Noise Ratio) Interpretation:

> 40 dB = Excellent quality (imperceptible changes)
30-40 dB = Good quality (minor changes)
20-30 dB = Acceptable quality (noticeable changes)
< 20 dB = Poor quality (visible artifacts)

For LSB steganography, PSNR is typically very high (> 40 dB) because changes are minimal and occur only in the least significant bits."""

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("PSNR Information")
        dialog.geometry("500x320")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        header = ctk.CTkFrame(dialog, fg_color=COLORS["primary"], corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="[i]", font=("JetBrains Mono", 24, "bold"),
                     text_color="white").pack(side="left", padx=20, pady=12)
        ctk.CTkLabel(header, text="PSNR Information", font=FONTS["subtitle"],
                     text_color="white").pack(side="left", pady=12)

        content = ctk.CTkFrame(dialog, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True, padx=25, pady=20)

        text_frame = ctk.CTkFrame(content, fg_color=COLORS["input_bg"], corner_radius=10)
        text_frame.pack(fill="both", expand=True, pady=(0, 15))

        info_label = ctk.CTkLabel(
            text_frame,
            text=info_text,
            font=FONTS["body"],
            text_color=COLORS["text_primary"],
            wraplength=430,
            justify="left"
        )
        info_label.pack(padx=20, pady=20)

        ctk.CTkButton(
            dialog, text="OK", font=FONTS["button"],
            fg_color=COLORS["primary"], text_color="white",
            hover_color="#0051D5", height=40, width=100,
            corner_radius=8, command=dialog.destroy
        ).pack(pady=(0, 20))
        dialog.focus_set()

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
