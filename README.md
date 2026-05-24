# 🛠 vnint

**vnint** is a high-performance project scaffold generator built for rapid development. It automates scaffolding structures, license integration via the GitHub API, linter setup, git initialization, and custom plugin execution.

## 📸 Preview

[![img.png](https://i.postimg.cc/yN9qSPbf/img.png)](https://postimg.cc/4KJ2DzZt)

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/vn-ct/vnint.git
cd vnint
```

### 2. Install dependencies

```bash
pip install requests inquirer
```

### 3. Run the generator

```bash
python vnint.py
```

---

## 📦 Functional Modules

### 1. 🗂 Boilerplate Templates

Instead of empty folders — ready-to-use starter files for your chosen language:

| Language | Generated files |
|----------|----------------|
| **Python** | `src/main.py`, `tests/`, `requirements.txt` |
| **Rust** | `src/main.rs`, `Cargo.toml` (with `log`, `serde`) |
| **C++** | `src/main.cpp`, `CMakeLists.txt` |
| **Go** | `main.go`, `go.mod` |
| **TypeScript** | `src/index.ts`, `tsconfig.json`, `package.json` |

Templates are configured via [`languages.json`](#%EF%B8%8F-extending-via-languagesjson) — add a new language without touching the source code.

---

### 2. 🙈 .gitignore Generator

Automatically downloads the up-to-date `.gitignore` for the selected language directly from the GitHub API:

```
GET https://api.github.com/gitignore/templates/{language}
```

If there is no network connection, a basic placeholder file is created instead.

---

### 3. 🔒 Pre-commit Hooks

Generates `.pre-commit-config.yaml` with language-appropriate linters:

| Language | Hooks |
|----------|-------|
| **Python** | `black` (formatting) + `flake8` (linting) |
| **Rust** | `clippy` (analysis) + `rustfmt` (formatting) |
| **C++** | `clang-format` + `clang-tidy` |
| **Go** | `go-fmt` + `go-vet` |
| **TypeScript** | `eslint` |

Activate the hooks after generation:

```bash
pip install pre-commit
pre-commit install
```

---

### 4. 🌿 Git Init & First Commit

After the project structure is created, vnint automatically:

1. Runs `git init`
2. Stages all files (`git add .`)
3. Creates the first commit `Initial commit`

This step can be skipped in the interactive wizard.

---

### 5. 🔌 Custom Scripts / Plugins

vnint supports running custom bash scripts from `~/.vnint/scripts/` after project initialization. Scripts are executed in alphabetical order; the absolute project path is passed as `$1`.

**Example scripts:**

```bash
# ~/.vnint/scripts/01_vscode.sh — open the project in VS Code
code "$1"
```

```bash
# ~/.vnint/scripts/02_venv.sh — create a Python virtual environment
python -m venv "$1/.venv"
echo "venv created at $1/.venv"
```

```bash
# ~/.vnint/scripts/03_deps.sh — install dependencies
cd "$1" && pip install -r requirements.txt -q
```

Create the folder and add your scripts:

```bash
mkdir -p ~/.vnint/scripts
chmod +x ~/.vnint/scripts/*.sh
```

---

## ⚙️ Extending via `languages.json`

Add a new language without modifying any Python code:

```json
{
  "Zig": {
    "gitignore_template": "Zig",
    "pre_commit_hooks": [],
    "boilerplate": {
      "files": {
        "src/main.zig": "const std = @import(\"std\");\n\npub fn main() void {\n    std.debug.print(\"Hello from {project}!\\n\", .{});\n}\n"
      }
    }
  }
}
```

Once the file is saved, the new language appears in the interactive selection list.

---

## 🗃 Project Structure

```
vnint/
├── vnint.py          # Main script
├── languages.json    # Language config (extend without changing code)
├── .vnint_cache.json # GitHub license cache (auto-generated)
└── README.md
```

```
~/.vnint/
└── scripts/          # Custom bash plugins
    ├── 01_vscode.sh
    └── 02_venv.sh
```

---

## 🔄 Full Generation Pipeline

```
Prompt: author / project name / language / license
        │
        ├─► src/, tests/, docs/          (structure)
        ├─► Boilerplate Files            (module 1)
        ├─► .gitignore ← GitHub API     (module 2)
        ├─► .pre-commit-config.yaml     (module 3)
        ├─► LICENSE ← GitHub API
        ├─► README.md
        ├─► git init + Initial commit   (module 4)
        └─► ~/.vnint/scripts/*.sh       (module 5)
```

---

## ⚙️ Architecture

Built on principles of modularity and extensibility. Each feature is a self-contained method of the `Vnint` class, language configurations are decoupled into `languages.json`, and user-defined logic lives in bash scripts.
