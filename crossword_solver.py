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
        self.root.title("Python .puz Solver - v9.0")
        self.root.geometry("1200x750")

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
        
        # Favorites Persistence
        self.favorites_file = "favorites.json"
        self.favorites = self.load_favorites()

        # Navigation State
        self.cursor_col = 0
        self.cursor_row = 0
        self.direction = 'across'
        
        # Settings Variables
        self.var_error_check = tk.BooleanVar(value=True)
        self.var_ctrl_reveal = tk.BooleanVar(value=True)
        self.var_skip_filled = tk.BooleanVar(value=True)
        self.var_end_behavior = tk.StringVar(value="next")
        self.var_dark_theme = tk.BooleanVar(value=True)
        
        # Visual Settings
        self.cell_size = 35 
        self.clue_font_size = 10 # Base font size for text panels
        self.sidebar_visible = False
        
        self.c = {} 

        # --- UI Layout ---
        
        # Menu
        menubar = tk.Menu(self.root)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open .puz File", command=self.browse_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Reveal Menu
        self.reveal_menu = tk.Menu(menubar, tearoff=0)
        self.reveal_menu.add_command(label="Reveal Current Word", command=self.reveal_current_word)
        menubar.add_cascade(label="Reveal", menu=self.reveal_menu)
        
        # Options Menu
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_checkbutton(label="Dark Theme", onvalue=True, offvalue=False,
                                     variable=self.var_dark_theme, command=self.apply_theme)
        options_menu.add_separator()
        options_menu.add_checkbutton(label="Error Check Mode", onvalue=True, offvalue=False, 
                                     variable=self.var_error_check, command=self.refresh_grid)
        options_menu.add_checkbutton(label="Enable 'Ctrl' to Reveal Letter", onvalue=True, offvalue=False, 
                                     variable=self.var_ctrl_reveal)
        options_menu.add_checkbutton(label="Skip Filled Squares", onvalue=True, offvalue=False, 
                                     variable=self.var_skip_filled)
        options_menu.add_separator()
        options_menu.add_radiobutton(label="At end of word: Jump to Next", value="next", variable=self.var_end_behavior)
        options_menu.add_radiobutton(label="At end of word: Stay", value="stay", variable=self.var_end_behavior)
        
        menubar.add_cascade(label="Options", menu=options_menu)
        self.root.config(menu=menubar)

        # Top Toolbar
        self.top_frame = tk.Frame(self.root, pady=8, padx=10, relief=tk.RIDGE, borderwidth=1)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)
        
        self.btn_sidebar = tk.Button(self.top_frame, text="📂 Files", command=self.toggle_sidebar, relief=tk.GROOVE)
        self.btn_sidebar.pack(side=tk.LEFT, padx=(0, 15))

        self.lbl_filename = tk.Label(self.top_frame, text="No File Selected", font=("Helvetica", 12, "bold", "italic"))
        self.lbl_filename.pack(side=tk.LEFT)
        
        # Zoom Controls
        self.btn_zoom_out = tk.Button(self.top_frame, text=" - ", command=lambda: self.change_zoom(-1), font=("Arial", 10, "bold"))
        self.btn_zoom_out.pack(side=tk.RIGHT, padx=5)
        
        self.btn_zoom_in = tk.Button(self.top_frame, text=" + ", command=lambda: self.change_zoom(1), font=("Arial", 10, "bold"))
        self.btn_zoom_in.pack(side=tk.RIGHT, padx=5)
        
        self.lbl_zoom = tk.Label(self.top_frame, text="Zoom", font=("Arial", 10))
        self.lbl_zoom.pack(side=tk.RIGHT)

        self.lbl_current_clue = tk.Label(self.top_frame, text="", font=("Helvetica", 12, "bold"), wraplength=600)
        self.lbl_current_clue.pack(side=tk.RIGHT, fill=tk.X, padx=15)

        # Resizable Layout
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=6)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Sidebar
        self.sidebar_frame = tk.Frame(self.main_paned, relief=tk.SUNKEN, borderwidth=1, width=200)
        self.sidebar_label = tk.Label(self.sidebar_frame, text="Folder Content", font=("Arial", 9, "bold"))
        self.sidebar_label.pack(fill=tk.X, pady=2)
        
        self.file_listbox = tk.Listbox(self.sidebar_frame, font=("Arial", 9), borderwidth=0)
        self.file_listbox.pack(expand=True, fill=tk.BOTH, padx=2, pady=2)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        
        # Context Menu for Sidebar
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="⭐ Add/Remove Favorite", command=self.toggle_favorite)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Delete File", command=self.delete_file)
        
        self.file_listbox.bind("<Button-3>", self.show_context_menu) # Right click
        # Fix 1: Stop spacebar from acting on listbox
        self.file_listbox.bind("<space>", self.block_listbox_space) 
        
        # Game Area
        self.game_paned = tk.PanedWindow(self.main_paned, orient=tk.HORIZONTAL, sashwidth=6)
        
        # Grid
        self.grid_frame = tk.Frame(self.game_paned)
        self.canvas = tk.Canvas(self.grid_frame, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Clues
        self.clues_frame = tk.Frame(self.game_paned)
        
        # Across
        self.lbl_across = tk.Label(self.clues_frame, text="Across", font=("Helvetica", 12, "bold"))
        self.lbl_across.pack(side=tk.TOP, anchor="w")
        
        frame_across = tk.Frame(self.clues_frame)
        frame_across.pack(side=tk.TOP, expand=True, fill=tk.BOTH, pady=(0, 10))
        
        sb_across = tk.Scrollbar(frame_across)
        sb_across.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.txt_across = tk.Text(frame_across, wrap=tk.WORD, 
                                  state=tk.DISABLED, cursor="arrow", yscrollcommand=sb_across.set, height=10)
        self.txt_across.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        sb_across.config(command=self.txt_across.yview)

        # Down
        self.lbl_down = tk.Label(self.clues_frame, text="Down", font=("Helvetica", 12, "bold"))
        self.lbl_down.pack(side=tk.TOP, anchor="w")
        
        frame_down = tk.Frame(self.clues_frame)
        frame_down.pack(side=tk.TOP, expand=True, fill=tk.BOTH)
        
        sb_down = tk.Scrollbar(frame_down)
        sb_down.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.txt_down = tk.Text(frame_down, wrap=tk.WORD, 
                                state=tk.DISABLED, cursor="arrow", yscrollcommand=sb_down.set, height=10)
        self.txt_down.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        sb_down.config(command=self.txt_down.yview)

        # Layout Assembly
        self.main_paned.add(self.game_paned)
        self.game_paned.add(self.grid_frame, minsize=400)
        self.game_paned.add(self.clues_frame, minsize=200)

        # Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.root.bind("<Key>", self.handle_keypress)
        self.root.bind("<Tab>", lambda e: self.jump_to_next_word())
        self.root.bind("<Control_L>", self.reveal_current_letter)
        self.root.bind("<Control_R>", self.reveal_current_letter)

        # Apply Theme Immediately
        self.apply_theme()

    # --- Persistence ---
    def load_favorites(self):
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_favorites(self):
        with open(self.favorites_file, 'w') as f:
            json.dump(self.favorites, f)

    def block_listbox_space(self, event):
        """Prevents spacebar from selecting list items and forces focus to canvas"""
        self.canvas.focus_set() # Force focus back to game
        # We can also manually trigger direction toggle here if desired:
        self.direction = 'down' if self.direction == 'across' else 'across'
        self.refresh_grid()
        self.update_clue_display()
        return "break"

    def show_context_menu(self, event):
        # Select the item under mouse
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
        # Strip star if present
        if filename.startswith("⭐ "):
            filename = filename.replace("⭐ ", "")
        
        # We need the directory. If a file is loaded, use that dir.
        if self.current_file_path:
            return os.path.join(os.path.dirname(self.current_file_path), filename)
        return None

    def toggle_favorite(self):
        path = self.get_selected_file_path()
        if not path: return
        
        # Normalize path for storage
        path = os.path.abspath(path)
        
        if path in self.favorites:
            self.favorites.remove(path)
        else:
            self.favorites.append(path)
        
        self.save_favorites()
        # Refresh sidebar
        if self.current_file_path:
            self.update_sidebar(os.path.dirname(self.current_file_path))

    def delete_file(self):
        path = self.get_selected_file_path()
        if not path: return
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete:\n{os.path.basename(path)}?"):
            try:
                os.remove(path)
                # Remove from favorites if there
                abs_path = os.path.abspath(path)
                if abs_path in self.favorites:
                    self.favorites.remove(abs_path)
                    self.save_favorites()
                
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
                'highlight': '#569fc9',
                'error': '#FF5555',
                'sash': '#444444',
                'completed': '#888888',
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
                'error': 'red',
                'sash': '#cccccc',
                'completed': '#999999',
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
        
        labels = [self.lbl_filename, self.lbl_current_clue, self.lbl_across, self.lbl_down, self.lbl_zoom]
        for lbl in labels:
            lbl.config(bg=c['panel_bg'], fg=c['fg'])
            
        btns = [self.btn_sidebar, self.btn_zoom_in, self.btn_zoom_out]
        for btn in btns:
            btn.config(bg=c['btn_bg'], fg=c['btn_fg'])

        self.grid_frame.config(bg=c['bg'])
        self.canvas.config(bg=c['bg'])
        
        self.clues_frame.config(bg=c['bg'])
        
        # Apply font size to text widgets
        clue_font = ("Arial", self.clue_font_size)
        
        for txt in [self.txt_across, self.txt_down]:
            txt.config(bg=c['input_bg'], fg=c['fg'], selectbackground=c['highlight'], font=clue_font)
            txt.tag_config("highlight", background=c['highlight'])
            txt.tag_config("completed", foreground=c['completed'])
            txt.tag_config("default", background=c['input_bg'], foreground=c['fg'])
            
        self.refresh_grid()
        self.update_clue_display()

    def change_zoom(self, delta):
        # Limit zoom
        new_cell = self.cell_size + (delta * 5)
        new_font = self.clue_font_size + delta
        
        if 20 <= new_cell <= 100:
            self.cell_size = new_cell
        if 8 <= new_font <= 24:
            self.clue_font_size = new_font
            
        self.apply_theme() # Re-applies font sizes and redraws grid

    def clean_clue_text(self, text):
        if not text: return ""
        text = re.sub(r'<[^>]+>', '', text)
        text = html.unescape(text)
        return text

    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Puzzle Files", "*.puz"), ("All Files", "*.*")])
        if filename:
            self.load_puz_file(filename)

    def load_puz_file(self, filename):
        try:
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
        total_cells = len(self.solution_grid) - self.solution_grid.count('.')
        
        if total_cells > 0 and (x_count / total_cells) > 0.8:
            self.is_redacted = True
            self.var_error_check.set(False)

        self.user_grid = ['-' if c != '.' else '.' for c in self.solution_grid]
        
        # Recalculate grid size based on puzzle dimensions but keep user zoom preference
        # We verify if the current cell_size fits, if not we might scale down, but for now strict zoom is better.
        self.canvas.config(width=self.width * self.cell_size, height=self.height * self.cell_size)

        self.parse_clues()
        
        self.cursor_col = 0
        self.cursor_row = 0
        self.direction = 'across'
        self.find_first_valid_cell()

        self.refresh_grid()
        self.update_clue_display()
        
        if not self.sidebar_visible:
            self.toggle_sidebar()

    def update_sidebar(self, folder_path):
        self.file_listbox.delete(0, tk.END)
        try:
            files = [f for f in os.listdir(folder_path) if f.lower().endswith('.puz')]
            files.sort()
            
            for f in files:
                full_p = os.path.abspath(os.path.join(folder_path, f))
                display_name = f
                if full_p in self.favorites:
                    display_name = "⭐ " + f
                self.file_listbox.insert(tk.END, display_name)
                
            current_name = os.path.basename(self.current_file_path)
            # Find index handling the star
            for i in range(self.file_listbox.size()):
                item = self.file_listbox.get(i)
                if item == current_name or item == "⭐ " + current_name:
                    self.file_listbox.selection_set(i)
                    self.file_listbox.see(i)
                    break
        except Exception:
            pass

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
        if filename.startswith("⭐ "):
            filename = filename.replace("⭐ ", "")
            
        full_path = os.path.join(os.path.dirname(self.current_file_path), filename)
        
        if full_path != self.current_file_path:
            self.load_puz_file(full_path)
        
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
                self.refresh_grid()
                self.update_clue_display()
                return

    def find_first_valid_cell(self):
        for i, char in enumerate(self.solution_grid):
            if char != '.':
                self.cursor_row = i // self.width
                self.cursor_col = i % self.width
                break

    def get_index(self, col, row):
        return row * self.width + col

    def refresh_grid(self):
        if not self.puzzle: return
        self.canvas.delete("all")
        
        # Ensure canvas is big enough for zoom
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
                    if is_filled:
                        txt_widget.tag_add("completed", ranges[0], ranges[1])
                    else:
                        txt_widget.tag_remove("completed", ranges[0], ranges[1])

        check_list(self.clue_mapping.across, 'across')
        check_list(self.clue_mapping.down, 'down')

    def is_highlighted(self, col, row):
        if self.solution_grid[self.get_index(col, row)] == '.': return False
        
        if self.direction == 'across':
            if row != self.cursor_row: return False
            start_c = self.cursor_col
            while start_c > 0 and self.solution_grid[self.get_index(start_c-1, row)] != '.':
                start_c -= 1
            end_c = self.cursor_col
            while end_c < self.width - 1 and self.solution_grid[self.get_index(end_c+1, row)] != '.':
                end_c += 1
            return start_c <= col <= end_c
        else: # Down
            if col != self.cursor_col: return False
            start_r = self.cursor_row
            while start_r > 0 and self.solution_grid[self.get_index(col, start_r-1)] != '.':
                start_r -= 1
            end_r = self.cursor_row
            while end_r < self.height - 1 and self.solution_grid[self.get_index(col, end_r+1)] != '.':
                end_r += 1
            return start_r <= row <= end_r

    def handle_keypress(self, event):
        if not self.puzzle: return
        key = event.keysym
        
        if event.state & 0x0004: return "break"
        if "Control" in key or "Alt" in key or "Shift" in key: return

        if key == "Left":
            self.move_smart(0, -1)
        elif key == "Right":
            self.move_smart(0, 1)
        elif key == "Up":
            self.move_cursor(-1, 0)
        elif key == "Down":
            self.move_cursor(1, 0)
        elif key == "space":
            self.direction = 'down' if self.direction == 'across' else 'across'
            self.refresh_grid()
            self.update_clue_display()
        elif key == "BackSpace":
            self.user_grid[self.get_index(self.cursor_col, self.cursor_row)] = '-'
            if self.direction == 'across':
                self.move_smart(0, -1)
            else:
                self.move_smart(-1, 0)
            self.refresh_grid()
        elif len(event.char) == 1 and event.char.isalpha():
            char = event.char.upper()
            idx = self.get_index(self.cursor_col, self.cursor_row)
            self.user_grid[idx] = char
            self.refresh_grid()
            self.step_forward()
        
        return "break"

    def move_smart(self, dr, dc):
        r, c = self.cursor_row, self.cursor_col
        while True:
            r += dr
            c += dc
            if c < 0:
                r -= 1
                c = self.width - 1
            elif c >= self.width:
                r += 1
                c = 0
            if r < 0:
                r = self.height - 1
                c = self.width - 1
            elif r >= self.height:
                r = 0
                c = 0
            
            idx = self.get_index(c, r)
            if self.solution_grid[idx] != '.':
                self.cursor_row = r
                self.cursor_col = c
                self.refresh_grid()
                self.update_clue_display()
                return
            if r == self.cursor_row and c == self.cursor_col:
                break

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
        else: # Down
            start_r = r
            while start_r > 0 and self.solution_grid[self.get_index(c, start_r-1)] != '.': start_r -= 1
            end_r = r
            while end_r < self.height - 1 and self.solution_grid[self.get_index(c, end_r+1)] != '.': end_r += 1
            for row in range(start_r, end_r + 1):
                self.user_grid[self.get_index(c, row)] = self.solution_grid[self.get_index(c, row)]
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
                if self.var_end_behavior.get() == "next": self.jump_to_next_word()
                return
            idx = self.get_index(c, r)
            if self.var_skip_filled.get() and self.user_grid[idx] not in ['-', '.']: continue
            else:
                self.cursor_row = r
                self.cursor_col = c
                self.refresh_grid()
                self.update_clue_display()
                return

    def jump_to_next_word(self, visited_indices=None):
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
        if current_clue_index != -1 and current_clue_index < len(current_list) - 1:
            next_clue = current_list[current_clue_index + 1]
        else:
            if len(next_list) > 0:
                next_clue = next_list[0]
                self.direction = next_direction 
            else:
                if len(current_list) > 0:
                    next_clue = current_list[0]

        if next_clue:
            self.cursor_row = next_clue['cell'] // self.width
            self.cursor_col = next_clue['cell'] % self.width
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
                    new_idx = self.get_index(self.cursor_col, self.cursor_row)
                    if new_idx not in visited_indices:
                        visited_indices.add(new_idx)
                        self.jump_to_next_word(visited_indices)
            
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
            self.refresh_grid()
            self.update_clue_display()

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
        clue_num = -1
        for clue in target_list:
            if clue['cell'] == start_idx:
                found_clue = f"{clue['num']}. {self.clean_clue_text(clue['clue'])}"
                clue_num = clue['num']
                break
        
        self.lbl_current_clue.config(text=found_clue)
        self.highlight_text_widget(self.txt_across, clue_num, self.direction == 'across')
        self.highlight_text_widget(self.txt_down, clue_num, self.direction == 'down')

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
