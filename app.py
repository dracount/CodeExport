# FILE: D:\PROCESSES\vscode_projects\CodeExport\app.py
# Action: Add configuration for the 'selected' tag background in the create_project_interface method.
# Line Number: Insert after line 173

import os
import tkinter as tk
from tkinter.font import Font
from tkinter import ttk, filedialog, messagebox
import json
import datetime
import copy # Import copy
from ttkbootstrap import Style

from project_manager import ProjectManager
from file_operations import FileOperations
from ui_dialogs import ProjectManagerDialog, FileTypeDialog, ProgressDialog
# Import format_size here as it's used for display
from utils import calculate_project_size, update_ui_status, count_characters_in_files, format_size

class FileMergerApp:
    def __init__(self, root):
        self.root = root
        self.style = Style("flatly") # Example theme
        # Configure Treeview font and row height
        try:
             tree_font = Font(family="Segoe UI", size=11) # Adjust font as needed
             self.style.configure("Treeview", font=tree_font, rowheight=tree_font.metrics("linespace") + 5)
             self.style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))
        except tk.TclError:
             print("Warning: Could not set custom Treeview font. Using default.")
             self.style.configure("Treeview", rowheight=25) # Default fallback
             self.style.configure("Treeview.Heading", font=('Arial', 10, 'bold'))

        # Core state management
        self.current_project = "Default"
        self.projects = {}
        # Default ignored types - consider moving to a config or default project settings
        self.ignored_file_types = [
            # Version control
            ".git", ".gitignore", ".gitattributes", ".svn", ".hg",
            # IDE/Editor specific
            ".vscode", ".idea", ".project", ".settings", "__pycache__", "*.pyc", "*.pyo",
            # Compiled/Binary
            "*.dll", "*.exe", "*.so", "*.o", "*.obj", "*.class", "*.jar",
            # Archives
            "*.zip", "*.tar", "*.gz", "*.rar", "*.7z",
            # Images (often large and not useful for merging text)
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
            # Media
            "*.mp3", "*.wav", "*.mp4", "*.avi", "*.mov",
            # Docs/Other Binary Formats
            "*.pdf", "*.doc", "*.docx", "*.xls", "*.xlsx", "*.ppt", "*.pptx", "*.odt", "*.ods",
            # Logs (can be large, maybe optional)
            # "*.log"
             # OS specific
             "Thumbs.db", ".DS_Store"
        ]
        self.root_dir = os.path.expanduser("~") # Default root
        self.output_dir = os.path.join(os.path.expanduser("~"), "Merged_Files") # Default output
        self.stats = {"files": 0, "selected": 0, "size": 0, "chars": 0}
        self.pending_selected_paths = set() # Initialize pending paths set

        # Setup main window
        self.root.title("File Merger Pro")
        self.root.geometry("1280x800")
        self.root.minsize(800, 600)

        # Initialize managers (pass self/app instance)
        self.project_manager = ProjectManager(self)
        self.file_operations = FileOperations(self)

        # Initialize UI components
        self.create_project_interface()
        self.setup_context_menus()

        # Load data and initialize view
        self.project_manager.load_preferences() # This loads projects and applies current project settings

        # Ensure output directory exists after loading prefs
        if not os.path.exists(self.output_dir):
            try: os.makedirs(self.output_dir)
            except Exception as e: print(f"Could not create initial output directory {self.output_dir}: {e}")

        # Build initial tree, passing any pending selections from loaded project
        self.file_operations.build_tree(self.root_dir, self.pending_selected_paths)
        self.pending_selected_paths = set() # Clear after use

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing) # Handle window close


    def create_project_interface(self):
        # --- Menu Bar ---
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Change Root Directory", command=self.change_root_directory)
        file_menu.add_command(label="Change Output Directory", command=self.change_output_directory)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing) # Use on_closing for clean exit

        # Project menu
        project_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Project", menu=project_menu)
        project_menu.add_command(label="New Project", command=self.project_manager.create_project)
        project_menu.add_command(label="Clone Current Project", command=self.project_manager.clone_current_project)
        project_menu.add_command(label="Manage Projects", command=self.project_manager.manage_projects)
        project_menu.add_separator()
        project_menu.add_command(label="Edit Ignored File Types/Names", command=self.edit_filetypes) # Updated label

        # --- Main Paned Window ---
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Left Frame (File Tree) ---
        self.left_frame = ttk.Frame(self.paned_window, padding=5)
        self.paned_window.add(self.left_frame, weight=3) # Give more weight to tree view

        # Tree navigation frame
        self.tree_nav_frame = ttk.Frame(self.left_frame)
        self.tree_nav_frame.pack(fill=tk.X, pady=(0, 5))

        # Current path display and controls
        ttk.Label(self.tree_nav_frame, text="Directory:").pack(side=tk.LEFT, padx=(0, 5))
        self.path_var = tk.StringVar(value=self.root_dir)
        self.path_entry = ttk.Entry(self.tree_nav_frame, textvariable=self.path_var)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        # Bind Enter key to navigate to the entered path
        self.path_entry.bind("<Return>", lambda e: self.change_root_directory(self.path_var.get()))
        ttk.Button(self.tree_nav_frame, text="Browse", command=lambda: self.change_root_directory(None)).pack(side=tk.LEFT, padx=5) # Pass None to trigger browse
        ttk.Button(self.tree_nav_frame, text="Refresh", command=self.refresh_directory).pack(side=tk.LEFT, padx=5)

        # Treeview with scrollbars
        tree_container = ttk.Frame(self.left_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.tree_scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        self.tree_scrollbar_x = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL)

        self.tree = ttk.Treeview(tree_container,
                                 yscrollcommand=self.tree_scrollbar_y.set,
                                 xscrollcommand=self.tree_scrollbar_x.set,
                                 selectmode="none") # Disable default selection highlighting

        self.tree_scrollbar_y.config(command=self.tree.yview)
        self.tree_scrollbar_x.config(command=self.tree.xview)

        self.tree_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)


        # Define Treeview columns
        self.tree["columns"] = ("select", "size", "date_modified")
        self.tree.column("#0", width=500, minwidth=250, stretch=tk.YES) # Name column (stretchable)
        self.tree.column("select", width=40, minwidth=40, anchor=tk.CENTER, stretch=tk.NO) # Checkbox fixed width
        self.tree.column("size", width=100, minwidth=80, anchor=tk.E, stretch=tk.NO)   # Size fixed width
        self.tree.column("date_modified", width=150, minwidth=120, anchor=tk.W, stretch=tk.NO) # Date fixed width

        # Define Treeview headings
        self.tree.heading("#0", text="Name", anchor=tk.W)
        self.tree.heading("select", text="", anchor=tk.CENTER) # Checkbox heading
        self.tree.heading("size", text="Size", anchor=tk.E)
        self.tree.heading("date_modified", text="Date Modified", anchor=tk.W)

        # Define tags for styling (using ttkbootstrap styles if available, else simple foreground)
        try:
            self.tree.tag_configure('folder', foreground=self.style.colors.primary)
            self.tree.tag_configure('file', foreground=self.style.colors.fg)
            self.tree.tag_configure('python', foreground=self.style.colors.success)
            self.tree.tag_configure('text', foreground=self.style.colors.info)
            self.tree.tag_configure('image', foreground=self.style.colors.warning)
            self.tree.tag_configure('error', foreground=self.style.colors.danger)
            # Configure 'selected' tag for row highlighting
            self.tree.tag_configure('selected', background=self.style.colors.selectbg, foreground=self.style.colors.selectfg)
        except AttributeError: # Fallback if style colors are not defined
             print("Using basic foreground colors for tree tags.")
             self.tree.tag_configure('folder', foreground='navy')
             self.tree.tag_configure('file', foreground='black')
             self.tree.tag_configure('python', foreground='darkgreen')
             self.tree.tag_configure('text', foreground='darkblue')
             self.tree.tag_configure('image', foreground='purple')
             self.tree.tag_configure('error', foreground='red')
             # Fallback 'selected' tag configuration
             self.tree.tag_configure('selected', background='lightblue', foreground='black') # Use a distinct background


        # Bind events to Treeview
        self.tree.bind("<ButtonRelease-1>", self.on_tree_item_click) # Handle checkbox clicks primarily
        self.tree.bind("<Double-Button-1>", self.on_tree_double_click) # Handle opening folders/files
        self.tree.bind("<space>", self.toggle_selection_spacebar) # Spacebar toggles focused item
        self.tree.bind("<<TreeviewOpen>>", self.file_operations.on_tree_open) # Load children when expanded


        # --- Right Frame (Controls) ---
        self.right_frame = ttk.Frame(self.paned_window, padding=5)
        self.paned_window.add(self.right_frame, weight=1) # Less weight

        # Project info frame
        project_frame = ttk.LabelFrame(self.right_frame, text="Project Information", padding=10)
        project_frame.pack(fill=tk.X, pady=5)
        self.project_name_var = tk.StringVar(value=self.current_project)
        ttk.Label(project_frame, text="Current Project:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(project_frame, textvariable=self.project_name_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

        # Project stats frame
        self.stats_frame = ttk.LabelFrame(self.right_frame, text="Statistics", padding=10)
        self.stats_frame.pack(fill=tk.X, pady=5)
        self.files_count_var = tk.StringVar(value="Total Items: 0")
        self.selected_count_var = tk.StringVar(value="Selected Items: 0")
        self.size_var = tk.StringVar(value="Selected Files Size: 0 B")
        self.chars_count_var = tk.StringVar(value="Selected Files Chars: 0")
        ttk.Label(self.stats_frame, textvariable=self.files_count_var).pack(anchor=tk.W, padx=5, pady=1)
        ttk.Label(self.stats_frame, textvariable=self.selected_count_var).pack(anchor=tk.W, padx=5, pady=1)
        ttk.Label(self.stats_frame, textvariable=self.size_var).pack(anchor=tk.W, padx=5, pady=1)
        ttk.Label(self.stats_frame, textvariable=self.chars_count_var).pack(anchor=tk.W, padx=5, pady=1)

        # Operations frame
        operations_frame = ttk.LabelFrame(self.right_frame, text="Operations", padding=10)
        operations_frame.pack(fill=tk.X, pady=5)
        ttk.Button(operations_frame, text="Merge Selected Files", command=self.file_operations.merge_files).pack(fill=tk.X, padx=5, pady=3)
        ttk.Button(operations_frame, text="Select All Visible", command=self.select_all_visible).pack(fill=tk.X, padx=5, pady=3)
        ttk.Button(operations_frame, text="Deselect All", command=self.deselect_all).pack(fill=tk.X, padx=5, pady=3)

        # Rules and prompt frame (using Notebook for tabs)
        rules_notebook = ttk.Notebook(self.right_frame)
        rules_notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # Prompt Tab
        prompt_tab = ttk.Frame(rules_notebook, padding=10)
        rules_notebook.add(prompt_tab, text='Prompt')
        ttk.Label(prompt_tab, text="Goal/Prompt:").pack(anchor=tk.W, pady=(0, 5))
        self.prompt_text = tk.Text(prompt_tab, height=6, width=30, wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
        self.prompt_text.pack(fill=tk.BOTH, expand=True)

        # Project Rules Tab
        project_rules_tab = ttk.Frame(rules_notebook, padding=10)
        rules_notebook.add(project_rules_tab, text='Project Rules')
        ttk.Label(project_rules_tab, text="Project Specific Rules:").pack(anchor=tk.W, pady=(0, 5))
        self.project_rules_text = tk.Text(project_rules_tab, height=6, width=30, wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
        self.project_rules_text.pack(fill=tk.BOTH, expand=True, pady=(0,5))
        ttk.Button(project_rules_tab, text="Apply Default Rules", command=self.apply_default_rules).pack(anchor=tk.E)


        # Default Rules Tab
        default_rules_tab = ttk.Frame(rules_notebook, padding=10)
        rules_notebook.add(default_rules_tab, text='Default Rules')
        ttk.Label(default_rules_tab, text="Default Rules Template:").pack(anchor=tk.W, pady=(0, 5))
        self.default_rules_text = tk.Text(default_rules_tab, height=6, width=30, wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
        self.default_rules_text.pack(fill=tk.BOTH, expand=True)


        # --- Status Bar ---
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=5)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_context_menus(self):
        # Tree context menu
        self.tree_context_menu = tk.Menu(self.tree, tearoff=0)
        self.tree_context_menu.add_command(label="Select", command=self.context_select_item)
        self.tree_context_menu.add_command(label="Deselect", command=self.context_deselect_item)
        self.tree_context_menu.add_separator()
        self.tree_context_menu.add_command(label="Expand All", command=self.context_expand_all)
        self.tree_context_menu.add_command(label="Collapse All", command=self.context_collapse_all)
        self.tree_context_menu.add_separator()
        self.tree_context_menu.add_command(label="Open in Explorer", command=self.context_open_in_explorer)

        # Bind right-click to show context menu
        self.tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Show context menu on right-click."""
        # Identify item under cursor
        item_id = self.tree.identify_row(event.y)
        if item_id:
            # Select the item under the cursor for context actions
            # Use focus instead of selection if selectmode is "none"
            self.tree.focus(item_id)
            # Post the menu
            self.tree_context_menu.post(event.x_root, event.y_root)
        else:
            # Maybe show a general context menu if clicking empty space?
            pass

    def context_select_item(self):
        """Context menu action: Select focused item and children."""
        item_id = self.tree.focus()
        if item_id:
            self.update_item_selection(item_id, True) # Select item and children
            self.update_project_stats()

    def context_deselect_item(self):
        """Context menu action: Deselect focused item and children."""
        item_id = self.tree.focus()
        if item_id:
             self.update_item_selection(item_id, False) # Deselect item and children
             self.update_project_stats()

    def context_expand_all(self):
        """Context menu action: Expand focused item and all its children."""
        item_id = self.tree.focus()
        if item_id:
            self.expand_recursive(item_id)

    def context_collapse_all(self):
        """Context menu action: Collapse focused item and all its children."""
        item_id = self.tree.focus()
        if item_id:
            self.collapse_recursive(item_id)

    def context_open_in_explorer(self):
        """Context menu action: Open the item's location in file explorer."""
        item_id = self.tree.focus() # Get focused item (path)
        if item_id and item_id in self.file_operations.file_paths:
            path = self.file_operations.file_paths[item_id]
            if os.path.exists(path):
                 try:
                     if os.path.isdir(path):
                         os.startfile(path)
                     else:
                         # Open the containing folder and select the file
                         os.startfile(os.path.dirname(path)) # Fallback: just open folder
                         # More specific selection might require platform specific code (e.g., subprocess with explorer args)
                 except Exception as e:
                     messagebox.showerror("Error", f"Could not open location: {e}")
            else:
                messagebox.showwarning("Not Found", "The selected item's path does not exist.")


    def expand_recursive(self, item_id):
        """Recursively expand a tree node and its children."""
        if not self.tree.exists(item_id): return
        self.tree.item(item_id, open=True)
        # Ensure children are loaded if opening causes 'Loading...' to resolve
        self.file_operations.on_tree_open(None) # Trigger loading check
        for child_id in self.tree.get_children(item_id):
            self.expand_recursive(child_id)

    def collapse_recursive(self, item_id):
         """Recursively collapse a tree node and its children."""
         if not self.tree.exists(item_id): return
         # Collapse children first
         for child_id in self.tree.get_children(item_id):
             self.collapse_recursive(child_id)
         # Collapse the item itself (if it's not the absolute root)
         if self.tree.parent(item_id) != "":
             self.tree.item(item_id, open=False)


    def on_tree_item_click(self, event):
        """Handle left-click events, primarily for checkbox toggling."""
        item_id = self.tree.identify_row(event.y)
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)

        # Only process clicks specifically on the 'select' column ('#1') checkbox area
        if item_id and region == "cell" and column == "#1":
            # Toggle the selection state of this item and its children
            current_tags = list(self.tree.item(item_id, "tags"))
            is_selected = "selected" in current_tags
            new_select_state = not is_selected
            self.update_item_selection(item_id, new_select_state)
            self.update_project_stats()
            return "break" # Prevent default click behavior like row selection highlight

        # Allow clicks on name/expander to proceed for default behavior (handled by double-click/open events)
        # Single clicks on the name itself won't do anything unless explicitly bound

    def on_tree_double_click(self, event):
        """Handle double-clicks to open folders or files."""
        item_id = self.tree.identify_row(event.y)
        if not item_id: return

        # If it's a folder, toggle its open state
        if "folder" in self.tree.item(item_id, "tags"):
            current_open_state = self.tree.item(item_id, "open")
            self.tree.item(item_id, open=not current_open_state)
        elif "file" in self.tree.item(item_id, "tags"):
            # If it's a file, try to open it with the default application
            path = self.file_operations.file_paths.get(item_id)
            if path and os.path.exists(path):
                try:
                    os.startfile(path)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open file: {e}")
            else:
                 messagebox.showwarning("Not Found", "The selected file's path does not exist.")


    def update_item_selection(self, item_id, should_select):
        """Updates the selection state of an item and its descendants."""
        if not self.tree.exists(item_id):
             return

        current_tags = list(self.tree.item(item_id, "tags"))
        # Filter out 'selected' tag if it exists, to avoid duplicates or removal errors
        current_tags = [tag for tag in current_tags if tag != 'selected']
        currently_selected = "selected" in self.tree.item(item_id, "tags") # Re-check initial state

        needs_update = False
        if should_select:
            # Add 'selected' tag if it's not already conceptually there
            if not currently_selected:
                current_tags.append("selected")
                needs_update = True
        else: # should_deselect
            # Remove 'selected' tag only if it was conceptually there
            if currently_selected:
                # We already filtered it out above, so just need to mark update
                needs_update = True

        # Apply the updated tags if a change occurred
        if needs_update:
             self.tree.item(item_id, tags=tuple(current_tags))
             self.update_selection_indicator(item_id) # Update checkbox visual

             # If it's a directory, recursively apply the same state to children
             # Check for 'folder' tag within the potentially updated current_tags
             if "folder" in current_tags:
                 for child_id in self.tree.get_children(item_id):
                     self.update_item_selection(child_id, should_select)


    def update_selection_indicator(self, item_id):
        """Update the checkbox visual in the 'select' column."""
        if not self.tree.exists(item_id): return

        if "selected" in self.tree.item(item_id, "tags"):
            self.tree.set(item_id, "select", "☑")  # Checked box
        else:
            self.tree.set(item_id, "select", "☐")  # Empty box


    def toggle_selection_spacebar(self, event):
        """Toggle selection state of focused item using the space bar."""
        item_id = self.tree.focus() # Get the item that has focus
        if not item_id:
            return

        # Determine the new selection state
        current_tags = list(self.tree.item(item_id, "tags"))
        is_selected = "selected" in current_tags
        new_select_state = not is_selected

        # Update the focused item and its descendants
        self.update_item_selection(item_id, new_select_state)
        self.update_project_stats()


    def select_all_visible(self):
        """Selects all currently visible items in the tree."""
        def select_recursive(parent_id):
            for item_id in self.tree.get_children(parent_id):
                if self.tree.exists(item_id): # Check existence
                    self.update_item_selection(item_id, True) # Select item and children

        # Start from top-level items
        for item_id in self.tree.get_children(""):
             select_recursive(item_id)

        self.update_project_stats()


    def deselect_all(self):
        """Deselects all items in the tree."""
        def deselect_recursive(parent_id):
             for item_id in self.tree.get_children(parent_id):
                if self.tree.exists(item_id): # Check existence
                    self.update_item_selection(item_id, False) # Deselect item and children

        # Start from top-level items
        for item_id in self.tree.get_children(""):
            deselect_recursive(item_id)

        self.update_project_stats()


    def apply_default_rules(self):
        """Apply default rules to the project rules text widget."""
        default_rules = self.default_rules_text.get("1.0", tk.END)
        # Ask for confirmation if project rules already exist?
        # current_project_rules = self.project_rules_text.get("1.0", tk.END).strip()
        # if current_project_rules and default_rules.strip() != current_project_rules:
        #    if not messagebox.askyesno("Overwrite Rules?", "Overwrite existing project rules with defaults?"):
        #        return
        self.project_rules_text.delete("1.0", tk.END)
        self.project_rules_text.insert("1.0", default_rules)
        self.project_manager._update_current_project_data() # Save change to project data
        self.project_manager.save_preferences()
        update_ui_status(self, "Default rules applied to current project")


    def edit_filetypes(self):
        """Open dialog to edit ignored file types/names."""
        dialog = FileTypeDialog(self.root, self.ignored_file_types)
        self.root.wait_window(dialog)
        if dialog.result is not None: # Check result exists (user didn't cancel)
            self.ignored_file_types = dialog.result
            # Preserve selections before rebuilding
            current_selections = set(self.file_operations.get_selected_paths())
            self.file_operations.build_tree(self.root_dir, current_selections) # Rebuild with new ignores
            self.project_manager.save_preferences() # Save updated ignores list


    def change_root_directory(self, path=None):
        """Change the root directory being displayed in the tree."""
        new_path_selected = False
        if path is None: # No path provided, open browse dialog
            browse_path = filedialog.askdirectory(
                initialdir=self.root_dir,
                title="Select Root Directory"
            )
            if not browse_path: return # User cancelled browse
            path = browse_path
            new_path_selected = True

        # Validate the chosen/entered path
        norm_path = os.path.normpath(path)
        if not os.path.isdir(norm_path):
            messagebox.showerror("Invalid Directory", f"The selected path is not a valid directory:\n{norm_path}")
            # Optionally clear the entry or revert path_var if browse failed validation
            # self.path_var.set(self.root_dir)
            return

        # Check if the path actually changed
        if norm_path == os.path.normpath(self.root_dir) and not new_path_selected:
            # If path entered manually is same as current, maybe just refresh?
            self.refresh_directory()
            return

        # Path is valid and different, proceed with change
        self.root_dir = norm_path
        self.path_var.set(norm_path) # Update entry widget

        # Clear pending selections when changing root fundamentally
        self.pending_selected_paths = set()
        # Build tree for the new root directory
        self.file_operations.build_tree(self.root_dir) # No selections to restore initially

        # Save the new root_dir to the current project's settings
        self.project_manager._update_current_project_data()
        self.project_manager.save_preferences()
        update_ui_status(self, f"Root directory changed to: {self.root_dir}")


    def change_output_directory(self):
        """Change the directory where merged files will be saved."""
        path = filedialog.askdirectory(
            initialdir=self.output_dir,
            title="Select Output Directory"
            )
        if path:
            norm_path = os.path.normpath(path)
            self.output_dir = norm_path
            # Save the change to the current project
            self.project_manager._update_current_project_data()
            self.project_manager.save_preferences()
            update_ui_status(self, f"Output directory set to: {norm_path}")


    def update_project_stats(self):
        """Update the statistics display based on current selections."""
        # Get all selected paths (files and dirs)
        selected_paths = self.file_operations.get_selected_paths()
        # Get only selected files for size/char counts
        selected_files_only = self.file_operations.get_selected_files_only()

        # Count total items mapped in the current view
        total_items_in_view = len(self.file_operations.file_paths)

        self.stats["files"] = total_items_in_view
        self.stats["selected"] = len(selected_paths) # Count of all selected items
        self.stats["size"] = calculate_project_size(self) # Uses selected_files_only
        self.stats["chars"] = count_characters_in_files(self) # Uses selected_files_only

        size_str = format_size(self.stats['size']) # Use utility function
        chars_str = f"{self.stats['chars']:,}" # Add commas for readability

        self.files_count_var.set(f"Total Items: {self.stats['files']}")
        self.selected_count_var.set(f"Selected Items: {self.stats['selected']}")
        self.size_var.set(f"Selected Files Size: {size_str}")
        self.chars_count_var.set(f"Selected Files Chars: {chars_str}")

        # Optionally update status bar as well
        # update_ui_status(self, f"{self.stats['selected']} items selected.")


    def refresh_directory(self):
        """Refresh the current directory view, preserving selections and open states."""
        current_dir = self.root_dir
        update_ui_status(self, f"Refreshing directory: {current_dir}...")

        # --- 1. Store current state ---
        # Store paths of all currently selected items
        previously_selected_paths = set(self.file_operations.get_selected_paths())
        # Store paths of all items currently in the tree map (before rebuild)
        all_existing_paths_in_map = set(self.file_operations.file_paths.values())

        # Store paths of open directories to restore view state
        open_paths = set()
        def find_open_paths_recursive(parent_id):
            for item_id in self.tree.get_children(parent_id):
                if self.tree.exists(item_id) and self.tree.item(item_id, 'open'):
                    path = self.file_operations.file_paths.get(item_id)
                    if path and os.path.isdir(path): # Check if it's a directory path
                        open_paths.add(path)
                        find_open_paths_recursive(item_id) # Recurse

        find_open_paths_recursive("") # Start from tree root

        # --- 2. Rebuild the tree ---
        # Pass the set of previously selected paths to build_tree for restoration
        self.file_operations.build_tree(current_dir, previously_selected_paths)
        # Note: build_tree now handles the restoration via restore_selection_state

        # --- 3. Auto-select NEW items (items not present before refresh) ---
        newly_selected_count = 0
        # Iterate through the *new* file paths map
        for item_id, path in self.file_operations.file_paths.items():
             # Auto-select if the path wasn't in the map before refresh AND is not the root itself
             if path not in all_existing_paths_in_map and path != current_dir:
                # Check it's not already selected (e.g., by restoration)
                if self.tree.exists(item_id) and "selected" not in self.tree.item(item_id, "tags"):
                    # Use update_item_selection to handle selection and indicator
                    self.update_item_selection(item_id, True) # Select this new item
                    newly_selected_count += 1

        # --- 4. Restore open state for directories using paths ---
        for path in open_paths:
            # Find the new item_id corresponding to the saved path
            # Since item_id is now the path, this is direct:
            new_item_id = path
            if self.tree.exists(new_item_id):
                try:
                    # Ensure it's a directory node before opening
                    if 'folder' in self.tree.item(new_item_id, 'tags'):
                        self.tree.item(new_item_id, open=True)
                        # Trigger content loading if necessary (similar to on_tree_open)
                        children = self.tree.get_children(new_item_id)
                        if children and self.tree.exists(children[0]) and self.tree.item(children[0], "text") == "Loading...":
                            self.tree.delete(children[0])
                            self.file_operations.process_directory(path, new_item_id, depth=self.file_operations.get_item_depth(new_item_id))
                except tk.TclError as e:
                    print(f"Warning: Could not re-open item {new_item_id} for path {path}: {e}")


        # --- 5. Update stats and UI ---
        self.update_project_stats() # Recalculate stats based on final selections
        restored_selection_count = len(self.file_operations.get_selected_paths())

        status_msg = f"Directory refreshed. {restored_selection_count} items currently selected."
        if newly_selected_count > 0:
            status_msg += f" {newly_selected_count} new items auto-selected."
        update_ui_status(self, status_msg)


    def on_closing(self):
        """Handle application close event."""
        # Save current project data before closing
        try:
             self.project_manager._update_current_project_data()
             self.project_manager.save_preferences()
        except Exception as e:
             print(f"Error saving preferences on close: {e}") # Log error but proceed with closing
        finally:
            self.root.destroy() # Close the Tkinter window