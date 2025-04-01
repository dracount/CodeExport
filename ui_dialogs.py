import os
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import time
import threading
import shutil
import tempfile

class ProjectManagerDialog(tk.Toplevel):
    def __init__(self, parent, projects, current_project):
        super().__init__(parent)
        self.title("Project Manager")
        self.geometry("500x400")
        self.resizable(True, True)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Dialog result
        self.result = None
        self.projects = projects
        self.current_project = current_project
        
        # Create UI
        self.create_widgets()
        
        # Focus dialog and wait for it to be closed
        self.focus_set()
        
    def create_widgets(self):
        # Project list frame
        list_frame = ttk.LabelFrame(self, text="Your Projects")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Project listbox with scrollbar
        self.project_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, height=15)
        self.project_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.project_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.project_listbox.config(yscrollcommand=scrollbar.set)
        
        # Populate project list
        self.populate_project_list(self.current_project)
        
        # Double-click to select
        self.project_listbox.bind("<Double-1>", lambda e: self.switch_project())
        
        # Buttons frame
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Switch to Selected", command=self.switch_project).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Rename", command=self.rename_project).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete", command=self.delete_project).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=5)
    
    def populate_project_list(self, current_project):
        """Populate the project list"""
        self.project_listbox.delete(0, tk.END)
        
        for i, name in enumerate(sorted(self.projects.keys())):
            if name == current_project:
                self.project_listbox.insert(tk.END, f"{name} (current)")
                self.project_listbox.selection_set(i)
                self.project_listbox.itemconfig(i, bg="#e0e0e0")
            else:
                self.project_listbox.insert(tk.END, name)
    
    def switch_project(self):
        """Switch to the selected project"""
        selection = self.project_listbox.curselection()
        if selection:
            # Get selected project name (remove " (current)" if present)
            project_name = self.project_listbox.get(selection[0]).split(" (current)")[0]
            
            # Return result
            self.result = ("switch", project_name)
            self.destroy()
    
    def rename_project(self):
        """Rename the selected project"""
        selection = self.project_listbox.curselection()
        if selection:
            # Get selected project name (remove " (current)" if present)
            project_name = self.project_listbox.get(selection[0]).split(" (current)")[0]
            
            # Return result
            self.result = ("rename", project_name)
            self.destroy()
    
    def delete_project(self):
        """Delete the selected project"""
        selection = self.project_listbox.curselection()
        if selection:
            # Get selected project name (remove " (current)" if present)
            project_name = self.project_listbox.get(selection[0]).split(" (current)")[0]
            
            # Don't allow deleting the last project
            if len(self.projects) <= 1:
                messagebox.showinfo("Cannot Delete", "You cannot delete the last remaining project.")
                return
            
            # Confirm deletion
            confirm = messagebox.askyesno("Confirm Delete", 
                                        f"Are you sure you want to delete project '{project_name}'?\nThis cannot be undone.")
            if not confirm:
                return
            
            # Return result
            self.result = ("delete", project_name)
            self.destroy()


class FileTypeDialog(tk.Toplevel):
    def __init__(self, parent, ignored_types):
        super().__init__(parent)
        self.title("Edit Ignored File Types")
        self.geometry("400x350")
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Store ignored types
        self.ignored_types = list(ignored_types)
        self.result = None
        
        # Create UI
        self.create_widgets()
        
        # Focus dialog
        self.focus_set()
    
    def create_widgets(self):
        # Instructions
        ttk.Label(self, text="File types that will be ignored during directory scanning:").pack(padx=10, pady=10, anchor=tk.W)
        
        # List frame with scrollbar
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.type_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, selectmode=tk.SINGLE)
        scrollbar.config(command=self.type_list.yview)
        
        self.type_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate the list
        for file_type in sorted(self.ignored_types):
            self.type_list.insert(tk.END, file_type)
        
        # Input for new type
        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(input_frame, text="New type:").pack(side=tk.LEFT, padx=5)
        self.new_type = ttk.Entry(input_frame)
        self.new_type.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.new_type.bind("<Return>", lambda e: self.add_type())
        
        ttk.Button(input_frame, text="Add", command=self.add_type).pack(side=tk.RIGHT, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Remove Selected", command=self.remove_type).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="OK", command=self.save_changes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=5)
    
    def add_type(self):
        """Add a new file type to ignore"""
        new_type = self.new_type.get().strip()
        
        if not new_type:
            return
        
        # Ensure it starts with a dot if it's an extension
        if not new_type.startswith(".") and not new_type.startswith("*"):
            new_type = "." + new_type
        
        # Add to list if not already present
        if new_type not in self.ignored_types:
            self.ignored_types.append(new_type)
            self.type_list.insert(tk.END, new_type)
            self.new_type.delete(0, tk.END)
    
    def remove_type(self):
        """Remove selected file type"""
        selection = self.type_list.curselection()
        if selection:
            type_to_remove = self.type_list.get(selection[0])
            self.ignored_types.remove(type_to_remove)
            self.type_list.delete(selection[0])
    
    def save_changes(self):
        """Save changes and close dialog"""
        self.result = self.ignored_types
        self.destroy()
    
    def cancel(self):
        """Cancel changes and close dialog"""
        self.result = None
        self.destroy()


class ProgressDialog(tk.Toplevel):
    def __init__(self, parent, title, max_value):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x150")
        self.resizable(False, False)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Progress variables
        self.max_value = max_value
        self.current = 0
        
        # Create UI
        self.create_widgets()
        
        # Focus dialog
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.cancel_operation)
        
        # Cancel flag
        self.cancelled = False
    
    def create_widgets(self):
        # Status label
        self.status_var = tk.StringVar(value="Starting operation...")
        ttk.Label(self, textvariable=self.status_var).pack(padx=20, pady=(20, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=350, mode='determinate', maximum=self.max_value)
        self.progress.pack(padx=20, pady=10)
        
        # Progress values
        self.progress_text = tk.StringVar(value="0 / 0")
        ttk.Label(self, textvariable=self.progress_text).pack(padx=20)
        
        # Cancel button
        ttk.Button(self, text="Cancel", command=self.cancel_operation).pack(pady=10)
    
    def update_progress(self, value, status_text=None, finished=False):
        """Update progress bar and status"""
        if self.cancelled:
            return
        
        self.current = value
        
        # Update UI in main thread
        self.progress['value'] = value
        self.progress_text.set(f"{value} / {self.max_value}")
        
        if status_text:
            self.status_var.set(status_text)
        
        # Process events to update display
        self.update()
        
        # If operation is complete, close dialog after delay
        if finished:
            self.after(1000, self.destroy)
    
    def cancel_operation(self):
        """Cancel the operation"""
        if messagebox.askyesno("Cancel Operation", "Are you sure you want to cancel the operation?"):
            self.cancelled = True
            self.status_var.set("Operation cancelled")
            self.destroy()
