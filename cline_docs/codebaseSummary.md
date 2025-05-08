# Codebase Summary

## Key Components and Their Interactions
- `app.py`: Main application class (`FileMergerApp`), orchestrates UI (Tkinter/ttkbootstrap), event handling, and interaction between modules. Contains the core UI setup and refresh logic (including auto-selection).
- `main.py`: (Purpose not analyzed in this task, likely script entry point that instantiates `FileMergerApp`).
- `file_operations.py`: Class (`FileOperations`) responsible for building the file tree (`build_tree`), handling tree interactions (`on_tree_open`, `get_selected_paths`, `restore_selection_state`), and performing the file merge operation (`merge_files`, `_perform_merge`).
- `project_manager.py`: Class (`ProjectManager`) manages project lifecycle (create, load, save, switch, delete), handles saving/loading preferences (including selected paths) to `~/.filemerger/preferences.json`.
- `ui_dialogs.py`: Contains custom dialog windows (e.g., `ProjectManagerDialog`, `FileTypeDialog`, `ProgressDialog`).
- `utils.py`: Contains helper functions used across modules (e.g., `update_ui_status`, `format_size`, `calculate_project_size`).

## Data Flow
- Project settings (including selected file/directory paths) are loaded from `preferences.json` by `ProjectManager` on startup or project switch.
- `FileOperations` uses these loaded paths (`app.pending_selected_paths`) to restore the selection state in the UI tree during `build_tree`.
- On directory refresh (`app.refresh_directory`), the list of files before and after is compared; new files are automatically selected.
- User interactions (clicks, spacebar) update the selection state in the UI tree (`app.update_item_selection`).
- `ProjectManager` retrieves the current selection state from the tree (`file_operations.get_selected_paths`) and saves it back to `preferences.json` when saving preferences or switching projects.
- During merge, selected file paths are retrieved (`file_operations.get_selected_files_only`) and their content is written to the output file.

## External Dependencies
- `ttkbootstrap` (v1.10.1+): Used for themed Tkinter widgets and styling. (Defined in `requirements.txt`).
- Python Standard Library modules used: `os`, `json`, `datetime`, `copy`, `tkinter`, `threading`, `time`.

## Recent Significant Changes
- Implemented saving and loading of user-selected items per project.
- Implemented auto-selection of newly added items upon data refresh.

## User Feedback Integration and Its Impact on Development
- (Track how user feedback influences changes - TBD)

## Additional Documentation References
- (List other relevant documents in `cline_docs` as they are created, e.g., `styleAesthetic.md`)