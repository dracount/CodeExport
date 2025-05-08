# File Merger Pro 📂✨

A graphical utility built with Python and Tkinter/ttkbootstrap to browse directories, select specific files and folders, and merge their content into a single output file. Includes project management features to save and load configurations, selections, and rules.

## Overview

File Merger Pro helps you consolidate text-based content from multiple files across a directory structure. It's particularly useful for:

*   Gathering code context for analysis or Large Language Models (LLMs).
*   Combining log files.
*   Creating a single document from various text sources.
*   Managing different sets of files (projects) with their specific settings.

## Features

*   **Intuitive GUI:** Built using Tkinter and styled with ttkbootstrap (`flatly` theme).
*   **File Tree Navigation:**
    *   Browse directories starting from a chosen root.
    *   Display files and folders in a tree view.
    *   Show file size and modification dates.
    *   Lazy loading of directory contents for performance.
*   **Selection:**
    *   Checkboxes next to each item for easy selection/deselection.
    *   Clicking a folder's checkbox toggles selection for all its children recursively.
    *   **Highlighting:** Selected rows are visually highlighted. The currently focused item (navigated with arrow keys) is also highlighted.
    *   Spacebar or Enter key toggles selection of the focused item.
    *   "Select All Visible" and "Deselect All" options.
*   **Merging:**
    *   Merge content of selected **files** into a single output file.
    *   **Customizable Header:** Include a "Goal/Prompt" and "Project Rules" section at the beginning of the merged file.
    *   **Directory Structure:** Automatically includes a summary of the directory structure of the merged files.
    *   **Line Numbering:** Adds line numbers to the content of each merged file.
    *   **Configurable Output:** Choose the output directory and filename.
    *   Progress bar during merge operation.
*   **Project Management:**
    *   Save and load different "projects".
    *   Each project stores:
        *   Root directory path.
        *   Output directory path.
        *   List of ignored file types/names.
        *   Currently selected files/folders (relative to project root).
        *   Goal/Prompt text.
        *   Project-specific rules.
        *   Default rules template.
    *   Create new projects.
    *   Clone existing projects.
    *   Rename and delete projects.
    *   Explicit "Save Project" menu option.
*   **Configuration:**
    *   Easily edit the list of ignored file types and names (e.g., `.git`, `__pycache__`, `*.log`, binary extensions).
    *   Project settings and preferences are saved automatically to `~/.filemerger/preferences.json` on close, project switch, or explicit save.
*   **Context Menu:** Right-click on tree items for quick actions:
    *   Select/Deselect item and children.
    *   Expand/Collapse item and children recursively.
    *   Open item location in the system's file explorer.
*   **Statistics:** View real-time stats:
    *   Total items loaded in the tree.
    *   Number of selected items.
    *   Total size of selected files.
    *   Total character count of selected files.
*   **Refresh:** Reload the directory view, preserving open folders and selections, and auto-selecting newly added files.

## Installation

1.  **Prerequisites:**
    *   Python 3.x
    *   `pip` (Python package installer)

2.  **Clone the repository (or download the source code):**
    ```bash
    # If you have git:
    # git clone https://github.com/your-username/file-merger-pro.git 
    # cd file-merger-pro
    ```
    (If you don't have a repository URL, just navigate to the directory where you've saved the code files.)

3.  **Install dependencies:**
    *   This project uses `ttkbootstrap`. Ensure you have a `requirements.txt` file in your project directory with the following content:
        ```txt
        ttkbootstrap>=1.10.1 # Or the version you are using
        ```
    *   Install the requirements:
        ```bash
        pip install -r requirements.txt
        ```

## Usage

1.  Navigate to the project directory in your terminal.
2.  Run the application:
    ```bash
    python main.py
    ```
3.  **Using the Application:**
    *   Use the "File" menu or the browse button to set the root directory you want to explore.
    *   Navigate the tree view. Expand folders by double-clicking or clicking the expander icon.
    *   Select files or folders by clicking anywhere on their row, or by focusing them with arrow keys and pressing Space/Enter.
    *   Use the "Project" menu to manage projects (create, load, save, clone, etc.).
    *   Edit ignored file types under the "Project" menu.
    *   Enter your goal/prompt and project rules in the respective tabs on the right.
    *   Click "Merge Selected Files" to start the merging process. You will be prompted to choose an output file location and name.
    *   Use the context menu (right-click) for additional actions on tree items.

## Building the Executable

To build a single executable file (e.g., for Windows distribution), you can use PyInstaller. If you haven't installed it yet, run: `pip install pyinstaller`.

If you want your executable to be named `FileMergerPro.exe`, use the following command from your project's root directory (where `main.py` is located):

```bash
pyinstaller --onefile --windowed --name FileMergerPro main.py