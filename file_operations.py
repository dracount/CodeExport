import os
import datetime
import shutil
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
import time

from ui_dialogs import ProgressDialog
from utils import update_ui_status, format_size # Added format_size import if needed here, though likely used more in app.py

class FileOperations:
    def __init__(self, app):
        self.app = app
        self.file_paths = {}  # Maps tree IDs (which are paths) to file paths
        self.pending_selection_restore = set() # Store paths to select during build and subsequent lazy loads for that cycle

    def build_tree(self, path, selected_paths_to_restore=None):
        """Build the file tree from the given root path, applying selection state during build."""
        self.pending_selection_restore = selected_paths_to_restore if selected_paths_to_restore is not None else set()

        for item in self.app.tree.get_children():
            if self.app.tree.exists(item): 
                self.app.tree.delete(item)

        self.file_paths = {} 

        try:
            norm_path = os.path.normpath(path)
            if not os.path.exists(norm_path) or not os.path.isdir(norm_path):
                 messagebox.showerror("Error", f"Root directory not found or is not a directory:\n{path}")
                 fallback_path = os.path.expanduser("~")
                 if os.path.exists(fallback_path) and os.path.isdir(fallback_path):
                     norm_path = fallback_path
                     self.app.root_dir = norm_path 
                     self.app.path_var.set(norm_path)
                 else:
                     messagebox.showerror("Fatal Error", "Cannot access root directory or home directory.")
                     self.app.root.quit() 
                     return 

            root_name = os.path.basename(norm_path) or norm_path 
        except Exception as e:
            messagebox.showerror("Error Setting Root", f"Failed to set root path '{path}': {e}")
            return 

        self.add_node("", root_name, norm_path, "directory") 

        if self.app.tree.exists(norm_path): 
             self.app.tree.item(norm_path, open=True) 
             self.process_directory(norm_path, norm_path) 
        else:
            messagebox.showerror("Error", f"Failed to insert root node for path: {norm_path}")
            self.pending_selection_restore = set() 
            return 

        update_ui_status(self.app, f"Loaded directory: {self.app.root_dir}")
        self.app.update_project_stats()

    def process_directory(self, path, parent_id, depth=0):
        """Process the contents of a directory for the tree view"""
        try:
            if depth > 15:  
                error_text = "Max depth reached"
                error_iid = f"{path}_error_max_depth_{depth}"
                self.app.tree.insert(parent_id, "end", iid=error_iid, text=error_text, values=("", "", ""), tags=("error",))
                return

            try:
                items = os.listdir(path)
            except PermissionError:
                 error_text = "Permission denied"
                 error_iid = f"{path}_error_permission"
                 self.app.tree.insert(parent_id, "end", iid=error_iid, text=error_text, values=("", "", ""), tags=("error",))
                 return
            except FileNotFoundError:
                error_text = "Not Found"
                error_iid = f"{path}_error_notfound"
                self.app.tree.insert(parent_id, "end", iid=error_iid, text=error_text, values=("", "", ""), tags=("error",))
                return
            except Exception as e:
                 error_text = f"Error listing: {e}"
                 error_iid = f"{path}_error_listing_{type(e).__name__}"
                 self.app.tree.insert(parent_id, "end", iid=error_iid, text=error_text, values=("", "", ""), tags=("error",))
                 return

            items.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))

            for item in items:
                full_path = os.path.join(path, item)
                norm_full_path = os.path.normpath(full_path) 

                base_name = os.path.basename(item)
                ext = os.path.splitext(item)[1].lower()
                if base_name.startswith(".") or \
                   any(ignore.lower() == base_name.lower() for ignore in self.app.ignored_file_types) or \
                   any(ignore.lower() == ext for ignore in self.app.ignored_file_types if ignore.startswith('.')):
                    continue

                try:
                    stats = os.stat(norm_full_path) 
                    size = stats.st_size
                    modified = datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")

                    if os.path.isdir(norm_full_path):
                        node_id = self.add_node(parent_id, item, norm_full_path, "directory")
                        if node_id: 
                            placeholder_iid = f"{norm_full_path}_placeholder"
                            self.app.tree.insert(node_id, "end", iid=placeholder_iid, text="Loading...", values=("", "", ""))
                    else:
                        size_str = format_size(size)
                        self.add_node(parent_id, item, norm_full_path, "file", size_str, modified)
                except PermissionError:
                    self.add_node(parent_id, item + " (Access Denied)", norm_full_path, "error")
                except FileNotFoundError:
                     self.add_node(parent_id, item + " (Not Found)", norm_full_path, "error")
                except Exception as e:
                    print(f"Warning: Could not process item {norm_full_path}: {e}") 
                    self.add_node(parent_id, item + f" (Error: {type(e).__name__})", norm_full_path, "error")
                    continue
        except Exception as e:
            print(f"Error processing directory {path}: {e}") 
            error_text=f"Error: {str(e)}"
            error_iid = f"{path}_error_processing_{type(e).__name__}"
            self.app.tree.insert(parent_id, "end", iid=error_iid, text=error_text, values=("", "", ""), tags=("error",))

    def add_node(self, parent_iid, text, norm_full_path, node_type, size_str="", modified=""):
        """Add a node to the tree view using the normalized path as iid"""
        if self.app.tree.exists(norm_full_path):
            return norm_full_path 

        try:
            node_id = self.app.tree.insert(parent_iid, "end", text=text, values=("☐", size_str, modified), iid=norm_full_path)
        except tk.TclError as e:
             print(f"Error inserting node with iid='{norm_full_path}': {e}. Skipping item.")
             return None

        self.file_paths[node_id] = norm_full_path

        tags_to_apply = []
        if node_type == "directory":
            tags_to_apply.append("folder")
        elif node_type == "file":
            tags_to_apply.append("file")
            ext = os.path.splitext(text)[1].lower()
            if ext in (".py", ".pyw"): tags_to_apply.append("python")
            elif ext in (".txt", ".md", ".log", ".json", ".yaml", ".yml", ".csv", ".xml"): tags_to_apply.append("text")
            elif ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico"): tags_to_apply.append("image")
        elif node_type == "error":
            tags_to_apply.append("error")
        self.app.tree.item(node_id, tags=tuple(tags_to_apply))

        # Determine selection state for this new node
        should_select_node = False
        if norm_full_path in self.pending_selection_restore:
            # This node itself was in the saved selection list
            should_select_node = True
        elif parent_iid and self.app.tree.exists(parent_iid):
            # Check if the parent was *explicitly* in the saved selection list
            # This prevents inheriting "selected" state if the parent was selected due to other reasons
            # (e.g. user clicked it after load but before this child was lazy-loaded).
            # For load/restore, selection should primarily come from pending_selection_restore.
            if parent_iid in self.pending_selection_restore and "folder" in self.app.tree.item(parent_iid, "tags"):
                 # If parent folder was in the restore list, its children should also be selected.
                 should_select_node = True
            # Removed general check for parent's current "selected" tag here to avoid
            # overly aggressive selection during lazy load if parent was selected interactively.
            # The primary mechanism for selection propagation is app.update_item_selection when user interacts.

        if should_select_node:
            # Use app.update_item_selection which handles recursion and UI update correctly.
            # This is crucial: if norm_full_path is a folder from pending_selection_restore,
            # this call will make it selected AND its children (if any are loaded immediately after)
            # will also get selected via this same add_node logic seeing their parent (norm_full_path)
            # was in pending_selection_restore.
            self.app.update_item_selection(node_id, True)

        return node_id

    def on_tree_open(self, event):
        """Handle tree open events - load contents when directory is expanded"""
        item = self.app.tree.focus() 
        if not item or not self.app.tree.exists(item):
            return

        path = item
        if not path: return # Should not happen with valid item
        
        # Check if path is a directory before processing
        is_dir = False
        try:
            if os.path.isdir(path):
                is_dir = True
        except OSError: # Path too long, etc.
            return 

        if not is_dir:
             # If it's an error node or something else, don't try to process as directory
            if "_error_" in path or "_placeholder" in path or "file" in self.app.tree.item(item, "tags"):
                return
            # If it's somehow not a dir and not an error/placeholder, also return.
            # This might indicate an issue with iid management if 'item' is not a path.
            return

        children = self.app.tree.get_children(item)
        if children:
            first_child_id = children[0]
            if self.app.tree.exists(first_child_id) and self.app.tree.item(first_child_id, "text") == "Loading...":
                self.app.tree.delete(first_child_id)
                self.process_directory(path, item, depth=self.get_item_depth(item))


    def get_item_depth(self, item):
        """Get the depth of an item in the tree"""
        depth = 0
        parent = self.app.tree.parent(item)
        while parent:
            depth += 1
            try:
                parent = self.app.tree.parent(parent)
            except tk.TclError:
                 print(f"Warning: Could not get parent for item {parent} during depth calculation.")
                 break 
        return depth

    def merge_files(self):
        """Prepare and execute file merge operation"""
        selected_files_only = self.get_selected_files_only()

        if not selected_files_only:
            messagebox.showinfo("No Files Selected", "Please select one or more files to merge.")
            return

        if not os.path.exists(self.app.output_dir):
             try:
                 os.makedirs(self.app.output_dir)
             except Exception as e:
                 messagebox.showerror("Output Directory Error", f"Could not create output directory:\n{self.app.output_dir}\nError: {e}")
                 return

        output_filename = filedialog.asksaveasfilename(
            initialdir=self.app.output_dir,
            title="Save Merged File As",
            defaultextension=".txt", 
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )

        if not output_filename:
            return 

        progress_dialog = ProgressDialog(self.app.root, "Merging Files", len(selected_files_only))
        merge_thread = threading.Thread(
            target=self._perform_merge,
            args=(selected_files_only, output_filename, progress_dialog), 
            daemon=True 
        )
        merge_thread.start()


    def _perform_merge(self, files, output_path, progress_dialog):
        """Perform the actual file merge operation"""
        try:
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            prompt = self.app.prompt_text.get("1.0", tk.END).strip()
            project_rules = self.app.project_rules_text.get("1.0", tk.END).strip()

            total_files = len(files)
            with open(output_path, 'w', encoding='utf-8', errors='replace') as outfile:
                outfile.write("--- START OF FILE export.txt ---\n\n") 

                if prompt:
                    if not prompt.startswith("GOAL:"): prompt = "GOAL:\n" + prompt
                    outfile.write(prompt + "\n")
                    outfile.write("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")

                if project_rules:
                    if not project_rules.startswith("RULES:"): project_rules = "RULES:\n" + project_rules
                    outfile.write(project_rules + "\n")
                    outfile.write("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")

                outfile.write("="*80 + "\n")
                outfile.write(f"MERGED FILE - Created {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                outfile.write(f"Contains {total_files} files\n")
                outfile.write("="*80 + "\n\n")

                directory_structure = self.generate_file_structure(files)
                outfile.write(directory_structure)
                outfile.write("\n\n" + "="*80 + "\n")

                for i, file_path in enumerate(files):
                    if progress_dialog.cancelled:
                        update_ui_status(self.app, "Merge cancelled by user.")
                        return 

                    progress_dialog.update_progress(i + 1, f"Processing {os.path.basename(file_path)}")

                    outfile.write("\n" + "-"*80 + "\n")
                    outfile.write(f"FILE: {os.path.normpath(file_path)}\n")
                    outfile.write("-"*80 + "\n\n")

                    try:
                        self.write_content(file_path, outfile)
                    except Exception as e:
                        outfile.write(f"\nERROR: Could not read file '{os.path.basename(file_path)}': {str(e)}\n")
                    outfile.write("\n\n") 
                outfile.write("\n--- END OF FILE export.txt ---\n")

            if not progress_dialog.cancelled:
                 progress_dialog.update_progress(total_files, "Merge complete!", True)
                 self.app.root.after(100, lambda: update_ui_status(self.app, f"Files merged successfully to: {output_path}"))
                 self.app.root.after(150, lambda: self.safe_startfile(output_dir)) 
                 self.app.root.after(200, lambda: self.app.project_manager._update_current_project_data())
                 self.app.root.after(250, lambda: self.app.project_manager.save_preferences())
        except Exception as e:
             error_msg = f"Failed to merge files: {str(e)}"
             print(f"Merge Error: {error_msg}") 
             if progress_dialog:
                 progress_dialog.update_progress(progress_dialog.current, f"Error: {e}", True) 
             self.app.root.after(100, lambda: messagebox.showerror("Merge Error", error_msg))
             self.app.root.after(150, lambda: update_ui_status(self.app, "Merge failed."))
        finally:
            if progress_dialog and progress_dialog.winfo_exists():
                progress_dialog.after(500, progress_dialog.destroy) 


    def write_content(self, file_path, outfile):
        """Write file content to the output file with line numbers"""
        line_number = 1
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as infile:
                for line in infile:
                    outfile.write(f"{line_number:5d} {line.rstrip()}\n")
                    line_number += 1
        except Exception as e:
            outfile.write(f"ERROR reading file content: {e}\n")

    def get_selected_paths(self):
        """Get a list of paths for all selected items (files and directories) in the tree"""
        selected_paths = []
        def collect_paths_recursive(node_id):
            if not self.app.tree.exists(node_id):
                return
            item_tags = self.app.tree.item(node_id, "tags")
            path = node_id 
            if path: 
                if "selected" in item_tags:
                    if "_error_" not in path and "_placeholder" not in path:
                        selected_paths.append(path)
                for child in self.app.tree.get_children(node_id):
                    collect_paths_recursive(child)
        for item in self.app.tree.get_children(""): 
            collect_paths_recursive(item)
        return list(set(selected_paths))


    def get_selected_files_only(self):
        """Get a list of selected files (not directories) in the tree"""
        selected_files = []
        def collect_files_recursive(node_id):
             if not self.app.tree.exists(node_id): return
             item_tags = self.app.tree.item(node_id, "tags")
             path = node_id 
             if path:
                 if "selected" in item_tags and "file" in item_tags:
                    try:
                        if os.path.isfile(path):
                            selected_files.append(path)
                    except OSError: 
                        pass
                 for child in self.app.tree.get_children(node_id):
                     collect_files_recursive(child)
        for item in self.app.tree.get_children(""):
            collect_files_recursive(item)
        return list(set(selected_files))

    def generate_file_structure(self, files):
        """Generate a text representation of the file structure based on a list of file paths"""
        if not files:
            return "DIRECTORY STRUCTURE:\n(No files selected)"
        try:
            norm_files = [os.path.normpath(f) for f in files]
            existing_files = [f for f in norm_files if os.path.exists(f)]
            if not existing_files: common_path = None 
            else:
                 common_path = os.path.commonpath(existing_files)
                 if common_path and not os.path.isdir(common_path):
                      common_path = os.path.dirname(common_path)
        except ValueError:
             common_path = None 
        dirs = {}
        for file_path in files:
             norm_file_path = os.path.normpath(file_path)
             dir_path = os.path.dirname(norm_file_path)
             if common_path and norm_file_path.startswith(common_path + os.sep): # Ensure common_path is prefix
                 relative_dir = os.path.relpath(dir_path, common_path)
                 # Handle dir_path being the same as common_path (files in the common root)
                 display_dir_name = relative_dir if relative_dir != '.' else os.path.basename(common_path) # or just common_path
                 # This needs to be robust for display
                 if relative_dir == '.': display_dir = common_path
                 else: display_dir = os.path.join(common_path, relative_dir) # Reconstruct with common_path for full display path

             else: # No common path or different drives
                 display_dir = dir_path
             
             display_dir = os.path.normpath(display_dir) # Normalize for dictionary key consistency

             if display_dir not in dirs:
                 dirs[display_dir] = []
             dirs[display_dir].append(os.path.basename(norm_file_path))
        output = ["DIRECTORY STRUCTURE:"]
        for dir_path_key in sorted(dirs.keys()):
            output.append(f"\nDirectory: {dir_path_key}")
            for file_item in sorted(dirs[dir_path_key]):
                output.append(f"  |- {file_item}")
        return "\n".join(output)

    def safe_startfile(self, path):
        """Attempt to open a file or directory safely."""
        try:
            norm_path = os.path.normpath(path)
            if os.path.exists(norm_path):
                 os.startfile(norm_path)
            else:
                 update_ui_status(self.app, f"Cannot open: Path not found '{norm_path}'")
        except Exception as e:
            update_ui_status(self.app, f"Error opening path '{path}': {e}")
            print(f"Error using os.startfile on '{path}': {e}") 