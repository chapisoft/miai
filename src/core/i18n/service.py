"""
Enterprise Multilingual i18n Service for miai Platform.
Supports 5 Languages: Vietnamese (vi - default), English (en), Chinese (zh), Japanese (ja), Korean (ko).
"""

import json
import os
from contextvars import ContextVar
from enum import Enum, unique
from typing import Dict, Optional, Any
from pathlib import Path

@unique
class SupportedLanguage(str, Enum):
    VI = "vi"
    EN = "en"
    ZH = "zh"
    JA = "ja"
    KO = "ko"


DEFAULT_LANGUAGE = SupportedLanguage.VI.value

# Thread-safe ContextVar to store request locale
current_language: ContextVar[str] = ContextVar("current_language", default=DEFAULT_LANGUAGE)

_LOCALES_DIR = Path(__file__).resolve().parent / "locales"
_TRANSLATIONS: Dict[str, Dict[str, str]] = {}


def _load_translations():
    global _TRANSLATIONS
    for lang in SupportedLanguage:
        locale_file = _LOCALES_DIR / f"{lang.value}.json"
        if locale_file.exists():
            try:
                with open(locale_file, "r", encoding="utf-8") as f:
                    _TRANSLATIONS[lang.value] = json.load(f)
            except Exception as e:
                _TRANSLATIONS[lang.value] = {}
        else:
            _TRANSLATIONS[lang.value] = {}


# Initial load
_load_translations()


def resolve_language(raw_value: Optional[str]) -> str:
    """
    Parses Accept-Language header, X-Language, or query param.
    Defaults to 'vi' if missing or not supported.
    """
    if not raw_value or not raw_value.strip():
        return DEFAULT_LANGUAGE

    # Handle standard Accept-Language format, e.g. "vi-VN,vi;q=0.9,en-US;q=0.8"
    parts = [p.strip().split(";")[0].strip() for p in raw_value.split(",")]
    for part in parts:
        normalized = part.lower().replace("_", "-")
        # Check direct 2-letter code
        prefix = normalized[:2]
        for sup in SupportedLanguage:
            if prefix == sup.value:
                return sup.value

    return DEFAULT_LANGUAGE


def set_request_language(lang_header_or_code: Optional[str]) -> str:
    """
    Resolves and stores the language code in the current request ContextVar.
    """
    lang = resolve_language(lang_header_or_code)
    current_language.set(lang)
    return lang


def get_current_language() -> str:
    """
    Gets the language code of the active request context.
    """
    return current_language.get()


def get_message(key: str, lang: Optional[str] = None, default: Optional[str] = None, **kwargs) -> str:
    """
    Translates a key into the target language.
    If key is not translated in target lang, fallbacks to Vietnamese ('vi').
    If still not found, returns default or the key itself.
    """
    if not key:
        return ""

    target_lang = lang or current_language.get() or DEFAULT_LANGUAGE

    # 1. Lookup in target language
    msg = _TRANSLATIONS.get(target_lang, {}).get(key)
    if msg:
        if kwargs:
            try:
                return msg.format(**kwargs)
            except Exception:
                return msg
        return msg

    # 2. Fallback to Vietnamese if target language is not Vietnamese
    if target_lang != DEFAULT_LANGUAGE:
        fallback_msg = _TRANSLATIONS.get(DEFAULT_LANGUAGE, {}).get(key)
        if fallback_msg:
            if kwargs:
                try:
                    return fallback_msg.format(**kwargs)
                except Exception:
                    return fallback_msg
            return fallback_msg

    # 3. Fallback to provided default or original key
    return default if default is not None else key
