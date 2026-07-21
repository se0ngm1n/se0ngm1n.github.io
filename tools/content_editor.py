#!/usr/bin/env python3
"""Dependency-free local web editor for the portfolio Markdown content."""

from __future__ import annotations

import argparse
import ast
import json
import re
import secrets
import subprocess
import threading
import webbrowser
from dataclasses import dataclass
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = ROOT / "src" / "content"
PROFILE_PATH = ROOT / "src" / "data" / "profile.ts"
PROFILE_SLUG = "home"
MEDIA_DIRECTORIES = {
    "projects": "project-media",
    "study": "study-media",
    "life": "life-media",
}
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_VIDEO_BYTES = 90 * 1024 * 1024


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str = "text"
    required: bool = False
    choices: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "required": self.required,
            "choices": list(self.choices),
        }


SCHEMAS: dict[str, tuple[Field, ...]] = {
    "projects": (
        Field("title", "제목", required=True),
        Field("subtitle", "부제"),
        Field("period", "기간", required=True),
        Field("category", "카테고리", required=True),
        Field("summary", "목록 요약", "multiline"),
        Field("technologies", "기술 (한 줄에 하나)", "list"),
        Field("outcomes", "성과 (한 줄에 하나)", "list"),
        Field("order", "정렬 순서", "integer", True),
    ),
    "study": (
        Field("title", "제목", required=True),
        Field("date", "날짜 (YYYY-MM-DD)", "date", True),
        Field("category", "카테고리", required=True),
        Field("summary", "목록 요약", "multiline", True),
        Field("tags", "태그 (한 줄에 하나)", "list"),
        Field("thumbnail", "썸네일 경로"),
    ),
    "life": (
        Field("title", "제목", required=True),
        Field("date", "날짜 (YYYY-MM-DD)", "date", True),
        Field("category", "카테고리", required=True),
        Field("summary", "목록 요약", "multiline"),
        Field("cover", "커버 이미지 경로"),
        Field("gallery", "갤러리 이미지 (한 줄에 하나)", "list"),
        Field("mediaLayout", "미디어 배치", "choice", choices=("gallery", "inline")),
    ),
}

PROFILE_SCHEMA: tuple[Field, ...] = (
    Field("homeQuote", "홈 상단 문구", "multiline"),
    Field("name", "이름", required=True),
    Field("englishName", "영문 이름", required=True),
    Field("role", "역할/소개", required=True),
    Field("university", "소속", required=True),
    Field("affiliations", "소속 표시 (한 줄에 하나)", "list"),
    Field("department", "학과"),
    Field("location", "위치"),
    Field("email", "이메일"),
    Field("phone", "전화번호"),
    Field("showPhone", "전화번호 표시", "boolean"),
    Field("image.src", "프로필 이미지 경로"),
    Field("image.alt", "프로필 이미지 대체 텍스트"),
    Field("resume.available", "이력서 버튼 표시", "boolean"),
    Field("resume.href", "이력서 파일 경로"),
    Field("education.school", "학교"),
    Field("education.major", "전공"),
    Field("education.degree", "학위/상태"),
    Field("education.period", "재학 기간"),
    Field("internship.company", "인턴십 회사"),
    Field("internship.role", "인턴십 직무"),
    Field("internship.period", "인턴십 기간"),
    Field("training", "교육/수료 (한 줄에 하나)", "list"),
    Field("awards", "수상/활동 (한 줄에 하나)", "list"),
    Field("certifications", "자격증 (이름 | 상태, 한 줄에 하나)", "list"),
    Field("languages", "어학 (이름 | 상태, 한 줄에 하나)", "list"),
    Field("focusAreas", "Focus Areas (한 줄에 하나)", "list"),
    Field("navigationCards", "하단 이동 카드 (제목 | 설명 | 링크, 한 줄에 하나)", "list"),
    Field("footerText", "푸터 문구"),
    Field("footerMark", "푸터 마크"),
)

EDITOR_SCHEMAS = {**SCHEMAS, "profile": PROFILE_SCHEMA}
PROFILE_DEFAULTS = {
    "homeQuote": "생각하는대로 살지 않으면 사는대로 생각하게 된다.",
    "footerText": "© 2025 se0ngm1n. 일부 권리 보유.",
    "footerMark": "071128",
}


class ContentError(ValueError):
    pass


def parse_scalar(value: str):
    value = value.strip()
    if value == "[]":
        return []
    if value.startswith('"') and value.endswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def parse_frontmatter(source: str) -> tuple[dict[str, object], str]:
    normalized = source.replace("\r\n", "\n")
    match = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)(.*)$", normalized, re.S)
    if not match:
        raise ContentError("파일 맨 앞의 YAML frontmatter(---)를 찾을 수 없습니다.")

    lines = match.group(1).splitlines()
    metadata: dict[str, object] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        key_match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$", line)
        if not key_match:
            raise ContentError(f"해석할 수 없는 frontmatter 줄입니다: {line}")
        key, raw_value = key_match.group(1), key_match.group(2) or ""
        if raw_value:
            metadata[key] = parse_scalar(raw_value)
            index += 1
            continue

        values: list[str] = []
        index += 1
        while index < len(lines):
            item = re.match(r"^[ \t]+-[ \t]*(.*)$", lines[index])
            if not item:
                break
            values.append(str(parse_scalar(item.group(1))))
            index += 1
        metadata[key] = values

    body = match.group(2)
    if body.startswith("\n"):
        body = body[1:]
    return metadata, body


