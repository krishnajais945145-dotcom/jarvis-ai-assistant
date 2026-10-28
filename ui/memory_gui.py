import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from datetime import datetime
from typing import Optional, Callable

# Reuse Color Tokens from jarvis_gui
COLOR_BG = "#030712"          # Deep cosmic obsidian
COLOR_PANEL = "#07132c"       # Glassmorphism panel background
COLOR_PANEL_ALT = "#0a193b"   # Elevated card background
COLOR_BORDER = "#122a5e"      # Neon-tinted border
COLOR_BORDER_GLOW = "#1e488f" # Active border glow

COLOR_CYAN = "#00f0ff"        # Electric Neon Cyan
COLOR_BLUE = "#0077ff"        # Vibrant High-Voltage Blue
COLOR_AZURE = "#38bdf8"       # Crisp Sky Azure
COLOR_PURPLE = "#a855f7"      # Plasma Purple
COLOR_GREEN = "#10b981"       # Status Emerald
COLOR_RED = "#f43f5e"         # Critical Red
COLOR_TEXT = "#f8fafc"        # Crystal White
COLOR_TEXT_DIM = "#8fa3c7"    # Muted Cyber Gray
COLOR_TEXT_MUTED = "#556b8d"  # Faint Tech Label

class CustomMemoryWindow(ctk.CTkToplevel):
    """
    Futuristic Cyberpunk UI for JARVIS Persistent Custom Q&A Memory Bank.
    Provides manual adding, searching/filtering, editing, deleting,
    real-time count, and safe export/import backup operations.
    """

    def __init__(self, parent, memory_manager, on_memory_changed: Optional[Callable] = None):
        super().__init__(parent)
        self.memory_mgr = memory_manager
        self.on_memory_changed = on_memory_changed

        self.title("J.A.R.V.I.S. // Persistent Custom Q&A Memory Bank")
        self.geometry("820x680")
        self.minsize(740, 560)
        self.configure(fg_color=COLOR_BG)

        # Bring window to front
        self.lift()
        self.focus_force()

        self._build_header()
        self._build_add_section()
        self._build_search_bar()
        self._build_list_container()

        self.refresh_memory_list()

    def _build_header(self):
        header_frame = ctk.CTkFrame(
            self,
            fg_color=COLOR_PANEL,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=12,
            height=60
        )
        header_frame.pack(fill="x", padx=16, pady=(14, 8))
        header_frame.pack_propagate(False)

        left_brand = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_brand.pack(side="left", padx=14, pady=10)

        title = ctk.CTkLabel(
            left_brand,
            text="🧠 PERSISTENT Q&A MEMORY BANK",
            font=ctk.CTkFont(family="Consolas", size=16, weight="bold"),
            text_color=COLOR_CYAN
        )
        title.pack(side="left", padx=(0, 10))

        self.count_badge = ctk.CTkLabel(
            left_brand,
            text="● 0 SAVED MEMORIES",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_AZURE,
            fg_color="#081a3d",
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.count_badge.pack(side="left")

        # Right actions: Export and Import Backup
        right_actions = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_actions.pack(side="right", padx=14, pady=10)

        export_btn = ctk.CTkButton(
            right_actions,
            text="📥 Export Backup",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=115,
            height=30,
            fg_color="#0a193b",
            hover_color="#122554",
            border_color=COLOR_BORDER,
            border_width=1,
            text_color=COLOR_TEXT,
            command=self._handle_export_backup
        )
        export_btn.pack(side="left", padx=4)

        import_btn = ctk.CTkButton(
            right_actions,
            text="📤 Import Backup",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=115,
            height=30,
            fg_color="#0a193b",
            hover_color="#122554",
            border_color=COLOR_BORDER,
            border_width=1,
            text_color=COLOR_TEXT,
            command=self._handle_import_backup
        )
        import_btn.pack(side="left", padx=4)

    def _build_add_section(self):
        add_frame = ctk.CTkFrame(
            self,
            fg_color=COLOR_PANEL,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=12
        )
        add_frame.pack(fill="x", padx=16, pady=4)

        add_label = ctk.CTkLabel(
            add_frame,
            text="➕ TEACH JARVIS A NEW QUESTION & ANSWER",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_TEXT_DIM
        )
        add_label.pack(anchor="w", padx=14, pady=(10, 4))

        input_row = ctk.CTkFrame(add_frame, fg_color="transparent")
        input_row.pack(fill="x", padx=14, pady=(0, 10))

        self.q_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Question (e.g., 'Who is my best friend?' or 'What is my project name?')",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            height=36,
            fg_color="#040a1c",
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT
        )
        self.q_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.a_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Exact Answer (e.g., 'Rahul' or 'Nova')",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            height=36,
            fg_color="#040a1c",
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT
        )
        self.a_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        save_btn = ctk.CTkButton(
            input_row,
            text="💾 Save Memory",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            width=110,
            height=36,
            fg_color=COLOR_CYAN,
            hover_color="#00ccdd",
            text_color="#000000",
            corner_radius=8,
            command=self._handle_manual_save
        )
        save_btn.pack(side="left")

    def _build_search_bar(self):
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=16, pady=(6, 4))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Search saved questions, answers, or keywords...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            height=36,
            fg_color=COLOR_PANEL,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            corner_radius=8
        )
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_memory_list())

    def _build_list_container(self):
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            border_width=0
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=16, pady=(4, 14))

    def refresh_memory_list(self):
        """Re-render the scrollable cards for all matching memories."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        search_query = self.search_entry.get().strip() if hasattr(self, "search_entry") else ""
        memories = self.memory_mgr.list_all_memories(search_term=search_query)

        # Update counter badge
        total_count = self.memory_mgr.get_memory_count()
        self.count_badge.configure(text=f"● {total_count} SAVED MEMORIES")

        if not memories:
            empty_card = ctk.CTkFrame(
                self.scroll_frame,
                fg_color=COLOR_PANEL,
                border_color=COLOR_BORDER,
                border_width=1,
                corner_radius=12
            )
            empty_card.pack(fill="x", pady=20, padx=4)
            msg = "No saved memories found." if search_query else "No custom memories saved yet. Teach JARVIS above or by voice!"
            lbl = ctk.CTkLabel(
                empty_card,
                text=msg,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=COLOR_TEXT_DIM
            )
            lbl.pack(pady=30)
            return

        for mem in memories:
            self._render_memory_card(mem)

    def _render_memory_card(self, mem: dict):
        card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=COLOR_PANEL_ALT,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=10
        )
        card.pack(fill="x", pady=5, padx=2)

        content_box = ctk.CTkFrame(card, fg_color="transparent")
        content_box.pack(side="left", fill="both", expand=True, padx=14, pady=10)

        # Question Line
        q_label = ctk.CTkLabel(
            content_box,
            text=f"Q: {mem.get('question', '')}",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_CYAN,
            anchor="w",
            wraplength=520,
            justify="left"
        )
        q_label.pack(fill="x", anchor="w")

        # Answer Line
        a_label = ctk.CTkLabel(
            content_box,
            text=f"A: {mem.get('answer', '')}",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT,
            anchor="w",
            wraplength=520,
            justify="left"
        )
        a_label.pack(fill="x", anchor="w", pady=(2, 4))

        # Metadata Line (Created & Updated timestamps)
        c_time = mem.get("created_at", "")[:16].replace("T", " ")
        u_time = mem.get("updated_at", "")[:16].replace("T", " ")
        acc_cnt = mem.get("access_count", 0)
        meta_str = f"Saved: {c_time}  |  Updated: {u_time}  |  Accessed: {acc_cnt}x"
        meta_label = ctk.CTkLabel(
            content_box,
            text=meta_str,
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLOR_TEXT_MUTED,
            anchor="w"
        )
        meta_label.pack(fill="x", anchor="w")

        # Action Buttons (Edit / Delete)
        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.pack(side="right", padx=12, pady=10)

        edit_btn = ctk.CTkButton(
            btn_box,
            text="✏ Edit",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=65,
            height=28,
            fg_color="#0e234d",
            hover_color="#183674",
            text_color=COLOR_AZURE,
            corner_radius=6,
            command=lambda m=mem: self._open_edit_dialog(m)
        )
        edit_btn.pack(side="top", pady=(0, 4))

        del_btn = ctk.CTkButton(
            btn_box,
            text="🗑 Delete",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=65,
            height=28,
            fg_color="#2a0815",
            hover_color="#450d22",
            border_color=COLOR_RED,
            border_width=1,
            text_color=COLOR_RED,
            corner_radius=6,
            command=lambda m=mem: self._handle_delete_memory(m)
        )
        del_btn.pack(side="top")

    def _handle_manual_save(self):
        q = self.q_entry.get().strip()
        a = self.a_entry.get().strip()
        if not q or not a:
            messagebox.showwarning("Incomplete Entry", "Please provide both a Question and an Answer.")
            return

        ok, mem, code = self.memory_mgr.save_memory(q, a, allow_overwrite=False)
        if code == "DUPLICATE_EXISTS":
            res = messagebox.askyesno(
                "Duplicate Question",
                f"This question already exists with answer:\n'{mem['answer']}'\n\nDo you want to overwrite it with:\n'{a}'?"
            )
            if res:
                self.memory_mgr.update_memory(mem["id"], a, new_question=q)
                self.q_entry.delete(0, "end")
                self.a_entry.delete(0, "end")
                self.refresh_memory_list()
                if self.on_memory_changed:
                    self.on_memory_changed()
        elif ok:
            self.q_entry.delete(0, "end")
            self.a_entry.delete(0, "end")
            self.refresh_memory_list()
            if self.on_memory_changed:
                self.on_memory_changed()
        else:
            messagebox.showerror("Error", f"Failed to save memory: {code}")

    def _open_edit_dialog(self, mem: dict):
        edit_dialog = ctk.CTkToplevel(self)
        edit_dialog.title("Edit Custom Memory")
        edit_dialog.geometry("520x330")
        edit_dialog.configure(fg_color=COLOR_BG)
        edit_dialog.grab_set()

        title_lbl = ctk.CTkLabel(
            edit_dialog,
            text="✏ Edit Question & Answer",
            font=ctk.CTkFont(family="Consolas", size=15, weight="bold"),
            text_color=COLOR_CYAN
        )
        title_lbl.pack(pady=(16, 10))

        # Question Edit
        q_lbl = ctk.CTkLabel(edit_dialog, text="Question:", font=ctk.CTkFont(size=12, weight="bold"))
        q_lbl.pack(anchor="w", padx=20, pady=(4, 2))
        q_input = ctk.CTkEntry(edit_dialog, width=480, fg_color="#040a1c", border_color=COLOR_BORDER)
        q_input.insert(0, mem.get("question", ""))
        q_input.pack(padx=20, pady=(0, 8))

        # Answer Edit
        a_lbl = ctk.CTkLabel(edit_dialog, text="Answer:", font=ctk.CTkFont(size=12, weight="bold"))
        a_lbl.pack(anchor="w", padx=20, pady=(4, 2))
        a_input = ctk.CTkEntry(edit_dialog, width=480, fg_color="#040a1c", border_color=COLOR_BORDER)
        a_input.insert(0, mem.get("answer", ""))
        a_input.pack(padx=20, pady=(0, 14))

        def _save_edit():
            new_q = q_input.get().strip()
            new_a = a_input.get().strip()
            if not new_q or not new_a:
                messagebox.showwarning("Warning", "Question and answer cannot be empty.", parent=edit_dialog)
                return
            ok, msg = self.memory_mgr.update_memory(mem["id"], new_a, new_question=new_q)
            if ok:
                edit_dialog.destroy()
                self.refresh_memory_list()
                if self.on_memory_changed:
                    self.on_memory_changed()
            else:
                messagebox.showerror("Error", msg, parent=edit_dialog)

        save_btn = ctk.CTkButton(
            edit_dialog,
            text="Save Changes",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLOR_CYAN,
            text_color="#000000",
            hover_color="#00ccdd",
            command=_save_edit,
            width=140,
            height=34
        )
        save_btn.pack(pady=10)

    def _handle_delete_memory(self, mem: dict):
        res = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete this saved memory?\n\nQuestion: {mem.get('question', '')}\nAnswer: {mem.get('answer', '')}"
        )
        if res:
            ok, msg = self.memory_mgr.delete_memory(mem["id"])
            if ok:
                self.refresh_memory_list()
                if self.on_memory_changed:
                    self.on_memory_changed()
            else:
                messagebox.showerror("Error", msg)

    def _handle_export_backup(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_file = filedialog.asksaveasfilename(
            parent=self,
            title="Export JARVIS Memories Backup",
            defaultextension=".json",
            initialfile=f"jarvis_memory_backup_{ts}.json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if target_file:
            ok, path_or_err = self.memory_mgr.export_backup(target_file)
            if ok:
                messagebox.showinfo("Backup Exported", f"Successfully exported memories to:\n{path_or_err}")
            else:
                messagebox.showerror("Export Failed", f"Failed to export backup:\n{path_or_err}")

    def _handle_import_backup(self):
        source_file = filedialog.askopenfilename(
            parent=self,
            title="Select JARVIS Memory Backup File",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if source_file:
            res = messagebox.askyesno(
                "Merge or Replace",
                "Do you want to MERGE imported memories with existing ones?\n\n(Click 'Yes' to Merge, or 'No' to Replace existing memories)"
            )
            merge_choice = True if res else False
            ok, cnt, msg = self.memory_mgr.import_backup(source_file, merge=merge_choice)
            if ok:
                messagebox.showinfo("Import Complete", msg)
                self.refresh_memory_list()
                if self.on_memory_changed:
                    self.on_memory_changed()
            else:
                messagebox.showerror("Import Error", msg)
