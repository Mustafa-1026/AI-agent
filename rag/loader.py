"""
loader.py
=========

Data loading and validation module for the AI-powered Faculty
Intelligence & Research Discovery System.

Single Responsibility
----------------------
This module is responsible ONLY for:
    - Discovering faculty JSON files on disk
    - Parsing and validating their structure
    - Returning clean Python data structures to callers (e.g. the RAG
      pipeline, agents, etc.)

This module explicitly does NOT:
    - Generate embeddings
    - Connect to ChromaDB
    - Perform retrieval or semantic search
    - Call any LLM or external API (e.g. Tavily)
    - Generate emails
    - Contain any agent / routing logic

Any of the above concerns belong in other modules (rag/embedder.py,
rag/chroma_db.py, rag/retriever.py, tools/*, agents/*).

Author: AI Agent Hackathon Team
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Top-level sections every faculty profile is expected to contain.
REQUIRED_SECTIONS: List[str] = [
    "Faculty",
    "Identity",
    "AcademicProfile",
    "ResearchIntelligence",
    "ResearchOutput",
    "EngagementLayer",
    "CredibilityLayer",
    "SystemMetadata",
]

#: Fields inside "Identity" that are required for a profile to be usable.
REQUIRED_IDENTITY_FIELDS: List[str] = [
    "Name",
    "FacultyID",
    "Department",
    "Designation",
    "Institution",
]

#: Default directory (relative to project root) where faculty JSON files live.
DEFAULT_FACULTY_DIR: Path = Path("data") / "faculty"

#: Regex used to extract the numeric portion of filenames like "faculty10.json".
_NUMERIC_SUFFIX_PATTERN = re.compile(r"(\d+)")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _numeric_sort_key(path: Path) -> tuple:
    """
    Build a sort key that orders faculty files numerically instead of
    alphabetically.

    Example ordering achieved:
        faculty1.json, faculty2.json, faculty10.json
        (NOT faculty1.json, faculty10.json, faculty2.json)

    Args:
        path: Path to a faculty JSON file.

    Returns:
        A tuple used as a sort key. Files with a discoverable numeric
        suffix are sorted by that number; files without one are sorted
        alphabetically and placed after numbered files.
    """
    match = _NUMERIC_SUFFIX_PATTERN.search(path.stem)
    if match:
        return (0, int(match.group(1)), path.stem.lower())
    return (1, 0, path.stem.lower())


def _read_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Safely read and parse a single JSON file.

    Args:
        file_path: Path to the JSON file to read.

    Returns:
        The parsed JSON content as a dictionary, or None if the file
        could not be read or parsed. Errors are logged to stdout and
        never raised, so a single bad file cannot crash the loader.
    """
    try:
        with file_path.open("r", encoding="utf-8") as f:
            content = json.load(f)
    except json.JSONDecodeError as exc:
        print(
            f"[loader.py] ERROR: Invalid JSON in '{file_path.name}' "
            f"(line {exc.lineno}, col {exc.colno}): {exc.msg}. Skipping file."
        )
        return None
    except UnicodeDecodeError as exc:
        print(
            f"[loader.py] ERROR: Encoding issue in '{file_path.name}' "
            f"(expected UTF-8): {exc}. Skipping file."
        )
        return None
    except PermissionError:
        print(
            f"[loader.py] ERROR: Permission denied while reading "
            f"'{file_path.name}'. Skipping file."
        )
        return None
    except OSError as exc:
        print(
            f"[loader.py] ERROR: OS error while reading '{file_path.name}': "
            f"{exc}. Skipping file."
        )
        return None
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(
            f"[loader.py] ERROR: Unexpected error while reading "
            f"'{file_path.name}': {exc}. Skipping file."
        )
        return None

    if not isinstance(content, dict):
        print(
            f"[loader.py] ERROR: '{file_path.name}' does not contain a "
            f"JSON object at the top level. Skipping file."
        )
        return None

    return content


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_profile(profile: Dict[str, Any], source_file: str = "") -> bool:
    """
    Validate that a faculty profile dictionary contains the expected
    top-level sections and required identity fields.

    This performs a structural check only. It does NOT mutate the
    profile in any way — all fields are preserved exactly as provided
    by the caller.

    Args:
        profile: The faculty profile dictionary to validate.
        source_file: Optional filename, used only for clearer log
            messages.

    Returns:
        True if the profile contains all required sections and
        identity fields, False otherwise. Missing sections/fields are
        printed as warnings; validation failure does not raise.
    """
    label = f"'{source_file}'" if source_file else "profile"
    is_valid = True

    missing_sections = [
        section for section in REQUIRED_SECTIONS if section not in profile
    ]
    if missing_sections:
        print(
            f"[loader.py] WARNING: {label} is missing required section(s): "
            f"{missing_sections}."
        )
        is_valid = False

    identity = profile.get("Identity")
    if isinstance(identity, dict):
        missing_identity_fields = [
            field for field in REQUIRED_IDENTITY_FIELDS if not identity.get(field)
        ]
        if missing_identity_fields:
            print(
                f"[loader.py] WARNING: {label} is missing required Identity "
                f"field(s): {missing_identity_fields}."
            )
            is_valid = False
    elif "Identity" in profile:
        print(
            f"[loader.py] WARNING: {label} has an 'Identity' section that "
            f"is not an object."
        )
        is_valid = False

    return is_valid