def quote_yaml(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def serialize_frontmatter(section: str, metadata: dict[str, object], body: str) -> str:
    schema_keys = [field.key for field in SCHEMAS[section]]
    ordered_keys = schema_keys + [key for key in metadata if key not in schema_keys]
    lines = ["---"]
    for key in ordered_keys:
        if key not in metadata:
            continue
        value = metadata[key]
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                lines.extend(f"  - {quote_yaml(item)}" for item in value)
            else:
                lines.append(f"{key}: []")
        elif key == "order":
            lines.append(f"{key}: {int(str(value))}")
        elif key == "date" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {quote_yaml(value)}")
    clean_body = body.rstrip()
    return "\n".join(lines) + "\n---\n\n" + clean_body + ("\n" if clean_body else "")


def validate_metadata(section: str, raw_metadata: object) -> dict[str, object]:
    if section not in SCHEMAS or not isinstance(raw_metadata, dict):
        raise ContentError("잘못된 콘텐츠 데이터입니다.")
    metadata = dict(raw_metadata)
    errors: list[str] = []
    for field in SCHEMAS[section]:
        value = metadata.get(field.key, [] if field.kind == "list" else "")
        if field.kind == "list":
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                errors.append(f"{field.label}: 목록 형식이 아닙니다.")
                continue
            metadata[field.key] = [item.strip() for item in value if item.strip()]
        else:
            value = str(value).strip()
            metadata[field.key] = value
        if field.required and (value == "" or value == []):
            errors.append(f"{field.label}: 필수 항목입니다.")
        if field.kind == "integer" and value != "":
            try:
                metadata[field.key] = int(value)
            except (TypeError, ValueError):
                errors.append(f"{field.label}: 정수를 입력하세요.")
        if field.kind == "date" and value:
            try:
                date.fromisoformat(str(value))
            except ValueError:
                errors.append(f"{field.label}: YYYY-MM-DD 형식이어야 합니다.")
        if field.kind == "choice" and value and value not in field.choices:
            errors.append(f"{field.label}: 허용되지 않는 값입니다.")
    if errors:
        raise ContentError("\n".join(errors))
    return metadata


def quote_unquoted_js_keys(source: str) -> str:
    return re.sub(
        r"([{\[,]\s*)([A-Za-z_$][A-Za-z0-9_$]*)\s*:",
        r'\1"\2":',
        source,
    )


def replace_js_literals(source: str) -> str:
    replacements = {"true": "True", "false": "False", "null": "None"}
    output: list[str] = []
    index = 0
    quote = ""
    escaped = False
    while index < len(source):
        char = source[index]
        if quote:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            output.append(char)
            index += 1
            continue
        match = re.match(r"[A-Za-z_$][A-Za-z0-9_$]*", source[index:])
        if match:
            token = match.group(0)
            output.append(replacements.get(token, token))
            index += len(token)
            continue
        output.append(char)
        index += 1
    return "".join(output)


def extract_profile_literal(source: str) -> str:
    match = re.search(r"export\s+const\s+profile\s*=", source)
    if not match:
        raise ContentError("profile.ts에서 export const profile을 찾을 수 없습니다.")
    start = source.find("{", match.end())
    if start == -1:
        raise ContentError("profile.ts에서 profile 객체를 찾을 수 없습니다.")

    depth = 0
    quote = ""
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise ContentError("profile.ts의 profile 객체가 닫히지 않았습니다.")


def load_profile() -> dict[str, object]:
    literal = extract_profile_literal(PROFILE_PATH.read_text(encoding="utf-8"))
    python_literal = replace_js_literals(quote_unquoted_js_keys(literal))
    try:
        value = ast.literal_eval(python_literal)
    except (SyntaxError, ValueError) as error:
        raise ContentError("profile.ts의 profile 객체를 해석할 수 없습니다.") from error
    if not isinstance(value, dict):
        raise ContentError("profile.ts의 profile 값이 객체가 아닙니다.")
    return value


def write_profile(profile: dict[str, object]) -> None:
    body = json.dumps(profile, ensure_ascii=False, indent=2)
    PROFILE_PATH.write_text(
        f"export const profile = {body};\n\nexport type Profile = typeof profile;\n",
        encoding="utf-8",
    )


def get_nested(data: dict[str, object], key: str, default: object = "") -> object:
    current: object = data
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def flatten_named_status(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    lines = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        status = str(item.get("status", "")).strip()
        if name:
            lines.append(f"{name} | {status}" if status else name)
    return lines


def flatten_navigation_cards(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    lines = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        description = str(item.get("description", "")).strip()
        href = str(item.get("href", "")).strip()
        if title or description or href:
            lines.append(" | ".join((title, description, href)))
    return lines


def flatten_profile(profile: dict[str, object]) -> dict[str, object]:
    metadata: dict[str, object] = {}
    for field in PROFILE_SCHEMA:
        key = field.key
        if key in {"certifications", "languages"}:
            metadata[key] = flatten_named_status(profile.get(key))
        elif key == "navigationCards":
            metadata[key] = flatten_navigation_cards(profile.get(key))
        elif key in PROFILE_DEFAULTS:
            metadata[key] = str(profile.get(key, PROFILE_DEFAULTS[key]))
        elif "." in key:
            metadata[key] = get_nested(profile, key)
        else:
            metadata[key] = profile.get(key, [] if field.kind == "list" else "")
    return metadata


def metadata_text(metadata: dict[str, object], key: str) -> str:
    return str(metadata.get(key, "")).strip()


def metadata_bool(metadata: dict[str, object], key: str) -> bool:
    value = metadata.get(key, False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def metadata_lines(metadata: dict[str, object], key: str) -> list[str]:
    value = metadata.get(key, [])
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [line.strip() for line in str(value).splitlines() if line.strip()]


def parse_named_status_lines(lines: list[str]) -> list[dict[str, str]]:
    items = []
    for line in lines:
        name, _, status = line.partition("|")
        item = {"name": name.strip()}
        if status.strip():
            item["status"] = status.strip()
        if item["name"]:
            items.append(item)
    return items


def parse_navigation_card_lines(lines: list[str]) -> list[dict[str, str]]:
    cards = []
    errors = []
    for line in lines:
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 3 or not parts[0] or not parts[2]:
            errors.append(f"하단 이동 카드: '{line}' 형식은 제목 | 설명 | 링크여야 합니다.")
            continue
        cards.append({"title": parts[0], "description": parts[1], "href": parts[2]})
    if errors:
        raise ContentError("\n".join(errors))
    return cards


def validate_profile_metadata(raw_metadata: object) -> dict[str, object]:
    if not isinstance(raw_metadata, dict):
        raise ContentError("잘못된 프로필 데이터입니다.")
    metadata = dict(raw_metadata)
    errors = []
    for field in PROFILE_SCHEMA:
        if field.required and not metadata_text(metadata, field.key):
            errors.append(f"{field.label}: 필수 항목입니다.")
    if errors:
        raise ContentError("\n".join(errors))

    profile = load_profile()
    profile.update(
        {
            "homeQuote": metadata_text(metadata, "homeQuote"),
            "name": metadata_text(metadata, "name"),
            "englishName": metadata_text(metadata, "englishName"),
            "role": metadata_text(metadata, "role"),
            "university": metadata_text(metadata, "university"),
            "affiliations": metadata_lines(metadata, "affiliations")
            or [metadata_text(metadata, "university")],
            "department": metadata_text(metadata, "department"),
            "location": metadata_text(metadata, "location"),
            "email": metadata_text(metadata, "email"),
            "phone": metadata_text(metadata, "phone"),
            "showPhone": metadata_bool(metadata, "showPhone"),
            "image": {
                "src": metadata_text(metadata, "image.src"),
                "alt": metadata_text(metadata, "image.alt"),
            },
            "resume": {
                "available": metadata_bool(metadata, "resume.available"),
                "href": metadata_text(metadata, "resume.href"),
            },
            "education": {
                "school": metadata_text(metadata, "education.school"),
                "major": metadata_text(metadata, "education.major"),
                "degree": metadata_text(metadata, "education.degree"),
                "period": metadata_text(metadata, "education.period"),
            },
            "internship": {
                "company": metadata_text(metadata, "internship.company"),
                "role": metadata_text(metadata, "internship.role"),
                "period": metadata_text(metadata, "internship.period"),
            },
            "training": metadata_lines(metadata, "training"),
            "awards": metadata_lines(metadata, "awards"),
            "certifications": parse_named_status_lines(metadata_lines(metadata, "certifications")),
            "languages": parse_named_status_lines(metadata_lines(metadata, "languages")),
            "focusAreas": metadata_lines(metadata, "focusAreas"),
            "navigationCards": parse_navigation_card_lines(metadata_lines(metadata, "navigationCards")),
            "footerText": metadata_text(metadata, "footerText"),
            "footerMark": metadata_text(metadata, "footerMark"),
        }
    )
    return profile


def content_path(section: str, slug: str) -> Path:
    if section not in SCHEMAS:
        raise ContentError("존재하지 않는 콘텐츠 영역입니다.")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ContentError("slug는 영문 소문자, 숫자, 하이픈만 사용할 수 있습니다.")
    return CONTENT_ROOT / section / f"{slug}.md"


def detect_image_extension(data: bytes) -> str | None:
    """Return a safe web image extension based on file signatures."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in {
        b"avif",
        b"avis",
    }:
        return "avif"
    return None


def detect_media_type(data: bytes) -> tuple[str, str, str] | None:
    """Return (kind, extension, mime_type) from a trusted file signature."""
    image_extension = detect_image_extension(data)
    if image_extension:
        image_mimes = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "avif": "image/avif",
        }
        return "image", image_extension, image_mimes[image_extension]

    if len(data) >= 12 and data[4:8] == b"ftyp":
        brands = {data[index : index + 4] for index in range(8, min(len(data), 80), 4)}
        if b"qt  " in brands:
            return "video", "mov", "video/quicktime"
        video_brands = {
            b"isom",
            b"iso2",
            b"iso5",
            b"iso6",
            b"mp41",
            b"mp42",
            b"avc1",
            b"M4V ",
            b"MSNV",
            b"3gp4",
            b"3gp5",
        }
        if brands & video_brands:
            return "video", "mp4", "video/mp4"
    if data.startswith(b"\x1aE\xdf\xa3") and b"webm" in data[:65536].lower():
        return "video", "webm", "video/webm"
    return None


def safe_image_stem(filename: str) -> str:
    stem = Path(filename).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return stem[:80] or "image"


def next_image_path(
    section: str,
    slug: str,
    filename: str,
    extension: str,
    occupied: set[Path] | None = None,
) -> Path:
    folder = ROOT / "public" / MEDIA_DIRECTORIES[section] / slug
    stem = safe_image_stem(filename)
    candidate = folder / f"{stem}.{extension}"
    counter = 2
    while candidate.exists() or (occupied is not None and candidate in occupied):
        candidate = folder / f"{stem}-{counter}.{extension}"
        counter += 1
    return candidate


def run_command(
    args: list[str], timeout: int = 180
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


class EditorState:
    def __init__(self) -> None:
        self.saved_paths: set[Path] = set()
        self.reserved_paths: set[Path] = set()
        self.lock = threading.Lock()


HTML = r'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Portfolio Content Editor</title>
  <style>
    :root { --bg:#f3f1ec; --panel:#fff; --ink:#191918; --muted:#73716d; --line:#d9d5cc; --accent:#285943; --accent2:#e7efe9; --danger:#a43b32; }
    * { box-sizing:border-box; }
    body { margin:0; color:var(--ink); background:var(--bg); font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    button,input,textarea,select { font:inherit; }
    button { border:1px solid var(--line); background:#fff; border-radius:8px; padding:9px 13px; cursor:pointer; color:var(--ink); }
    button:hover { border-color:#aaa69d; }
    button:disabled { opacity:.5; cursor:not-allowed; }
    button.primary { background:var(--accent); border-color:var(--accent); color:white; font-weight:700; }
    .app { display:grid; grid-template-columns:300px minmax(0,1fr); min-height:100vh; }
    aside { display:flex; flex-direction:column; border-right:1px solid var(--line); padding:22px 16px; background:#ece9e2; min-height:100vh; }
    h1 { font:700 22px/1.2 Georgia,serif; margin:0 0 17px; }
    .tabs { display:grid; grid-template-columns:repeat(4,1fr); gap:5px; margin-bottom:10px; }
    .tab { padding:8px 4px; background:transparent; }
    .tab.active { background:var(--ink); color:#fff; border-color:var(--ink); }
    #search { width:100%; border:1px solid var(--line); border-radius:8px; padding:10px; background:white; margin-bottom:10px; }
    #documents { list-style:none; padding:0; margin:0; overflow:auto; flex:1; min-height:180px; }
    #documents li { padding:10px; border-radius:7px; cursor:pointer; margin-bottom:3px; }
    #documents li:hover { background:rgba(255,255,255,.55); }
    #documents li.active { background:white; box-shadow:0 1px 4px #00000010; }
    #documents .slug { display:block; color:var(--muted); font-size:11px; margin-top:2px; }
    .saved-dot { color:var(--accent); font-weight:800; }
    .side-actions { display:grid; grid-template-columns:1fr 1fr; gap:7px; margin-top:10px; }
    main { min-width:0; padding:22px 28px 30px; }
    header { display:flex; align-items:flex-start; justify-content:space-between; gap:20px; margin-bottom:18px; }
    h2 { margin:0; font:700 25px/1.25 Georgia,serif; }
    #filePath { color:var(--muted); margin-top:4px; font-size:12px; }
    .header-actions { display:flex; gap:7px; white-space:nowrap; }
    .editor-grid { display:grid; grid-template-columns:minmax(300px, 42%) minmax(400px, 1fr); gap:16px; min-height:590px; }
    .editor-grid.profile-mode { grid-template-columns:minmax(0, 760px); }
    .editor-grid.profile-mode .body-card { display:none; }
    .card { background:var(--panel); border:1px solid var(--line); border-radius:12px; overflow:hidden; box-shadow:0 2px 12px #392e1e0b; }
    .card-title { padding:13px 16px; border-bottom:1px solid var(--line); font-weight:700; }
    #metadataForm { padding:14px 16px; overflow:auto; height:calc(100% - 48px); }
    .field { margin-bottom:13px; }
    .field label { display:block; font-weight:650; margin-bottom:5px; }
    .required { color:var(--danger); }
    .field input,.field textarea,.field select { width:100%; border:1px solid var(--line); border-radius:7px; padding:9px 10px; color:var(--ink); background:#fff; }
    .field input[type="checkbox"] { width:auto; min-width:18px; min-height:18px; accent-color:var(--accent); }
    .field textarea { min-height:72px; resize:vertical; }
    .body-card { display:flex; flex-direction:column; position:relative; }
    .body-heading { display:flex; align-items:center; justify-content:space-between; gap:10px; }
    .body-tools { display:flex; align-items:center; gap:8px; }
    .body-tools small { color:var(--muted); font-weight:400; }
    .body-card.dragging { outline:3px solid var(--accent); outline-offset:-3px; }
    .body-card.dragging::after { content:'여기에 놓으면 현재 커서 위치에 사진·동영상이 추가됩니다'; position:absolute; inset:48px 0 0; display:grid; place-items:center; padding:30px; z-index:3; color:var(--accent); background:#e7efe9eF; font-size:16px; font-weight:750; text-align:center; pointer-events:none; }
    #body { border:0; outline:0; resize:none; width:100%; flex:1; min-height:540px; padding:16px; font:13px/1.65 Menlo,Monaco,monospace; color:#222; }
    .publish { display:grid; grid-template-columns:auto minmax(180px,1fr) auto; align-items:center; gap:9px; margin-top:15px; }
    #commitMessage { border:1px solid var(--line); border-radius:8px; padding:10px; width:100%; }
    .status-row { display:flex; align-items:center; justify-content:space-between; margin-top:10px; min-height:24px; }
    #status { color:var(--muted); }
    #status.ok { color:var(--accent); }
    #status.error { color:var(--danger); }
    #log { display:none; white-space:pre-wrap; background:#191918; color:#e9e7e1; border-radius:9px; padding:12px; max-height:190px; overflow:auto; font:11px/1.5 Menlo,monospace; margin:9px 0 0; }
    #log.visible { display:block; }
    .empty { color:var(--muted); padding:30px 5px; text-align:center; }
    @media (max-width:900px) { .app{grid-template-columns:230px minmax(0,1fr)} main{padding:18px}.editor-grid{grid-template-columns:1fr}.body-card{min-height:600px} }
  </style>
</head>
<body>
<div class="app">
  <aside>
    <h1>Content Editor</h1>
    <div class="tabs" id="tabs"></div>
    <input id="search" type="search" placeholder="제목 또는 slug 검색">
    <ul id="documents"></ul>
    <div class="side-actions"><button id="newButton">새 Projects 글</button><button id="refreshButton">새로고침</button></div>
  </aside>
  <main>
    <header><div><h2 id="title">글을 선택하세요</h2><div id="filePath"></div></div><div class="header-actions"><button id="buildButton">빌드 검사</button><button id="saveButton">저장</button></div></header>
    <div class="editor-grid">
      <section class="card"><div class="card-title">목록 정보</div><div id="metadataForm"></div></section>
      <section class="card body-card" id="bodyCard">
        <div class="card-title body-heading"><span>본문 (Markdown)</span><div class="body-tools"><small>사진·동영상 드래그 가능</small><button id="mediaButton" type="button">미디어 추가</button><input id="mediaInput" type="file" accept="image/jpeg,image/png,image/webp,image/gif,image/avif,video/mp4,video/webm,video/quicktime,.m4v" multiple hidden></div></div>
        <textarea id="body" spellcheck="false" placeholder="Markdown 본문"></textarea>
      </section>
    </div>
    <div class="publish"><label for="commitMessage">커밋 메시지</label><input id="commitMessage"><button class="primary" id="publishButton">저장한 글 Commit &amp; Push</button></div>
    <div class="status-row"><span id="status">준비됨</span><button id="logToggle">로그 보기</button></div><pre id="log"></pre>
  </main>
</div>
<script>
const TOKEN = __TOKEN__;
const SCHEMAS = __SCHEMAS__;
const labels = {projects:'Projects', study:'Study', life:'Life', profile:'Home'};
let section = 'projects', documents = [], current = null, originalSnapshot = '', busy = false;
let bodyCursor = 0, dragDepth = 0;
const $ = id => document.getElementById(id);

function setStatus(text, type='') { $('status').textContent=text; $('status').className=type; }
function setBusy(value, text='') { busy=value; document.querySelectorAll('button').forEach(b=>b.disabled=value); if(text)setStatus(text); }
function appendLog(text) { $('log').textContent += ( $('log').textContent?'\n':'') + text; $('log').scrollTop=$('log').scrollHeight; }
async function api(path, options={}) {
  const response = await fetch(path, {headers:{'Content-Type':'application/json','X-Editor-Token':TOKEN,...options.headers}, ...options});
  const data = await response.json().catch(()=>({error:`HTTP ${response.status}`}));
  if(!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}
function valueFromField(field) {
  const input = document.querySelector(`[data-key="${field.key}"]`);
  if(!input) return '';
  if(field.kind==='boolean') return input.checked;
  return field.kind==='list' ? input.value.split('\n').map(v=>v.trim()).filter(Boolean) : input.value.trim();
}
function collectDocument() {
  if(!current) return null;
  const metadata = {...current.extras};
  for(const field of SCHEMAS[section]) metadata[field.key]=valueFromField(field);
  return {section, slug:current.slug, metadata, body:$('body').value};
}
function snapshot() { return JSON.stringify(collectDocument()); }
function isDirty() { return !!current && snapshot() !== originalSnapshot; }
function markDirty() { if(isDirty()) setStatus('수정됨 · 저장 필요'); }
function confirmNavigation() { return !isDirty() || confirm('저장하지 않은 변경 사항이 있습니다. 변경을 버리고 이동할까요?'); }

function renderTabs() {
  $('tabs').innerHTML='';
  for(const key of Object.keys(labels)) {
    const button=document.createElement('button'); button.className='tab'+(key===section?' active':''); button.textContent=labels[key];
    button.onclick=async()=>{ if(key===section||!confirmNavigation())return; section=key; current=null; renderTabs(); clearEditor(); await loadDocuments(true); };
    $('tabs').appendChild(button);
  }
  $('newButton').textContent=`새 ${labels[section]} 글`;
  $('newButton').hidden=section==='profile';
}
function renderDocuments() {
  const q=$('search').value.trim().toLowerCase(); $('documents').innerHTML='';
  const shown=documents.filter(d=>!q||d.title.toLowerCase().includes(q)||d.slug.includes(q));
  if(!shown.length) {$('documents').innerHTML='<li class="empty">글이 없습니다.</li>';return;}
  for(const doc of shown) {
    const li=document.createElement('li'); li.className=current?.slug===doc.slug?'active':'';
    li.innerHTML=`<span>${escapeHtml(doc.title)} ${doc.saved?'<span class="saved-dot">●</span>':''}</span><span class="slug">${escapeHtml(doc.slug)}</span>`;
    li.onclick=()=>selectDocument(doc.slug); $('documents').appendChild(li);
  }
}
function escapeHtml(value) { const span=document.createElement('span'); span.textContent=value; return span.innerHTML; }
async function loadDocuments(selectFirst=false) {
  try { const data=await api(`/api/documents?section=${section}`); documents=data.documents; renderDocuments(); if(selectFirst&&documents.length)await selectDocument(documents[0].slug,true); }
  catch(error){setStatus(error.message,'error');}
}
async function selectDocument(slug, force=false) {
  if(!force && current?.slug===slug)return;
  if(!force && !confirmNavigation()){renderDocuments();return;}
  try {
    const data=await api(`/api/document?section=${section}&slug=${encodeURIComponent(slug)}`); current=data; renderForm();
    $('body').value=data.body||''; $('title').textContent=data.metadata.title||data.title||slug; $('filePath').textContent=data.path||`src/content/${section}/${slug}.md`;
    document.querySelector('.editor-grid').classList.toggle('profile-mode', section==='profile');
    bodyCursor=0; $('commitMessage').value=section==='profile'?'content: update home profile':`content: update ${slug}`; originalSnapshot=snapshot(); setStatus('불러옴'); renderDocuments();
  } catch(error){setStatus(error.message,'error');}
}
function renderForm() {
  const form=$('metadataForm'); form.innerHTML='';
  if(!current){form.innerHTML='<div class="empty">왼쪽에서 글을 선택하세요.</div>';return;}
  for(const field of SCHEMAS[section]) {
    const wrap=document.createElement('div'); wrap.className='field';
    const label=document.createElement('label'); label.textContent=field.label; if(field.required)label.innerHTML+= ' <span class="required">*</span>'; wrap.appendChild(label);
    let input;
    if(field.kind==='multiline'||field.kind==='list') input=document.createElement('textarea');
    else if(field.kind==='choice') { input=document.createElement('select'); for(const choice of field.choices){const option=document.createElement('option');option.value=choice;option.textContent=choice;input.appendChild(option);} }
    else { input=document.createElement('input'); input.type=field.kind==='date'?'date':field.kind==='integer'?'number':field.kind==='boolean'?'checkbox':'text'; }
    const value=current.metadata[field.key]??(field.kind==='list'?[]:'');
    if(field.kind==='boolean') input.checked=Boolean(value);
    else input.value=Array.isArray(value)?value.join('\n'):value;
    input.dataset.key=field.key; input.addEventListener(field.kind==='boolean'?'change':'input',markDirty); wrap.appendChild(input); form.appendChild(wrap);
  }
}
function clearEditor(){ $('title').textContent='글을 선택하세요';$('filePath').textContent='';$('metadataForm').innerHTML='<div class="empty">왼쪽에서 글을 선택하세요.</div>';$('body').value='';document.querySelector('.editor-grid').classList.toggle('profile-mode', section==='profile');renderDocuments(); }
async function saveCurrent(showMessage=true) {
  if(!current){setStatus('먼저 글을 선택하세요.','error');return false;}
  try { const data=await api('/api/save',{method:'POST',body:JSON.stringify(collectDocument())}); current=data.document; originalSnapshot=snapshot(); setStatus(`저장됨 · push 대기 ${data.savedCount}개`,'ok'); if(showMessage)appendLog(`저장: ${data.document.path||`src/content/${section}/${current.slug}.md`}`); await loadDocuments(false); return true; }
  catch(error){setStatus(error.message,'error');alert(`저장 실패\n\n${error.message}`);return false;}
}
async function createDocument() {
  if(!confirmNavigation())return;
  const title=prompt(`새 ${labels[section]} 글의 제목을 입력하세요.`); if(title===null)return; if(!title.trim()){alert('제목을 입력하세요.');return;}
  const suggested=title.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'') || `new-${section}-${new Date().toISOString().slice(0,10)}`;
  const slug=prompt('URL에 사용할 영문 slug를 입력하세요.\n영문 소문자, 숫자, 하이픈만 사용합니다.',suggested); if(slug===null)return;
  try { const data=await api('/api/new',{method:'POST',body:JSON.stringify({section,title:title.trim(),slug:slug.trim().toLowerCase()})}); await loadDocuments(false); await selectDocument(data.slug,true); setStatus('새 글 생성됨 · 내용을 수정한 뒤 저장하세요','ok'); }
  catch(error){setStatus(error.message,'error');alert(error.message);}
}
function rememberBodyCursor() { bodyCursor=$('body').selectionStart ?? bodyCursor; }
function insertAtBodyCursor(text) {
  const body=$('body'), start=Math.min(bodyCursor,body.value.length), before=body.value.slice(0,start), after=body.value.slice(start);
  const prefix=before && !before.endsWith('\n\n') ? (before.endsWith('\n')?'\n':'\n\n') : '';
  const suffix=after && !after.startsWith('\n\n') ? (after.startsWith('\n')?'\n':'\n\n') : '';
  const inserted=prefix+text+suffix; body.value=before+inserted+after; bodyCursor=start+prefix.length+text.length;
  body.focus(); body.setSelectionRange(bodyCursor,bodyCursor); markDirty();
}
async function uploadMedia(fileList) {
  if(busy)return;
  if(!current){alert('먼저 글을 선택하거나 새 글을 만드세요.');return;}
  const files=Array.from(fileList).filter(file=>/^(image|video)\//.test(file.type)||/\.(png|jpe?g|gif|webp|avif|mp4|webm|mov|m4v)$/i.test(file.name));
  if(!files.length){alert('지원되는 사진 또는 동영상 파일을 선택하세요.');return;}
  const oversized=files.find(file=>file.size>(file.type.startsWith('video/')||/\.(mp4|webm|mov|m4v)$/i.test(file.name)?90:25)*1024*1024);
  if(oversized){alert(`${oversized.name}: 사진은 25MB, 동영상은 90MB 이하여야 합니다.`);return;}
  rememberBodyCursor(); setBusy(true,`미디어 업로드 중 · 0/${files.length}`);
  const snippets=[], uploaded=[];
  try {
    for(let index=0;index<files.length;index++) {
      const file=files[index]; setStatus(`미디어 업로드 중 · ${index+1}/${files.length} · ${file.name}`);
      const query=new URLSearchParams({section,slug:current.slug,filename:file.name});
      const response=await fetch(`/api/upload?${query}`,{method:'POST',headers:{'Content-Type':file.type||'application/octet-stream','X-Editor-Token':TOKEN},body:file});
      const data=await response.json().catch(()=>({error:`HTTP ${response.status}`}));
      if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);
      if(data.mediaType==='video') snippets.push(`<video controls preload="metadata" playsinline>\n  <source src="${data.url}" type="${data.mimeType}" />\n</video>`);
      else {
        const fallback=file.name.replace(/\.[^.]+$/,'').replace(/[\[\]]/g,' ').trim();
        const alt=(current.metadata.title||fallback||'이미지').replace(/[\[\]]/g,' ');
        snippets.push(`![${alt}](${data.url})`);
      }
      uploaded.push(data.path);
    }
    insertAtBodyCursor(snippets.join('\n\n'));
    appendLog(`미디어 업로드:\n${uploaded.map(path=>'- '+path).join('\n')}`);
    setStatus(`미디어 ${files.length}개 추가됨 · 본문 저장 필요`,'ok');
  } catch(error) {
    if(snippets.length) {
      insertAtBodyCursor(snippets.join('\n\n'));
      appendLog(`미디어 일부 업로드:\n${uploaded.map(path=>'- '+path).join('\n')}`);
    }
    setStatus(snippets.length?`미디어 ${snippets.length}개 추가 후 업로드 중단`:'미디어 업로드 실패','error'); alert(`미디어 업로드 실패\n\n${error.message}`);
  } finally { setBusy(false); $('mediaInput').value=''; }
}
async function buildSite() {
  if(busy)return; if(isDirty() && !(await saveCurrent(false)))return; setBusy(true,'사이트 빌드 검사 중…');appendLog('$ npm run build');
  try { const data=await api('/api/build',{method:'POST',body:'{}'});appendLog(data.output);setStatus('빌드 성공','ok'); }
  catch(error){appendLog(error.message);setStatus('빌드 실패','error');$('log').classList.add('visible');alert('빌드에 실패했습니다. 로그를 확인하세요.');}
  finally{setBusy(false);}
}
async function publish() {
  if(busy)return; if(current && !(await saveCurrent(false)))return; const message=$('commitMessage').value.trim(); if(!message){alert('커밋 메시지를 입력하세요.');return;}
  const allSaved=await api('/api/saved');
  if(!allSaved.paths.length){alert('저장하거나 변경한 글이 없습니다.');return;}
  if(!confirm(`다음 파일만 커밋하고 push합니다.\n\n${allSaved.paths.map(p=>'• '+p).join('\n')}\n\n커밋: ${message}`))return;
  setBusy(true,'Commit & Push 진행 중…');
  try { const data=await api('/api/publish',{method:'POST',body:JSON.stringify({message})});appendLog(data.output);setStatus('Commit & Push 완료','ok');await loadDocuments(false);alert('커밋하고 원격 저장소에 push했습니다.'); }
  catch(error){appendLog(error.message);$('log').classList.add('visible');setStatus('Commit & Push 실패','error');alert(`Commit & Push 실패\n\n${error.message}`);}
  finally{setBusy(false);}
}
$('search').oninput=renderDocuments; $('body').addEventListener('input',()=>{rememberBodyCursor();markDirty();}); $('body').addEventListener('click',rememberBodyCursor); $('body').addEventListener('keyup',rememberBodyCursor); $('body').addEventListener('select',rememberBodyCursor);
$('saveButton').onclick=()=>saveCurrent(); $('refreshButton').onclick=()=>{if(confirmNavigation())loadDocuments(false)};
$('newButton').onclick=createDocument;$('buildButton').onclick=buildSite;$('publishButton').onclick=publish;$('logToggle').onclick=()=>{$('log').classList.toggle('visible');};
$('mediaButton').onclick=()=>{rememberBodyCursor();$('mediaInput').click();}; $('mediaInput').onchange=event=>uploadMedia(event.target.files);
$('body').addEventListener('paste',event=>{const files=Array.from(event.clipboardData?.files||[]).filter(file=>/^(image|video)\//.test(file.type));if(files.length){event.preventDefault();uploadMedia(files);}});
$('bodyCard').addEventListener('dragenter',event=>{if(Array.from(event.dataTransfer?.types||[]).includes('Files')){event.preventDefault();dragDepth++;$('bodyCard').classList.add('dragging');}});
$('bodyCard').addEventListener('dragover',event=>{if(Array.from(event.dataTransfer?.types||[]).includes('Files')){event.preventDefault();event.dataTransfer.dropEffect='copy';}});
$('bodyCard').addEventListener('dragleave',()=>{dragDepth=Math.max(0,dragDepth-1);if(!dragDepth)$('bodyCard').classList.remove('dragging');});
$('bodyCard').addEventListener('drop',event=>{event.preventDefault();dragDepth=0;$('bodyCard').classList.remove('dragging');uploadMedia(event.dataTransfer.files);});
window.addEventListener('beforeunload',event=>{if(isDirty()){event.preventDefault();event.returnValue='';}});
renderTabs();clearEditor();loadDocuments(true);
</script>
</body>
</html>'''


class EditorHandler(BaseHTTPRequestHandler):
    server: "EditorServer"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, error: Exception, status: int = HTTPStatus.BAD_REQUEST) -> None:
        self.send_json({"error": str(error)}, status)

    def check_mutation_auth(self) -> None:
        if self.headers.get("X-Editor-Token") != self.server.token:
            raise PermissionError("편집기 인증 토큰이 올바르지 않습니다.")
        origin = self.headers.get("Origin")
        if origin and origin not in self.server.allowed_origins:
            raise PermissionError("허용되지 않은 요청 출처입니다.")

    def content_length(self, maximum: int) -> int:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ContentError("잘못된 요청입니다.") from error
        if length <= 0:
            raise ContentError("요청 내용이 비어 있습니다.")
        if length > maximum:
            raise ContentError("요청 크기가 너무 큽니다.")
        return length

    def read_json(self) -> dict[str, object]:
        self.check_mutation_auth()
        length = self.content_length(10_000_000)
        try:
            value = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as error:
            raise ContentError("JSON 요청을 해석할 수 없습니다.") from error
        if not isinstance(value, dict):
            raise ContentError("JSON 객체가 필요합니다.")
        return value

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                schemas = {
                    key: [field.as_dict() for field in fields]
                    for key, fields in EDITOR_SCHEMAS.items()
                }
                html = HTML.replace("__TOKEN__", json.dumps(self.server.token)).replace(
                    "__SCHEMAS__", json.dumps(schemas, ensure_ascii=False)
                )
                body = html.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            elif parsed.path == "/api/documents":
                section = self.query_value(parsed, "section")
                if section == "profile":
                    profile = load_profile()
                    with self.server.state.lock:
                        saved = PROFILE_PATH in self.server.state.saved_paths
                    title = f"홈 배경화면 · {profile.get('name', 'Profile')}"
                    self.send_json(
                        {
                            "documents": [
                                {"slug": PROFILE_SLUG, "title": title, "saved": saved}
                            ]
                        }
                    )
                    return
                if section not in SCHEMAS:
                    raise ContentError("잘못된 콘텐츠 영역입니다.")
                items = []
                for path in sorted((CONTENT_ROOT / section).glob("*.md")):
                    metadata, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
                    with self.server.state.lock:
                        saved = path in self.server.state.saved_paths
                    items.append({"slug": path.stem, "title": str(metadata.get("title", path.stem)), "saved": saved})
                self.send_json({"documents": items})
            elif parsed.path == "/api/document":
                section = self.query_value(parsed, "section")
                slug = self.query_value(parsed, "slug")
                if section == "profile":
                    if slug != PROFILE_SLUG:
                        raise ContentError("프로필 문서를 찾을 수 없습니다.")
                    profile = load_profile()
                    self.send_json(
                        {
                            "section": section,
                            "slug": slug,
                            "title": "홈 배경화면",
                            "path": PROFILE_PATH.relative_to(ROOT).as_posix(),
                            "metadata": flatten_profile(profile),
                            "extras": {},
                            "body": "",
                        }
                    )
                    return
                path = content_path(section, slug)
                if not path.exists():
                    raise ContentError("글을 찾을 수 없습니다.")
                metadata, body = parse_frontmatter(path.read_text(encoding="utf-8"))
                known = {field.key for field in SCHEMAS[section]}
                extras = {key: value for key, value in metadata.items() if key not in known}
                self.send_json({"section": section, "slug": slug, "path": path.relative_to(ROOT).as_posix(), "metadata": metadata, "extras": extras, "body": body})
            elif parsed.path == "/api/saved":
                with self.server.state.lock:
                    paths = sorted(str(path.relative_to(ROOT)) for path in self.server.state.saved_paths)
                self.send_json({"paths": paths})
            else:
                self.send_error_json(ContentError("Not found"), HTTPStatus.NOT_FOUND)
        except PermissionError as error:
            self.send_error_json(error, HTTPStatus.FORBIDDEN)
        except (ContentError, OSError) as error:
            self.send_error_json(error)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/upload":
                self.handle_upload(parsed)
                return
            payload = self.read_json()
            if parsed.path == "/api/save":
                self.handle_save(payload)
            elif parsed.path == "/api/new":
                self.handle_new(payload)
            elif parsed.path == "/api/build":
                result = run_command(["npm", "run", "build"])
                output = (result.stdout + result.stderr).strip()
                if result.returncode:
                    self.send_json({"error": output or "빌드 실패"}, HTTPStatus.INTERNAL_SERVER_ERROR)
                else:
                    self.send_json({"output": output})
            elif parsed.path == "/api/publish":
                self.handle_publish(payload)
            else:
                self.send_error_json(ContentError("Not found"), HTTPStatus.NOT_FOUND)
        except PermissionError as error:
            self.send_error_json(error, HTTPStatus.FORBIDDEN)
        except subprocess.TimeoutExpired:
            self.send_error_json(
                ContentError("작업이 3분 안에 끝나지 않아 중단했습니다."),
                HTTPStatus.REQUEST_TIMEOUT,
            )
        except (ContentError, OSError, ValueError) as error:
            self.send_error_json(error)

    def handle_save(self, payload: dict[str, object]) -> None:
        section, slug = str(payload.get("section", "")), str(payload.get("slug", ""))
        if section == "profile":
            self.handle_profile_save(slug, payload)
            return
        path = content_path(section, slug)
        if not path.exists():
            raise ContentError("저장할 글을 찾을 수 없습니다.")
        metadata = validate_metadata(section, payload.get("metadata"))
        body = str(payload.get("body", ""))
        path.write_text(serialize_frontmatter(section, metadata, body), encoding="utf-8")
        with self.server.state.lock:
            self.server.state.saved_paths.add(path)
            saved_count = len(self.server.state.saved_paths)
        known = {field.key for field in SCHEMAS[section]}
        extras = {key: value for key, value in metadata.items() if key not in known}
        document = {"section": section, "slug": slug, "path": path.relative_to(ROOT).as_posix(), "metadata": metadata, "extras": extras, "body": body.rstrip() + ("\n" if body.rstrip() else "")}
        self.send_json({"document": document, "savedCount": saved_count})

    def handle_profile_save(self, slug: str, payload: dict[str, object]) -> None:
        if slug != PROFILE_SLUG:
            raise ContentError("저장할 프로필 문서를 찾을 수 없습니다.")
        profile = validate_profile_metadata(payload.get("metadata"))
        write_profile(profile)
        with self.server.state.lock:
            self.server.state.saved_paths.add(PROFILE_PATH)
            saved_count = len(self.server.state.saved_paths)
        document = {
            "section": "profile",
            "slug": PROFILE_SLUG,
            "title": "홈 배경화면",
            "path": PROFILE_PATH.relative_to(ROOT).as_posix(),
            "metadata": flatten_profile(profile),
            "extras": {},
            "body": "",
        }
        self.send_json({"document": document, "savedCount": saved_count})

    def handle_new(self, payload: dict[str, object]) -> None:
        section, slug = str(payload.get("section", "")), str(payload.get("slug", ""))
        if section not in SCHEMAS:
            raise ContentError("새 글은 Projects, Study, Life 탭에서만 만들 수 있습니다.")
        title = str(payload.get("title", "")).strip()
        if not title:
            raise ContentError("글 제목을 입력하세요.")
        path = content_path(section, slug)
        if path.exists():
            raise ContentError("같은 slug의 글이 이미 있습니다.")
        today = date.today().isoformat()
        templates: dict[str, dict[str, object]] = {
            "projects": {"title": title, "subtitle": "", "period": f"{date.today().year}.01 - Present", "category": "Project", "summary": "프로젝트 요약", "technologies": [], "outcomes": [], "order": 99},
            "study": {"title": title, "date": today, "category": "Study", "summary": "글 요약", "tags": [], "thumbnail": ""},
            "life": {"title": title, "date": today, "category": "Life", "summary": "글 요약", "cover": "", "gallery": [], "mediaLayout": "gallery"},
        }
        path.write_text(serialize_frontmatter(section, templates[section], "# 새 글\n\n본문을 작성하세요."), encoding="utf-8")
        with self.server.state.lock:
            self.server.state.saved_paths.add(path)
        self.send_json({"slug": slug}, HTTPStatus.CREATED)

    def handle_upload(self, parsed) -> None:
        section = self.query_value(parsed, "section")
        slug = self.query_value(parsed, "slug")
        filename = self.query_value(parsed, "filename")
        article_path = content_path(section, slug)
        if not article_path.exists():
            raise ContentError("미디어를 추가할 글을 찾을 수 없습니다.")

        self.check_mutation_auth()
        length = self.content_length(MAX_VIDEO_BYTES)
        header_size = min(length, 65536)
        header = self.rfile.read(header_size)
        if len(header) != header_size:
            raise ContentError("미디어 업로드가 완료되지 않았습니다.")
        media = detect_media_type(header)
        if not media:
            self.close_connection = True
            raise ContentError(
                "PNG, JPEG, GIF, WebP, AVIF, MP4, WebM, MOV 파일만 업로드할 수 있습니다."
            )
        media_kind, extension, mime_type = media
        maximum = MAX_IMAGE_BYTES if media_kind == "image" else MAX_VIDEO_BYTES
        if length > maximum:
            self.close_connection = True
            limit_mb = maximum // (1024 * 1024)
            kind_label = "사진" if media_kind == "image" else "동영상"
            raise ContentError(f"{kind_label} 파일은 {limit_mb}MB 이하여야 합니다.")

        with self.server.state.lock:
            path = next_image_path(
                section,
                slug,
                filename,
                extension,
                self.server.state.reserved_paths,
            )
            self.server.state.reserved_paths.add(path)
        temporary = path.with_name(f".{path.name}.{secrets.token_hex(6)}.uploading")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("wb") as output:
                output.write(header)
                remaining = length - len(header)
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ContentError("미디어 업로드가 완료되지 않았습니다.")
                    output.write(chunk)
                    remaining -= len(chunk)
            temporary.replace(path)
            with self.server.state.lock:
                self.server.state.saved_paths.add(path)
                self.server.state.reserved_paths.discard(path)
        except Exception:
            temporary.unlink(missing_ok=True)
            with self.server.state.lock:
                self.server.state.reserved_paths.discard(path)
            raise

        relative = path.relative_to(ROOT)
        public_url = "/" + path.relative_to(ROOT / "public").as_posix()
        self.send_json(
            {
                "url": public_url,
                "path": relative.as_posix(),
                "mediaType": media_kind,
                "mimeType": mime_type,
            },
            HTTPStatus.CREATED,
        )

    def handle_publish(self, payload: dict[str, object]) -> None:
        message = str(payload.get("message", "")).strip()
        if not message or "\n" in message:
            raise ContentError("한 줄 커밋 메시지를 입력하세요.")
        with self.server.state.lock:
            paths = sorted(self.server.state.saved_paths)
        if not paths:
            raise ContentError("저장하거나 변경한 글이 없습니다.")
        relative = [str(path.relative_to(ROOT)) for path in paths]
        logs = ["커밋 대상:", *[f"- {path}" for path in relative]]

        add_result = run_command(["git", "add", "--", *relative])
        logs.extend(["$ git add -- <대상 파일>", (add_result.stdout + add_result.stderr).strip()])
        if add_result.returncode:
            self.send_json(
                {"error": f"git add 단계 실패\n\n{'\n'.join(logs)}"},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        staged_result = run_command(
            ["git", "diff", "--cached", "--name-only", "--", *relative]
        )
        staged_paths = [line for line in staged_result.stdout.splitlines() if line.strip()]
        logs.extend(["$ git diff --cached --name-only -- <대상 파일>", *staged_paths])
        if staged_result.returncode or not staged_paths:
            with self.server.state.lock:
                self.server.state.saved_paths.difference_update(paths)
            self.send_json(
                {
                    "error": "선택한 콘텐츠 파일에 실제로 커밋할 변경 사항이 없습니다.\n\n"
                    + "\n".join(logs)
                },
                HTTPStatus.CONFLICT,
            )
            return

        steps = [
            ["git", "commit", "-m", message, "--", *relative],
            ["git", "push"],
        ]
        for command in steps:
            result = run_command(command)
            logs.append("$ " + " ".join(command[:2]))
            logs.append((result.stdout + result.stderr).strip())
            if result.returncode:
                detail = "\n".join(logs)
                if command[1] == "push":
                    detail += "\n\n커밋은 로컬에 완료되었습니다. 네트워크를 확인한 뒤 터미널에서 git push를 실행하세요."
                    with self.server.state.lock:
                        self.server.state.saved_paths.difference_update(paths)
                self.send_json({"error": f"{' '.join(command[:2])} 단계 실패\n\n{detail}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
                return
        with self.server.state.lock:
            self.server.state.saved_paths.difference_update(paths)
        self.send_json({"output": "\n".join(logs)})

    @staticmethod
    def query_value(parsed, key: str) -> str:
        values = parse_qs(parsed.query).get(key)
        if not values:
            raise ContentError(f"필수 값이 없습니다: {key}")
        return values[0]


class EditorServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int]) -> None:
        super().__init__(address, EditorHandler)
        self.token = secrets.token_urlsafe(24)
        self.state = EditorState()
        port = self.server_address[1]
        self.allowed_origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}


def check_content() -> int:
    failures = 0
    count = 0
    for section in SCHEMAS:
        for path in sorted((CONTENT_ROOT / section).glob("*.md")):
            count += 1
            try:
                metadata, body = parse_frontmatter(path.read_text(encoding="utf-8"))
                validate_metadata(section, metadata)
                serialize_frontmatter(section, metadata, body)
            except (OSError, ContentError, ValueError) as error:
                failures += 1
                print(f"FAIL {path.relative_to(ROOT)}: {error}")
    count += 1
    try:
        profile = load_profile()
        validate_profile_metadata(flatten_profile(profile))
    except (OSError, ContentError, ValueError) as error:
        failures += 1
        print(f"FAIL {PROFILE_PATH.relative_to(ROOT)}: {error}")
    if failures:
        print(f"{failures}/{count} files failed")
        return 1
    print(f"OK: {count} content files")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate content without starting the editor")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if args.check:
        return check_content()

    try:
        server = EditorServer((args.host, args.port))
    except OSError:
        if args.port != 8765:
            raise
        server = EditorServer((args.host, 0))
    url = f"http://{args.host}:{server.server_address[1]}"
    print(f"Portfolio Content Editor: {url}")
    print("종료: Ctrl+C")
    if not args.no_browser:
        threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n편집기를 종료합니다.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
