import os
import json
import datetime
import copy
import tkinter as tk
from tkinter import messagebox, simpledialog
import threading
import time

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
        """Save current project state"""
        # Update current project data
        self._update_current_project_data()
        
        # Save to file
        try:
            data = {
                "projects": self.app.projects,
                "current_project": self.app.current_project,
                "last_saved": datetime.datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            update_ui_status(self.app, "Preferences saved")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save preferences: {str(e)}")
    
    def create_project(self, name=None):
        """Create new project"""
        if name is None:
            name = simpledialog.askstring("New Project", "Enter project name:", parent=self.app.root)
        
        if name:
            if name in self.app.projects:
                messagebox.showerror("Error", f"Project '{name}' already exists!")
                return
            
            # Create a new project configuration
            self.app.projects[name] = {
                "created": datetime.datetime.now().isoformat(),
                "modified": datetime.datetime.now().isoformat(),
                "root_dir": self.app.root_dir,
                "output_dir": self.app.output_dir,
                "ignored_file_types": copy.deepcopy(self.app.ignored_file_types)
            }
            
            # Switch to the new project
            self._switch_to_project(name)
            self.save_preferences()
            
            messagebox.showinfo("Success", f"Project '{name}' created")
    
    def clone_current_project(self):
        """Clone existing project"""
        name = simpledialog.askstring("Clone Project", 
                                      f"Enter name for the clone of '{self.app.current_project}':", 
                                      parent=self.app.root)
        
        if name:
            if name in self.app.projects:
                messagebox.showerror("Error", f"Project '{name}' already exists!")
                return
            
            # Clone the current project
            self.app.projects[name] = copy.deepcopy(self.app.projects[self.app.current_project])
            self.app.projects[name]["created"] = datetime.datetime.now().isoformat()
            self.app.projects[name]["modified"] = datetime.datetime.now().isoformat()
            
            # Switch to the new project
            self._switch_to_project(name)
            self.save_preferences()
            
            messagebox.showinfo("Success", f"Project '{name}' created as a clone of '{self.app.current_project}'")
    
    def manage_projects(self):
        """Show project management dialog"""
        dialog = ProjectManagerDialog(self.app.root, self.app.projects, self.app.current_project)
        self.app.root.wait_window(dialog)
        
        if dialog.result:
            action, project = dialog.result
            
            if action == "switch":
                self._switch_to_project(project)
            elif action == "delete":
                self._delete_project(project)
            elif action == "rename":
                new_name = simpledialog.askstring("Rename Project", 
                                                  f"Enter new name for '{project}':", 
                                                  parent=self.app.root)
                if new_name and new_name != project:
                    self._rename_project(project, new_name)
            
            self.save_preferences()
    
    def show_project_dashboard(self):
        """Show dashboard with project analytics"""
        # Count files by type
        files = self.app.file_operations.get_all_files()
        extension_counts = {}
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in extension_counts:
                extension_counts[ext] += 1
            else:
                extension_counts[ext] = 1
        
        # Create dashboard window
        dashboard = tk.Toplevel(self.app.root)
        dashboard.title(f"Project Dashboard - {self.app.current_project}")
        dashboard.geometry("600x400")
        
        ttk.Label(dashboard, text=f"Project: {self.app.current_project}", font=("", 12, "bold")).pack(pady=10)
        
        # File information
        info_frame = ttk.LabelFrame(dashboard, text="Project Information")
        info_frame.pack(fill=tk.X, expand=False, padx=10, pady=5)
        
        created = datetime.datetime.fromisoformat(self.app.projects[self.app.current_project]["created"])
        modified = datetime.datetime.fromisoformat(self.app.projects[self.app.current_project]["modified"])
        
        ttk.Label(info_frame, text=f"Created: {created.strftime('%Y-%m-%d %H:%M')}").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=f"Last Modified: {modified.strftime('%Y-%m-%d %H:%M')}").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=f"Total Files: {len(files)}").pack(anchor=tk.W, padx=5, pady=2)
        
        # File types breakdown
        types_frame = ttk.LabelFrame(dashboard, text="File Types")
        types_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tree = ttk.Treeview(types_frame, columns=("count", "percentage"), show="headings")
        tree.heading("count", text="Count")
        tree.heading("percentage", text="Percentage")
        tree.column("count", width=80, anchor=tk.E)
        tree.column("percentage", width=80, anchor=tk.E)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add file extensions to tree
        for ext, count in sorted(extension_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = f"{count / len(files) * 100:.1f}%"
            tree.insert("", "end", text=ext, values=(count, percentage))
    
    def edit_project_settings(self):
        """Edit core project settings"""
        settings = tk.Toplevel(self.app.root)
        settings.title(f"Edit Project Settings - {self.app.current_project}")
        settings.geometry("500x300")
        
        ttk.Label(settings, text=f"Project: {self.app.current_project}", font=("", 12, "bold")).pack(pady=10)
        
        # Project path settings
        paths_frame = ttk.LabelFrame(settings, text="File Paths")
        paths_frame.pack(fill=tk.X, expand=False, padx=10, pady=5)
        
        # Root directory
        root_dir_var = tk.StringVar(value=self.app.root_dir)
        ttk.Label(paths_frame, text="Root Directory:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(paths_frame, textvariable=root_dir_var, width=40).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(paths_frame, text="Browse", command=lambda: root_dir_var.set(
            filedialog.askdirectory(initialdir=root_dir_var.get()))
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Output directory
        output_dir_var = tk.StringVar(value=self.app.output_dir)
        ttk.Label(paths_frame, text="Output Directory:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(paths_frame, textvariable=output_dir_var, width=40).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(paths_frame, text="Browse", command=lambda: output_dir_var.set(
            filedialog.askdirectory(initialdir=output_dir_var.get()))
        ).grid(row=1, column=2, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(settings)
        button_frame.pack(fill=tk.X, expand=False, padx=10, pady=15)
        
        ttk.Button(button_frame, text="Save", command=lambda: self._save_settings(
            root_dir_var.get(), output_dir_var.get(), settings)
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(button_frame, text="Cancel", command=settings.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _save_settings(self, root_dir, output_dir, dialog):
        """Save settings from the settings dialog"""
        if os.path.exists(root_dir) and os.path.exists(output_dir):
            self.app.root_dir = root_dir
            self.app.output_dir = output_dir
            self.save_preferences()
            self.app.file_operations.build_tree(root_dir)
            dialog.destroy()
        else:
            messagebox.showerror("Error", "Invalid directory paths provided!")
    
    def _switch_to_project(self, project_name):
        """Switch to a different project"""
        if project_name in self.app.projects:
            # Save current project first
            self._update_current_project_data()
            
            # Switch to the new project
            self.app.current_project = project_name
            project_data = self.app.projects[project_name]
            self._apply_project_settings(project_data)
            
            # Update UI
            self.app.project_name_var.set(project_name)
            self.app.file_operations.build_tree(self.app.root_dir)
            update_ui_status(self.app, f"Switched to project: {project_name}")
    
    def _delete_project(self, project_name):
        """Delete a project"""
        if project_name in self.app.projects and len(self.app.projects) > 1:
            confirm = messagebox.askyesno("Confirm Delete", 
                                         f"Are you sure you want to delete project '{project_name}'?\nThis cannot be undone.")
            if confirm:
                # If we're deleting the current project, switch to another one first
                if project_name == self.app.current_project:
                    # Find another project to switch to
                    for name in self.app.projects:
                        if name != project_name:
                            self._switch_to_project(name)
                            break
                
                # Delete the project
                del self.app.projects[project_name]
                update_ui_status(self.app, f"Project '{project_name}' deleted")
        else:
            messagebox.showinfo("Cannot Delete", "You cannot delete the last remaining project.")
    
    def _rename_project(self, old_name, new_name):
        """Rename a project"""
        if old_name in self.app.projects and new_name not in self.app.projects:
            # Copy the project with the new name
            self.app.projects[new_name] = copy.deepcopy(self.app.projects[old_name])
            self.app.projects[new_name]["modified"] = datetime.datetime.now().isoformat()
            
            # Delete the old project
            del self.app.projects[old_name]
            
            # Update current project if needed
            if self.app.current_project == old_name:
                self.app.current_project = new_name
                self.app.project_name_var.set(new_name)
            
            update_ui_status(self.app, f"Project renamed to '{new_name}'")
    
    def _update_current_project_data(self):
        """Update the data for the current project"""
        if self.app.current_project in self.app.projects:
            # Get selected paths (files and directories)
            selected_paths = self.app.file_operations.get_selected_paths() # Use the new method

            # Get rules and prompt
            default_rules = self.app.default_rules_text.get("1.0", tk.END).strip()
            project_rules = self.app.project_rules_text.get("1.0", tk.END).strip()
            prompt = self.app.prompt_text.get("1.0", tk.END).strip()

            self.app.projects[self.app.current_project].update({
                "modified": datetime.datetime.now().isoformat(),
                "root_dir": self.app.root_dir,
                "output_dir": self.app.output_dir,
                "ignored_file_types": copy.deepcopy(self.app.ignored_file_types),
                "selected_paths": selected_paths, # Store selected paths
                "default_rules": default_rules,
                "project_rules": project_rules,
                "prompt": prompt
            })


    
    def _apply_project_settings(self, project_data):
        """Apply settings from a project"""
        if "root_dir" in project_data and os.path.exists(project_data["root_dir"]):
            self.app.root_dir = project_data["root_dir"]
            self.app.path_var.set(project_data["root_dir"])
        else:
            # Handle case where saved root_dir is invalid, fallback to default
            self.app.root_dir = os.path.expanduser("~")
            self.app.path_var.set(self.app.root_dir)


        if "output_dir" in project_data:
            # Create output directory if it doesn't exist
            output_dir = project_data["output_dir"]
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                    print(f"Created output directory: {output_dir}") # Optional: Log creation
                except Exception as e:
                    print(f"Error creating output directory {output_dir}: {e}") # Optional: Log error
                    # Fallback to default if creation fails
                    output_dir = os.path.join(os.path.expanduser("~"), "Merged_Files")
                    if not os.path.exists(output_dir):
                        try: os.makedirs(output_dir)
                        except: pass # Ignore error on fallback creation
            self.app.output_dir = output_dir
        else:
            # Fallback to default output dir if not set
            self.app.output_dir = os.path.join(os.path.expanduser("~"), "Merged_Files")
            if not os.path.exists(self.app.output_dir):
                try: os.makedirs(self.app.output_dir)
                except: pass # Ignore error on fallback creation


        if "selected_paths" in project_data: # Look for selected_paths
            # Store the selected paths as a set for efficient lookup
            # during restoration
            self.app.pending_selected_paths = set(project_data["selected_paths"]) # Use pending_selected_paths
        else:
            self.app.pending_selected_paths = set() # Ensure it's initialized if not in project data


        if "ignored_file_types" in project_data:
            self.app.ignored_file_types = copy.deepcopy(project_data["ignored_file_types"])

        # Load rules and prompt if they exist
        # Default rules
        default_rules = project_data.get("default_rules", "") # Use .get for safety
        self.app.default_rules_text.delete("1.0", tk.END)
        self.app.default_rules_text.insert("1.0", default_rules)

        # Project rules - populate from default if project rules are missing
        project_rules = project_data.get("project_rules") # Use .get
        if project_rules is None: # Check if key is missing or value is None
            project_rules = default_rules # Fallback to default rules

        self.app.project_rules_text.delete("1.0", tk.END)
        self.app.project_rules_text.insert("1.0", project_rules)


        # Prompt
        prompt = project_data.get("prompt", "") # Use .get for safety
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
                "default_rules": "",
                "project_rules": "",
                "prompt": ""
            }
        }
