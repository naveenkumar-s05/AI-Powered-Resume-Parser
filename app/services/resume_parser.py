import re
from datetime import date, datetime
from pathlib import Path

import pdfplumber
from docx import Document

from app.core.validation import normalize_phone

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_CANDIDATE_RE = re.compile(r"(?:\+?\d[\d\s\-().]{7,}\d)")
DEGREE_RE = re.compile(
    r"\b(?:B\.E\.?|B\.Tech|M\.Tech|B\.Sc|M\.Sc|BCA|MCA|MBA|B\.Com|M\.Com|Ph\.?D|BE|ME|BSc|MSc|BCom|MCom)\b"
    r"|(?i:\b(?:Bachelor|Master|Diploma)\b)"
)

NAME_BLACKLIST = {
    "resume",
    "curriculum",
    "vitae",
    "education",
    "skills",
    "experience",
    "project",
    "projects",
    "profile",
    "contact",
    "summary",
    "objective",
    "certification",
    "certifications",
    "declaration",
    "achievements",
    "languages",
    "hobbies",
    "references",
}

SKILLS = [
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust",
    "PHP", "Ruby", "Kotlin", "Swift", "SQL", "PostgreSQL", "MySQL", "MongoDB",
    "Redis", "FastAPI", "Django", "Flask", "React", "ReactJS", "Angular", "Vue",
    "Node.js", "Express", "HTML", "CSS", "Bootstrap", "Tailwind", "Docker",
    "Kubernetes", "AWS", "Azure", "GCP", "Git", "Linux", "Machine Learning",
    "Deep Learning", "NLP", "Data Science", "Pandas", "NumPy", "TensorFlow",
    "PyTorch", "Scikit-learn", "REST", "GraphQL", "Microservices", "JWT",
    "Celery", "RabbitMQ", "Kafka", "Agile", "Scrum", "Selenium", "Postman",
    "AutoCAD", "SolidWorks", "Creo", "CATIA", "ANSYS", "MATLAB", "MS Office",
    "MS Excel", "MS Word", "PowerPoint", "Manufacturing",
]

SECTION_ALIASES = {
    "education": ("education", "academic", "qualification"),
    "projects": ("project",),
    "internships": ("internship", "training"),
    "experience": ("experience", "employment"),
    "skills": ("skill", "technolog", "competenc"),
}

MONTH_RE = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\.?"
)

DURATION_RE = re.compile(
    rf"(?:{MONTH_RE}\s+\d{{4}}|\d{{4}})\s*(?:[-–—]|to)\s*"
    rf"(?:Present|Current|{MONTH_RE}\s+\d{{4}}|\d{{4}})"
    rf"|\b\d+\s*(?:months?|years?)\b",
    re.IGNORECASE,
)

SINGLE_DATE_RE = re.compile(rf"{MONTH_RE}\s+\d{{4}}", re.IGNORECASE)

YEAR_RE = re.compile(
    r"\b(?:19|20)\d{2}\s*(?:[-–—]\s*(?:(?:19|20)?\d{2}|Present|Current))?\b",
    re.IGNORECASE,
)

CGPA_RE = re.compile(
    r"(?:CGPA|GPA|Percentage|Score)\s*[:\-]?\s*"
    r"([0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?\s*%?)",
    re.IGNORECASE,
)

INSTITUTION_RE = re.compile(
    r"\b(?:university|college|institute|school|academy|polytechnic)\b",
    re.IGNORECASE,
)

SECONDARY_RE = re.compile(
    r"\b(?:HSC|SSLC|12th|10th|Higher Secondary|Secondary School)\b",
    re.IGNORECASE,
)

PERCENTAGE_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")

OTHER_SECTION_RE = re.compile(
    r"^(?:github|gitlab|portfolio|certifications?|achievements?|awards?|"
    r"co[- ]?curricular|extra[- ]?curricular|activities|languages|hobbies|"
    r"interests|declaration|references|publications|volunteer|leadership|"
    r"professional summary|summary|objective|profile)$",
    re.IGNORECASE,
)

TECH_LINE_RE = re.compile(
    r"^(?:tech(?:nologies|nology)?(?:\s+used)?|tech\s*stack|tools?|stack)"
    r"\s*[:\-]\s*(.+)$",
    re.IGNORECASE,
)

