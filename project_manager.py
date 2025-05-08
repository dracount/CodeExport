import os
import json
import datetime
import copy
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog # Added filedialog just in case, though not used in this diff
import threading # Not directly used in this diff, but present
import time # Not directly used in this diff, but present

from ui_dialogs import ProjectManagerDialog
from utils import update_ui_status

class ProjectManager:
    def __init__(self, app):
        self.app = app
        self.config_dir = os.path.join(os.path.expanduser("~"), ".filemerger")
        self.config_file = os.path.join(self.config_dir, "preferences.json")
        
        # Create config directory if it doesn't exist
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
    
    def load_preferences(self):
        """Load saved projects and preferences"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                # Load projects
                if "projects" in data:
                    self.app.projects = data["projects"]
                
                # Load current project
                if "current_project" in data and data["current_project"] in self.app.projects:
                    self.app.current_project = data["current_project"]
                    project_data = self.app.projects[self.app.current_project]
                    self._apply_project_settings(project_data)
                else:
                    self._init_default_project()
                
                # Update UI
                self.app.project_name_var.set(self.app.current_project)
                update_ui_status(self.app, f"Project {self.app.current_project} loaded")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load preferences: {str(e)}")
                self._init_default_project()
        else:
            self._init_default_project()
    
    def save_preferences(self):
        """Save current project state TO DISK"""
        # Note: _update_current_project_data should be called BEFORE this
        # if the goal is to save the latest UI state into the projects dictionary.
        try:
            data = {
                "projects": self.app.projects,
                "current_project": self.app.current_project,
                "last_saved": datetime.datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # update_ui_status(self.app, "Preferences saved to disk") # Make it more specific if called explicitly
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save preferences: {str(e)}")

    def save_current_project_explicitly(self):
        """Explicitly save the current project's state."""
        self._update_current_project_data() # Ensure current UI state (selections, text fields) is in self.app.projects
        self.save_preferences() # Write to disk
        update_ui_status(self.app, f"Project '{self.app.current_project}' saved.")

    def create_project(self, name=None):
        """Create new project"""
        if name is None:
            name = simpledialog.askstring("New Project", "Enter project name:", parent=self.app.root)
        
        if name:
            if name in self.app.projects:
                messagebox.showerror("Error", f"Project '{name}' already exists!")
                return
            
            # Save current project's state before creating a new one
            self._update_current_project_data()
            # self.save_preferences() # Not strictly needed here as _switch_to_project will save after.

            # Create a new project configuration using current app state as baseline
            self.app.projects[name] = {
                "created": datetime.datetime.now().isoformat(),
                "modified": datetime.datetime.now().isoformat(),
                "root_dir": self.app.root_dir, # Current root_dir
                "output_dir": self.app.output_dir, # Current output_dir
                "ignored_file_types": copy.deepcopy(self.app.ignored_file_types), # Current ignored types
                "selected_paths_relative": [], # New project starts with no selections
                "default_rules": self.app.default_rules_text.get("1.0", tk.END).strip(), # Current default rules
                "project_rules": "", # New project specific rules are empty initially
                "prompt": "" # New project prompt is empty initially
            }
            
            self._switch_to_project(name) # This will also call save_preferences
            
            messagebox.showinfo("Success", f"Project '{name}' created")
    
    def clone_current_project(self):
        """Clone existing project"""
        current_project_name = self.app.current_project
        name = simpledialog.askstring("Clone Project", 
                                      f"Enter name for the clone of '{current_project_name}':", 
                                      parent=self.app.root)
        
        if name:
            if name in self.app.projects:
                messagebox.showerror("Error", f"Project '{name}' already exists!")
                return
            
            # Ensure current project data (like selections) is up-to-date before cloning
            self._update_current_project_data() 
            
            # Clone the current project (which is now up-to-date in self.app.projects)
            self.app.projects[name] = copy.deepcopy(self.app.projects[current_project_name])
            self.app.projects[name]["created"] = datetime.datetime.now().isoformat()
            self.app.projects[name]["modified"] = datetime.datetime.now().isoformat() # Mark modification for clone
            
            self._switch_to_project(name) # This will also call save_preferences
            
            messagebox.showinfo("Success", f"Project '{name}' created as a clone of '{current_project_name}'")
    
    def manage_projects(self):
        """Show project management dialog"""
        dialog = ProjectManagerDialog(self.app.root, self.app.projects, self.app.current_project)
        self.app.root.wait_window(dialog)
        
        if dialog.result:
            action, project_name_arg = dialog.result # Renamed `project` to `project_name_arg` for clarity
            
            if action == "switch":
                self._switch_to_project(project_name_arg)
            elif action == "delete":
                self._delete_project(project_name_arg)
            elif action == "rename":
                new_name = simpledialog.askstring("Rename Project", 
                                                  f"Enter new name for '{project_name_arg}':", 
                                                  parent=self.app.root)
                if new_name and new_name != project_name_arg:
                    self._rename_project(project_name_arg, new_name)
            
    def show_project_dashboard(self):
        """Show dashboard with project analytics (Not directly related to saving, kept for context)"""
        pass 
    
    def edit_project_settings(self):
        """Edit core project settings (Not directly related to saving, kept for context)"""
        pass 
    
    def _save_settings(self, root_dir, output_dir, dialog):
        """Save settings from the settings dialog (Not directly related to selection saving, kept for context)"""
        if os.path.exists(root_dir) and os.path.exists(output_dir):
            self.app.root_dir = root_dir
            self.app.output_dir = output_dir
            self._update_current_project_data() 
            self.save_preferences()
            self.app.file_operations.build_tree(root_dir) 
            dialog.destroy()
        else:
            messagebox.showerror("Error", "Invalid directory paths provided!")
    
    def _switch_to_project(self, project_name):
        """Switch to a different project"""
        if project_name in self.app.projects:
            self._update_current_project_data()
            
            self.app.current_project = project_name
            project_data = self.app.projects[project_name]
            self._apply_project_settings(project_data) 
            
            self.app.project_name_var.set(project_name)
            
            paths_that_were_pending_selection = self.app.pending_selected_paths.copy()
            self.app.file_operations.build_tree(self.app.root_dir, self.app.pending_selected_paths)
            self.app.pending_selected_paths = set() 

            # After tree is built, open directories that were part of the saved selection
            for path_to_open in paths_that_were_pending_selection:
                if self.app.tree.exists(path_to_open): # path_to_open is the item_id (path)
                    if "folder" in self.app.tree.item(path_to_open, "tags"):
                        self.app.tree.item(path_to_open, open=True)
                        # If opening a folder reveals a "Loading..." placeholder,
                        # we need to ensure its contents are actually loaded.
                        # The <<TreeviewOpen>> event should ideally handle this.
                        # Forcing it if needed:
                        children = self.app.tree.get_children(path_to_open)
                        if children and self.app.tree.exists(children[0]) and \
                           self.app.tree.item(children[0], "text") == "Loading...":
                            original_focus = self.app.tree.focus()
                            self.app.tree.focus(path_to_open) 
                            self.app.file_operations.on_tree_open(None) # event=None uses tree.focus()
                            # Restore focus carefully
                            if self.app.tree.exists(original_focus) and original_focus != path_to_open :
                                self.app.tree.focus(original_focus)
                            elif not self.app.tree.focus(): # if focus is empty (e.g. path_to_open was the only item)
                                current_children = self.app.tree.get_children("")
                                if current_children and self.app.tree.exists(current_children[0]):
                                     self.app.tree.focus(current_children[0])


            self.save_preferences() 
            update_ui_status(self.app, f"Switched to project: {project_name}")
    
    def _delete_project(self, project_name):
        """Delete a project"""
        if project_name in self.app.projects and len(self.app.projects) > 1:
            confirm = messagebox.askyesno("Confirm Delete", 
                                         f"Are you sure you want to delete project '{project_name}'?\nThis cannot be undone.")
            if confirm:
                is_current_project = (project_name == self.app.current_project)
                
                del self.app.projects[project_name]
                
                if is_current_project:
                    fallback_project_name = sorted(self.app.projects.keys())[0]
                    self._switch_to_project(fallback_project_name) 
                else:
                    self.save_preferences()

                update_ui_status(self.app, f"Project '{project_name}' deleted")
        elif len(self.app.projects) <= 1:
            messagebox.showinfo("Cannot Delete", "You cannot delete the last remaining project.")
    
    def _rename_project(self, old_name, new_name):
        """Rename a project"""
        if old_name in self.app.projects and new_name not in self.app.projects and new_name:
            if self.app.current_project == old_name:
                self._update_current_project_data()

            self.app.projects[new_name] = copy.deepcopy(self.app.projects[old_name])
            self.app.projects[new_name]["modified"] = datetime.datetime.now().isoformat()
            
            del self.app.projects[old_name]
            
            if self.app.current_project == old_name:
                self.app.current_project = new_name
                self.app.project_name_var.set(new_name)
            
            self.save_preferences() 
            update_ui_status(self.app, f"Project '{old_name}' renamed to '{new_name}'")
        elif new_name in self.app.projects:
            messagebox.showerror("Error", f"Project '{new_name}' already exists.")

    def _update_current_project_data(self):
        """Update the IN-MEMORY data for the current project from the UI state."""
        if self.app.current_project in self.app.projects:
            # Use the root_dir currently set in the app for making paths relative,
            # as this is the frame of reference for current selections.
            # The project's stored root_dir will be updated to this app.root_dir.
            project_root_for_relpath = self.app.root_dir 
            selected_absolute_paths = self.app.file_operations.get_selected_paths()
            selected_relative_paths = []
            for abs_path in selected_absolute_paths:
                try:
                    norm_root = os.path.normpath(project_root_for_relpath)
                    norm_abs_path = os.path.normpath(abs_path)
                    if os.path.commonpath([norm_root, norm_abs_path]) == norm_root:
                         relative_path = os.path.relpath(norm_abs_path, norm_root)
                         if relative_path == ".": 
                             relative_path = "." 
                         selected_relative_paths.append(relative_path)
                except ValueError: 
                    pass 

            default_rules = self.app.default_rules_text.get("1.0", tk.END).strip()
            project_rules = self.app.project_rules_text.get("1.0", tk.END).strip()
            prompt = self.app.prompt_text.get("1.0", tk.END).strip()

            self.app.projects[self.app.current_project].update({
                "modified": datetime.datetime.now().isoformat(),
                "root_dir": self.app.root_dir, 
                "output_dir": self.app.output_dir, 
                "ignored_file_types": copy.deepcopy(self.app.ignored_file_types), 
                "selected_paths_relative": selected_relative_paths, 
                "default_rules": default_rules,
                "project_rules": project_rules,
                "prompt": prompt
            })
    
    def _apply_project_settings(self, project_data):
        """Apply settings from loaded project_data TO THE UI and app state."""
        project_root_from_data = project_data.get("root_dir", self.app.root_dir)
        if os.path.exists(project_root_from_data) and os.path.isdir(project_root_from_data):
            self.app.root_dir = os.path.normpath(project_root_from_data)
        else:
            print(f"Warning: Project root '{project_root_from_data}' invalid. Using current: {self.app.root_dir}")
        self.app.path_var.set(self.app.root_dir)

        output_dir_from_data = project_data.get("output_dir", os.path.join(os.path.expanduser("~"), "Merged_Files"))
        if not os.path.exists(output_dir_from_data):
            try: os.makedirs(output_dir_from_data)
            except Exception: output_dir_from_data = os.path.join(os.path.expanduser("~"), "Merged_Files") 
        if not os.path.exists(output_dir_from_data): 
             try: os.makedirs(output_dir_from_data)
             except Exception as e: print(f"Critical: Cannot create any output directory: {e}")
        self.app.output_dir = output_dir_from_data

        selected_absolute_paths = set()
        # Use self.app.root_dir as the base for resolving relative paths,
        # as it has just been set from project_data or defaulted.
        base_root_for_relpath = self.app.root_dir
        if "selected_paths_relative" in project_data:
            for rel_path in project_data["selected_paths_relative"]:
                if rel_path == ".": 
                    abs_path = os.path.normpath(base_root_for_relpath)
                else:
                    abs_path = os.path.normpath(os.path.join(base_root_for_relpath, rel_path))
                selected_absolute_paths.add(abs_path)
        
        self.app.pending_selected_paths = selected_absolute_paths 

        if "ignored_file_types" in project_data:
            self.app.ignored_file_types = copy.deepcopy(project_data["ignored_file_types"])

        default_rules = project_data.get("default_rules", "") 
        self.app.default_rules_text.delete("1.0", tk.END)
        self.app.default_rules_text.insert("1.0", default_rules)

        project_rules = project_data.get("project_rules") 
        if project_rules is None: 
            project_rules = default_rules 
        self.app.project_rules_text.delete("1.0", tk.END)
        self.app.project_rules_text.insert("1.0", project_rules)

        prompt = project_data.get("prompt", "") 
        self.app.prompt_text.delete("1.0", tk.END)
        self.app.prompt_text.insert("1.0", prompt)
    
    def _init_default_project(self):
        """Initialize default project if none exists"""
        self.app.current_project = "Default"
        self.app.projects = {
            "Default": {
                "created": datetime.datetime.now().isoformat(),
                "modified": datetime.datetime.now().isoformat(),
                "root_dir": self.app.root_dir,
                "output_dir": self.app.output_dir,
                "ignored_file_types": copy.deepcopy(self.app.ignored_file_types),
                "selected_paths_relative": [], 
                "default_rules": "",
                "project_rules": "",
                "prompt": ""
            }
        }
        self._apply_project_settings(self.app.projects["Default"])