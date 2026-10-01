"""Lightweight skill canonicalization for the demo dataset and matching.

Deliberately small and curated: RecruitAgent is about agent engineering, not
a second-generation matching engine. Precision over recall; unknown terms pass
through untouched (normalized lowercase).
"""

from __future__ import annotations

import re

ALIASES: dict[str, str] = {
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "node": "node.js",
    "nodejs": "node.js",
    "node.js": "node.js",
    "react": "react",
    "react.js": "react",
    "reactjs": "react",
    "next.js": "next.js",
    "nextjs": "next.js",
    "vue": "vue",
    "angular": "angular",
    "python": "python",
    "py": "python",
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "java": "java",
    "go": "go",
    "golang": "go",
    "rust": "rust",
    "ruby": "ruby",
    "rails": "ruby on rails",
    "php": "php",
    "c#": "c#",
    ".net": ".net",
    "c++": "c++",
    "kotlin": "kotlin",
    "swift": "swift",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "mysql": "mysql",
    "sqlite": "sqlite",
    "mongodb": "mongodb",
    "redis": "redis",
    "elasticsearch": "elasticsearch",
    "sql": "sql",
    "graphql": "graphql",
    "rest": "rest apis",
    "rest apis": "rest apis",
    "api development": "rest apis",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "aws": "aws",
    "gcp": "gcp",
    "azure": "azure",
    "terraform": "terraform",
    "ansible": "ansible",
    "linux": "linux",
    "bash": "bash",
    "git": "git",
    "ci/cd": "ci/cd",
    "github actions": "github actions",
    "jenkins": "jenkins",
    "kafka": "kafka",
    "rabbitmq": "rabbitmq",
    "spark": "apache spark",
    "airflow": "airflow",
    "dbt": "dbt",
    "etl": "etl",
    "snowflake": "snowflake",
    "bigquery": "bigquery",
    "machine learning": "machine learning",
    "ml": "machine learning",
    "pytorch": "pytorch",
    "tensorflow": "tensorflow",
    "nlp": "nlp",
    "pandas": "pandas",
    "numpy": "numpy",
    "tableau": "tableau",
    "power bi": "power bi",
    "looker": "looker",
    "excel": "excel",
    "data analysis": "data analysis",
    "pytest": "pytest",
    "jest": "jest",
    "playwright": "playwright",
    "selenium": "selenium",
    "cypress": "cypress",
    "testing": "testing",
    "agile": "agile",
    "scrum": "scrum",
    "jira": "jira",
    "confluence": "confluence",
    "salesforce": "salesforce",
    "hubspot": "hubspot",
    "zendesk": "zendesk",
    "freshdesk": "freshdesk",
    "intercom": "intercom",
    "customer support": "customer support",
    "customer success": "customer success",
    "stakeholder management": "stakeholder management",
    "project management": "project management",
    "communication": "communication",
    "recruiting": "recruiting",
    "sourcing": "sourcing",
    "ats": "ats systems",
    "interviewing": "interviewing",
    "onboarding": "onboarding",
    "hr operations": "hr operations",
    "payroll": "payroll",
    "product management": "product management",
    "figma": "figma",
    "ui design": "ui design",
    "ux": "ux design",
    "accessibility": "accessibility",
    "seo": "seo",
    "content marketing": "content marketing",
    "sales": "sales",
    "negotiation": "negotiation",
    "account management": "account management",
}

#: Coarse families for related-skill partial credit (same family, different skill).
FAMILIES: dict[str, str] = {
    "python": "backend",
    "fastapi": "backend",
    "django": "backend",
    "flask": "backend",
    "node.js": "backend",
    "java": "backend",
    "go": "backend",
    "ruby on rails": "backend",
    "php": "backend",
    ".net": "backend",
    "c#": "backend",
    "javascript": "frontend",
    "typescript": "frontend",
    "react": "frontend",
    "next.js": "frontend",
    "vue": "frontend",
    "angular": "frontend",
    "postgresql": "databases",
    "mysql": "databases",
    "mongodb": "databases",
    "redis": "databases",
    "sqlite": "databases",
    "elasticsearch": "databases",
    "sql": "databases",
    "docker": "devops",
    "kubernetes": "devops",
    "terraform": "devops",
    "ansible": "devops",
    "jenkins": "devops",
    "github actions": "devops",
    "ci/cd": "devops",
    "aws": "cloud",
    "gcp": "cloud",
    "azure": "cloud",
    "machine learning": "ml",
    "pytorch": "ml",
    "tensorflow": "ml",
    "nlp": "ml",
    "pandas": "ml",
    "numpy": "ml",
    "tableau": "analytics",
    "power bi": "analytics",
    "looker": "analytics",
    "excel": "analytics",
    "data analysis": "analytics",
    "zendesk": "support-tools",
    "freshdesk": "support-tools",
    "intercom": "support-tools",
    "customer support": "support",
    "customer success": "support",
    "recruiting": "recruiting",
    "sourcing": "recruiting",
    "interviewing": "recruiting",
    "ats systems": "recruiting",
    "onboarding": "recruiting",
}

_token_re = re.compile(r"[^a-z0-9+#./ -]")


def canonicalize(name: str) -> str:
    """Normalize a raw skill name into its canonical form."""
    cleaned = _token_re.sub("", name.strip().lower()).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return ALIASES.get(cleaned, cleaned)


def family_of(skill: str) -> str | None:
    return FAMILIES.get(skill)


def are_related(a: str, b: str) -> bool:
    """Two *different* skills in the same family count as related."""
    if a == b:
        return False
    fa, fb = family_of(a), family_of(b)
    return fa is not None and fa == fb


def mention_in_text(term: str, text: str) -> bool:
    """Word-boundary search for a term inside (untrusted) text."""
    if not term or not text:
        return False
    pattern = re.escape(term)
    return bool(re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", text.lower()))