CONTINUATION_RE = re.compile(
    r"^(?:built|developed|created|designed|implemented|integrated|deployed|used|"
    r"worked|led|managed|analy[sz]ed|trained|achieved|improved|automated|enabled|"
    r"provided|added|generated|stored|maintained|documented|applied|gained|covered|"
    r"conducted|organized|organised|attended|successfully|fine[- ]?tuned|"
    r"fine[- ]?tuning|tested|evaluated|optimized|optimised|scaled|delivered|"
    r"collaborated|researched|visualized|visualised|simulated|modeled|modelled|"
    r"leveraged|utilized|utilised)\b",
    re.IGNORECASE,
)

CONTINUATION_TAIL_RE = re.compile(
    r"(?:[,;:]|\b(?:and|with|for|to|of|in|on|by|using|from|via))\s*$",
    re.IGNORECASE,
)

ROLE_KEYWORDS = re.compile(
    r"\b(?:intern|internship|engineer|developer|analyst|manager|consultant|"
    r"trainee|associate|specialist|designer|architect|lead|head|officer|"
    r"executive|scientist|administrator|coordinator)\b",
    re.IGNORECASE,
)

COMPANY_KEYWORDS = re.compile(
    r"\b(?:pvt|private|ltd|limited|inc|corp|corporation|company|technologies|"
    r"technology|solutions|systems|services|labs|consulting|group|enterprises|"
    r"university|college|institute)\b",
    re.IGNORECASE,
)

DOB_RE = re.compile(
    r"(?:date\s*of\s*birth|d\.?\s*o\.?\s*b\.?|dob|born)[^0-9\n]{0,40}"
    r"([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4}"
    r"|[0-9]{4}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{1,2}"
    r"|[0-9]{1,2}\s+[A-Za-z]{3,9},?\s+[0-9]{4}"
    r"|[A-Za-z]{3,9}\s+[0-9]{1,2},?\s+[0-9]{4})",
    re.IGNORECASE,
)


def extract_text(path: Path, suffix: str) -> str:
    suffix = suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".docx":
        return _extract_docx(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def _extract_pdf(path: Path) -> str:
    parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            parts.append(text)
    return "\n".join(parts).strip()


def _extract_docx(path: Path) -> str:
    document = Document(str(path))
    parts: list[str] = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts).strip()


def _extract_email(text: str) -> str | None:
    match = EMAIL_RE.search(text)
    return match.group(0).lower() if match else None


def _extract_phone(text: str) -> str | None:
    lines = [line for line in text.splitlines() if line.strip()]

    prioritized = [
        line for line in lines
        if re.search(r"phone|mobile|contact|tel", line, re.IGNORECASE)
    ]
    for source in (prioritized, lines):
        for candidate in PHONE_CANDIDATE_RE.findall("\n".join(source)):
            digits = re.sub(r"\D", "", candidate)
            if not (10 <= len(digits) <= 15):
                continue
            if digits.startswith(("19", "20")) and len(digits) == 4:
                continue
            try:
                return normalize_phone(candidate)
            except ValueError:
                continue
    return None


def _looks_like_name(line: str) -> bool:
    cleaned = line.strip(" \t-•|,")
    if not cleaned or len(cleaned) > 60:
        return False
    lowered = cleaned.lower()
    if any(keyword in lowered for keyword in NAME_BLACKLIST):
        return False
    if EMAIL_RE.search(cleaned) or "http" in lowered or "@" in cleaned:
        return False
    if re.search(r"\d", cleaned):
        return False
    words = cleaned.split()
    if not (2 <= len(words) <= 4):
        return False
    return all(re.fullmatch(r"[A-Za-z][A-Za-z.'\-]*", word) for word in words)


def _extract_name(text: str) -> str | None:
    for line in text.splitlines()[:20]:
        if _looks_like_name(line):
            words = line.strip().split()
            return " ".join(word[:1].upper() + word[1:].lower() for word in words)
    return None


FILENAME_STOPWORDS = NAME_BLACKLIST | {
    "cv",
    "final",
    "updated",
    "latest",
    "new",
    "copy",
    "doc",
    "docx",
    "pdf",
}