def load_faculty_profiles(
    directory: Optional[Path] = None,
    strict: bool = False,
) -> List[Dict[str, Any]]:
    """
    Load and validate all faculty JSON profiles from a directory.

    This is the primary entry point of the loader module. It:
        1. Verifies the target directory exists and is a directory.
        2. Discovers all '*.json' files within it.
        3. Sorts them numerically (faculty1, faculty2, ..., faculty10).
        4. Parses each file, skipping any that are unreadable or
           malformed, without crashing.
        5. Structurally validates each parsed profile.
        6. Detects and warns about duplicate FacultyID values.
        7. Returns every successfully parsed profile, with all fields
           preserved exactly as found in the source JSON.

    Args:
        directory: Path to the folder containing faculty JSON files.
            Defaults to 'data/faculty' relative to the current working
            directory if not provided.
        strict: If True, profiles that fail structural validation
            (via validate_profile) are excluded from the returned
            list. If False (default), invalid-but-parseable profiles
            are still included (with a warning already printed),
            since downstream consumers may want to handle them.

    Returns:
        A list of faculty profile dictionaries, in numeric filename
        order. Returns an empty list if the directory is missing,
        empty, unreadable, or contains no valid JSON files.
    """
    faculty_dir = Path(directory) if directory is not None else DEFAULT_FACULTY_DIR

    if not faculty_dir.exists():
        print(f"[loader.py] ERROR: Faculty directory not found: '{faculty_dir}'.")
        return []

    if not faculty_dir.is_dir():
        print(f"[loader.py] ERROR: '{faculty_dir}' exists but is not a directory.")
        return []

    try:
        json_files = list(faculty_dir.glob("*.json"))
    except PermissionError:
        print(f"[loader.py] ERROR: Permission denied while listing '{faculty_dir}'.")
        return []
    except OSError as exc:
        print(f"[loader.py] ERROR: Could not list '{faculty_dir}': {exc}.")
        return []

    if not json_files:
        print(f"[loader.py] WARNING: No JSON files found in '{faculty_dir}'.")
        return []

    json_files.sort(key=_numeric_sort_key)

    profiles: List[Dict[str, Any]] = []
    seen_faculty_ids: Dict[str, str] = {}  # FacultyID -> filename first seen in

    for file_path in json_files:
        profile = _read_json_file(file_path)
        if profile is None:
            continue

        is_valid = validate_profile(profile, source_file=file_path.name)
        if strict and not is_valid:
            print(
                f"[loader.py] INFO: Excluding '{file_path.name}' from results "
                f"(strict mode, failed validation)."
            )
            continue

        faculty_id = profile.get("Identity", {}).get("FacultyID") if isinstance(
            profile.get("Identity"), dict
        ) else None

        if faculty_id:
            if faculty_id in seen_faculty_ids:
                print(
                    f"[loader.py] WARNING: Duplicate FacultyID '{faculty_id}' "
                    f"found in '{file_path.name}' (first seen in "
                    f"'{seen_faculty_ids[faculty_id]}')."
                )
            else:
                seen_faculty_ids[faculty_id] = file_path.name

        profiles.append(profile)

    print(
        f"[loader.py] INFO: Loaded {len(profiles)} faculty profile(s) from "
        f"{len(json_files)} file(s) in '{faculty_dir}'."
    )

    return profiles


def get_faculty_count(profiles: List[Dict[str, Any]]) -> int:
    """
    Return the number of faculty profiles in a loaded list.

    Args:
        profiles: List of faculty profile dictionaries, typically
            returned by load_faculty_profiles().

    Returns:
        The count of profiles in the list.
    """
    return len(profiles)


def get_departments(profiles: List[Dict[str, Any]]) -> List[str]:
    """
    Extract a sorted list of unique departments across all profiles.

    Args:
        profiles: List of faculty profile dictionaries.

    Returns:
        A sorted list of unique, non-empty department names found in
        the "Identity" section of each profile. Profiles missing this
        information are silently skipped.
    """
    departments: Set[str] = set()
    for profile in profiles:
        identity = profile.get("Identity", {})
        if isinstance(identity, dict):
            department = identity.get("Department")
            if department:
                departments.add(department)
    return sorted(departments)


def get_institutions(profiles: List[Dict[str, Any]]) -> List[str]:
    """
    Extract a sorted list of unique institutions across all profiles.

    Args:
        profiles: List of faculty profile dictionaries.

    Returns:
        A sorted list of unique, non-empty institution names found in
        the "Identity" section of each profile. Profiles missing this
        information are silently skipped.
    """
    institutions: Set[str] = set()
    for profile in profiles:
        identity = profile.get("Identity", {})
        if isinstance(identity, dict):
            institution = identity.get("Institution")
            if institution:
                institutions.add(institution)
    return sorted(institutions)


def get_faculty_by_id(
    profiles: List[Dict[str, Any]], faculty_id: str
) -> Optional[Dict[str, Any]]:
    """
    Look up a single faculty profile by its FacultyID.

    Args:
        profiles: List of faculty profile dictionaries.
        faculty_id: The FacultyID to search for (case-sensitive, exact
            match against Identity.FacultyID).

    Returns:
        The matching faculty profile dictionary, or None if no profile
        with the given FacultyID is found.
    """
    for profile in profiles:
        identity = profile.get("Identity", {})
        if isinstance(identity, dict) and identity.get("FacultyID") == faculty_id:
            return profile
    return None


# ---------------------------------------------------------------------------
# Manual/standalone execution (useful for quick sanity checks during dev)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    loaded_profiles = load_faculty_profiles()
    print(f"Total faculty loaded: {get_faculty_count(loaded_profiles)}")
    print(f"Departments: {get_departments(loaded_profiles)}")
    print(f"Institutions: {get_institutions(loaded_profiles)}")