import tkinter as tk
from tkinter import filedialog, messagebox, font
import puz
import os
import re
import html
import json

class CrosswordApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python .puz Solver - v22.1")
        self.root.geometry("1200x750")
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Game State
        self.puzzle = None
        self.width = 0
        self.height = 0
        self.solution_grid = [] 
        self.user_grid = []     
        self.grid_numbers = {}  
        self.clue_mapping = None
        self.is_redacted = False
        self.current_file_path = ""
        
        # Highlight State
        self.highlighted_ref_indices = set() 
        
        # Files
        self.favorites_file = "favorites.json"
        self.settings_file = "settings.json"
        self.saves_file = "saves.json"
        
        self.favorites = self.load_json(self.favorites_file, [])
        self.game_saves = self.load_json(self.saves_file, {})

        # Navigation State
        self.cursor_col = 0
        self.cursor_row = 0
        self.direction = 'across'
        
        # Settings
        self.var_error_check = tk.BooleanVar(value=True)
        self.var_skip_filled = tk.BooleanVar(value=True)
        self.var_end_behavior = tk.StringVar(value="next")
        self.var_dark_theme = tk.BooleanVar(value=True)
        self.var_ctrl_mode = tk.StringVar(value="letter") 
        self.var_ctrl_reveal = tk.BooleanVar(value=True)
        
        # Visuals
        self.cell_size = 35 
        self.clue_font_size = 10 
        self.sidebar_visible = False
        self.last_opened_file = ""
        self.c = {} 
        
        self.load_settings()

        # --- UI Layout ---
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open .puz File", command=self.browse_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        
        self.reveal_menu = tk.Menu(menubar, tearoff=0)
        self.reveal_menu.add_command(label="Reveal Current Word", command=self.reveal_current_word)
        self.reveal_menu.add_command(label="Reveal Puzzle", command=self.reveal_puzzle)
        self.reveal_menu.add_separator()
        self.reveal_menu.add_command(label="Reset Puzzle (Clear All)", command=self.reset_puzzle)
        menubar.add_cascade(label="Reveal", menu=self.reveal_menu)
        
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_checkbutton(label="Dark Theme", onvalue=True, offvalue=False,
                                     variable=self.var_dark_theme, command=self.apply_theme_and_save)
        options_menu.add_separator()
        options_menu.add_checkbutton(label="Error Check Mode", onvalue=True, offvalue=False, 
                                     variable=self.var_error_check, command=self.save_settings_trigger)
        options_menu.add_checkbutton(label="Skip Filled Squares", onvalue=True, offvalue=False, 
                                     variable=self.var_skip_filled, command=self.save_settings_trigger)
        
        ctrl_menu = tk.Menu(options_menu, tearoff=0)
        ctrl_menu.add_radiobutton(label="Reveal Letter", value="letter", variable=self.var_ctrl_mode, command=self.save_settings)
        ctrl_menu.add_radiobutton(label="Reveal Word", value="word", variable=self.var_ctrl_mode, command=self.save_settings)
        options_menu.add_cascade(label="Ctrl Key Behavior", menu=ctrl_menu)

        options_menu.add_separator()
        options_menu.add_radiobutton(label="At end of word: Jump to Next", value="next", variable=self.var_end_behavior, command=self.save_settings)
        options_menu.add_radiobutton(label="At end of word: Stay", value="stay", variable=self.var_end_behavior, command=self.save_settings)
        
        menubar.add_cascade(label="Options", menu=options_menu)
        self.root.config(menu=menubar)

        # Top Toolbar
        self.top_frame = tk.Frame(self.root, pady=8, padx=10, relief=tk.RIDGE, borderwidth=1)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)
        
        self.btn_sidebar = tk.Button(self.top_frame, text="📂 Files", command=self.toggle_sidebar, relief=tk.GROOVE)
        self.btn_sidebar.pack(side=tk.LEFT, padx=(0, 15))

        self.lbl_filename = tk.Label(self.top_frame, text="No File Selected", font=("Helvetica", 12, "bold", "italic"))
        self.lbl_filename.pack(side=tk.LEFT)
        
        # Zoom
        self.btn_text_plus = tk.Button(self.top_frame, text=" + ", command=lambda: self.change_text_zoom(1), font=("Arial", 9, "bold"), width=2, takefocus=0)
        self.btn_text_plus.pack(side=tk.RIGHT, padx=2)
        self.btn_text_minus = tk.Button(self.top_frame, text=" - ", command=lambda: self.change_text_zoom(-1), font=("Arial", 9, "bold"), width=2, takefocus=0)
        self.btn_text_minus.pack(side=tk.RIGHT, padx=2)
        tk.Label(self.top_frame, text="Text:", font=("Arial", 10)).pack(side=tk.RIGHT, padx=(10, 2))

        self.btn_grid_plus = tk.Button(self.top_frame, text=" + ", command=lambda: self.change_grid_zoom(5), font=("Arial", 9, "bold"), width=2, takefocus=0)
        self.btn_grid_plus.pack(side=tk.RIGHT, padx=2)
        self.btn_grid_minus = tk.Button(self.top_frame, text=" - ", command=lambda: self.change_grid_zoom(-5), font=("Arial", 9, "bold"), width=2, takefocus=0)
        self.btn_grid_minus.pack(side=tk.RIGHT, padx=2)
        tk.Label(self.top_frame, text="Grid:", font=("Arial", 10)).pack(side=tk.RIGHT, padx=(10, 2))

        self.lbl_current_clue = tk.Label(self.top_frame, text="", font=("Helvetica", 12, "bold"), wraplength=500)
        self.lbl_current_clue.pack(side=tk.RIGHT, fill=tk.X, padx=15)

        # Main Layout
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=6)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Sidebar
        self.sidebar_frame = tk.Frame(self.main_paned, relief=tk.SUNKEN, borderwidth=1, width=200)
        self.sidebar_label = tk.Label(self.sidebar_frame, text="Folder Content", font=("Arial", 9, "bold"))
        self.sidebar_label.pack(fill=tk.X, pady=2)
        
        self.file_listbox = tk.Listbox(self.sidebar_frame, font=("Arial", 9), borderwidth=0)
        self.file_listbox.pack(expand=True, fill=tk.BOTH, padx=2, pady=2)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="⭐ Add/Remove Favorite", command=self.toggle_favorite)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Delete File", command=self.delete_file)
        
        self.file_listbox.bind("<Button-3>", self.show_context_menu)
        self.file_listbox.bind("<space>", self.block_listbox_space) 
        
        # Game
        self.game_paned = tk.PanedWindow(self.main_paned, orient=tk.HORIZONTAL, sashwidth=6)
        
        self.grid_frame = tk.Frame(self.game_paned)
        self.canvas = tk.Canvas(self.grid_frame, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.clues_frame = tk.Frame(self.game_paned)
        
        # Across
        self.lbl_across = tk.Label(self.clues_frame, text="Across", font=("Helvetica", 12, "bold"))
        self.lbl_across.pack(side=tk.TOP, anchor="w")
        
        frame_across = tk.Frame(self.clues_frame)
        frame_across.pack(side=tk.TOP, expand=True, fill=tk.BOTH, pady=(0, 10))
        sb_across = tk.Scrollbar(frame_across)
        sb_across.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_across = tk.Text(frame_across, wrap=tk.WORD, state=tk.DISABLED, cursor="arrow", yscrollcommand=sb_across.set, height=10)
        self.txt_across.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        sb_across.config(command=self.txt_across.yview)

        # Down
        self.lbl_down = tk.Label(self.clues_frame, text="Down", font=("Helvetica", 12, "bold"))
        self.lbl_down.pack(side=tk.TOP, anchor="w")
        
        frame_down = tk.Frame(self.clues_frame)
        frame_down.pack(side=tk.TOP, expand=True, fill=tk.BOTH)
        sb_down = tk.Scrollbar(frame_down)
        sb_down.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_down = tk.Text(frame_down, wrap=tk.WORD, state=tk.DISABLED, cursor="arrow", yscrollcommand=sb_down.set, height=10)
        self.txt_down.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        sb_down.config(command=self.txt_down.yview)

        # Tags
        for txt in [self.txt_across, self.txt_down]:
            txt.tag_config("highlight", background="#E1F5FE") 
            txt.tag_config("default", background="white")

        self.main_paned.add(self.game_paned)
        self.game_paned.add(self.grid_frame, minsize=400)
        self.game_paned.add(self.clues_frame, minsize=200)

        # Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.root.bind("<Key>", self.handle_keypress)
        
        self.root.bind("<Tab>", self.handle_tab)
        self.root.bind("<Shift-Tab>", self.handle_shift_tab)
        
        self.root.bind("<Control_L>", self.handle_ctrl_key)
        self.root.bind("<Control_R>", self.handle_ctrl_key)
        self.root.bind("<Button-1>", lambda e: self.canvas.focus_set())

        self.apply_theme()
        if self.last_opened_file and os.path.exists(self.last_opened_file):
            self.load_puz_file(self.last_opened_file)

    # --- Persistence ---
    def load_json(self, filepath, default):
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f: return json.load(f)
            except: return default
        return default

    def save_json(self, filepath, data):
        try:
            with open(filepath, 'w') as f: json.dump(data, f)
        except: pass

    def on_close(self):
        self.save_current_progress()
        self.save_settings()
        self.root.destroy()

    def save_current_progress(self):
        if self.puzzle and self.current_file_path:
            self.game_saves[self.current_file_path] = self.user_grid
            self.save_json(self.saves_file, self.game_saves)

    def load_settings(self):
        data = self.load_json(self.settings_file, {})
        if not data: return
        self.var_dark_theme.set(data.get("dark_theme", True))
        self.var_error_check.set(data.get("error_check", True))
        self.var_ctrl_mode.set(data.get("ctrl_mode", "letter"))
        self.var_skip_filled.set(data.get("skip_filled", True))
        self.var_end_behavior.set(data.get("end_behavior", "next"))
        self.cell_size = data.get("cell_size", 35)
        self.clue_font_size = data.get("clue_font_size", 10)
        self.last_opened_file = data.get("last_file", "")
        geom = data.get("geometry", "1200x750")
        try: self.root.geometry(geom)
        except: pass

    def save_settings(self):
        data = {
            "dark_theme": self.var_dark_theme.get(),
            "error_check": self.var_error_check.get(),
            "ctrl_mode": self.var_ctrl_mode.get(),
            "skip_filled": self.var_skip_filled.get(),
            "end_behavior": self.var_end_behavior.get(),
            "cell_size": self.cell_size,
            "clue_font_size": self.clue_font_size,
            "geometry": self.root.geometry(),
            "last_file": self.current_file_path
        }
        self.save_json(self.settings_file, data)

    def save_settings_trigger(self):
        self.refresh_grid()
        self.save_settings()

    def apply_theme_and_save(self):
        self.apply_theme()
        self.save_settings()

    # --- Handlers ---
    def handle_tab(self, event):
        if event.state & 0x0001:
            self.jump_to_next_word(forward=False, skip_full_words=True)
        else:
            self.jump_to_next_word(forward=True, skip_full_words=True)
        return "break"

    def handle_shift_tab(self, event):
        self.jump_to_next_word(forward=False, skip_full_words=True)
        return "break"

    def handle_ctrl_key(self, event):
        if self.var_ctrl_mode.get() == "word":
            self.reveal_current_word()
            # FORCE jump to next word immediately after revealing
            self.jump_to_next_word(forward=True, skip_full_words=True)
        else:
            self.reveal_current_letter(event)
        return "break"

    def block_listbox_space(self, event):
        self.canvas.focus_set()
        self.direction = 'down' if self.direction == 'across' else 'across'
        self.refresh_grid()
        self.update_clue_display()
        return "break"

    def show_context_menu(self, event):
        try:
            self.file_listbox.selection_clear(0, tk.END)
            self.file_listbox.selection_set(self.file_listbox.nearest(event.y))
            self.file_listbox.activate(self.file_listbox.nearest(event.y))
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def get_selected_file_path(self):
        selection = self.file_listbox.curselection()
        if not selection: return None
        filename = self.file_listbox.get(selection[0])
        if filename.startswith("⭐ "):
            filename = filename.replace("⭐ ", "")
        if self.current_file_path:
            return os.path.join(os.path.dirname(self.current_file_path), filename)
        return None

    def toggle_favorite(self):
        path = self.get_selected_file_path()
        if not path: return
        path = os.path.abspath(path)
        if path in self.favorites:
            self.favorites.remove(path)
        else:
            self.favorites.append(path)
        self.save_json(self.favorites_file, self.favorites)
        if self.current_file_path:
            self.update_sidebar(os.path.dirname(self.current_file_path))

    def delete_file(self):
        path = self.get_selected_file_path()
        if not path: return
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete:\n{os.path.basename(path)}?"):
            try:
                os.remove(path)
                abs_path = os.path.abspath(path)
                if abs_path in self.favorites:
                    self.favorites.remove(abs_path)
                    self.save_json(self.favorites_file, self.favorites)
                if self.current_file_path:
                    self.update_sidebar(os.path.dirname(self.current_file_path))
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete file: {e}")

    # --- Zoom & Theme ---
    def define_colors(self):
        if self.var_dark_theme.get():
            self.c = {
                'bg': '#333333',
                'fg': 'white',
                'panel_bg': '#333333',
                'input_bg': '#333333',
                'grid_bg': '#757575',
                'grid_fg': '#FFFFFF',
                'grid_num': '#E0E0E0',
                'black_sq': '#333333',
                'cursor': '#d19e44',
                'highlight': '#506880',
                'ref_highlight': '#554466',
                'error': '#FF5555',
                'sash': '#444444',
                'completed': '#888888',
                'ref_text': '#A480CF',
                'btn_bg': '#444444',
                'btn_fg': 'white'
            }
        else:
            self.c = {
                'bg': 'white',
                'fg': 'black',
                'panel_bg': '#f8f9fa',
                'input_bg': 'white',
                'grid_bg': 'white',
                'grid_fg': 'black',
                'grid_num': '#222222',
                'black_sq': 'black',
                'cursor': '#FFEB3B',
                'highlight': '#E1F5FE',
                'ref_highlight': '#F3E5F5',
                'error': 'red',
                'sash': '#cccccc',
                'completed': '#999999',
                'ref_text': '#673AB7',
                'btn_bg': '#e9ecef',
                'btn_fg': 'black'
            }

    def apply_theme(self):
        self.define_colors()
        c = self.c
        self.root.config(bg=c['bg'])
        self.top_frame.config(bg=c['panel_bg'])
        self.main_paned.config(bg=c['sash'])
        self.game_paned.config(bg=c['sash'])
        
        self.sidebar_frame.config(bg=c['input_bg'])
        self.sidebar_label.config(bg=c['input_bg'], fg=c['fg'])
        self.file_listbox.config(bg=c['input_bg'], fg=c['fg'], selectbackground=c['highlight'], selectforeground=c['fg'])
        
        for lbl in [self.lbl_filename, self.lbl_current_clue, self.lbl_across, self.lbl_down]:
            lbl.config(bg=c['panel_bg'], fg=c['fg'])
        for btn in [self.btn_sidebar, self.btn_text_plus, self.btn_text_minus, self.btn_grid_plus, self.btn_grid_minus]:
            btn.config(bg=c['btn_bg'], fg=c['btn_fg'])

        self.grid_frame.config(bg=c['bg'])
        self.canvas.config(bg=c['bg'])
        self.clues_frame.config(bg=c['bg'])
        
        clue_font = ("Arial", self.clue_font_size)
        for txt in [self.txt_across, self.txt_down]:
            txt.config(bg=c['input_bg'], fg=c['fg'], selectbackground=c['highlight'], font=clue_font)
            txt.tag_config("highlight", background=c['highlight'])
            txt.tag_config("completed", foreground=c['completed'])
            txt.tag_config("ref", foreground=c['ref_text'], font=("Arial", self.clue_font_size, "bold"))
            txt.tag_config("default", background=c['input_bg'], foreground=c['fg'])
            
        self.refresh_grid()
        self.update_clue_display()

    def change_grid_zoom(self, delta):
        new_cell = self.cell_size + delta
        if 20 <= new_cell <= 100:
            self.cell_size = new_cell
            self.refresh_grid()
            self.save_settings()

    def change_text_zoom(self, delta):
        new_font = self.clue_font_size + delta
        if 8 <= new_font <= 24:
            self.clue_font_size = new_font
            self.apply_theme()
            self.save_settings()

    def clean_clue_text(self, text):
        if not text: return ""
        text = re.sub(r'<[^>]+>', '', text)
        text = html.unescape(text)
        return text

    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Puzzle Files", "*.puz"), ("All Files", "*.*")])
        if filename: self.load_puz_file(filename)

    def load_puz_file(self, filename):
        try:
            self.save_current_progress()
            self.puzzle = puz.read(filename)
            self.current_file_path = filename
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file.\n\nDetails: {e}")
            return

        base_name = os.path.basename(filename)
        self.lbl_filename.config(text=base_name)
        self.update_sidebar(os.path.dirname(filename))

        self.width = self.puzzle.width
        self.height = self.puzzle.height
        self.solution_grid = list(self.puzzle.solution)
        
        self.is_redacted = False
        x_count = self.solution_grid.count('X') + self.solution_grid.count('x')
        if (len(self.solution_grid) - self.solution_grid.count('.')) > 0 and (x_count / (len(self.solution_grid) - self.solution_grid.count('.'))) > 0.8:
            self.is_redacted = True
            self.var_error_check.set(False)

        if self.current_file_path in self.game_saves:
            saved_grid = self.game_saves[self.current_file_path]
            if len(saved_grid) == len(self.solution_grid):
                self.user_grid = saved_grid
            else:
                self.user_grid = ['-' if c != '.' else '.' for c in self.solution_grid]
        else:
            self.user_grid = ['-' if c != '.' else '.' for c in self.solution_grid]
        
        self.canvas.config(width=self.width * self.cell_size, height=self.height * self.cell_size)
        self.parse_clues()
        self.cursor_col = 0
        self.cursor_row = 0
        self.direction = 'across'
        self.find_first_valid_cell()
        
        self.refresh_grid()
        self.update_clue_display()
        self.refresh_grid() 
        
        self.save_settings()
        if not self.sidebar_visible: self.toggle_sidebar()

    def reset_puzzle(self):
        if not self.puzzle: return
        if messagebox.askyesno("Reset Puzzle", "Are you sure you want to clear all progress?\nThis cannot be undone."):
            self.user_grid = ['-' if c != '.' else '.' for c in self.solution_grid]
            self.cursor_col = 0
            self.cursor_row = 0
            self.find_first_valid_cell()
            self.refresh_grid()
            self.update_clue_display()
            self.save_current_progress()

    def update_sidebar(self, folder_path):
        self.file_listbox.delete(0, tk.END)
        try:
            files = [f for f in os.listdir(folder_path) if f.lower().endswith('.puz')]
            files.sort()
            for f in files:
                full_p = os.path.abspath(os.path.join(folder_path, f))
                display_name = "⭐ " + f if full_p in self.favorites else f
                self.file_listbox.insert(tk.END, display_name)
            current_name = os.path.basename(self.current_file_path)
            for i in range(self.file_listbox.size()):
                item = self.file_listbox.get(i)
                if item == current_name or item == "⭐ " + current_name:
                    self.file_listbox.selection_set(i)
                    self.file_listbox.see(i)
                    break
        except: pass

    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.main_paned.remove(self.sidebar_frame)
            self.sidebar_visible = False
            self.btn_sidebar.config(relief=tk.GROOVE)
        else:
            self.main_paned.add(self.sidebar_frame, before=self.game_paned, width=200)
            self.sidebar_visible = True
            self.btn_sidebar.config(relief=tk.SUNKEN)

    def on_file_select(self, event):
        selection = self.file_listbox.curselection()
        if not selection: return
        filename = self.file_listbox.get(selection[0])
        if filename.startswith("⭐ "): filename = filename.replace("⭐ ", "")
        full_path = os.path.join(os.path.dirname(self.current_file_path), filename)
        if full_path != self.current_file_path: self.load_puz_file(full_path)
        self.canvas.focus_set()

    def parse_clues(self):
        self.clue_mapping = self.puzzle.clue_numbering()
        self.grid_numbers = {}
        self.txt_across.config(state=tk.NORMAL)
        self.txt_across.delete(1.0, tk.END)
        for clue in self.clue_mapping.across:
            r = clue['cell'] // self.width
            c = clue['cell'] % self.width
            self.grid_numbers[(c, r)] = clue['num']
            clean_text = self.clean_clue_text(clue['clue'])
            tag = f"across_{clue['num']}"
            self.txt_across.insert(tk.END, f"{clue['num']}. {clean_text}\n", tag)
            self.txt_across.tag_bind(tag, "<Button-1>", lambda e, num=clue['num']: self.click_clue_text(num, 'across'))
        self.txt_across.config(state=tk.DISABLED)

        self.txt_down.config(state=tk.NORMAL)
        self.txt_down.delete(1.0, tk.END)
        for clue in self.clue_mapping.down:
            r = clue['cell'] // self.width
            c = clue['cell'] % self.width
            self.grid_numbers[(c, r)] = clue['num']
            clean_text = self.clean_clue_text(clue['clue'])
            tag = f"down_{clue['num']}"
            self.txt_down.insert(tk.END, f"{clue['num']}. {clean_text}\n", tag)
            self.txt_down.tag_bind(tag, "<Button-1>", lambda e, num=clue['num']: self.click_clue_text(num, 'down'))
        self.txt_down.config(state=tk.DISABLED)

    def click_clue_text(self, num, direction):
        target_list = self.clue_mapping.across if direction == 'across' else self.clue_mapping.down
        for clue in target_list:
            if clue['num'] == num:
                self.cursor_row = clue['cell'] // self.width
                self.cursor_col = clue['cell'] % self.width
                self.direction = direction
                self.update_clue_display()
                self.refresh_grid()
                return

    def find_first_valid_cell(self):
        for i, char in enumerate(self.solution_grid):
            if char != '.':
                self.cursor_row = i // self.width
                self.cursor_col = i % self.width
                break

    def get_index(self, col, row):
        return row * self.width + col

    # --- Grid Logic with Ref Highlighting ---
    def refresh_grid(self):
        if not self.puzzle: return
        self.canvas.delete("all")
        self.canvas.config(width=self.width * self.cell_size, height=self.height * self.cell_size)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        c = self.c 
        fnt_num = font.Font(family="Arial", size=int(self.cell_size*0.28))
        fnt_char = font.Font(family="Helvetica", size=int(self.cell_size*0.55), weight="normal")

        for r in range(self.height):
            for c_idx in range(self.width):
                x1 = c_idx * self.cell_size
                y1 = r * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                
                idx = self.get_index(c_idx, r)
                cell_val = self.user_grid[idx]
                sol_val = self.solution_grid[idx]
                
                bg_color = c['grid_bg']
                if sol_val == '.':
                    bg_color = c['black_sq']
                elif r == self.cursor_row and c_idx == self.cursor_col:
                    bg_color = c['cursor']
                elif self.is_highlighted(c_idx, r):
                    bg_color = c['highlight']
                elif idx in self.highlighted_ref_indices:
                    bg_color = c['ref_highlight']
                
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg_color, outline="#555555")

                if (c_idx, r) in self.grid_numbers:
                    self.canvas.create_text(x1+2, y1+1, anchor="nw", text=str(self.grid_numbers[(c_idx,r)]), font=fnt_num, fill=c['grid_num'])

                if cell_val not in ['-', '.']:
                    text_color = c['grid_fg']
                    if self.var_error_check.get() and not self.is_redacted:
                        if cell_val != sol_val:
                            text_color = c['error']
                    
                    self.canvas.create_text(x1 + self.cell_size/2, y1 + self.cell_size/2 + 2, 
                                            text=cell_val, font=fnt_char, fill=text_color)
        self.check_completed_clues()

    def check_completed_clues(self):
        if not self.puzzle: return
        def check_list(clue_list, direction):
            txt_widget = self.txt_across if direction == 'across' else self.txt_down
            for clue in clue_list:
                start_cell = clue['cell']
                r = start_cell // self.width
                c = start_cell % self.width
                is_filled = True
                curr_r, curr_c = r, c
                while 0 <= curr_r < self.height and 0 <= curr_c < self.width:
                    idx = self.get_index(curr_c, curr_r)
                    if self.solution_grid[idx] == '.': break
                    if self.user_grid[idx] in ['-', '.']:
                        is_filled = False
                        break
                    if direction == 'across': curr_c += 1
                    else: curr_r += 1
                tag_name = f"{direction}_{clue['num']}"
                ranges = txt_widget.tag_ranges(tag_name)
                if ranges:
                    if is_filled: txt_widget.tag_add("completed", ranges[0], ranges[1])
                    else: txt_widget.tag_remove("completed", ranges[0], ranges[1])
        check_list(self.clue_mapping.across, 'across')
        check_list(self.clue_mapping.down, 'down')

    def is_highlighted(self, col, row):
        if self.solution_grid[self.get_index(col, row)] == '.': return False
        if self.direction == 'across':
            if row != self.cursor_row: return False
            start_c = self.cursor_col
            while start_c > 0 and self.solution_grid[self.get_index(start_c-1, row)] != '.': start_c -= 1
            end_c = self.cursor_col
            while end_c < self.width - 1 and self.solution_grid[self.get_index(end_c+1, row)] != '.': end_c += 1
            return start_c <= col <= end_c
        else:
            if col != self.cursor_col: return False
            start_r = self.cursor_row
            while start_r > 0 and self.solution_grid[self.get_index(col, start_r-1)] != '.': start_r -= 1
            end_r = self.cursor_row
            while end_r < self.height - 1 and self.solution_grid[self.get_index(col, end_r+1)] != '.': end_r += 1
            return start_r <= row <= end_r

    def is_locked(self, idx):
        return self.var_error_check.get() and not self.is_redacted and self.user_grid[idx] == self.solution_grid[idx]

    def get_word_range(self, c, r, direction):
        if direction == 'across':
            start_c = c
            while start_c > 0 and self.solution_grid[self.get_index(start_c-1, r)] != '.': start_c -= 1
            end_c = c
            while end_c < self.width - 1 and self.solution_grid[self.get_index(end_c+1, r)] != '.': end_c += 1
            return [(col, r) for col in range(start_c, end_c + 1)]
        else:
            start_r = r
            while start_r > 0 and self.solution_grid[self.get_index(c, start_r-1)] != '.': start_r -= 1
            end_r = r
            while end_r < self.height - 1 and self.solution_grid[self.get_index(c, end_r+1)] != '.': end_r += 1
            return [(c, row) for row in range(start_r, end_r + 1)]

    def is_word_locked(self, c, r, direction):
        if not self.var_error_check.get() or self.is_redacted: return False
        coords = self.get_word_range(c, r, direction)
        for col, row in coords:
            idx = self.get_index(col, row)
            if self.user_grid[idx] != self.solution_grid[idx]: return False
        return True

    def handle_keypress(self, event):
        if not self.puzzle: return
        key = event.keysym
        
        is_shift = (event.state & 0x0001) or (event.state & 1)

        if event.state & 0x0004: return "break"
        if "Control" in key or "Alt" in key: return 

        if key == "Left": self.move_vector_jump(0, -1)
        elif key == "Right": self.move_vector_jump(0, 1)
        elif key == "Up": self.move_vector_jump(-1, 0)
        elif key == "Down": self.move_vector_jump(1, 0)
        elif key == "space":
            self.direction = 'down' if self.direction == 'across' else 'across'
            self.update_clue_display()
            self.refresh_grid()
        elif key == "BackSpace":
            # Shift-Backspace
            if is_shift:
                self.jump_to_next_word(forward=False, skip_full_words=True)
                return "break"

            if self.is_word_locked(self.cursor_col, self.cursor_row, self.direction):
                self.jump_to_next_word(forward=False, skip_full_words=True)
                return "break"
            
            idx = self.get_index(self.cursor_col, self.cursor_row)
            if not self.is_locked(idx): self.user_grid[idx] = '-'
            
            # --- FIXED BACKSPACE MOVEMENT LOGIC ---
            dr, dc = (0, -1) if self.direction == 'across' else (-1, 0)
            nr, nc = self.cursor_row + dr, self.cursor_col + dc
            
            # Check bounds and if previous is black square
            if 0 <= nr < self.height and 0 <= nc < self.width:
                if self.solution_grid[self.get_index(nc, nr)] != '.':
                    self.cursor_row, self.cursor_col = nr, nc
                    self.update_clue_display()
            # If hit black square or wall, DO NOT move (stay on current empty cell)
            
            self.refresh_grid()
        elif key == "Delete":
            idx = self.get_index(self.cursor_col, self.cursor_row)
            if not self.is_locked(idx):
                self.user_grid[idx] = '-'
                self.refresh_grid()
        elif len(event.char) == 1 and event.char.isalpha():
            char = event.char.upper()
            idx = self.get_index(self.cursor_col, self.cursor_row)
            if not self.is_locked(idx):
                self.user_grid[idx] = char
                self.refresh_grid()
            self.step_forward()
        return "break"

    def move_smart(self, dr, dc):
        r, c = self.cursor_row, self.cursor_col
        while True:
            r += dr
            c += dc
            if c < 0: r, c = r - 1, self.width - 1
            elif c >= self.width: r, c = r + 1, 0
            if r < 0: r, c = self.height - 1, self.width - 1
            elif r >= self.height: r, c = 0, 0
            idx = self.get_index(c, r)
            if self.solution_grid[idx] != '.':
                self.cursor_row, self.cursor_col = r, c
                self.update_clue_display()
                self.refresh_grid()
                return
            if r == self.cursor_row and c == self.cursor_col: break

    def move_vector_jump(self, dr, dc):
        r, c = self.cursor_row, self.cursor_col
        nr, nc = r + dr, c + dc
        hit_barrier = False
        if not (0 <= nr < self.height and 0 <= nc < self.width): hit_barrier = True
        elif self.solution_grid[self.get_index(nc, nr)] == '.': hit_barrier = True

        if hit_barrier:
            search_r, search_c = nr, nc
            while True:
                search_r += dr
                search_c += dc
                if not (0 <= search_r < self.height and 0 <= search_c < self.width): break
                idx = self.get_index(search_c, search_r)
                if self.solution_grid[idx] != '.':
                    self.cursor_row, self.cursor_col = search_r, search_c
                    self.update_clue_display()
                    self.refresh_grid()
                    return
            self.move_smart(dr, dc)
        else:
            self.cursor_row, self.cursor_col = nr, nc
            self.update_clue_display()
            self.refresh_grid()

    def reveal_current_letter(self, event):
        if not self.puzzle: return
        if not self.var_ctrl_reveal.get(): return
        if self.is_redacted: return
        idx = self.get_index(self.cursor_col, self.cursor_row)
        correct_char = self.solution_grid[idx]
        if correct_char == '.': return
        self.user_grid[idx] = correct_char
        self.refresh_grid()
        self.step_forward()
        return "break"

    def reveal_current_word(self):
        if not self.puzzle: return
        if self.is_redacted:
            messagebox.showinfo("Cannot Reveal", "Hidden answers.")
            return
        r, c = self.cursor_row, self.cursor_col
        if self.direction == 'across':
            start_c = c
            while start_c > 0 and self.solution_grid[self.get_index(start_c-1, r)] != '.': start_c -= 1
            end_c = c
            while end_c < self.width - 1 and self.solution_grid[self.get_index(end_c+1, r)] != '.': end_c += 1
            for col in range(start_c, end_c + 1):
                self.user_grid[self.get_index(col, r)] = self.solution_grid[self.get_index(col, r)]
        else:
            start_r = r
            while start_r > 0 and self.solution_grid[self.get_index(c, start_r-1)] != '.': start_r -= 1
            end_r = r
            while end_r < self.height - 1 and self.solution_grid[self.get_index(c, end_r+1)] != '.': end_r += 1
            for row in range(start_r, end_r + 1):
                self.user_grid[self.get_index(c, row)] = self.solution_grid[self.get_index(c, row)]
        self.refresh_grid()

    def reveal_puzzle(self):
        if not self.puzzle: return
        if self.is_redacted:
            messagebox.showinfo("Cannot Reveal", "Hidden answers.")
            return
        if messagebox.askyesno("Reveal Puzzle", "Are you sure you want to reveal the entire puzzle?"):
            self.user_grid = list(self.solution_grid)
            self.refresh_grid()

    def move_cursor(self, dr, dc):
        new_r = self.cursor_row + dr
        new_c = self.cursor_col + dc
        if 0 <= new_r < self.height and 0 <= new_c < self.width:
            if self.solution_grid[self.get_index(new_c, new_r)] != '.':
                self.cursor_row = new_r
                self.cursor_col = new_c
                self.refresh_grid()
                self.update_clue_display()

    def step_forward(self):
        dr, dc = (0, 1) if self.direction == 'across' else (1, 0)
        r, c = self.cursor_row, self.cursor_col
        while True:
            r += dr
            c += dc
            hit_block = False
            if not (0 <= r < self.height and 0 <= c < self.width): hit_block = True
            elif self.solution_grid[self.get_index(c, r)] == '.': hit_block = True
            if hit_block:
                if self.var_end_behavior.get() == "next": self.jump_to_next_word(forward=True, skip_full_words=True)
                return
            idx = self.get_index(c, r)
            if self.var_skip_filled.get() and self.user_grid[idx] not in ['-', '.']: continue
            else:
                self.cursor_row, self.cursor_col = r, c
                self.refresh_grid()
                self.update_clue_display()
                return

    def jump_to_next_word(self, forward=True, visited_indices=None, skip_full_words=False):
        if not self.puzzle: return
        current_idx = self.get_index(self.cursor_col, self.cursor_row)
        if visited_indices is None: visited_indices = {current_idx}
        start_idx = current_idx
        if self.direction == 'across':
            c = self.cursor_col
            while c >= 0 and self.solution_grid[self.get_index(c, self.cursor_row)] != '.':
                start_idx = self.get_index(c, self.cursor_row)
                c -= 1
            current_list = self.clue_mapping.across
            next_list = self.clue_mapping.down
            next_direction = 'down'
        else: 
            r = self.cursor_row
            while r >= 0 and self.solution_grid[self.get_index(self.cursor_col, r)] != '.':
                start_idx = self.get_index(self.cursor_col, r)
                r -= 1
            current_list = self.clue_mapping.down
            next_list = self.clue_mapping.across
            next_direction = 'across'
        current_clue_index = -1
        for i, clue in enumerate(current_list):
            if clue['cell'] == start_idx:
                current_clue_index = i
                break
        next_clue = None
        if forward:
            if current_clue_index != -1 and current_clue_index < len(current_list) - 1:
                next_clue = current_list[current_clue_index + 1]
            else:
                if len(next_list) > 0:
                    next_clue = next_list[0]
                    self.direction = next_direction 
                else:
                    if len(current_list) > 0: next_clue = current_list[0]
        else:
            if current_clue_index > 0:
                next_clue = current_list[current_clue_index - 1]
            else:
                if len(next_list) > 0:
                    next_clue = next_list[-1]
                    self.direction = next_direction
                else:
                    if len(current_list) > 0: next_clue = current_list[-1]
        if next_clue:
            start = next_clue['cell']
            nr, nc = start // self.width, start % self.width
            if skip_full_words and self.is_word_locked(nc, nr, self.direction):
                new_idx = start
                if new_idx not in visited_indices:
                    self.cursor_row, self.cursor_col = nr, nc
                    visited_indices.add(new_idx)
                    self.jump_to_next_word(forward, visited_indices, skip_full_words)
                    return
            self.cursor_row = nr
            self.cursor_col = nc
            self.refresh_grid()
            self.update_clue_display()
            if self.var_skip_filled.get():
                dr, dc = (0, 1) if self.direction == 'across' else (1, 0)
                temp_r, temp_c = self.cursor_row, self.cursor_col
                idx = self.get_index(temp_c, temp_r)
                if self.user_grid[idx] in ['-', '.']: return
                found_empty = False
                while True:
                    next_r, next_c = temp_r + dr, temp_c + dc
                    if not (0 <= next_r < self.height and 0 <= next_c < self.width) or \
                       self.solution_grid[self.get_index(next_c, next_r)] == '.': break
                    idx_next = self.get_index(next_c, next_r)
                    if self.user_grid[idx_next] in ['-', '.']:
                        self.cursor_row = next_r
                        self.cursor_col = next_c
                        found_empty = True
                        break
                    temp_r, temp_c = next_r, next_c
                if found_empty:
                    self.refresh_grid()
                    self.update_clue_display()
                else:
                    pass
            
    def on_click(self, event):
        if not self.puzzle: return
        c = event.x // self.cell_size
        r = event.y // self.cell_size
        if 0 <= c < self.width and 0 <= r < self.height:
            if self.solution_grid[self.get_index(c, r)] == '.': return
            if c == self.cursor_col and r == self.cursor_row:
                self.direction = 'down' if self.direction == 'across' else 'across'
            else:
                self.cursor_col = c
                self.cursor_row = r
            self.update_clue_display() 
            self.refresh_grid() 

    def update_clue_display(self):
        if not self.puzzle: return
        current_idx = self.get_index(self.cursor_col, self.cursor_row)
        start_idx = current_idx
        if self.direction == 'across':
            c = self.cursor_col
            while c >= 0 and self.solution_grid[self.get_index(c, self.cursor_row)] != '.':
                start_idx = self.get_index(c, self.cursor_row)
                c -= 1
        else:
            r = self.cursor_row
            while r >= 0 and self.solution_grid[self.get_index(self.cursor_col, r)] != '.':
                start_idx = self.get_index(self.cursor_col, r)
                r -= 1
        
        target_list = self.clue_mapping.across if self.direction == 'across' else self.clue_mapping.down
        found_clue = ""
        found_clue_text = ""
        clue_num = -1
        for clue in target_list:
            if clue['cell'] == start_idx:
                found_clue_text = self.clean_clue_text(clue['clue'])
                found_clue = f"{clue['num']}. {found_clue_text}"
                clue_num = clue['num']
                break
        
        self.lbl_current_clue.config(text=found_clue)
        self.highlight_text_widget(self.txt_across, clue_num, self.direction == 'across')
        self.highlight_text_widget(self.txt_down, clue_num, self.direction == 'down')
        
        self.txt_across.tag_remove("ref", "1.0", tk.END)
        self.txt_down.tag_remove("ref", "1.0", tk.END)
        self.highlighted_ref_indices.clear()
        
        if found_clue_text:
            explicit_refs = re.findall(r'(\d+)-(Across|Down)', found_clue_text, re.IGNORECASE)
            for num_str, direction_str in explicit_refs:
                d = direction_str.lower()
                n = int(num_str)
                target = self.txt_across if d == 'across' else self.txt_down
                self.highlight_ref_text(target, d, n)
                self.highlight_ref_grid(n, d)

            potential_refs = re.findall(r'(\d+)-', found_clue_text)
            context_across = "across" in found_clue_text.lower()
            context_down = "down" in found_clue_text.lower()
            
            for num_str in potential_refs:
                n = int(num_str)
                is_across = any(c['num'] == n for c in self.clue_mapping.across)
                is_down = any(c['num'] == n for c in self.clue_mapping.down)
                final_dir = None
                if context_across and is_across: final_dir = 'across'
                elif context_down and is_down: final_dir = 'down'
                elif is_across and not is_down: final_dir = 'across'
                elif is_down and not is_across: final_dir = 'down'
                
                if final_dir:
                    target = self.txt_across if final_dir == 'across' else self.txt_down
                    self.highlight_ref_text(target, final_dir, n)
                    self.highlight_ref_grid(n, final_dir)

    def highlight_ref_text(self, txt_widget, direction, num):
        tag_name = f"{direction}_{num}"
        ranges = txt_widget.tag_ranges(tag_name)
        if ranges: txt_widget.tag_add("ref", ranges[0], ranges[1])

    def highlight_ref_grid(self, num, direction):
        clue_list = self.clue_mapping.across if direction == 'across' else self.clue_mapping.down
        found_clue = next((c for c in clue_list if c['num'] == num), None)
        if found_clue:
            start = found_clue['cell']
            r, c = start // self.width, start % self.width
            while 0 <= r < self.height and 0 <= c < self.width:
                idx = self.get_index(c, r)
                if self.solution_grid[idx] == '.': break
                self.highlighted_ref_indices.add(idx)
                if direction == 'across': c += 1
                else: r += 1

    def highlight_text_widget(self, txt_widget, clue_num, is_active_direction):
        txt_widget.tag_remove("highlight", "1.0", tk.END)
        if not is_active_direction or clue_num == -1: return
        tag_name = f"across_{clue_num}" if self.direction == 'across' else f"down_{clue_num}"
        ranges = txt_widget.tag_ranges(tag_name)
        if ranges:
            txt_widget.tag_add("highlight", ranges[0], ranges[1])
            txt_widget.see(ranges[0])

if __name__ == "__main__":
    root = tk.Tk()
    app = CrosswordApp(root)
    root.mainloop()
