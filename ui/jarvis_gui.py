import os
import math
import time
import threading
import tkinter as tk
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Futuristic Cyberpunk / Iron Man Bluish Palette
COLOR_BG = "#030712"          # Deep cosmic obsidian
COLOR_BG_GRAD = "#060f26"     # Deep midnight sapphire
COLOR_PANEL = "#07132c"       # Glassmorphism panel background
COLOR_PANEL_ALT = "#0a193b"   # Elevated card background
COLOR_BORDER = "#122a5e"      # Neon-tinted border
COLOR_BORDER_GLOW = "#1e488f" # Active border glow

COLOR_CYAN = "#00f0ff"        # Electric Neon Cyan
COLOR_BLUE = "#0077ff"        # Vibrant High-Voltage Blue
COLOR_AZURE = "#38bdf8"       # Crisp Sky Azure
COLOR_PURPLE = "#a855f7"      # Plasma Purple
COLOR_GREEN = "#10b981"       # Status Ready Emerald
COLOR_RED = "#f43f5e"         # Critical Stop Red
COLOR_TEXT = "#f8fafc"        # 4K Crystal White
COLOR_TEXT_DIM = "#8fa3c7"    # Muted Cyber Gray
COLOR_TEXT_MUTED = "#556b8d"  # Faint Tech Label