def name_from_filename(filename: str) -> str | None:
    tokens = re.split(r"[\s\-_().,]+", Path(filename).stem)
    words: list[str] = []
    for token in tokens:
        cleaned = token.strip()
        if not cleaned:
            continue
        if cleaned.lower() in FILENAME_STOPWORDS:
            if words:
                break
            continue
        if not re.fullmatch(r"[A-Za-z][A-Za-z.'\-]*", cleaned):
            if words:
                break
            continue
        words.append(cleaned)
        if len(words) == 4:
            break
    if not (2 <= len(words) <= 4):
        return None
    return " ".join(word[:1].upper() + word[1:].lower() for word in words)


def _skill_present(lowered_text: str, skill: str) -> bool:
    pattern = r"(?<![a-z0-9+#])" + re.escape(skill.lower()) + r"(?![a-z0-9+#])"
    return re.search(pattern, lowered_text) is not None


def _extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    return [skill for skill in SKILLS if _skill_present(lowered, skill)]


def _extract_experience(text: str) -> str | None:
    lowered = text.lower()
    if re.search(r"\bfresher\b", lowered):
        return "Fresher"

    lines = [
        line
        for line in text.splitlines()
        if not re.search(r"\b(?:age|dob|date of birth)\b", line, re.IGNORECASE)
    ]
    experience_lines = [
        line
        for line in lines
        if re.search(r"experience|worked|professional", line, re.IGNORECASE)
    ]

    for scoped in (experience_lines, lines):
        joined = "\n".join(scoped).lower()
        years = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", joined)
        if years:
            return f"{years.group(1)} years"
        months = re.search(r"(\d+)\s*\+?\s*months?", joined)
        if months:
            return f"{months.group(1)} months"
    return None


def _extract_qualification(text: str) -> str | None:
    for line in text.splitlines():
        cleaned = line.strip(" \t-•|,")
        if not cleaned or len(cleaned) > 120:
            continue
        if DEGREE_RE.search(cleaned):
            return cleaned
    return None


