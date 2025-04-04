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

    def build_tree(self, path, selected_paths_to_restore=None):
        """Build the file tree from the given root path and restore selection"""
        if selected_paths_to_restore is None:
            selected_paths_to_restore = set()

        # Clear existing tree
        for item in self.app.tree.get_children():
            if self.app.tree.exists(item): # Check if item still exists before deleting
                self.app.tree.delete(item)

        self.file_paths = {} # Reset path mapping

        # Set root node (use os.path.normpath for consistency)
        try:
            norm_path = os.path.normpath(path)
            if not os.path.exists(norm_path) or not os.path.isdir(norm_path):
                 messagebox.showerror("Error", f"Root directory not found or is not a directory:\n{path}")
                 # Attempt to fallback to user's home directory
                 fallback_path = os.path.expanduser("~")
                 if os.path.exists(fallback_path) and os.path.isdir(fallback_path):
                     norm_path = fallback_path
                     self.app.root_dir = norm_path # Update app state
                     self.app.path_var.set(norm_path)
                 else:
                     messagebox.showerror("Fatal Error", "Cannot access root directory or home directory.")
                     self.app.root.quit() # Or handle more gracefully
                     return # Stop build process

            root_name = os.path.basename(norm_path) or norm_path # Handle drive letters like C:\
        except Exception as e:
            messagebox.showerror("Error Setting Root", f"Failed to set root path '{path}': {e}")
            return # Stop build process


        # Insert root node - initially not selected, path stored
        # Use path itself as iid for easier lookup during restoration
        root_id = self.app.tree.insert("", "end", text=root_name, values=("☐", "", ""), iid=norm_path, open=True) # Start open
        self.file_paths[root_id] = norm_path
        self.app.tree.item(root_id, tags=("folder",)) # Tag root as folder

        # Process the directory contents starting under the root_id
        self.process_directory(norm_path, root_id) # Build the rest of the tree

        # Restore selection state *after* the tree is fully built
        if selected_paths_to_restore:
            self.restore_selection_state(selected_paths_to_restore)
            # Clear the pending set on the app instance if it matches what we just restored
            if hasattr(self.app, 'pending_selected_paths') and self.app.pending_selected_paths == selected_paths_to_restore:
                 self.app.pending_selected_paths = set()


        update_ui_status(self.app, f"Loaded directory: {self.app.root_dir}")

        # Update stats AFTER building and restoring selections
        self.app.update_project_stats()

    def process_directory(self, path, parent_id, depth=0):
        """Process the contents of a directory for the tree view"""
        try:
            # Stop if we're too deep to prevent performance issues
            if depth > 15:  # Limit directory depth
                # Use a unique iid for error messages to avoid conflicts if path repeats
                error_text = "Max depth reached"
                error_iid = f"{path}_error_max_depth_{depth}"
                self.app.tree.insert(parent_id, "end", iid=error_iid, text=error_text, values=("", "", ""), tags=("error",))
                # No need to add to file_paths as it's not a real item
                return

            # List directory contents, handle potential errors
            try:
                items = os.listdir(path)
            except PermissionError:
                 error_text = "Permission denied"
                 error_iid = f"{path}_error_permission"
                 error_id = self.app.tree.insert(parent_id, "end", iid=error_iid, text=error_text, values=("", "", ""), tags=("error",))
                 # Map the *parent* path to the error id if needed, though error nodes usually aren't interactive
                 # self.file_paths[error_id] = path # Maybe map the error iid?
                 return
            except FileNotFoundError:
                error_text = "Not Found"
                error_iid = f"{path}_error_notfound"
                error_id = self.app.tree.insert(parent_id, "end", iid=error_iid, text=error_text, values=("", "", ""), tags=("error",))
                return
            except Exception as e:
                 error_text = f"Error listing: {e}"
                 error_iid = f"{path}_error_listing_{type(e).__name__}"
                 error_id = self.app.tree.insert(parent_id, "end", iid=error_iid, text=error_text, values=("", "", ""), tags=("error",))
                 return

            # Sort items: directories first, then files, case-insensitive
            items.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))

            # Add directories first, then files
            for item in items:
                full_path = os.path.join(path, item)
                norm_full_path = os.path.normpath(full_path) # Normalize here

                # Skip hidden files/folders (starting with '.') and ignored types/names
                base_name = os.path.basename(item)
                ext = os.path.splitext(item)[1].lower()
                if base_name.startswith(".") or \
                   any(ignore.lower() == base_name.lower() for ignore in self.app.ignored_file_types) or \
                   any(ignore.lower() == ext for ignore in self.app.ignored_file_types if ignore.startswith('.')):
                    continue

                try:
                    # Get file information
                    stats = os.stat(norm_full_path) # Use normalized path
                    size = stats.st_size
                    modified = datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")

                    if os.path.isdir(norm_full_path):
                        # Add directory node using norm_full_path as iid
                        node_id = self.add_node(parent_id, item, norm_full_path, "directory")
                        if node_id: # Check if node was added successfully
                            # Insert placeholder, expanded later on demand
                            # Use a unique placeholder iid to avoid clashes
                            placeholder_iid = f"{norm_full_path}_placeholder"
                            self.app.tree.insert(node_id, "end", iid=placeholder_iid, text="Loading...", values=("", "", ""))
                    else:
                        # Format size using the utility
                        size_str = format_size(size)
                        # Add file node using norm_full_path as iid
                        self.add_node(parent_id, item, norm_full_path, "file", size_str, modified)
                except PermissionError:
                    self.add_node(parent_id, item + " (Access Denied)", norm_full_path, "error")
                except FileNotFoundError:
                     # File might have been deleted between listdir and stat
                     self.add_node(parent_id, item + " (Not Found)", norm_full_path, "error")
                except Exception as e:
                    # Skip files we can't access or stat
                    print(f"Warning: Could not process item {norm_full_path}: {e}") # Log warning
                    self.add_node(parent_id, item + f" (Error: {type(e).__name__})", norm_full_path, "error")
                    continue

        except Exception as e:
            # Handle other errors during processing
            print(f"Error processing directory {path}: {e}") # Log error
            error_text=f"Error: {str(e)}"
            error_iid = f"{path}_error_processing_{type(e).__name__}"
            error_id = self.app.tree.insert(parent_id, "end", iid=error_iid, text=error_text, values=("", "", ""), tags=("error",))
            # No file path mapping for general processing error

    def add_node(self, parent, text, norm_full_path, node_type, size_str="", modified=""):
        """Add a node to the tree view using the normalized path as iid"""
        # Check if a node with this path (iid) already exists under this parent
        # This helps prevent duplicates if process_directory is called multiple times somehow
        if self.app.tree.exists(norm_full_path):
            # Optionally update existing node instead of skipping?
            # print(f"Warning: Node with path {norm_full_path} already exists. Skipping add.")
            # Update existing item?
            # self.app.tree.item(norm_full_path, text=text, values=("☐", size_str, modified)) # Reset values?
            return norm_full_path # Return existing id

        # Create the node with default unselected state, using path as iid
        try:
            node_id = self.app.tree.insert(parent, "end", text=text, values=("☐", size_str, modified), iid=norm_full_path)
        except tk.TclError as e:
             # This can happen if the iid (path) is somehow considered invalid by Tcl/Tk
             print(f"Error inserting node with iid='{norm_full_path}': {e}. Skipping item.")
             return None

        # Store the path using the node_id (which is the path)
        # Redundant mapping? iid is the path. But useful for quick checks.
        self.file_paths[node_id] = norm_full_path

        # Apply tags based on type
        tags_to_apply = []
        if node_type == "directory":
            tags_to_apply.append("folder")
        elif node_type == "file":
            tags_to_apply.append("file")
            ext = os.path.splitext(text)[1].lower()
            if ext in (".py", ".pyw"):
                tags_to_apply.append("python")
            elif ext in (".txt", ".md", ".log", ".json", ".yaml", ".yml", ".csv", ".xml"):
                tags_to_apply.append("text")
            elif ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico"):
                tags_to_apply.append("image")
            # Add more specific types if needed
        elif node_type == "error":
            tags_to_apply.append("error")

        # Set the tags (initial state is unselected)
        self.app.tree.item(node_id, tags=tuple(tags_to_apply))

        return node_id

    def on_tree_open(self, event):
        """Handle tree open events - load contents when directory is expanded"""
        item = self.app.tree.focus() # The item being opened
        if not item or not self.app.tree.exists(item):
            return

        # Get the item path (which is the item id)
        path = item
        if not path or not os.path.isdir(path):
            # Check if it's a path-like error node or placeholder before returning
            if "_error_" in path or "_placeholder" in path:
                return
            # Check if the path actually exists and is a directory
            try:
                if not os.path.isdir(path):
                    return
            except OSError: # Handle potential errors like path too long
                return


        # Check for "Loading..." placeholder
        children = self.app.tree.get_children(item)
        if children:
            first_child_id = children[0]
            if self.app.tree.exists(first_child_id) and self.app.tree.item(first_child_id, "text") == "Loading...":
                # Delete placeholder before loading actual content
                self.app.tree.delete(first_child_id)
                # Load actual content
                self.process_directory(path, item, depth=self.get_item_depth(item))


    def get_item_depth(self, item):
        """Get the depth of an item in the tree"""
        depth = 0
        parent = self.app.tree.parent(item)
        while parent:
            depth += 1
            # Handle potential case where parent is not found (shouldn't happen with valid iids)
            try:
                parent = self.app.tree.parent(parent)
            except tk.TclError:
                 print(f"Warning: Could not get parent for item {parent} during depth calculation.")
                 break # Stop calculation if hierarchy is broken
        return depth

    # toggle_children and update_parents might be less necessary with the new
    # recursive toggle logic in app.py, but keep if needed for other purposes.
    # def toggle_children(self, parent, tag_state): ...
    # def update_parents(self, child): ...

    def merge_files(self):
        """Prepare and execute file merge operation"""
        # Use the method that gets only files for merging
        selected_files_only = self.get_selected_files_only()

        if not selected_files_only:
            messagebox.showinfo("No Files Selected", "Please select one or more files to merge.")
            return

        # Ensure output directory exists
        if not os.path.exists(self.app.output_dir):
             try:
                 os.makedirs(self.app.output_dir)
             except Exception as e:
                 messagebox.showerror("Output Directory Error", f"Could not create output directory:\n{self.app.output_dir}\nError: {e}")
                 return

        # Ask for output filename
        output_filename = filedialog.asksaveasfilename(
            initialdir=self.app.output_dir,
            title="Save Merged File As",
            defaultextension=".txt", # Suggest .txt
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )

        if not output_filename:
            return # User cancelled

        # Create a progress dialog
        progress_dialog = ProgressDialog(self.app.root, "Merging Files", len(selected_files_only))

        # Start merge process in a separate thread
        merge_thread = threading.Thread(
            target=self._perform_merge,
            args=(selected_files_only, output_filename, progress_dialog), # Pass dialog itself
            daemon=True # Ensure thread exits if main app closes
        )
        merge_thread.start()

        # Show dialog (will block until closed or operation finishes/cancels)
        # Handled by ProgressDialog's grab_set and wait_window mechanism implicitly
        # self.app.root.wait_window(progress_dialog) # This might block UI updates, let dialog manage itself


    def _perform_merge(self, files, output_path, progress_dialog):
        """Perform the actual file merge operation"""
        try:
            # Create output directory if needed (double check)
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Get prompt and project rules from UI thread safely (or pass them)
            # For simplicity here, assume app state is accessible, but passing is safer
            prompt = self.app.prompt_text.get("1.0", tk.END).strip()
            project_rules = self.app.project_rules_text.get("1.0", tk.END).strip()

            total_files = len(files)
            with open(output_path, 'w', encoding='utf-8', errors='replace') as outfile:
                # Write header info
                outfile.write("--- START OF FILE export.txt ---\n\n") # Added standard header

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

                # Add directory structure (using the files being merged)
                directory_structure = self.generate_file_structure(files)
                outfile.write(directory_structure)
                outfile.write("\n\n" + "="*80 + "\n")

                # Process each file
                for i, file_path in enumerate(files):
                    # Check for cancellation via progress dialog
                    if progress_dialog.cancelled:
                        update_ui_status(self.app, "Merge cancelled by user.")
                        # Clean up partially written file? Optional.
                        # try: os.remove(output_path)
                        # except: pass
                        return # Stop processing

                    # Update progress (use thread-safe queue or after() if modifying UI directly)
                    progress_dialog.update_progress(i + 1, f"Processing {os.path.basename(file_path)}")

                    # Write file separator and content
                    outfile.write("\n" + "-"*80 + "\n")
                    # Use normpath for consistent display
                    outfile.write(f"FILE: {os.path.normpath(file_path)}\n")
                    outfile.write("-"*80 + "\n\n")

                    try:
                        self.write_content(file_path, outfile)
                    except Exception as e:
                        outfile.write(f"\nERROR: Could not read file '{os.path.basename(file_path)}': {str(e)}\n")

                    outfile.write("\n\n") # Spacing after file content

                # Write footer
                outfile.write("\n--- END OF FILE export.txt ---\n")


            # Merge completed successfully (if not cancelled)
            if not progress_dialog.cancelled:
                 progress_dialog.update_progress(total_files, "Merge complete!", True)
                 # Use app.root.after for thread-safe UI updates
                 self.app.root.after(100, lambda: update_ui_status(self.app, f"Files merged successfully to: {output_path}"))
                 self.app.root.after(150, lambda: self.safe_startfile(output_dir)) # Safely open directory
                 # Save project state after successful merge (includes current selections)
                 self.app.root.after(200, lambda: self.app.project_manager._update_current_project_data())
                 self.app.root.after(250, lambda: self.app.project_manager.save_preferences())


        except Exception as e:
            # Handle errors during the merge process
             error_msg = f"Failed to merge files: {str(e)}"
             print(f"Merge Error: {error_msg}") # Log detailed error
             # Safely update UI and close progress dialog on error
             if progress_dialog:
                 progress_dialog.update_progress(progress_dialog.current, f"Error: {e}", True) # Mark as finished (with error)
             self.app.root.after(100, lambda: messagebox.showerror("Merge Error", error_msg))
             self.app.root.after(150, lambda: update_ui_status(self.app, "Merge failed."))
        finally:
            # Ensure progress dialog closes even if an unexpected error occurs before 'finished=True'
            if progress_dialog and progress_dialog.winfo_exists():
                progress_dialog.after(500, progress_dialog.destroy) # Schedule close just in case


    def write_content(self, file_path, outfile):
        """Write file content to the output file with line numbers"""
        line_number = 1
        try:
            # Try UTF-8 first, replacing errors to avoid crashes
            with open(file_path, 'r', encoding='utf-8', errors='replace') as infile:
                for line in infile:
                    # Strip trailing whitespace before checking if line is empty
                    stripped_line = line.rstrip()
                    # Write line number and original line content
                    # Use rstrip() on the line itself to avoid extra blank lines in output
                    outfile.write(f"{line_number:5d} {line.rstrip()}\n")
                    line_number += 1
        except Exception as e:
            # Broad catch for other file reading issues
            outfile.write(f"ERROR reading file content: {e}\n")

    def get_selected_paths(self):
        """Get a list of paths for all selected items (files and directories) in the tree"""
        selected_paths = []

        def collect_paths_recursive(node_id):
            # Check if node exists before accessing properties
            if not self.app.tree.exists(node_id):
                # print(f"Warning: Node {node_id} not found during selection collection.")
                return

            item_tags = self.app.tree.item(node_id, "tags")
            # Path is the node_id itself
            path = node_id

            if path: # Ensure path is not empty (shouldn't happen for valid nodes)
                if "selected" in item_tags:
                    # Check if it's a real file/dir path, not an error/placeholder node id
                    if "_error_" not in path and "_placeholder" not in path:
                        selected_paths.append(path)

                # Recursively check children (no need to check if folder, get_children handles leaves)
                for child in self.app.tree.get_children(node_id):
                    collect_paths_recursive(child)

        # Start from top-level nodes (which should be only the root node initially)
        for item in self.app.tree.get_children(""): # Get children of the invisible root
            collect_paths_recursive(item)

        # Remove duplicates just in case (shouldn't happen with recursive logic but safe)
        return list(set(selected_paths))


    def get_selected_files_only(self):
        """Get a list of selected files (not directories) in the tree"""
        selected_files = []

        def collect_files_recursive(node_id):
             # Check if node exists
             if not self.app.tree.exists(node_id): return

             item_tags = self.app.tree.item(node_id, "tags")
             # Path is the node_id itself
             path = node_id

             if path:
                 # Add if selected AND it's tagged as a file
                 # Check os.path.isfile as a final verification
                 if "selected" in item_tags and "file" in item_tags:
                    try:
                        if os.path.isfile(path):
                            selected_files.append(path)
                        #else: print(f"Warning: Item {path} tagged as file but os.path.isfile is false.") # Debugging
                    except OSError: # Handle errors like path too long
                        pass

                 # Recurse into children regardless of current node type (needed to find files in selected folders)
                 for child in self.app.tree.get_children(node_id):
                     collect_files_recursive(child)

        # Start from top-level nodes
        for item in self.app.tree.get_children(""):
            collect_files_recursive(item)

        # Return unique list
        return list(set(selected_files))


    def restore_selection_state(self, selected_paths_set):
        """Restore selection state for items (files and directories) in the tree"""
        if not selected_paths_set:
            return

        restored_count = 0
        deselected_count = 0
        processed_nodes = set() # Keep track of nodes processed to avoid redundant calls

        # Define a recursive function to process nodes
        def process_node(item_id):
            if item_id in processed_nodes or not self.app.tree.exists(item_id):
                return

            processed_nodes.add(item_id)
            should_be_selected = item_id in selected_paths_set

            # Check if it's an actual file/folder path, not an error/placeholder
            is_valid_path = "_error_" not in item_id and "_placeholder" not in item_id

            if is_valid_path:
                current_tags = self.app.tree.item(item_id, "tags")
                is_currently_selected = "selected" in current_tags

                if should_be_selected and not is_currently_selected:
                     # Use update_item_selection to handle recursive selection and visuals
                     # We pass False for should_select initially to just update the indicator
                     # for the current node, then handle children recursion manually below
                     # to avoid triggering updates multiple times for the same node.
                     # Correction: Just call update_item_selection - it handles recursion correctly.
                    self.app.update_item_selection(item_id, True)
                    nonlocal restored_count
                    restored_count += 1 # Count successful restorations
                elif not should_be_selected and is_currently_selected:
                    # Explicitly deselect if it shouldn't be selected but currently is
                    self.app.update_item_selection(item_id, False)
                    nonlocal deselected_count
                    deselected_count +=1

            # Process children regardless of the current node's selection state
            for child_id in self.app.tree.get_children(item_id):
                process_node(child_id)

        # Start processing from the root node(s)
        for root_item_id in self.app.tree.get_children(""):
            process_node(root_item_id)

        # Note: update_project_stats is called in build_tree after restoration finishes.
        if restored_count > 0 or deselected_count > 0:
            print(f"Restored selection state: {restored_count} items selected, {deselected_count} items deselected.")


    def generate_file_structure(self, files):
        """Generate a text representation of the file structure based on a list of file paths"""
        if not files:
            return "DIRECTORY STRUCTURE:\n(No files selected)"

        # Find the common base directory to make the structure relative
        try:
            # Use normpath to handle mixed separators and trailing slashes
            norm_files = [os.path.normpath(f) for f in files]
            # Filter out non-existent files before finding common path
            existing_files = [f for f in norm_files if os.path.exists(f)]
            if not existing_files:
                 common_path = None # No common path if no files exist
            else:
                 common_path = os.path.commonpath(existing_files)
                 # Ensure common_path is a directory, if it points to a file, get its dirname
                 if common_path and not os.path.isdir(common_path):
                      common_path = os.path.dirname(common_path)

        except ValueError:
             # Happens if files are on different drives (e.g., C:\ and D:\)
             common_path = None # Cannot determine common path easily

        # Group files by directory relative to the common path or root
        dirs = {}
        for file_path in files:
             norm_file_path = os.path.normpath(file_path)
             dir_path = os.path.dirname(norm_file_path)

             # Make dir_path relative if possible and meaningful
             if common_path and norm_file_path.startswith(common_path + os.sep):
                 relative_dir = os.path.relpath(dir_path, common_path)
                 # Use '.' for files directly in the common path
                 display_dir = f"{common_path}{os.sep}{relative_dir}" if relative_dir != '.' else common_path
             else:
                 # Show full path if no commonality, different drives, or file is the common path itself
                 display_dir = dir_path

             if display_dir not in dirs:
                 dirs[display_dir] = []
             dirs[display_dir].append(os.path.basename(norm_file_path))


        # Format output
        output = ["DIRECTORY STRUCTURE:"]
        # Sort directories for consistent output
        for dir_path in sorted(dirs.keys()):
            output.append(f"\nDirectory: {dir_path}")
            # Sort files within each directory
            for file in sorted(dirs[dir_path]):
                output.append(f"  |- {file}")

        return "\n".join(output)

    def safe_startfile(self, path):
        """Attempt to open a file or directory safely."""
        try:
            # Ensure path is normalized for the OS
            norm_path = os.path.normpath(path)
            if os.path.exists(norm_path):
                 os.startfile(norm_path)
            else:
                 update_ui_status(self.app, f"Cannot open: Path not found '{norm_path}'")
        except Exception as e:
            update_ui_status(self.app, f"Error opening path '{path}': {e}")
            print(f"Error using os.startfile on '{path}': {e}") # Log detailed error