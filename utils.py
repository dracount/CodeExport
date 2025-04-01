import os
import tkinter as tk

def calculate_project_size(app):
    """Calculate total size of selected files in the project"""
    total_size = 0
    # Use the new method that explicitly returns only files
    selected_files = app.file_operations.get_selected_files_only()

    for file_path in selected_files:
        try:
            # Double check it exists and is a file before getting size
            if os.path.exists(file_path) and os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
        except OSError: # Catch potential OS errors during stat
            # Skip if file can't be accessed
            continue

    return total_size

def update_ui_status(app, message=None):
    """Update the UI status bar with message or default status"""
    if message:
        app.status_var.set(message)
    else:
        app.status_var.set("Ready")
    
    # Update UI to show status immediately
    app.root.update_idletasks()

def format_size(size_bytes):
    """Format a file size in bytes to a human-readable string"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f} GB"

def debug_tree_structure(app):
    """Debug helper to identify duplicate entries"""
    paths = {}
    duplicates = []
    
    for node_id, path in app.file_operations.file_paths.items():
        if path in paths:
            duplicates.append((path, node_id, paths[path]))
        else:
            paths[path] = node_id
    
    return duplicates

def count_characters_in_files(app):
    """Count total characters in selected files"""
    total_chars = 0
    # Use the new method that explicitly returns only files
    selected_files = app.file_operations.get_selected_files_only()

    for file_path in selected_files:
        try:
            # Double check it exists and is a file before reading
            if os.path.exists(file_path) and os.path.isfile(file_path):
                # Try to read as text file
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f: # Add errors='ignore' for robustness
                        content = f.read()
                        total_chars += len(content)
                except Exception: # Broad catch if opening fails for other reasons
                    # Consider logging this error if debugging is needed
                    pass # Skip file if it cannot be read as text
        except OSError: # Catch potential OS errors during exists/isfile check
            # Skip if file can't be accessed
            continue

    return total_chars
