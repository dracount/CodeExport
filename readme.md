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
    *   **Highlighting:** Selected rows are visually highlighted.
    *   Spacebar toggles selection of the focused item.
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
        *   Currently selected files/folders.
        *   Goal/Prompt text.
        *   Project-specific rules.
        *   Default rules template.
    *   Create new projects.
    *   Clone existing projects.
    *   Rename and delete projects.
*   **Configuration:**
    *   Easily edit the list of ignored file types and names (e.g., `.git`, `__pycache__`, `*.log`, binary extensions).
    *   Project settings and preferences are saved automatically to `~/.filemerger/preferences.json`.
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

2.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/file-merger-pro.git # Replace with your repo URL
    cd file-merger-pro
    ```

3.  **Install dependencies:**
    *   This project uses `ttkbootstrap`. Create a `requirements.txt` file with the following content:
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
    *   Select files or folders using the checkboxes.
    *   Use the "Project" menu to manage projects (create, load, clone, etc.).
    *   Edit ignored file types under the "Project" menu.
    *   Enter your goal/prompt and project rules in the respective tabs on the right.
    *   Click "Merge Selected Files" to start the merging process. You will be prompted to choose an output file location and name.
    *   Use the context menu (right-click) for additional actions on tree items.

## Configuration

*   Project configurations and application state are stored in `~/.filemerger/preferences.json` (on Windows, this is usually `C:\Users\YourUsername\.filemerger\preferences.json`).
*   Ignored file types and project settings (paths, rules) are managed directly through the application's UI and saved within the project data in the preferences file.

## Development Environment

*   Developed primarily using VS Code on Windows.
*   Code is structured into separate modules for UI (`app.py`, `ui_dialogs.py`), file operations (`file_operations.py`), project management (`project_manager.py`), and utilities (`utils.py`).

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs, feature requests, or improvements. I may or may not look at them. This was developed purely to help me paste data into LLM's.

## License

MIT License

## Prompt default rules (feel free to change or use your own)
```
Core Directive: 
The user's GOAL: is the absolute primary objective. All rules serve to fulfill the GOAL: safely and effectively within the provided codebase context. The primary output will be the complete content of modified files.

## 1. Output Format & Structure

Full File Output: ALWAYS provide the ENTIRE, complete content of any file that has been modified. Do not provide only fragments, functions, or classes.

File Identification: Precede the full content of each outputted file with a clear identifier on its own line. This identifier line IS NOT part of the file content itself.

# FILE: [Full path to the target file]

Example Structure:

FILE: path/to/your/modified_file.py
Codeblock:
```
import os # <--- Raw file content starts here

def function_one():
    # ... code ...

class MyClass:
    # ... code ...
# [... continues to the end of the file's raw content]
```

Multiple File Output (Post-Refactoring): If refactoring occurs (see Rule #7), output the full content of all affected files (the original modified file and any newly created files). Each file's content must be preceded by its own # FILE: identifier line. Ensure new files follow existing naming conventions and structure.

Action Summary (Optional but Recommended): Optionally, include a brief # ACTION: comment before the first # FILE: line to summarize the primary change implemented (e.g., # ACTION: Implemented feature X by modifying function Y and creating helper module Z.).

## 2. Code Modification & Refactoring Principles

Adhere to Existing Patterns: Strictly follow the programming patterns, styles, and conventions already present in the provided codebase. Do not introduce new design patterns unless explicitly requested in the GOAL:.

Maintain Consistency: Ensure consistency with existing component structure, organization, naming conventions, and error handling approaches throughout the project. Apply these consistently during refactoring.

Mandatory Refactoring (File Length Limit):

Target: Keep all source code files strictly under 300 lines.

Trigger: If fulfilling the GOAL: causes any modified file to exceed 300 lines, you MUST refactor that file.

Action: Logically break down the oversized file into smaller, cohesive modules or helper functions/classes located in appropriate new or existing files. Prioritize clarity, maintainability, and adherence to existing project structure (Rule #8). Update all necessary imports and calls across affected files.

Rationale: This ensures the codebase remains manageable and adheres to modularity principles.

Preserve Project Structure: Follow existing project structure patterns when creating new files during refactoring. Do not introduce new top-level structural patterns unless the GOAL: specifically requires it. Place new modules logically within the existing hierarchy.

Refactor Sparingly (Beyond Length Limit): Only refactor code beyond the mandatory length-driven refactoring if it's essential for the GOAL: implementation or significantly improves clarity/maintainability directly related to the task within the modified sections.

## 3. Code Quality & Implementation

Write Complete & Functional Code: Ensure the full content provided for each file (following the # FILE: identifier) is complete, syntactically correct, internally consistent (e.g., imports match usage), and immediately usable.

Include Robust Error Handling: Implement comprehensive error handling consistent with the project's existing strategies. Consider edge cases and potential failure modes.

No Placeholders or Mocks: Never use placeholder comments (e.g., # TODO: Implement this later) or stub implementations in the final proposed code. Do not use mock or test data in production code logic.

Security Best Practices: Implement security best practices relevant to the language and context of the code being modified. Be mindful of potential vulnerabilities (e.g., injection attacks, data exposure).

Document Where Necessary: Document new public APIs, functions, or complex logic clearly, especially in newly created files resulting from refactoring. Update existing documentation if behavior changes. Follow the project's documentation style.

## 4. Technology & Environment (Apply When Relevant to GOAL)

Use Established Technology Stack: Only use libraries, frameworks, and tools already established in the project. Do not switch technologies to solve problems.

Library Usage: If adding a new library is essential to the GOAL: (and allowed), prefer widely-used, well-maintained options compatible with the existing stack. Verify version compatibility.

Environment-Specific Values: When dealing with configuration or deployment-related code:

Maintain separation between environments (development, testing, production) if the pattern exists.

Use configuration files or environment variables; never hardcode environment-specific values (like API keys or database URLs).

## 5. Testing (Apply When Relevant to GOAL)

Add/Update Tests: When adding new features, modifying complex logic, or refactoring, include/update corresponding unit or integration tests, following the project's existing testing patterns and frameworks. Ensure tests cover the new structure post-refactoring.

Test Edge Cases: Ensure tests cover relevant edge cases and failure modes for the modified and refactored code.
```
