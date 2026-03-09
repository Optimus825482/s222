#!/usr/bin/env python3
"""
Kiro SKILL.md frontmatter validator & fixer.
Fixes invalid `name` fields like:
  name: skill-name: "description"  → splits into name + description
  name: skill-name: some text      → same
  name: skill-name: |              → block scalar description
"""

import os
import re
import sys
from pathlib import Path

SKILLS_DIR = Path(r"C:\Users\erkan\.kiro\skills")

# Matches: name: something: "rest" or name: something: rest (not a pure slug)
# Valid name is only lowercase letters, numbers, hyphens
INVALID_NAME_PATTERN = re.compile(
    r'^name:\s*([a-zA-Z0-9_-]+):\s*(.+)$',
    re.MULTILINE
)

def parse_frontmatter(content: str):
    """Extract frontmatter block and body."""
    if not content.startswith('---'):
        return None, None, content
    parts = content.split('---', 2)
    if len(parts) < 3:
        return None, None, content
    return parts[0], parts[1], parts[2]

def has_description(frontmatter: str) -> bool:
    return bool(re.search(r'^description:', frontmatter, re.MULTILINE))

def fix_frontmatter(frontmatter: str, skill_dir_name: str) -> tuple[str, bool, str]:
    """
    Returns (fixed_frontmatter, was_changed, reason)
    """
    match = INVALID_NAME_PATTERN.search(frontmatter)
    if not match:
        return frontmatter, False, ""

    full_name_value = match.group(1)  # e.g. "varlock-claude-skill"
    extra_value = match.group(2).strip()  # e.g. '"Secure env..."' or 'Amit Rathiesh'

    # Skip if extra_value looks like a version number (e.g. "2.1.2")
    if re.match(r'^[\d.]+$', extra_value.strip('"').strip("'")):
        reason = f"name has version-like value '{extra_value}' — skipping (manual review needed)"
        return frontmatter, False, reason

    # Skip block scalar (|) — complex, needs manual fix
    if extra_value.strip() == '|':
        reason = f"name has block scalar '|' — skipping (manual review needed)"
        return frontmatter, False, reason

    # Clean up description value — remove surrounding quotes if present
    desc_value = extra_value.strip('"').strip("'")

    # Fix: replace the bad name line
    old_line = match.group(0)
    new_name_line = f"name: {full_name_value}"

    fixed = frontmatter.replace(old_line, new_name_line, 1)

    # Add description if not already present
    if not has_description(fixed) and desc_value:
        # Insert description right after name line
        fixed = fixed.replace(
            new_name_line,
            f"{new_name_line}\ndescription: \"{desc_value}\"",
            1
        )
        reason = f"Moved description from name field"
    else:
        reason = f"Fixed name field (description already exists)"

    return fixed, True, reason

def process_skill(skill_path: Path, dry_run: bool = False) -> dict:
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return None

    content = skill_md.read_text(encoding='utf-8', errors='replace')
    pre, frontmatter, body = parse_frontmatter(content)

    if frontmatter is None:
        return {"skill": skill_path.name, "status": "no_frontmatter"}

    fixed_fm, changed, reason = fix_frontmatter(frontmatter, skill_path.name)

    if not changed:
        if reason:
            return {"skill": skill_path.name, "status": "skipped", "reason": reason}
        return {"skill": skill_path.name, "status": "ok"}

    if not dry_run:
        new_content = f"---{fixed_fm}---{body}"
        skill_md.write_text(new_content, encoding='utf-8')

    return {"skill": skill_path.name, "status": "fixed", "reason": reason}

def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("🔍 DRY RUN — no files will be changed\n")
    else:
        print("🔧 FIXING skills...\n")

    results = {"ok": [], "fixed": [], "skipped": [], "no_frontmatter": []}

    skill_dirs = sorted([d for d in SKILLS_DIR.iterdir() if d.is_dir()])
    print(f"Scanning {len(skill_dirs)} skills...\n")

    for skill_dir in skill_dirs:
        result = process_skill(skill_dir, dry_run=dry_run)
        if result is None:
            continue
        status = result["status"]
        results[status].append(result)

    # Report
    print(f"✅ OK (valid):        {len(results['ok'])}")
    print(f"🔧 Fixed:             {len(results['fixed'])}")
    print(f"⚠️  Skipped (manual): {len(results['skipped'])}")
    print(f"❌ No frontmatter:    {len(results['no_frontmatter'])}")

    if results['fixed']:
        print("\n--- FIXED ---")
        for r in results['fixed']:
            print(f"  {r['skill']}: {r['reason']}")

    if results['skipped']:
        print("\n--- NEEDS MANUAL REVIEW ---")
        for r in results['skipped']:
            print(f"  {r['skill']}: {r['reason']}")

    if results['no_frontmatter']:
        print("\n--- NO FRONTMATTER ---")
        for r in results['no_frontmatter']:
            print(f"  {r['skill']}")

if __name__ == "__main__":
    main()
