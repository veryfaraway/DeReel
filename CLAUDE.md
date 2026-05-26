# Agent Instructions

## Package Manager
Use **uv**: `uv sync`, `uv run python -m dereel.run`

## File-Scoped Commands
| Task | Command |
|------|---------|
| Typecheck | `uv run mypy <file_path>` |
| Lint | `uv run ruff check <file_path>` |
| Test | `uv run pytest <test_file_path>` |

## Git & Command Permissions
* **Read-Only Commands Only:** Only execute read-only terminal/git commands.
* **Prohibited Commands:** DO NOT run write commands such as `mkdir`, `git commit`, `git push`, or package installation (`uv add`/`pip install`). Ask the user to run them.
* **Commit Messages:** Do not commit directly. Suggest a commit message to the user including:
  ```
  Co-Authored-By: Antigravity <antigravity@google.com>
  ```

## Development Conventions
* **Approval First:** Always present proposed code changes and obtain explicit user approval before modifying files.
* **Design Alignment:** Adhere strictly to the design documents (`docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/DATA_SCHEMA.md`).
* **Design Changes:** If a more efficient design is discovered, propose it to the user before implementing.
* **Security:** Sensitive configurations must be handled via environment variables (Pydantic `Settings`) and configured in GitHub Secrets. Never hardcode secrets.
