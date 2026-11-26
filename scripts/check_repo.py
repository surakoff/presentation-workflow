"""Check that the team starter is usable without files from its source project."""

from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
OWN_SKILL = SKILLS / "presentation-art-director"
LINK = re.compile(r"(?<!!)\[[^\]\n]+\]\(<?([^\s)>]+)>?\)")
REQUIRED = (
    "README.md", "AGENTS.md", "THIRD_PARTY.md", "templates/brief.md",
    "templates/pdf-block-review.tsv",
    ".agents/skills/presentation-art-director/SKILL.md",
    ".agents/skills/presentation-art-director/scripts/audit-slide.js",
    ".agents/skills/presentation-art-director/references/figma-design.md",
    ".agents/skills/presentation-art-director/references/powerpoint.md",
    ".agents/skills/presentation-art-director/references/pdf-optimization.md",
    ".agents/skills/presentation-art-director/references/motion.md",
    ".agents/skills/presentation-art-director/references/tools.md",
    ".agents/skills/ppt-master/LICENSE",
    ".agents/skills/pptx/LICENSE.txt",
    ".agents/skills/pdf/LICENSE.txt",
)
NONPORTABLE = re.compile(r"(?i)[a-z]:[/\\](?:Users|CodexData)")


def check_docs() -> list[str]:
    errors = []
    files = [
        *ROOT.glob("*.md"), *OWN_SKILL.rglob("*.md"),
        *(ROOT / "templates").glob("*.md"),
    ]
    for file in files:
        content = file.read_text(encoding="utf-8-sig")
        if NONPORTABLE.search(content):
            errors.append(f"Source project still referenced in {file.relative_to(ROOT)}")
        for link in LINK.findall(content):
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path:
                continue
            dest = (file.parent / unquote(url.path)).resolve()
            if not dest.is_relative_to(ROOT) or not dest.exists():
                errors.append(f"{file.relative_to(ROOT)}: missing or external local link {link}")
    return errors


def check_skills() -> list[str]:
    errors = []
    for name in ("presentation-art-director", "ppt-master", "pptx", "pdf"):
        skill = SKILLS / name / "SKILL.md"
        if not skill.is_file():
            errors.append(f"Missing entry point for {name}")
            continue
        parts = skill.read_text(encoding="utf-8-sig").split("---", 2)
        if (len(parts) != 3 or parts[0].strip()
                or not re.search(rf"(?m)^name:\s*{re.escape(name)}\s*$", parts[1])
                or not re.search(r"(?m)^description:", parts[1])):
            errors.append(f"Invalid skill metadata for {name}")
    return errors


def check_starter_contents() -> list[str]:
    errors = []
    # Inspect the distributed surface. Projects and exported files are local and ignored.
    for folder in (ROOT / "templates", OWN_SKILL):
        for file in folder.rglob("*"):
            if file == OWN_SKILL / "scripts" / "audit-slide.js":
                continue
            if file.is_file() and file.suffix not in {".md", ".tsv", ".yaml"}:
                errors.append(f"Unexpected starter artifact: {file.relative_to(ROOT)}")
    return errors


def main() -> int:
    errors = [f"Missing {path}" for path in REQUIRED if not (ROOT / path).is_file()]
    errors += check_docs() + check_skills() + check_starter_contents()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Starter checks passed: 4 skills, guide links, and starter contents.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
