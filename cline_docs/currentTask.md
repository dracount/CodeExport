# Current Task

## Current Objective
- **Debug and fix:** User reports that saving/loading selections and auto-selection on refresh are not working correctly.

## Context
- Previous implementation aimed to save selected paths in `preferences.json` via `ProjectManager` and auto-select new files on refresh in `app.py`.
- User feedback indicates these features are failing in practice.

## Next Steps
- **Applied Fix:** Modified `file_operations.py` to restore selections during node creation (`add_node`) instead of a separate pass, fixing the timing issue with unexpanded directories. Updated relative path handling in `project_manager.py`.
- Verify the fix resolves the reported issues (selections not saving/loading, auto-selection incorrect).
- Update documentation if necessary (changes were primarily bug fixes, documentation might still be accurate conceptually).