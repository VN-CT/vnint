import os
import json
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
CACHE_FILE = Path(".vnint_cache.json")

class Vnint:
    def __init__(self):
        print(LOGO)
        self.licenses = self._load_licenses()

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
        lic_item = next((item for item in self.licenses if item['spdx_id'] == spdx_id), None)
        if not lic_item: return None
        
        try:
            resp = requests.get(lic_item['url'], timeout=10)
            return resp.json()['body']
        except Exception:
            return "License content could not be retrieved."

    def run(self):
        questions = [
            inquirer.Text('author', message="Enter author name"),
            inquirer.Text('project', message="Enter project name"),
            inquirer.List('license', message="Select license", 
                          choices=[l['spdx_id'] for l in self.licenses] + ['No License']),
            inquirer.Checkbox('extra', message="Select extra files", 
                              choices=['Makefile', 'Docker', 'SECURITY.md', 'CHANGELOG.md'])
        ]
        
        answers = inquirer.prompt(questions)
        self.generate(answers)

    def generate(self, data):
        root = Path(data['project'])
        root.mkdir(exist_ok=True)
        
        # Structure
        for folder in ['src', 'tests', 'docs']:
            (root / folder).mkdir(exist_ok=True)
        
        # README
        (root / "README.md").write_text(f"# {data['project']}\nAuthor: {data['author']}\nLicense: {data['license']}")
        
        # License
        if data['license'] != 'No License':
            content = self._get_license_content(data['license'])
            (root / "LICENSE").write_text(content or "Custom License")
        
        # Extra Files
        for item in data['extra']:
            (root / item).write_text(f"# {item} for {data['project']}")
            
        print(f"\n[+] Successfully deployed '{data['project']}' via vnint.")

if __name__ == "__main__":
    Vnint().run()