import os
import json
import subprocess
import requests
import inquirer
from pathlib import Path

# ASCII Art Logo
LOGO = r"""
 __   __  _   _  ___  _   _  _____ 
 \ \ / / | \ | ||_ _|| \ | ||_   _|
  \ V /  |  \| | | | |  \| |  | |  
   | |   | |\  | | | | |\  |  | |  
   |_|   |_| \_||___||_| \_|  |_|  
"""

LICENSE_API = "https://api.github.com/licenses"
GITIGNORE_API = "https://api.github.com/gitignore/templates"
CACHE_FILE = Path(".vnint_cache.json")
LANGUAGE_CONFIG = Path(__file__).parent / "languages.json"
SCRIPTS_DIR = Path.home() / ".vnint" / "scripts"

# ──────────────────────────────────────────────
# Default language definitions (used if languages.json is absent)
# ──────────────────────────────────────────────
DEFAULT_LANGUAGES = {
    "Python": {
        "gitignore_template": "Python",
        "pre_commit_hooks": [
            {"repo": "https://github.com/psf/black", "rev": "23.12.1",
             "hooks": [{"id": "black"}]},
            {"repo": "https://github.com/PyCQA/flake8", "rev": "7.0.0",
             "hooks": [{"id": "flake8"}]},
        ],
        "boilerplate": {
            "files": {
                "src/__init__.py": "",
                "src/main.py": (
                    "def main():\n"
                    "    print('Hello from {project}!')\n\n"
                    "if __name__ == '__main__':\n"
                    "    main()\n"
                ),
                "tests/__init__.py": "",
                "tests/test_main.py": (
                    "from src.main import main\n\n"
                    "def test_main():\n"
                    "    main()  # smoke test\n"
                ),
                "requirements.txt": "# Add your dependencies here\n",
            }
        },
    },
    "Rust": {
        "gitignore_template": "Rust",
        "pre_commit_hooks": [
            {"repo": "https://github.com/doublify/pre-commit-rust", "rev": "v1.0",
             "hooks": [{"id": "clippy"}, {"id": "fmt"}]},
        ],
        "boilerplate": {
            "files": {
                "src/main.rs": (
                    'fn main() {{\n'
                    '    println!("Hello from {{}}!", "{project}");\n'
                    '}}\n'
                ),
                "Cargo.toml": (
                    '[package]\n'
                    'name = "{project}"\n'
                    'version = "0.1.0"\n'
                    'edition = "2021"\n\n'
                    '[dependencies]\n'
                    'log = "0.4"\n'
                    'serde = {{ version = "1", features = ["derive"] }}\n'
                ),
            }
        },
    },
    "C++": {
        "gitignore_template": "C++",
        "pre_commit_hooks": [
            {"repo": "https://github.com/pocc/pre-commit-hooks", "rev": "v1.3.5",
             "hooks": [{"id": "clang-format"}, {"id": "clang-tidy"}]},
        ],
        "boilerplate": {
            "files": {
                "src/main.cpp": (
                    '#include <iostream>\n\n'
                    'int main() {{\n'
                    '    std::cout << "Hello from {project}!" << std::endl;\n'
                    '    return 0;\n'
                    '}}\n'
                ),
                "CMakeLists.txt": (
                    'cmake_minimum_required(VERSION 3.20)\n'
                    'project({project})\n\n'
                    'set(CMAKE_CXX_STANDARD 17)\n\n'
                    'add_executable(${{PROJECT_NAME}} src/main.cpp)\n'
                ),
            }
        },
    },
}


# ──────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────

def _load_language_config() -> dict:
    """Load language definitions from languages.json if it exists, else use defaults."""
    if LANGUAGE_CONFIG.exists():
        try:
            return json.loads(LANGUAGE_CONFIG.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"[!] languages.json is malformed: {exc}. Using built-in defaults.")
    return DEFAULT_LANGUAGES