class JarvisGUI(ctk.CTk):
    def __init__(self, on_command_submit=None, on_mic_click=None, on_stop_click=None, on_pause_toggle=None, on_save_settings=None, current_settings=None, memory_manager=None, on_whatsapp_open=None, on_whatsapp_cancel=None, on_whatsapp_confirm=None, companion_manager=None):
        super().__init__()

        self.title("J.A.R.V.I.S. // Personal AI Assistant")
        self.geometry("1120x800")
        self.minsize(980, 700)
        self.configure(fg_color=COLOR_BG)

        self.on_command_submit = on_command_submit
        self.on_mic_click = on_mic_click
        self.on_stop_click = on_stop_click
        self.on_pause_toggle = on_pause_toggle
        self.on_save_settings = on_save_settings
        self.settings = current_settings or {}
        self.memory_mgr = memory_manager
        self.companion_mgr = companion_manager
        self.memory_window = None
        self.on_whatsapp_open = on_whatsapp_open
        self.on_whatsapp_cancel = on_whatsapp_cancel
        self.on_whatsapp_confirm = on_whatsapp_confirm

        self.status = "IDLE"  # IDLE, LISTENING, THINKING, SPEAKING, PAUSED
        self.anim_angle = 0
        self.is_paused = False
        self.particles = []
        self._init_particles()

        self._build_header()
        self._build_main_layout()
        self._build_bottom_controls()
        self._start_60fps_visualizer()

        # Handle window close / minimize to tray
        self.protocol("WM_DELETE_WINDOW", self.on_close_requested)

    def _init_particles(self):
        """Initialize floating plasma energy particles."""
        import random
        for _ in range(18):
            self.particles.append({
                "radius": random.uniform(40, 130),
                "angle": random.uniform(0, 360),
                "speed": random.uniform(0.5, 2.0),
                "size": random.uniform(1.5, 3.2),
                "color": random.choice([COLOR_CYAN, COLOR_BLUE, COLOR_AZURE, "#ffffff"])
            })

    def _build_header(self):
        header_frame = ctk.CTkFrame(
            self,
            fg_color=COLOR_PANEL,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=14,
            height=65
        )
        header_frame.pack(fill="x", padx=18, pady=(14, 8))
        header_frame.pack_propagate(False)

        # Brand Container
        brand_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        brand_frame.pack(side="left", padx=16, pady=10)

        title_label = ctk.CTkLabel(
            brand_frame,
            text="J.A.R.V.I.S.",
            font=ctk.CTkFont(family="Consolas", size=24, weight="bold"),
            text_color=COLOR_CYAN
        )
        title_label.pack(side="left", padx=(0, 10))

        # Header Badge
        subtitle_badge = ctk.CTkLabel(
            brand_frame,
            text="PERSONAL AI ASSISTANT",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLOR_AZURE,
            fg_color="#081a3d",
            corner_radius=8,
            padx=10,
            pady=3
        )
        subtitle_badge.pack(side="left", pady=2)

        # Controls Container (Right side)
        right_ctrl = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_ctrl.pack(side="right", padx=14, pady=10)

        # Live Status Glow Badge
        self.status_badge = ctk.CTkLabel(
            right_ctrl,
            text="● SYSTEM READY",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_CYAN,
            fg_color="#062238",
            corner_radius=8,
            padx=14,
            pady=5
        )
        self.status_badge.pack(side="left", padx=6)

        # Pause / Resume Wake Word
        self.pause_btn = ctk.CTkButton(
            right_ctrl,
            text="Pause Wake Word",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=125,
            height=32,
            fg_color="#0e1d3b",
            hover_color="#172b54",
            border_color=COLOR_BORDER,
            border_width=1,
            text_color=COLOR_TEXT,
            command=self._handle_pause_toggle
        )
        self.pause_btn.pack(side="left", padx=6)

        # Memory Bank Button
        self.memory_btn = ctk.CTkButton(
            right_ctrl,
            text="🧠 Memory Bank",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=115,
            height=32,
            fg_color="#0e1d3b",
            hover_color="#172b54",
            border_color=COLOR_BORDER,
            border_width=1,
            text_color=COLOR_CYAN,
            command=self.open_memory_modal
        )
        self.memory_btn.pack(side="left", padx=6)

        # Settings Button
        settings_btn = ctk.CTkButton(
            right_ctrl,
            text="⚙ Settings",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=95,
            height=32,
            fg_color="#0e1d3b",
            hover_color="#172b54",
            border_color=COLOR_BORDER,
            border_width=1,
            text_color=COLOR_TEXT,
            command=self.open_settings_modal
        )
        settings_btn.pack(side="left", padx=6)

    def _build_main_layout(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=18, pady=4)

        # Left Column: Animated 60FPS Arc Reactor Centerpiece + Quick Queries
        left_panel = ctk.CTkFrame(
            main_container,
            fg_color=COLOR_PANEL,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=16,
            width=460
        )
        left_panel.pack(side="left", fill="both", padx=(0, 10), pady=0)
        left_panel.pack_propagate(False)

        # Arc Reactor Header
        arc_header = ctk.CTkFrame(left_panel, fg_color="transparent")
        arc_header.pack(fill="x", padx=16, pady=(14, 0))

        arc_title = ctk.CTkLabel(
            arc_header,
            text="⚡ NEURAL ARC REACTOR",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=COLOR_CYAN
        )
        arc_title.pack(side="left")

        fps_badge = ctk.CTkLabel(
            arc_header,
            text="60 FPS ACTIVE",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_MUTED
        )
        fps_badge.pack(side="right")

        # 60FPS High-DPI Arc Reactor Canvas
        self.canvas = tk.Canvas(
            left_panel,
            width=420,
            height=330,
            bg=COLOR_PANEL,
            highlightthickness=0
        )
        self.canvas.pack(pady=(4, 2))

        # Real-time Status Subtitle
        self.status_subtext = ctk.CTkLabel(
            left_panel,
            text="At your command, Boss. Say 'Hey Jarvis' or click Speak.",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT
        )
        self.status_subtext.pack(pady=(0, 8))

        # Quick Voice Command Chips
        quick_frame = ctk.CTkFrame(left_panel, fg_color="#050d21", corner_radius=12, border_color=COLOR_BORDER, border_width=1)
        quick_frame.pack(fill="both", expand=True, padx=14, pady=(2, 14))

        quick_label = ctk.CTkLabel(
            quick_frame,
            text="QUICK COMMAND SHORTCUTS",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_TEXT_DIM
        )
        quick_label.pack(anchor="w", padx=12, pady=(8, 4))

        quick_commands = [
            ("💬 WhatsApp Rahul: 10 min me aa raha hu", "Jarvis, Rahul ko WhatsApp pe message bhejo: Main 10 minute mein aa raha hoon."),
            ("📄 WhatsApp assignment.pdf Amit ko", "Downloads folder se assignment.pdf Amit ko bhej do."),
            ("🌐 Open WhatsApp Web", "Jarvis, WhatsApp Web open kar do."),
            ("💖 Person I Love The Most", "Jarvis show me the person i love the most"),
            ("✨ Most Beautiful Girl On Earth", "Jarvis show me the most beautiful girl on earth"),
            ("🧠 Show All Saved Questions", "Maine tumhe kya-kya yaad karwaya hai?"),
            ("▶ Play Chaleya song on YouTube", "Chaleya song chalao YouTube pe"),
            ("📂 File explorer me downloads kholo", "file explorer me downloads open karo")
        ]

        for display_txt, cmd in quick_commands:
            btn = ctk.CTkButton(
                quick_frame,
                text=display_txt,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                fg_color="#0a1736",
                hover_color="#122554",
                text_color=COLOR_AZURE,
                anchor="w",
                height=26,
                corner_radius=6,
                command=lambda c=cmd: self._trigger_quick_command(c)
            )
            btn.pack(fill="x", padx=10, pady=2)

        # Right Column: Conversation Transcript with Crystal Clear Formatting
        right_panel = ctk.CTkFrame(
            main_container,
            fg_color=COLOR_PANEL,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=16
        )
        right_panel.pack(side="right", fill="both", expand=True, padx=0, pady=0)

        right_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        right_header.pack(fill="x", padx=18, pady=(14, 6))

        right_title = ctk.CTkLabel(
            right_header,
            text="CONVERSATION & ACTIVITY STREAM",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=COLOR_TEXT_DIM
        )
        right_title.pack(side="left")

        clear_btn = ctk.CTkButton(
            right_header,
            text="Clear Log",
            font=ctk.CTkFont(size=11),
            width=70,
            height=24,
            fg_color="#0a1838",
            hover_color="#132759",
            text_color=COLOR_TEXT_DIM,
            command=self._clear_transcript
        )
        clear_btn.pack(side="right")

        # Live Nodes Status Container (WhatsApp Web + Phone Companion Realme 10 Pro)
        nodes_status_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        nodes_status_frame.pack(fill="x", padx=16, pady=(0, 8))

        # 1. WhatsApp Web Live Status & Control Card
        self.wa_card = ctk.CTkFrame(
            nodes_status_frame,
            fg_color="#05102a",
            border_color="#1a3668",
            border_width=1,
            corner_radius=12,
            height=72
        )
        self.wa_card.pack(fill="x", pady=(0, 6))
        self.wa_card.pack_propagate(False)

        # Row 1: WhatsApp Badge & Action Buttons
        wa_top_row = ctk.CTkFrame(self.wa_card, fg_color="transparent")
        wa_top_row.pack(fill="x", padx=12, pady=(5, 2))

        wa_brand = ctk.CTkLabel(
            wa_top_row,
            text="💬 WHATSAPP WEB",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#25D366"
        )
        wa_brand.pack(side="left", padx=(0, 8))

        self.wa_status_badge = ctk.CTkLabel(
            wa_top_row,
            text="● DISCONNECTED",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_TEXT_DIM,
            fg_color="#0e1f3d",
            corner_radius=6,
            padx=10,
            pady=3
        )
        self.wa_status_badge.pack(side="left")

        # Action Buttons on Right
        self.wa_confirm_btn = ctk.CTkButton(
            wa_top_row,
            text="✔ Confirm & Send",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            width=110,
            height=26,
            fg_color="#059669",
            hover_color="#047857",
            text_color="#ffffff",
            corner_radius=6,
            command=self._handle_wa_confirm
        )
        # Hidden by default until confirmation required

        self.wa_cancel_btn = ctk.CTkButton(
            wa_top_row,
            text="❌ Cancel Send",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            width=90,
            height=26,
            fg_color="#3b0f16",
            hover_color="#54121d",
            border_color=COLOR_RED,
            border_width=1,
            text_color="#fca5a5",
            corner_radius=6,
            command=self._handle_wa_cancel
        )
        self.wa_cancel_btn.pack(side="right", padx=(4, 0))

        self.wa_open_btn = ctk.CTkButton(
            wa_top_row,
            text="🌐 Open WhatsApp",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            width=110,
            height=26,
            fg_color="#0a2342",
            hover_color="#133d6f",
            border_color="#1d4ed8",
            border_width=1,
            text_color=COLOR_CYAN,
            corner_radius=6,
            command=self._handle_wa_open
        )
        self.wa_open_btn.pack(side="right", padx=(4, 4))

        # Row 2: Status detail subtext
        self.wa_detail_label = ctk.CTkLabel(
            self.wa_card,
            text="WhatsApp Web is offline. Say 'Hey Jarvis, WhatsApp kholo' or click Open.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_DIM,
            anchor="w"
        )
        self.wa_detail_label.pack(fill="x", padx=14, pady=(0, 4))

        # 2. Phone Companion (Realme 10 Pro) Live Status Card
        self.phone_card = ctk.CTkFrame(
            nodes_status_frame,
            fg_color="#05102a",
            border_color="#1a3668",
            border_width=1,
            corner_radius=12,
            height=70
        )
        self.phone_card.pack(fill="x", pady=(0, 0))
        self.phone_card.pack_propagate(False)

        phone_top_row = ctk.CTkFrame(self.phone_card, fg_color="transparent")
        phone_top_row.pack(fill="x", padx=12, pady=(5, 2))

        phone_brand = ctk.CTkLabel(
            phone_top_row,
            text="📱 PHONE COMPANION (Realme 10 Pro)",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#38bdf8"
        )
        phone_brand.pack(side="left", padx=(0, 8))

        self.phone_status_badge = ctk.CTkLabel(
            phone_top_row,
            text="● DISCONNECTED",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_TEXT_DIM,
            fg_color="#0e1f3d",
            corner_radius=6,
            padx=10,
            pady=3
        )
        self.phone_status_badge.pack(side="left")

        # Live IP & Copy Button on the right
        self.copy_ip_btn = ctk.CTkButton(
            phone_top_row,
            text="📋 Copy IP",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            width=78,
            height=24,
            fg_color="#0a2342",
            hover_color="#133d6f",
            border_color="#1d4ed8",
            border_width=1,
            text_color=COLOR_CYAN,
            corner_radius=6,
            command=self._handle_copy_ip
        )
        self.copy_ip_btn.pack(side="right", padx=(4, 0))

        cur_ip = self.companion_mgr.server_ip if self.companion_mgr else "127.0.0.1"
        cur_pin = self.companion_mgr.pin if self.companion_mgr else "742918"
        cur_port = self.companion_mgr.port if self.companion_mgr else 8765

        self.phone_info_label = ctk.CTkLabel(
            phone_top_row,
            text=f"IP: {cur_ip}:{cur_port} | PIN: {cur_pin}",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#38bdf8"
        )
        self.phone_info_label.pack(side="right", padx=(0, 6))

        self.phone_detail_label = ctk.CTkLabel(
            self.phone_card,
            text=f"Phone offline. On phone app, enter Laptop IP: {cur_ip} (Port: {cur_port}, PIN: {cur_pin}) & tap Connect.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#93c5fd",
            anchor="w"
        )
        self.phone_detail_label.pack(fill="x", padx=14, pady=(0, 4))

        self.transcript_box = ctk.CTkTextbox(
            right_panel,
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color="#040a1b",
            text_color=COLOR_TEXT,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=12,
            wrap="word"
        )
        self.transcript_box.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        self.append_transcript("System", "J.A.R.V.I.S. Mark 85 Initialized. System ready with 60FPS Neural Core.")

    def _build_bottom_controls(self):
        bottom_frame = ctk.CTkFrame(
            self,
            fg_color=COLOR_PANEL,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=16,
            height=70
        )
        bottom_frame.pack(fill="x", padx=18, pady=(8, 14))
        bottom_frame.pack_propagate(False)

        # Glowing Circular / Pill Mic Button
        self.mic_btn = ctk.CTkButton(
            bottom_frame,
            text="🎙 Speak",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            width=120,
            height=44,
            fg_color=COLOR_BLUE,
            hover_color="#0055cc",
            corner_radius=10,
            border_color=COLOR_CYAN,
            border_width=1,
            text_color="#ffffff",
            command=self._handle_mic_click
        )
        self.mic_btn.pack(side="left", padx=(14, 8), pady=12)

        # Stop Voice Output Button
        self.stop_btn = ctk.CTkButton(
            bottom_frame,
            text="⏹ Stop",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            width=85,
            height=44,
            fg_color="#260814",
            hover_color="#3d0e20",
            border_color=COLOR_RED,
            border_width=1,
            text_color=COLOR_RED,
            corner_radius=10,
            command=self._handle_stop_click
        )
        self.stop_btn.pack(side="left", padx=(0, 10), pady=12)

        # Command Input Field
        self.entry = ctk.CTkEntry(
            bottom_frame,
            placeholder_text="Talk to JARVIS in Hinglish, Hindi, or English (e.g., '10th mark sheet pdf open karo' or 'Chaleya song chala do')...",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=44,
            fg_color="#040a1c",
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            corner_radius=10
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=12)
        self.entry.bind("<Return>", lambda e: self._handle_submit())

        # Send Button
        send_btn = ctk.CTkButton(
            bottom_frame,
            text="⚡ Send",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            width=90,
            height=44,
            fg_color=COLOR_CYAN,
            text_color="#000000",
            hover_color="#00ccdd",
            corner_radius=10,
            command=self._handle_submit
        )
        send_btn.pack(side="right", padx=(0, 14), pady=12)

    def _start_60fps_visualizer(self):
        """Ultra-smooth 60 FPS Arc Reactor animation engine (~16ms delta)."""
        def _render_frame():
            self.canvas.delete("all")
            cx, cy = 210, 165
            self.anim_angle = (self.anim_angle + 2.5) % 360

            # State-dependent colors & pulse frequencies
            t = time.time()
            if self.status == "LISTENING":
                primary_color = COLOR_CYAN
                secondary_color = COLOR_BLUE
                pulse = 14 * math.sin(t * 10)
                rot_speed = 3.5
            elif self.status == "THINKING":
                primary_color = COLOR_PURPLE
                secondary_color = COLOR_CYAN
                pulse = 10 * math.sin(t * 14)
                rot_speed = 5.0
            elif self.status == "SPEAKING":
                primary_color = COLOR_GREEN
                secondary_color = COLOR_CYAN
                pulse = 18 * math.sin(t * 12)
                rot_speed = 4.0
            elif self.status == "PAUSED":
                primary_color = "#475569"
                secondary_color = "#334155"
                pulse = 0
                rot_speed = 0.5
            else:  # IDLE
                primary_color = COLOR_CYAN
                secondary_color = COLOR_BLUE
                pulse = 5 * math.sin(t * 3.5)
                rot_speed = 1.8

            r_outer = 130 + pulse
            r_mid = 95 + (pulse * 0.6)
            r_inner = 60 + (pulse * 0.4)
            r_core = 26 + (pulse * 0.3)

            # Layer 1: Ambient Glowing Volumetric Backlight (Radial Halo)
            for r_halo, col in [(155, "#04143a"), (140, "#061c4d"), (125, "#092463")]:
                self.canvas.create_oval(
                    cx - r_halo, cy - r_halo, cx + r_halo, cy + r_halo,
                    fill=col, outline=""
                )

            # Layer 2: Floating Energy Particles Orbiting the Core
            for p in self.particles:
                p["angle"] = (p["angle"] + p["speed"] * (rot_speed * 0.5)) % 360
                rad = math.radians(p["angle"])
                px = cx + (p["radius"] + (pulse * 0.3)) * math.cos(rad)
                py = cy + (p["radius"] + (pulse * 0.3)) * math.sin(rad)
                sz = p["size"]
                self.canvas.create_oval(px - sz, py - sz, px + sz, py + sz, fill=p["color"], outline="")

            # Layer 3: Outer Orbital Ring with Radar Ticks
            self.canvas.create_oval(
                cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer,
                outline=secondary_color, width=1
            )
            for a in range(0, 360, 15):
                tick_angle = math.radians(a + self.anim_angle * rot_speed)
                t_inner = r_outer - 5
                t_outer = r_outer + 5
                x1 = cx + t_inner * math.cos(tick_angle)
                y1 = cy + t_inner * math.sin(tick_angle)
                x2 = cx + t_outer * math.cos(tick_angle)
                y2 = cy + t_outer * math.sin(tick_angle)
                t_col = primary_color if a % 45 == 0 else secondary_color
                self.canvas.create_line(x1, y1, x2, y2, fill=t_col, width=1.5 if a % 45 == 0 else 1)

            # Layer 4: Segmented Counter-Rotating Cyber Arcs
            for i, offset in enumerate([0, 120, 240]):
                arc_start = (self.anim_angle * -rot_speed * 1.2) + offset
                self.canvas.create_arc(
                    cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid,
                    start=arc_start, extent=75,
                    outline=primary_color, width=3, style="arc"
                )

            # Layer 5: High-Speed Glowing Inner Reactor Teeth Ring
            for a in range(0, 360, 30):
                ang = math.radians(a + self.anim_angle * rot_speed * 1.5)
                rx1 = cx + (r_inner - 8) * math.cos(ang)
                ry1 = cy + (r_inner - 8) * math.sin(ang)
                rx2 = cx + (r_inner + 8) * math.cos(ang)
                ry2 = cy + (r_inner + 8) * math.sin(ang)
                self.canvas.create_line(rx1, ry1, rx2, ry2, fill=secondary_color, width=2)

            # Layer 6: Dynamic Plasma Filaments twisting toward Core (Electric Orb Style)
            for i in range(6):
                filament_ang = math.radians((i * 60) + (self.anim_angle * rot_speed * 2.0))
                wiggle = 8 * math.sin(t * 12 + i)
                fx1 = cx + (r_inner - 4) * math.cos(filament_ang)
                fy1 = cy + (r_inner - 4) * math.sin(filament_ang)
                fx2 = cx + (r_core + 4) * math.cos(filament_ang + math.radians(wiggle))
                fy2 = cy + (r_core + 4) * math.sin(filament_ang + math.radians(wiggle))
                self.canvas.create_line(fx1, fy1, fx2, fy2, fill=primary_color, width=1.5)

            # Layer 7: Nuclear Core Glowing Center
            self.canvas.create_oval(
                cx - r_core, cy - r_core, cx + r_core, cy + r_core,
                fill=secondary_color, outline=primary_color, width=2
            )
            # Ultra-bright nuclear white point
            r_nuke = max(4, r_core * 0.45)
            self.canvas.create_oval(
                cx - r_nuke, cy - r_nuke, cx + r_nuke, cy + r_nuke,
                fill="#ffffff", outline=primary_color, width=1
            )

            # Exact 60 FPS callback (~16 milliseconds)
            self.after(16, _render_frame)

        self.after(50, _render_frame)

    def set_status(self, status_text: str):
        self.status = status_text.upper()
        if self.status == "LISTENING":
            self.status_badge.configure(text="● LISTENING...", text_color=COLOR_CYAN, fg_color="#062238")
            self.status_subtext.configure(text="Listening to your voice... Speak naturally.", text_color=COLOR_CYAN)
            self.mic_btn.configure(fg_color=COLOR_CYAN, text_color="#000000", text="🎙 Listening...")
        elif self.status == "THINKING":
            self.status_badge.configure(text="● PROCESSING QUERY...", text_color=COLOR_PURPLE, fg_color="#200a2e")
            self.status_subtext.configure(text="Neural Brain querying Gemini AI & system...", text_color=COLOR_PURPLE)
            self.mic_btn.configure(fg_color=COLOR_PURPLE, text_color="#ffffff", text="🧠 Thinking...")
        elif self.status == "SPEAKING":
            self.status_badge.configure(text="● JARVIS SPEAKING", text_color=COLOR_GREEN, fg_color="#0a2a1a")
            self.status_subtext.configure(text="Responding with natural Indian Hinglish voice...", text_color=COLOR_GREEN)
            self.mic_btn.configure(fg_color=COLOR_GREEN, text_color="#000000", text="🔊 Speaking")
        elif self.status == "PAUSED":
            self.status_badge.configure(text="❚❚ PAUSED", text_color=COLOR_TEXT_DIM, fg_color="#182030")
            self.status_subtext.configure(text="Wake word listener paused. Click 'Resume Wake Word' to activate.", text_color=COLOR_TEXT_DIM)
            self.mic_btn.configure(fg_color="#182030", text_color=COLOR_TEXT_DIM, text="🎙 Paused")
        else:
            self.status_badge.configure(text="● SYSTEM READY", text_color=COLOR_CYAN, fg_color="#062238")
            self.status_subtext.configure(text="At your command, Boss. Say 'Hey Jarvis' or click Speak.", text_color=COLOR_TEXT)
            self.mic_btn.configure(fg_color=COLOR_BLUE, text_color="#ffffff", text="🎙 Speak")

    def append_transcript(self, sender: str, message: str):
        self.transcript_box.configure(state="normal")
        timestamp = time.strftime("%H:%M")
        if sender.lower() == "user":
            self.transcript_box.insert("end", f"[{timestamp}] User:\n", "user_header")
            self.transcript_box.insert("end", f"{message}\n\n", "user_text")
        elif sender.lower() == "jarvis":
            self.transcript_box.insert("end", f"[{timestamp}] JARVIS:\n", "jarvis_header")
            self.transcript_box.insert("end", f"{message}\n\n", "jarvis_text")
        else:
            self.transcript_box.insert("end", f"[{timestamp}] {sender}: {message}\n\n", "sys_text")

        self.transcript_box.see("end")
        self.transcript_box.configure(state="disabled")

    def _clear_transcript(self):
        self.transcript_box.configure(state="normal")
        self.transcript_box.delete("1.0", "end")
        self.transcript_box.insert("end", "[Log Cleared] Ready for new interactions.\n\n")
        self.transcript_box.configure(state="disabled")

    def _handle_submit(self):
        text = self.entry.get().strip()
        if text:
            self.entry.delete(0, "end")
            self.append_transcript("User", text)
            if self.on_command_submit:
                threading.Thread(target=self.on_command_submit, args=(text,), daemon=True).start()

    def _trigger_quick_command(self, cmd_text: str):
        self.append_transcript("User", cmd_text)
        if self.on_command_submit:
            threading.Thread(target=self.on_command_submit, args=(cmd_text,), daemon=True).start()

    def _handle_mic_click(self):
        if self.on_mic_click:
            self.on_mic_click()

    def _handle_stop_click(self):
        if self.on_stop_click:
            self.on_stop_click()
        self.set_status("IDLE")

    def _handle_pause_toggle(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.configure(text="Resume Wake Word", fg_color="#3b1f0c")
            self.set_status("PAUSED")
        else:
            self.pause_btn.configure(text="Pause Wake Word", fg_color="#0e1d3b")
            self.set_status("IDLE")
        if self.on_pause_toggle:
            self.on_pause_toggle(self.is_paused)

    def _handle_wa_open(self):
        if self.on_whatsapp_open:
            self.on_whatsapp_open()
        elif self.on_command_submit:
            threading.Thread(target=self.on_command_submit, args=("Jarvis WhatsApp kholo",), daemon=True).start()

    def _handle_wa_cancel(self):
        if self.on_whatsapp_cancel:
            self.on_whatsapp_cancel()
        elif self.on_command_submit:
            threading.Thread(target=self.on_command_submit, args=("WhatsApp cancel karo",), daemon=True).start()

    def _handle_wa_confirm(self):
        if self.on_whatsapp_confirm:
            self.on_whatsapp_confirm()
        elif self.on_command_submit:
            threading.Thread(target=self.on_command_submit, args=("Haan bhejo",), daemon=True).start()

    def update_whatsapp_status(self, status: str, message: str = ""):
        """Dynamically updates the WhatsApp card badge, subtext, and action buttons."""
        st = status.upper()
        if st == "CONNECTED":
            self.wa_status_badge.configure(text="● CONNECTED & READY", text_color="#10b981", fg_color="#064e3b")
            self.wa_detail_label.configure(text=message or "WhatsApp Web is logged in. Ready for voice commands.", text_color=COLOR_AZURE)
            self.wa_confirm_btn.pack_forget()
        elif st == "AWAITING_QR":
            self.wa_status_badge.configure(text="● SCAN QR CODE ON PHONE", text_color="#fbbf24", fg_color="#78350f")
            self.wa_detail_label.configure(text=message or "Please open WhatsApp on your phone, tap Linked Devices, and scan the QR code.", text_color="#fcd34d")
            self.wa_confirm_btn.pack_forget()
        elif st == "AWAITING_CONFIRMATION":
            self.wa_status_badge.configure(text="● CONFIRMATION REQUIRED", text_color="#fbbf24", fg_color="#78350f")
            self.wa_detail_label.configure(text=message or "Say 'Haan bhejo' or click Confirm & Send to send.", text_color="#fde68a")
            # Show Confirm button next to Cancel button
            self.wa_confirm_btn.pack(side="right", padx=(4, 4))
        elif st in ["CONNECTING", "SEARCHING_CONTACT"]:
            self.wa_status_badge.configure(text=f"● {st.replace('_', ' ')}", text_color=COLOR_CYAN, fg_color="#0c2a4d")
            self.wa_detail_label.configure(text=message or "Processing WhatsApp Web request...", text_color=COLOR_TEXT)
            self.wa_confirm_btn.pack_forget()
        elif st == "PREPARING_ATTACHMENT":
            self.wa_status_badge.configure(text="● ATTACHING FILE", text_color=COLOR_PURPLE, fg_color="#3b0764")
            self.wa_detail_label.configure(text=message or "Uploading document/image attachment...", text_color=COLOR_TEXT)
            self.wa_confirm_btn.pack_forget()
        elif st == "SENDING":
            self.wa_status_badge.configure(text="● SENDING...", text_color=COLOR_BLUE, fg_color="#1e3a8a")
            self.wa_detail_label.configure(text=message or "Dispatching message to recipient...", text_color=COLOR_TEXT)
            self.wa_confirm_btn.pack_forget()
        elif st == "SUCCESS":
            self.wa_status_badge.configure(text="● MESSAGE SENT", text_color="#10b981", fg_color="#064e3b")
            self.wa_detail_label.configure(text=message or "Message delivered successfully!", text_color="#a7f3d0")
            self.wa_confirm_btn.pack_forget()
        elif st == "FAILED":
            self.wa_status_badge.configure(text="● FAILED", text_color=COLOR_RED, fg_color="#450a0a")
            self.wa_detail_label.configure(text=message or "Send action failed. Please check WhatsApp Web window.", text_color="#fca5a5")
            self.wa_confirm_btn.pack_forget()
        else:  # DISCONNECTED
            self.wa_status_badge.configure(text="● DISCONNECTED", text_color=COLOR_TEXT_DIM, fg_color="#0e1f3d")
            self.wa_detail_label.configure(text=message or "WhatsApp Web is offline. Say 'Hey Jarvis, WhatsApp kholo' or click Open.", text_color=COLOR_TEXT_DIM)
            self.wa_confirm_btn.pack_forget()

    def _handle_copy_ip(self):
        cur_ip = self.companion_mgr.server_ip if self.companion_mgr else ""
        if cur_ip:
            self.clipboard_clear()
            self.clipboard_append(cur_ip)
            self.copy_ip_btn.configure(text="✅ Copied!")
            self.after(2000, lambda: self.copy_ip_btn.configure(text="📋 Copy IP"))

    def update_phone_status(self, st: str, message: str = ""):
        st_upper = (st or "").upper()
        cur_ip = self.companion_mgr.server_ip if self.companion_mgr else "127.0.0.1"
        cur_pin = self.companion_mgr.pin if self.companion_mgr else "742918"
        cur_port = self.companion_mgr.port if self.companion_mgr else 8765

        if hasattr(self, "phone_info_label"):
            self.phone_info_label.configure(text=f"IP: {cur_ip}:{cur_port} | PIN: {cur_pin}")

        if "CONNECT" in st_upper and "DIS" not in st_upper:
            self.phone_status_badge.configure(
                text="● ONLINE & PAIRED",
                text_color="#10b981",
                fg_color="#064e3b"
            )
            self.phone_detail_label.configure(
                text=message or "Realme 10 Pro connected via Wi-Fi. Ready to make instant calls.",
                text_color="#6ee7b7"
            )
        elif "AUTH" in st_upper:
            self.phone_status_badge.configure(
                text="● AUTHENTICATING",
                text_color="#f59e0b",
                fg_color="#451a03"
            )
            self.phone_detail_label.configure(
                text=message or "Verifying companion pairing PIN...",
                text_color="#fde68a"
            )
        else:  # DISCONNECTED
            self.phone_status_badge.configure(
                text="● DISCONNECTED",
                text_color=COLOR_TEXT_DIM,
                fg_color="#0e1f3d"
            )
            self.phone_detail_label.configure(
                text=message or f"Phone offline. On phone app, enter Laptop IP: {cur_ip} (Port: {cur_port}, PIN: {cur_pin}) & tap Connect.",
                text_color="#93c5fd"
            )

    def on_close_requested(self):
        if self.settings.get("system_tray_minimize", True):
            self.withdraw()
        else:
            self.destroy()

    def open_settings_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("JARVIS Settings & AI Configuration")
        modal.geometry("540x500")
        modal.configure(fg_color=COLOR_BG)
        modal.grab_set()

        title = ctk.CTkLabel(
            modal,
            text="⚙ Assistant Configuration",
            font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
            text_color=COLOR_CYAN
        )
        title.pack(pady=(18, 12))

        # API Key
        key_label = ctk.CTkLabel(
            modal,
            text="⚡ Google Gemini Flash API Key (Personal Brain):",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_CYAN
        )
        key_label.pack(anchor="w", padx=25, pady=(8, 2))
        key_subtext = ctk.CTkLabel(
            modal,
            text="Powers conversational AI, Hinglish sarcasm, intelligent code diagnosis, and advice.",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_DIM
        )
        key_subtext.pack(anchor="w", padx=25, pady=(0, 4))
        key_entry = ctk.CTkEntry(modal, placeholder_text="Paste your Gemini API key here", width=490, fg_color="#050c21", border_color=COLOR_BORDER)
        curr_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
        if curr_key:
            key_entry.insert(0, curr_key)
        key_entry.pack(padx=25, pady=(0, 8))

        # Voice engine
        voice_label = ctk.CTkLabel(modal, text="Text-To-Speech Engine:", font=ctk.CTkFont(size=12, weight="bold"))
        voice_label.pack(anchor="w", padx=25, pady=(8, 2))
        voice_opt = ctk.CTkOptionMenu(
            modal,
            values=["edge-tts (High Quality Indian Female - Swara / Neerja)", "pyttsx3 (100% Offline SAPI5)"],
            width=490,
            fg_color="#08183d",
            button_color=COLOR_BLUE
        )
        voice_opt.pack(padx=25, pady=(0, 8))

        # Language mode
        lang_label = ctk.CTkLabel(modal, text="Preferred Response Language:", font=ctk.CTkFont(size=12, weight="bold"))
        lang_label.pack(anchor="w", padx=25, pady=(8, 2))
        lang_opt = ctk.CTkOptionMenu(
            modal,
            values=["Auto-Detect (Match User Language)", "Hinglish (Hindi + English)", "Pure Hindi", "Pure English"],
            width=490,
            fg_color="#08183d",
            button_color=COLOR_BLUE
        )
        lang_opt.pack(padx=25, pady=(0, 8))

        # Privacy Notice
        notice = ctk.CTkLabel(
            modal,
            text="🔒 Privacy: Audio is processed locally when wake word is triggered or mic clicked.\nDirect YouTube playback and Chrome launcher are enabled.",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_DIM,
            justify="left"
        )
        notice.pack(padx=25, pady=12)

        def save_and_close():
            new_key = key_entry.get().strip()
            if new_key:
                os.environ["GEMINI_API_KEY"] = new_key
            if self.on_save_settings:
                self.on_save_settings({
                    "gemini_key": new_key,
                    "voice_engine": "edge-tts" if "edge-tts" in voice_opt.get() else "pyttsx3",
                    "language_mode": lang_opt.get()
                })
            modal.destroy()

        save_btn = ctk.CTkButton(
            modal,
            text="Save & Apply",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_CYAN,
            text_color="#000",
            hover_color="#00c4d6",
            command=save_and_close,
            width=180,
            height=38
        )
        save_btn.pack(pady=15)

    def open_memory_modal(self):
        """Open or bring to focus the Persistent Custom Q&A Memory Bank window."""
        if not self.memory_mgr:
            return
        if hasattr(self, "memory_window") and self.memory_window and self.memory_window.winfo_exists():
            self.memory_window.deiconify()
            self.memory_window.lift()
            self.memory_window.focus_force()
            self.memory_window.refresh_memory_list()
        else:
            from ui.memory_gui import CustomMemoryWindow
            self.memory_window = CustomMemoryWindow(
                self,
                self.memory_mgr,
                on_memory_changed=lambda: self.append_transcript("System", "Custom Q&A memory updated successfully.")
            )
