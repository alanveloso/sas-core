"""Load and cache versioned spectrum profiles from an allowlisted directory."""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any

import yaml
from pydantic import ValidationError

from spectrum_profiles.schema import SpectrumProfile

_PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_PROFILES_DIR = _PACKAGE_DIR / "profiles"

_cache: dict[str, SpectrumProfile] = {}
_cache_lock = RLock()
_profiles_dir_override: Path | None = None


class ProfileError(Exception):
    """Base error for spectrum profile loading failures."""


class ProfileNotFoundError(ProfileError):
    """Raised when no profile file exists for the requested id."""


class ProfileValidationError(ProfileError):
    """Raised when a profile file fails schema or structural validation."""


class ProfilePathError(ProfileError):
    """Raised when a resolved profile path escapes the allowlisted directory."""


def get_profiles_dir() -> Path:
    return (_profiles_dir_override or DEFAULT_PROFILES_DIR).resolve()


def set_profiles_dir(path: Path | str | None) -> Path:
    """Override the allowlisted profiles directory (tests / diagnostics)."""
    global _profiles_dir_override
    if path is None:
        _profiles_dir_override = None
    else:
        _profiles_dir_override = Path(path).resolve()
    clear_profile_cache()
    return get_profiles_dir()


def clear_profile_cache(profile_id: str | None = None) -> None:
    with _cache_lock:
        if profile_id is None:
            _cache.clear()
        else:
            _cache.pop(profile_id, None)


def _assert_within_profiles_dir(path: Path, profiles_dir: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(profiles_dir)
    except ValueError as exc:
        raise ProfilePathError(
            f"profile path '{resolved}' is outside allowlisted directory '{profiles_dir}'"
        ) from exc
    return resolved


def _candidate_paths(profile_id: str, profiles_dir: Path) -> list[Path]:
    if not profile_id or "/" in profile_id or "\\" in profile_id or ".." in profile_id:
        raise ProfilePathError(f"invalid profile id '{profile_id}'")
    return [
        profiles_dir / f"{profile_id}.yaml",
        profiles_dir / f"{profile_id}.yml",
        profiles_dir / f"{profile_id}.json",
    ]


def _read_profile_document(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            return json.loads(text)
        if suffix in {".yaml", ".yml"}:
            return yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ProfileValidationError(
            f"malformed profile document at '{path}': {exc}"
        ) from exc
    raise ProfileValidationError(f"unsupported profile format '{suffix}' for '{path}'")


def _validate_document(profile_id: str, document: Any, source: Path) -> SpectrumProfile:
    if not isinstance(document, dict):
        raise ProfileValidationError(
            f"profile '{profile_id}' at '{source}' must be a mapping, got {type(document).__name__}"
        )
    if document.get("api_version") == "spectrum-access/v2":
        raise ProfileValidationError(
            f"profile '{profile_id}' at '{source}' is Profile v2; "
            "use parse_profile_v2_spectrum (load_profile is the v1 loader)"
        )
    try:
        profile = SpectrumProfile.model_validate(document)
    except ValidationError as exc:
        raise ProfileValidationError(
            f"profile '{profile_id}' at '{source}' failed validation: {exc}"
        ) from exc
    if profile.id != profile_id:
        raise ProfileValidationError(
            f"profile id mismatch: requested '{profile_id}', document declares '{profile.id}'"
        )
    return profile


def load_profile(profile_id: str, *, use_cache: bool = True) -> SpectrumProfile:
    """Load a spectrum profile by id from the allowlisted profiles directory."""
    if use_cache:
        with _cache_lock:
            cached = _cache.get(profile_id)
            if cached is not None:
                return cached

    profiles_dir = get_profiles_dir()
    if not profiles_dir.is_dir():
        raise ProfileNotFoundError(
            f"profiles directory '{profiles_dir}' does not exist or is not a directory"
        )

    existing: list[Path] = []
    for candidate in _candidate_paths(profile_id, profiles_dir):
        path = _assert_within_profiles_dir(candidate, profiles_dir)
        if path.is_file():
            existing.append(path)

    if not existing:
        raise ProfileNotFoundError(
            f"spectrum profile '{profile_id}' not found under '{profiles_dir}'"
        )
    if len(existing) > 1:
        names = ", ".join(str(path.name) for path in existing)
        raise ProfileValidationError(
            f"multiple profile files for '{profile_id}' under '{profiles_dir}': {names}"
        )

    source = existing[0]
    document = _read_profile_document(source)
    profile = _validate_document(profile_id, document, source)

    if use_cache:
        with _cache_lock:
            _cache[profile_id] = profile
    return profile