def _render_template(text: str, project: str, author: str) -> str:
    """Substitute {project} and {author} placeholders in template strings."""
    return text.replace("{project}", project).replace("{author}", author)


# ──────────────────────────────────────────────
# Core class
# ──────────────────────────────────────────────

class Vnint:
    def __init__(self):
        print(LOGO)
        self.licenses = self._load_licenses()
        self.languages = _load_language_config()

    # ── License helpers ──────────────────────────────

    def _load_licenses(self):
        """Fetches licenses from GitHub API with local caching."""
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text())
        try:
            response = requests.get(LICENSE_API, timeout=10)
            data = response.json()
            CACHE_FILE.write_text(json.dumps(data))
            return data
        except Exception:
            return []

    def _get_license_content(self, spdx_id):
        """Fetches the full license text."""
        lic_item = next((i for i in self.licenses if i["spdx_id"] == spdx_id), None)
        if not lic_item:
            return None
        try:
            resp = requests.get(lic_item["url"], timeout=10)
            return resp.json()["body"]
        except Exception:
            return "License content could not be retrieved."

    # ── Module 1: Boilerplate Templates ─────────────

    def _generate_boilerplate(self, root: Path, language: str, project: str, author: str):
        """
        Creates language-specific starter files.
        File templates are read from languages.json (or built-in defaults).
        """
        lang_cfg = self.languages.get(language, {})
        boilerplate = lang_cfg.get("boilerplate", {})
        files = boilerplate.get("files", {})

        if not files:
            print(f"  [~] No boilerplate defined for '{language}', skipping.")
            return

        for rel_path, template in files.items():
            dest = root / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            content = _render_template(template, project, author)
            dest.write_text(content, encoding="utf-8")
            print(f"  [+] {rel_path}")

    # ── Module 2: .gitignore via GitHub API ──────────

    def _generate_gitignore(self, root: Path, language: str):
        """Downloads the official GitHub .gitignore template for the chosen language."""
        lang_cfg = self.languages.get(language, {})
        template_name = lang_cfg.get("gitignore_template", language)

        try:
            url = f"{GITIGNORE_API}/{template_name}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                content = resp.json().get("source", "")
                (root / ".gitignore").write_text(content, encoding="utf-8")
                print(f"  [+] .gitignore ({template_name} template from GitHub)")
                return
        except Exception:
            pass

        # Graceful fallback
        (root / ".gitignore").write_text(f"# {language} – add patterns here\n")
        print("  [~] .gitignore (offline fallback – no GitHub connection)")

    # ── Module 3: Pre-commit Hooks ───────────────────

    def _generate_precommit(self, root: Path, language: str):
        """
        Creates .pre-commit-config.yaml with language-appropriate linting hooks.
        Hook definitions come from languages.json (or built-in defaults).
        """
        lang_cfg = self.languages.get(language, {})
        hooks = lang_cfg.get("pre_commit_hooks", [])

        if not hooks:
            print(f"  [~] No pre-commit hooks defined for '{language}', skipping.")
            return

        lines = ["repos:"]
        for repo in hooks:
            lines.append(f"  - repo: {repo['repo']}")
            lines.append(f"    rev: {repo['rev']}")
            lines.append("    hooks:")
            for hook in repo["hooks"]:
                lines.append(f"      - id: {hook['id']}")

        (root / ".pre-commit-config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("  [+] .pre-commit-config.yaml")

    # ── Module 4: Git Init & First Commit ───────────

    def _git_init(self, root: Path, project: str):
        """Runs git init and creates the initial commit."""
        try:
            subprocess.run(["git", "init"], cwd=root, check=True,
                           capture_output=True, text=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True,
                           capture_output=True, text=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=root, check=True, capture_output=True, text=True,
            )
            print(f"  [+] git init + Initial commit")
        except FileNotFoundError:
            print("  [!] git not found – skipping repository init.")
        except subprocess.CalledProcessError as exc:
            print(f"  [!] git error: {exc.stderr.strip()}")

    # ── Module 5: Custom Scripts / Plugins ──────────

    def _run_custom_scripts(self, root: Path):
        """
        Discovers and executes bash scripts from ~/.vnint/scripts/ in sorted order.
        Scripts receive the absolute project path as $1.
        """
        if not SCRIPTS_DIR.exists():
            return

        scripts = sorted(SCRIPTS_DIR.glob("*.sh"))
        if not scripts:
            return

        print("\n[~] Running custom scripts from ~/.vnint/scripts/")
        for script in scripts:
            print(f"  [>] {script.name}")
            try:
                subprocess.run(
                    ["bash", str(script), str(root.resolve())],
                    check=True,
                )
            except subprocess.CalledProcessError as exc:
                print(f"  [!] Script '{script.name}' exited with code {exc.returncode}")
            except Exception as exc:
                print(f"  [!] Could not run '{script.name}': {exc}")

    # ── Interactive wizard ───────────────────────────

    def run(self):
        questions = [
            inquirer.Text("author", message="Enter author name"),
            inquirer.Text("project", message="Enter project name"),
            inquirer.List(
                "language",
                message="Select language",
                choices=list(self.languages.keys()),
            ),
            inquirer.List(
                "license",
                message="Select license",
                choices=[l["spdx_id"] for l in self.licenses] + ["No License"],
            ),
            inquirer.Checkbox(
                "extra",
                message="Select extra files",
                choices=["Makefile", "Docker", "SECURITY.md", "CHANGELOG.md"],
            ),
            inquirer.Confirm(
                "git_init",
                message="Initialize a git repository with an initial commit?",
                default=True,
            ),
            inquirer.Confirm(
                "pre_commit",
                message="Generate .pre-commit-config.yaml?",
                default=True,
            ),
        ]

        answers = inquirer.prompt(questions)
        if answers:
            self.generate(answers)

    # ── Main generation pipeline ─────────────────────

    def generate(self, data: dict):
        project = data["project"]
        author = data["author"]
        language = data.get("language", "Python")
        root = Path(project)
        root.mkdir(exist_ok=True)

        print(f"\n[*] Scaffolding '{project}' ({language})\n")

        # Standard directories (Rust & C++ have their own src via boilerplate)
        for folder in ["src", "tests", "docs"]:
            (root / folder).mkdir(exist_ok=True)

        # README (always created)
        readme = (
            f"# {project}\n\n"
            f"**Author:** {author}  \n"
            f"**Language:** {language}  \n"
            f"**License:** {data.get('license', 'No License')}\n\n"
            f"## Getting Started\n\n"
            f"> Add project description and setup instructions here.\n"
        )
        (root / "README.md").write_text(readme, encoding="utf-8")
        print("  [+] README.md")

        # Module 1 – Boilerplate
        self._generate_boilerplate(root, language, project, author)

        # Module 2 – .gitignore
        self._generate_gitignore(root, language)

        # License
        if data.get("license") and data["license"] != "No License":
            content = self._get_license_content(data["license"])
            (root / "LICENSE").write_text(content or "Custom License", encoding="utf-8")
            print("  [+] LICENSE")

        # Extra files
        for item in data.get("extra", []):
            (root / item).write_text(f"# {item} for {project}\n", encoding="utf-8")
            print(f"  [+] {item}")

        # Module 3 – Pre-commit hooks
        if data.get("pre_commit", True):
            self._generate_precommit(root, language)

        # Module 4 – Git init
        if data.get("git_init", True):
            self._git_init(root, project)

        # Module 5 – Custom scripts
        self._run_custom_scripts(root)

        print(f"\n[✓] Project '{project}' deployed successfully via vnint.")
        print(f"    Location: {root.resolve()}\n")


if __name__ == "__main__":
    Vnint().run()
