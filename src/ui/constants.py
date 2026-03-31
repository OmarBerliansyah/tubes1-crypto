import customtkinter as ctk

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
