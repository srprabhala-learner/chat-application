import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SourceDoc:
    source_path: str
    text: str


def read_text_file(path: Path) -> str:
    # best-effort UTF-8
    return path.read_text(encoding="utf-8", errors="ignore")


def iter_source_docs(entitlements_root: Path) -> list[SourceDoc]:
    """
    Collect knowledge sources from entitlements-app:
    - db/schema.sql, db/data_seed.sql
    - markdown docs
    - backend java/yaml
    - frontend key files (optional)
    """
    allow_ext = {".sql", ".md", ".java", ".yaml", ".yml", ".ts", ".tsx", ".js", ".jsx"}
    deny_dirs = {"node_modules", "target", ".git", "dist", "build"}

    docs: list[SourceDoc] = []

    for root, dirs, files in os.walk(entitlements_root):
        dirs[:] = [d for d in dirs if d not in deny_dirs]

        for f in files:
            p = Path(root) / f
            if p.suffix.lower() not in allow_ext:
                continue
            # keep it focused
            rel = str(p.relative_to(entitlements_root))
            if rel.startswith("frontend/node_modules") or rel.startswith("backend/entitlements-service/target"):
                continue
            text = read_text_file(p)
            if not text.strip():
                continue
            docs.append(SourceDoc(source_path=rel, text=text))

    return docs