def _heading_key(line: str) -> str | None:
    cleaned = re.sub(r"[^a-z ]", " ", line.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned or len(cleaned) > 40 or any(ch.isdigit() for ch in line):
        return None
    if len(cleaned.split()) > 5:
        return None
    if "internship" in cleaned or "training" in cleaned:
        return "internships"
    if "education" in cleaned or "academic" in cleaned or "qualification" in cleaned:
        return "education"
    if "project" in cleaned:
        return "projects"
    if "skill" in cleaned or "technolog" in cleaned or "competenc" in cleaned:
        return "skills"
    if "experience" in cleaned or "employment" in cleaned:
        return "experience"
    if OTHER_SECTION_RE.match(cleaned):
        return "other"
    return None


def _split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if ":" in line:
            prefix, _, rest = line.partition(":")
            prefix_key = _heading_key(prefix)
            if prefix_key:
                current = prefix_key
                sections.setdefault(current, [])
                if rest.strip():
                    sections[current].append(rest.strip())
                continue
        key = _heading_key(line)
        if key:
            current = key
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _is_bullet(line: str) -> bool:
    return bool(re.match(r"^\s*(?:[-•*–—]|\d+[.)])\s+", line))


def _clean_bullet(line: str) -> str:
    cleaned = re.sub(r"^\s*(?:[-•*–—]|\d+[.)])\s+", "", line).strip()
    return cleaned.strip(" \t|,;")


def _normalize_date(raw: str) -> str | None:
    value = raw.strip()
    for fmt in (
        "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y",
        "%B %d %Y", "%b %d %Y", "%d %B, %Y", "%d %b, %Y",
    ):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue

    normalized = value.replace(".", "/").replace("-", "/")
    parts = [part for part in re.split(r"[\/\s]+", normalized) if part]
    if len(parts) != 3:
        return None
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return None

    if len(parts[0]) == 4:
        year, month, day = numbers
    else:
        first, second, year = numbers
        if first > 12:
            day, month = first, second
        elif second > 12:
            month, day = first, second
        else:
            day, month = first, second
    if year < 100:
        year += 1900 if year >= 30 else 2000
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _extract_dob(text: str) -> str | None:
    match = DOB_RE.search(text)
    return _normalize_date(match.group(1)) if match else None


def _extract_year(line: str) -> str | None:
    match = YEAR_RE.search(line)
    return match.group(0).strip() if match else None


def _extract_cgpa(line: str) -> str | None:
    match = CGPA_RE.search(line)
    return match.group(1).strip() if match else None


def _extract_percentage(line: str) -> str | None:
    match = PERCENTAGE_RE.search(line)
    return f"{match.group(1)}%" if match else None


def _institution_from_line(line: str) -> str | None:
    parts = [
        part.strip(" \t|,;-–—")
        for part in re.split(r"\s*[|•·]\s*", line)
        if part.strip()
    ]
    candidates = [part for part in parts if INSTITUTION_RE.search(part)]
    source = candidates[0] if candidates else (line if INSTITUTION_RE.search(line) else None)
    if not source:
        return None
    if ":" in source:
        prefix, _, rest = source.partition(":")
        if (
            DEGREE_RE.search(prefix) or SECONDARY_RE.search(prefix)
        ) and INSTITUTION_RE.search(rest):
            source = rest.strip()
    first, _, rest = source.partition(",")
    if (DEGREE_RE.search(first) or SECONDARY_RE.search(first)) and rest.strip():
        source = rest.strip()
    cleaned = YEAR_RE.sub("", source)
    cleaned = PERCENTAGE_RE.sub("", cleaned)
    cleaned = re.sub(
        r"\b(?:CGPA|GPA|Percentage|Score)\b\s*[:\-]?\s*[0-9.]+\s*%?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" \t|,;-–—:")
    return cleaned[:200] or None


def _degree_label(line: str) -> str:
    cleaned = line.strip()
    if ":" in cleaned:
        prefix = cleaned.split(":", 1)[0].strip()
        if DEGREE_RE.search(prefix) or SECONDARY_RE.search(prefix):
            return prefix[:150]
    parts = [
        part.strip()
        for part in re.split(r"\s*[|•·]\s*|\s*,\s*", cleaned)
        if part.strip()
    ]
    if parts and (DEGREE_RE.search(parts[0]) or SECONDARY_RE.search(parts[0])):
        return parts[0][:150]
    return cleaned[:150]


def _line_has_education_meta(line: str) -> bool:
    return bool(
        _extract_year(line)
        or _extract_cgpa(line)
        or _extract_percentage(line)
        or INSTITUTION_RE.search(line)
    )


def _make_education_entry(degree_line: str, metadata_lines: list[str]) -> dict:
    parts = [degree_line, *metadata_lines]
    detail_parts = [degree_line]
    detail_parts.extend(
        line for line in metadata_lines if not _line_has_education_meta(line)
    )
    details = " | ".join(
        part.strip() for part in detail_parts if part.strip()
    )[:1000]
    entry = {
        "degree": _degree_label(degree_line),
        "institution": None,
        "year": None,
        "cgpa": None,
        "details": details or None,
    }
    for source in parts:
        year = _extract_year(source)
        if year and not entry["year"]:
            entry["year"] = year
        cgpa = _extract_cgpa(source) or _extract_percentage(source)
        if cgpa and not entry["cgpa"]:
            entry["cgpa"] = cgpa
        institution = _institution_from_line(source)
        if institution and not entry["institution"]:
            entry["institution"] = institution
    return entry


def _extract_education(text: str) -> list[dict]:
    sections = _split_sections(text)
    lines = sections.get("education") or []
    if not lines:
        lines = [
            line.strip()
            for line in text.splitlines()
            if DEGREE_RE.search(line) or SECONDARY_RE.search(line)
        ]

    lines = [
        line.strip()
        for line in lines
        if line.strip() and not _heading_key(line)
    ]
    degree_indices = [
        index
        for index, line in enumerate(lines)
        if DEGREE_RE.search(line) or SECONDARY_RE.search(line)
    ]
    if not degree_indices:
        return []

    first_degree = degree_indices[0]
    metadata_before_first = any(
        _line_has_education_meta(line) for line in lines[:first_degree]
    )

    entries: list[dict] = []
    if metadata_before_first:
        buffer: list[str] = []
        for line in lines:
            if DEGREE_RE.search(line) or SECONDARY_RE.search(line):
                entries.append(_make_education_entry(line, buffer))
                buffer = []
            else:
                buffer.append(line)
    else:
        current_degree: str | None = None
        buffer = []
        for line in lines:
            if DEGREE_RE.search(line) or SECONDARY_RE.search(line):
                if current_degree is not None:
                    entries.append(_make_education_entry(current_degree, buffer))
                current_degree = line
                buffer = []
            else:
                buffer.append(line)
        if current_degree is not None:
            entries.append(_make_education_entry(current_degree, buffer))
    return entries[:5]


def _parse_tech_list(raw: str) -> list[str]:
    items = re.split(r"[|,;/]|\s+and\s+", raw, flags=re.IGNORECASE)
    result: list[str] = []
    for item in items:
        cleaned = item.strip(" \t.-–—")
        if cleaned and len(cleaned) <= 50:
            result.append(cleaned)
    return result[:50]


def _merge_technologies(primary: list[str], secondary: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in [*primary, *secondary]:
        cleaned = item.strip()
        if not cleaned:
            continue
        key = cleaned.lower().rstrip(".")
        if key in seen:
            continue
        if any(f"{key}." in existing.lower() for existing in result):
            continue
        result.append(cleaned)
        seen.add(key)
        if len(result) >= 50:
            break
    return result


def _is_project_title(line: str) -> bool:
    cleaned = line.strip()
    if not cleaned or len(cleaned) > 160:
        return False
    if TECH_LINE_RE.match(cleaned) or CONTINUATION_RE.match(cleaned):
        return False
    if CONTINUATION_TAIL_RE.search(cleaned) or cleaned[:1].islower():
        return False
    if re.search(r"[.!?]\s*$", cleaned) and not cleaned.isupper():
        return False
    if cleaned.isupper():
        return True
    return len(cleaned) <= 80 and len(cleaned.split()) <= 10


def _is_project_continuation(line: str) -> bool:
    cleaned = line.strip()
    if not cleaned:
        return False
    if cleaned[:1].islower() or CONTINUATION_RE.match(cleaned):
        return True
    if CONTINUATION_TAIL_RE.search(cleaned) or len(cleaned) > 120:
        return True
    return False


def _extract_projects(text: str) -> list[dict]:
    lines = _split_sections(text).get("projects") or []
    if not lines:
        return []
    entries: list[dict] = []
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current and current.get("title"):
            entries.append(current)
        current = None

    for raw in lines:
        cleaned = _clean_bullet(raw)
        if not cleaned or _heading_key(cleaned):
            continue

        tech_match = TECH_LINE_RE.match(cleaned)
        if tech_match:
            if current is not None:
                explicit = _parse_tech_list(tech_match.group(1))
                current["technologies"] = _merge_technologies(
                    current["technologies"], explicit
                )
            continue

        if current is None:
            if _is_project_title(cleaned):
                current = {
                    "title": cleaned[:150],
                    "description": "",
                    "technologies": [],
                }
            continue

        if _is_project_title(cleaned) and not _is_project_continuation(cleaned):
            flush()
            current = {
                "title": cleaned[:150],
                "description": "",
                "technologies": [],
            }
            continue

        current["description"] = (
            current["description"] + " " + cleaned
        ).strip()[:2000]

    flush()
    for entry in entries:
        detected = _extract_skills(f"{entry['title']} {entry['description']}")
        entry["technologies"] = _merge_technologies(
            entry["technologies"], detected
        )
        entry["description"] = entry["description"] or None
    return entries[:10]


def _parse_role_company(line: str) -> tuple[str | None, str | None, str | None]:
    cleaned = line.strip()
    duration = None
    duration_match = DURATION_RE.search(cleaned)
    if duration_match:
        duration = duration_match.group(0).strip()[:100]
        cleaned = (
            cleaned[:duration_match.start()] + " " + cleaned[duration_match.end():]
        ).strip(" |,;-–—")
    else:
        single_match = SINGLE_DATE_RE.search(cleaned)
        if single_match:
            duration = single_match.group(0).strip()[:100]
            cleaned = (
                cleaned[:single_match.start()] + " " + cleaned[single_match.end():]
            ).strip(" |,;-–—")

    parts = [
        part.strip(" |,;-–—")
        for part in re.split(r"\s*[|•·]\s*|\s+[–—]\s+|\s+-\s+|\s+at\s+|,\s*", cleaned)
        if part.strip(" |,;-–—")
    ]
    role: str | None = None
    company: str | None = None
    for part in parts:
        if ROLE_KEYWORDS.search(part) and role is None:
            role = part[:150]
        elif COMPANY_KEYWORDS.search(part) and company is None:
            company = part[:150]

    if role is None and company is None:
        if len(parts) >= 2:
            role, company = parts[0][:150], parts[1][:150]
        elif parts:
            if ROLE_KEYWORDS.search(parts[0]):
                role = parts[0][:150]
            else:
                company = parts[0][:150]
    elif role is None:
        for part in parts:
            if part != company and ROLE_KEYWORDS.search(part):
                role = part[:150]
                break
    elif company is None:
        for part in parts:
            if part != role:
                company = part[:150]
                break
    return role, company, duration


def _extract_work_entries(
    text: str, section: str, skip_fresher: bool = False
) -> list[dict]:
    lines = _split_sections(text).get(section) or []
    if not lines:
        return []
    entries: list[dict] = []
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current and any(current.values()):
            entries.append(current)
        current = None

    for raw in lines:
        cleaned = _clean_bullet(raw)
        if not cleaned or _heading_key(cleaned):
            continue
        if skip_fresher and cleaned.lower() in {"fresher", "fresher graduate"}:
            continue

        if current is None:
            current = {
                "company": None,
                "role": None,
                "duration": None,
                "description": "",
            }

        bullet = _is_bullet(raw)
        duration = DURATION_RE.search(cleaned)
        role_match = ROLE_KEYWORDS.search(cleaned)
        company_match = COMPANY_KEYWORDS.search(cleaned)

        if bullet:
            if not current["role"] and not current["company"] and not current["description"]:
                role, company, dur = _parse_role_company(cleaned)
                if role or company:
                    current["role"] = role
                    current["company"] = company
                    current["duration"] = dur
                    continue
            current["description"] = (current["description"] + " " + cleaned).strip()[:2000]
            continue

        word_count = len(cleaned.split())
        is_sentence = bool(
            CONTINUATION_RE.match(cleaned)
            or cleaned[:1].islower()
            or (cleaned.endswith((",", ";")) and word_count > 6)
            or (cleaned.endswith(".") and word_count > 6)
            or len(cleaned) > 120
        )
        if is_sentence:
            current["description"] = (
                current["description"] + " " + cleaned
            ).strip()[:2000]
            continue

        if duration and not role_match and not company_match:
            if current["duration"] is None:
                current["duration"] = duration.group(0).strip()[:100]
                continue

        if role_match or company_match:
            if current["role"] and current["company"]:
                flush()
                current = {
                    "company": None,
                    "role": None,
                    "duration": None,
                    "description": "",
                }
            role, company, dur = _parse_role_company(cleaned)
            if role and not current["role"]:
                current["role"] = role
            if company and not current["company"]:
                current["company"] = company
            if dur and not current["duration"]:
                current["duration"] = dur
            if not role and not company:
                if not current["role"]:
                    current["role"] = cleaned[:150]
                else:
                    current["description"] = (
                        current["description"] + " " + cleaned
                    ).strip()[:2000]
            continue

        if current["role"] is None and len(cleaned) <= 100:
            current["role"] = cleaned[:150]
        elif current["company"] is None and len(cleaned) <= 150:
            current["company"] = cleaned[:150]
        else:
            current["description"] = (current["description"] + " " + cleaned).strip()[:2000]

    flush()
    for entry in entries:
        entry["description"] = entry["description"] or None
    return entries[:10]


def parse_fields(text: str, filename: str | None = None) -> tuple[dict, list[str]]:
    warnings: list[str] = []

    email = _extract_email(text)
    phone = _extract_phone(text)
    full_name = _extract_name(text)
    skills = _extract_skills(text)
    experience = _extract_experience(text)
    education = _extract_education(text)
    qualification = _extract_qualification(text) or (
        education[0]["degree"] if education else None
    )
    dob = _extract_dob(text)
    projects = _extract_projects(text)
    internships = _extract_work_entries(text, "internships")
    experience_entries = _extract_work_entries(
        text, "experience", skip_fresher=True
    )

    if not full_name and filename:
        full_name = name_from_filename(filename)
        if full_name:
            warnings.append("Name inferred from the uploaded file name")

    if not email:
        warnings.append("Email could not be detected; please enter it manually")
    if not phone:
        warnings.append("Phone could not be detected; please enter it manually")
    if not full_name:
        warnings.append("Name could not be detected; please enter it manually")
    if not skills:
        warnings.append("No known skills were detected")
    if not experience:
        warnings.append("Experience could not be detected")
    if not education and not qualification:
        warnings.append("Education details could not be detected; add them manually")

    parsed = {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "dob": dob,
        "skills": skills,
        "experience": experience,
        "qualification": qualification,
        "education": education,
        "projects": projects,
        "internships": internships,
        "experience_entries": experience_entries,
    }
    return parsed, warnings
