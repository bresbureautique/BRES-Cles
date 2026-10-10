#!/usr/bin/env python3
"""R344: reject implausible or lossy JSON numeric evidence.

Diagnostic-only external receipt validator. The OCR runtime, benchmark and stable
V2.27 are intentionally not touched. Acceptance is NOT device authentication.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
from validate_r343_device_result import MAX_FILE_BYTES, no_duplicates, reject_constant
from validate_r343_device_result import validate as validate_r343

JS_MAX_SAFE_INTEGER = 2 ** 53 - 1


def parse_js_integer(token: str):
    if token == '-0':
        raise ValueError('noncanonical_js_negative_zero')
    value = int(token)
    if abs(value) > JS_MAX_SAFE_INTEGER:
        raise ValueError('unsafe_js_integer')
    return value


def parse_js_float(token: str):
    value = float(token)
    if not math.isfinite(value):
        raise ValueError('nonfinite_json_number')
    try:
        exact = Decimal(token)
    except InvalidOperation as exc:
        raise ValueError('invalid_decimal_number') from exc
    if exact != 0 and value == 0:
        raise ValueError('underflow_json_number')
    if token.startswith('-') and value == 0:
        raise ValueError('noncanonical_js_negative_zero')
    return value


def parse_native_number_json(raw: bytes):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=no_duplicates,
                      parse_constant=reject_constant, parse_int=parse_js_integer,
                      parse_float=parse_js_float)


def validate(path: Path) -> dict:
    raw = path.read_bytes()
    errors = []
    if len(raw) > MAX_FILE_BYTES:
        errors.append('json_file_too_large')
    else:
        try:
            data = parse_native_number_json(raw)
            if not isinstance(data, dict):
                errors.append('json_top_level_not_object')
        except (ValueError, UnicodeError, RecursionError, TypeError, OverflowError) as exc:
            errors.append('number_strict_json_invalid:' + str(exc))
    base = validate_r343(path) if not errors else None
    ok = bool(not errors and base and base.get('ok'))
    return {
        'schema': 'bres-r344-js-number-evidence-v1',
        'milestone': 'R344', 'source': path.name,
        'sha256': hashlib.sha256(raw).hexdigest(),
        'max_file_bytes': MAX_FILE_BYTES,
        'js_max_safe_integer': JS_MAX_SAFE_INTEGER,
        'number_format_ok': not errors, 'r343_ok': bool(base and base.get('ok')),
        'engineering_review_candidate': bool(ok and base.get('engineering_review_candidate')),
        'activation_candidate': False, 'automatic_activation': False,
        'physical_device_authenticated': False,
        'errors': errors, 'warnings': [], 'base_r343': base, 'ok': ok,
    }


def main():
    ap = argparse.ArgumentParser(description='Validate JavaScript JSON number syntax; never activates OCR.')
    ap.add_argument('result_json', type=Path)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    result = validate(args.result_json)
    out = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if args.out: args.out.write_text(out, encoding='utf-8')
    print(out, end='')
    return 0 if result['ok'] else 2

if __name__ == '__main__':
    raise SystemExit(main())