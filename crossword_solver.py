import tkinter as tk
from tkinter import filedialog, messagebox, font
import puz
import math

class CrosswordApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python .puz Solver")
        self.root.geometry("1000x700")

        # Game State
        self.puzzle = None
        self.width = 0
        self.height = 0
        self.solution_grid = [] # 1D array of correct characters
        self.user_grid = []     # 1D array of user characters
        self.grid_numbers = {}  # Map (col, row) -> number
        
        # Navigation State
        self.cursor_col = 0
        self.cursor_row = 0
        self.direction = 'across' # or 'down'
        
        # Settings
        self.error_check_mode = tk.BooleanVar(value=False)
        self.cell_size = 35 # Size of grid squares

        # --- UI Layout ---
        
        # Menu
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open .puz File", command=self.load_puz_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_checkbutton(label="Error Check Mode", onvalue=True, offvalue=False, 
                                     variable=self.error_check_mode, command=self.refresh_grid)
        menubar.add_cascade(label="Options", menu=options_menu)
        self.root.config(menu=menubar)

        # Main Containers
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)
        
        main_content = tk.Frame(self.root)
        main_content.pack(side=tk.TOP, expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Current Clue Display (Top)
        self.lbl_current_clue = tk.Label(top_frame, text="Open a file to begin", font=("Arial", 14, "bold"), wraplength=800)
        self.lbl_current_clue.pack()

        # Grid (Left)
        self.canvas = tk.Canvas(main_content, bg="white", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, expand=False, fill=tk.BOTH)

        # Clues Lists (Right)
        right_panel = tk.Frame(main_content)
        right_panel.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        
        # Across Clues
        lbl_across = tk.Label(right_panel, text="Across", font=("Arial", 12, "bold"))
        lbl_across.pack(side=tk.TOP, anchor="w")
        self.list_across = tk.Listbox(right_panel, font=("Arial", 10), exportselection=False)
        self.list_across.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

        # Down Clues
        lbl_down = tk.Label(right_panel, text="Down", font=("Arial", 12, "bold"))
        lbl_down.pack(side=tk.TOP, anchor="w")
        self.list_down = tk.Listbox(right_panel, font=("Arial", 10), exportselection=False)
        self.list_down.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

        # Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.root.bind("<Key>", self.handle_keypress)
        # Bind Control keys specifically for the Reveal function
        self.root.bind("<Control_L>", self.reveal_current)
        self.root.bind("<Control_R>", self.reveal_current)
        
        # Scroll logic for listboxes to sync with selection (optional/basic)
        self.list_across.bind("<<ListboxSelect>>", lambda e: self.jump_to_clue('across'))
        self.list_down.bind("<<ListboxSelect>>", lambda e: self.jump_to_clue('down'))

    def load_puz_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Puzzle Files", "*.puz"), ("All Files", "*.*")])
        if not filename:
            return

        try:
            self.puzzle = puz.read(filename)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")
            return

        # Initialize Data
        self.width = self.puzzle.width
        self.height = self.puzzle.height
        self.solution_grid = list(self.puzzle.solution)
        # User grid: '.' is black, '-' is empty. We make a copy.
        self.user_grid = ['-' if c != '.' else '.' for c in self.solution_grid]
        
        # Calculate sizing
        max_h = 600
        self.cell_size = min(40, max_h // self.height)
        self.canvas.config(width=self.width * self.cell_size, height=self.height * self.cell_size)

        # Parse Clues and Numbering
        self.parse_clues()
        
        # Reset Cursor
        self.cursor_col = 0
        self.cursor_row = 0
        self.direction = 'across'
        self.find_first_valid_cell()

        self.refresh_grid()
        self.update_clue_display()

    def parse_clues(self):
        # puzpy helper to get numbering
        numbering = self.puzzle.clue_numbering()
        
        self.grid_numbers = {}
        self.clues_across = [] # Stores (number, text, [cells])
        self.clues_down = []
        
        self.list_across.delete(0, tk.END)
        self.list_down.delete(0, tk.END)

        for clue in numbering.across:
            self.list_across.insert(tk.END, f"{clue['num']}. {clue['clue']}")
            # Map numbering to grid for display
            r = clue['cell'] // self.width
            c = clue['cell'] % self.width
            self.grid_numbers[(c, r)] = clue['num']
            
        for clue in numbering.down:
            self.list_down.insert(tk.END, f"{clue['num']}. {clue['clue']}")
            r = clue['cell'] // self.width
            c = clue['cell'] % self.width
            self.grid_numbers[(c, r)] = clue['num']
            
        self.clue_mapping = numbering

    def find_first_valid_cell(self):
        # Find the first non-black square to start cursor
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
                
                # Background Color
                bg_color = "white"
                if sol_val == '.':
                    bg_color = "black"
                elif r == self.cursor_row and c == self.cursor_col:
                    bg_color = "#FFFF00" # Yellow for cursor
                elif self.is_highlighted(c, r):
                    bg_color = "#E0F7FA" # Cyan tint for current word
                
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg_color, outline="black")

                # Numbers
                if (c, r) in self.grid_numbers:
                    self.canvas.create_text(x1+2, y1+2, anchor="nw", text=str(self.grid_numbers[(c,r)]), font=fnt_num)

                # Characters
                if cell_val not in ['-', '.']:
                    text_color = "black"
                    # Error Check Logic
                    if self.error_check_mode.get() and cell_val != sol_val:
                        text_color = "red"
                    
                    self.canvas.create_text(x1 + self.cell_size/2, y1 + self.cell_size/2, 
                                            text=cell_val, font=fnt_char, fill=text_color)

    def is_highlighted(self, col, row):
        # Highlight the word associated with the cursor direction
        if self.solution_grid[self.get_index(col, row)] == '.':
            return False
        
        # Simple check: are we in the same word line?
        if self.direction == 'across':
            if row != self.cursor_row: return False
            # Scan left and right from cursor to find boundaries
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
            
            # Logic: Update grid
            self.user_grid[idx] = char
            self.refresh_grid()

            # Logic: Move Cursor
            if self.error_check_mode.get():
                # If error check ON: only move if correct
                if char == correct_char:
                    self.step_forward()
            else:
                # Standard: always move
                self.step_forward()

    def reveal_current(self, event):
        """Reveal current letter and move next (Ctrl key)"""
        if not self.puzzle: return
        
        idx = self.get_index(self.cursor_col, self.cursor_row)
        correct_char = self.solution_grid[idx]
        
        if correct_char == '.': return
        
        self.user_grid[idx] = correct_char
        self.refresh_grid()
        self.step_forward()

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
        # Move to next cell in current direction, skipping filled blacks?
        # Standard crossword behavior: just go to next cell, skip blacks
        dr, dc = (0, 1) if self.direction == 'across' else (1, 0)
        
        # Try moving
        next_r, next_c = self.cursor_row + dr, self.cursor_col + dc
        
        # Simple bounds check
        if 0 <= next_r < self.height and 0 <= next_c < self.width:
            # If black, skip over it
            while 0 <= next_r < self.height and 0 <= next_c < self.width and \
                  self.solution_grid[self.get_index(next_c, next_r)] == '.':
                next_r += dr
                next_c += dc
            
            if 0 <= next_r < self.height and 0 <= next_c < self.width:
                self.cursor_row = next_r
                self.cursor_col = next_c
                self.refresh_grid()
                self.update_clue_display()

    def move_cursor_back(self):
        dr, dc = (0, -1) if self.direction == 'across' else (-1, 0)
        new_r, new_c = self.cursor_row + dr, self.cursor_col + dc
        
        if 0 <= new_r < self.height and 0 <= new_c < self.width:
             while 0 <= new_r < self.height and 0 <= new_c < self.width and \
                  self.solution_grid[self.get_index(new_c, new_r)] == '.':
                new_r += dr
                new_c += dc
             
             if 0 <= new_r < self.height and 0 <= new_c < self.width:
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
            
            # If clicking same square, toggle direction
            if c == self.cursor_col and r == self.cursor_row:
                self.direction = 'down' if self.direction == 'across' else 'across'
            else:
                self.cursor_col = c
                self.cursor_row = r
                
            self.refresh_grid()
            self.update_clue_display()

    def update_clue_display(self):
        # Find clue number for current cursor
        # This is a bit complex in puzpy struct, but we can do a reverse lookup or search
        # puzpy numbering helper has 'across' list of dicts: {'num': 1, 'clue': '...', 'cell': 0}
        
        current_idx = self.get_index(self.cursor_col, self.cursor_row)
        
        found_clue = ""
        clue_num = -1
        
        target_list = self.clue_mapping.across if self.direction == 'across' else self.clue_mapping.down
        
        # We need to find which word the cursor belongs to.
        # Efficient way: find the starting cell of the word containing cursor
        start_idx = current_idx
        if self.direction == 'across':
            # walk left
            c = self.cursor_col
            while c >= 0 and self.solution_grid[self.get_index(c, self.cursor_row)] != '.':
                start_idx = self.get_index(c, self.cursor_row)
                c -= 1
        else:
            # walk up
            r = self.cursor_row
            while r >= 0 and self.solution_grid[self.get_index(self.cursor_col, r)] != '.':
                start_idx = self.get_index(self.cursor_col, r)
                r -= 1
                
        # Now find the clue that starts at start_idx
        for clue in target_list:
            if clue['cell'] == start_idx:
                found_clue = f"{clue['num']}. {clue['clue']}"
                clue_num = clue['num']
                break
        
        self.lbl_current_clue.config(text=found_clue)
        
        # Highlight in Listbox
        self.highlight_listbox(self.list_across, clue_num, self.direction == 'across')
        self.highlight_listbox(self.list_down, clue_num, self.direction == 'down')

    def highlight_listbox(self, listbox, clue_num, is_active_direction):
        listbox.selection_clear(0, tk.END)
        if not is_active_direction: return
        
        # Find index
        for i, item in enumerate(listbox.get(0, tk.END)):
            if item.startswith(f"{clue_num}."):
                listbox.selection_set(i)
                listbox.see(i)
                break
                
    def jump_to_clue(self, direction):
        # Optional: Click listbox to move cursor
        pass

if __name__ == "__main__":
    root = tk.Tk()
    app = CrosswordApp(root)
    root.mainloop()
