import tkinter as tk
from tkinter import filedialog, messagebox, font
import puz

class CrosswordApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python .puz Solver v2.1")
        self.root.geometry("1000x700")

        # Game State
        self.puzzle = None
        self.width = 0
        self.height = 0
        self.solution_grid = [] 
        self.user_grid = []     
        self.grid_numbers = {}  
        self.clue_mapping = None
        
        # Navigation State
        self.cursor_col = 0
        self.cursor_row = 0
        self.direction = 'across'
        
        # Settings Variables
        self.var_error_check = tk.BooleanVar(value=False)
        self.var_ctrl_reveal = tk.BooleanVar(value=True)
        self.var_end_behavior = tk.StringVar(value="next") # "stay" or "next"
        self.cell_size = 35 

        # --- UI Layout ---
        
        # Menu
        menubar = tk.Menu(self.root)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open .puz File", command=self.load_puz_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Options Menu
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_checkbutton(label="Error Check Mode", onvalue=True, offvalue=False, 
                                     variable=self.var_error_check, command=self.refresh_grid)
        options_menu.add_checkbutton(label="Enable 'Ctrl' to Reveal", onvalue=True, offvalue=False, 
                                     variable=self.var_ctrl_reveal)
        options_menu.add_separator()
        options_menu.add_radiobutton(label="At end of word: Jump to Next", value="next", variable=self.var_end_behavior)
        options_menu.add_radiobutton(label="At end of word: Stay", value="stay", variable=self.var_end_behavior)
        
        menubar.add_cascade(label="Options", menu=options_menu)
        self.root.config(menu=menubar)

        # Main Containers
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)
        
        main_content = tk.Frame(self.root)
        main_content.pack(side=tk.TOP, expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Current Clue Display
        self.lbl_current_clue = tk.Label(top_frame, text="Open a file to begin", font=("Arial", 14, "bold"), wraplength=800)
        self.lbl_current_clue.pack()

        # Grid
        self.canvas = tk.Canvas(main_content, bg="white", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, expand=False, fill=tk.BOTH)

        # Clues Lists
        right_panel = tk.Frame(main_content)
        right_panel.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        
        lbl_across = tk.Label(right_panel, text="Across", font=("Arial", 12, "bold"))
        lbl_across.pack(side=tk.TOP, anchor="w")
        self.list_across = tk.Listbox(right_panel, font=("Arial", 10), exportselection=False)
        self.list_across.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

        lbl_down = tk.Label(right_panel, text="Down", font=("Arial", 12, "bold"))
        lbl_down.pack(side=tk.TOP, anchor="w")
        self.list_down = tk.Listbox(right_panel, font=("Arial", 10), exportselection=False)
        self.list_down.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

        # Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.root.bind("<Key>", self.handle_keypress)
        self.root.bind("<Control_L>", self.reveal_current)
        self.root.bind("<Control_R>", self.reveal_current)
        self.root.bind("<Tab>", lambda e: self.jump_to_next_word())

    def load_puz_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Puzzle Files", "*.puz"), ("All Files", "*.*")])
        if not filename: return

        try:
            self.puzzle = puz.read(filename)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")
            return

        self.width = self.puzzle.width
        self.height = self.puzzle.height
        self.solution_grid = list(self.puzzle.solution)
        self.user_grid = ['-' if c != '.' else '.' for c in self.solution_grid]
        
        # Calculate sizing
        max_h = 600
        self.cell_size = min(40, max_h // self.height)
        self.canvas.config(width=self.width * self.cell_size, height=self.height * self.cell_size)

        self.parse_clues()
        
        self.cursor_col = 0
        self.cursor_row = 0
        self.direction = 'across'
        self.find_first_valid_cell()

        self.refresh_grid()
        self.update_clue_display()

    def parse_clues(self):
        self.clue_mapping = self.puzzle.clue_numbering()
        
        self.grid_numbers = {}
        self.list_across.delete(0, tk.END)
        self.list_down.delete(0, tk.END)

        for clue in self.clue_mapping.across:
            self.list_across.insert(tk.END, f"{clue['num']}. {clue['clue']}")
            r = clue['cell'] // self.width
            c = clue['cell'] % self.width
            self.grid_numbers[(c, r)] = clue['num']
            
        for clue in self.clue_mapping.down:
            self.list_down.insert(tk.END, f"{clue['num']}. {clue['clue']}")
            r = clue['cell'] // self.width
            c = clue['cell'] % self.width
            self.grid_numbers[(c, r)] = clue['num']

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
        
        fnt_num = font.Font(family="Arial", size=int(self.cell_size*0.3))
        fnt_char = font.Font(family="Arial", size=int(self.cell_size*0.6), weight="bold")

        for r in range(self.height):
            for c in range(self.width):
                x1 = c * self.cell_size
                y1 = r * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                
                idx = self.get_index(c, r)
                cell_val = self.user_grid[idx]
                sol_val = self.solution_grid[idx]
                
                bg_color = "white"
                if sol_val == '.':
                    bg_color = "black"
                elif r == self.cursor_row and c == self.cursor_col:
                    bg_color = "#FFFF00"
                elif self.is_highlighted(c, r):
                    bg_color = "#E0F7FA"
                
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg_color, outline="black")

                if (c, r) in self.grid_numbers:
                    self.canvas.create_text(x1+2, y1+2, anchor="nw", text=str(self.grid_numbers[(c,r)]), font=fnt_num)

                if cell_val not in ['-', '.']:
                    text_color = "black"
                    if self.var_error_check.get() and cell_val != sol_val:
                        text_color = "red"
                    
                    self.canvas.create_text(x1 + self.cell_size/2, y1 + self.cell_size/2, 
                                            text=cell_val, font=fnt_char, fill=text_color)

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
        
        # --- FIX: STRICTLY IGNORE IF CONTROL IS HELD ---
        # 0x0004 is the bitmask for Control. 
        # This prevents "Ctrl" presses from being interpreted as typed letters.
        if event.state & 0x0004:
            return "break"
        
        # Also ignore modifier keys themselves
        if "Control" in key or "Alt" in key or "Shift" in key:
            return

        if key == "Left":
            self.move_cursor(0, -1)
        elif key == "Right":
            self.move_cursor(0, 1)
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
            self.move_cursor_back()
            self.refresh_grid()
        elif len(event.char) == 1 and event.char.isalpha():
            char = event.char.upper()
            idx = self.get_index(self.cursor_col, self.cursor_row)
            correct_char = self.solution_grid[idx]
            
            self.user_grid[idx] = char
            self.refresh_grid()

            if self.var_error_check.get():
                if char == correct_char:
                    self.step_forward()
            else:
                self.step_forward()
        
        return "break"

    def reveal_current(self, event):
        if not self.puzzle: return
        if not self.var_ctrl_reveal.get(): return 
        
        idx = self.get_index(self.cursor_col, self.cursor_row)
        correct_char = self.solution_grid[idx]
        
        if correct_char == '.': return
        
        self.user_grid[idx] = correct_char
        self.refresh_grid()
        self.step_forward()
        return "break"

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
        next_r, next_c = self.cursor_row + dr, self.cursor_col + dc
        
        hit_block = False
        if not (0 <= next_r < self.height and 0 <= next_c < self.width):
            hit_block = True
        elif self.solution_grid[self.get_index(next_c, next_r)] == '.':
            hit_block = True
            
        if hit_block:
            if self.var_end_behavior.get() == "next":
                self.jump_to_next_word()
        else:
            self.cursor_row = next_r
            self.cursor_col = next_c
            self.refresh_grid()
            self.update_clue_display()

    def jump_to_next_word(self):
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
        
        next_clue = None
        for i, clue in enumerate(target_list):
            if clue['cell'] == start_idx:
                next_index = (i + 1) % len(target_list)
                next_clue = target_list[next_index]
                break
        
        if next_clue is None and len(target_list) > 0:
            next_clue = target_list[0]

        if next_clue:
            self.cursor_row = next_clue['cell'] // self.width
            self.cursor_col = next_clue['cell'] % self.width
            self.refresh_grid()
            self.update_clue_display()

    def move_cursor_back(self):
        dr, dc = (0, -1) if self.direction == 'across' else (-1, 0)
        new_r, new_c = self.cursor_row + dr, self.cursor_col + dc
        
        if 0 <= new_r < self.height and 0 <= new_c < self.width:
            if self.solution_grid[self.get_index(new_c, new_r)] != '.':
                self.cursor_row = new_r
                self.cursor_col = new_c
                self.refresh_grid()
                self.update_clue_display()

    def on_click(self, event):
        if not self.puzzle: return
        c = event.x // self.cell_size
        r = event.y // self.cell_size
        
        if 0 <= c < self.width and 0 <= r < self.height:
            if self.solution_grid[self.get_index(c, r)] == '.':
                return
            
            if c == self.cursor_col and r == self.cursor_row:
                self.direction = 'down' if self.direction == 'across' else 'across'
            else:
                self.cursor_col = c
                self.cursor_row = r
                
            self.refresh_grid()
            self.update_clue_display()

    def update_clue_display(self):
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
                found_clue = f"{clue['num']}. {clue['clue']}"
                clue_num = clue['num']
                break
        
        self.lbl_current_clue.config(text=found_clue)
        self.highlight_listbox(self.list_across, clue_num, self.direction == 'across')
        self.highlight_listbox(self.list_down, clue_num, self.direction == 'down')

    def highlight_listbox(self, listbox, clue_num, is_active_direction):
        listbox.selection_clear(0, tk.END)
        if not is_active_direction: return
        for i, item in enumerate(listbox.get(0, tk.END)):
            if item.startswith(f"{clue_num}."):
                listbox.selection_set(i)
                listbox.see(i)
                break

if __name__ == "__main__":
    root = tk.Tk()
    app = CrosswordApp(root)
    root.mainloop()
