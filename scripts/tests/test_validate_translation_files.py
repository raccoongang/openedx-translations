"""
Tests for the validate_translation_files.py script.
"""

import os.path
import re

from ..validate_translation_files import (
    get_json_translation_files,
    get_translation_files,
    validate_json_translation_file,
    validate_translation_files,
)

SCRIPT_DIR = os.path.dirname(__file__)


def test_get_translation_files():
    """
    Ensure `get_translation_files` skips the source translation files and non-po files.
    """
    mock_translations_dir = os.path.join(SCRIPT_DIR, 'mock_translations_dir')
    po_files_sorted = sorted(get_translation_files(mock_translations_dir))
    relative_po_files = [
        os.path.relpath(po_file, SCRIPT_DIR)
        for po_file in po_files_sorted
    ]

    assert relative_po_files == [
        'mock_translations_dir/demo-xblock/conf/locale/ar/LC_MESSAGES/django.po',
        'mock_translations_dir/demo-xblock/conf/locale/de_DE/LC_MESSAGES/django.po',
        'mock_translations_dir/demo-xblock/conf/locale/hi/LC_MESSAGES/django.po',
    ]


def test_main_on_invalid_files(capsys):
    """
    Integration test for the `main` function on some invalid files.
    """
    mock_translations_dir = os.path.join(SCRIPT_DIR, 'mock_translations_dir')
    exit_code = validate_translation_files(mock_translations_dir)
    out, err = capsys.readouterr()

    assert 'VALID:' in out, 'Valid files should be printed in stdout'
    assert 'de_DE/LC_MESSAGES/django.po' in out, 'German translation file should be found valid'
    assert 'ar/LC_MESSAGES/django.po' in out, 'Arabic translation file should be found valid'
    assert 'hi/LC_MESSAGES/django.po' not in out, 'Invalid file should be printed in stderr'
    assert 'en/LC_MESSAGES/django.po' not in out, 'Source file should not be validated'

    assert re.match(r'INVALID: .*hi/LC_MESSAGES/django.po', err)
    assert '\'msgstr\' is not a valid Python brace format string, unlike \'msgid\'' in err
    assert 'FAILURE: Some translations are invalid.' in err

    assert exit_code == 1, 'Should fail due to invalid hi/LC_MESSAGES/django.po file'


def test_main_on_valid_files(capsys):
    """
    Integration test for the `main` function but only for the Arabic translations which is valid.
    """
    mock_translations_dir = os.path.join(SCRIPT_DIR, 'mock_translations_dir/demo-xblock/conf/locale/ar')
    exit_code = validate_translation_files(mock_translations_dir)
    out, err = capsys.readouterr()

    assert 'VALID:' in out, 'Valid files should be printed in stdout'
    assert 'ar/LC_MESSAGES/django.po' in out, 'Arabic translation file is valid'
    assert 'SUCCESS: All translation files are valid.' in out
    assert not err.strip(), 'The stderr should be empty'
    assert exit_code == 0, 'Should succeed due in validating the ar/LC_MESSAGES/django.po file'


def test_get_json_translation_files():
    """
    Ensure `get_json_translation_files` finds all .json files in the directory.
    """
    mock_translations_dir = os.path.join(SCRIPT_DIR, 'mock_translations_dir/frontend-app-authn')
    json_files_sorted = sorted(get_json_translation_files(mock_translations_dir))
    relative_json_files = [
        os.path.relpath(f, SCRIPT_DIR)
        for f in json_files_sorted
    ]

    assert relative_json_files == [
        'mock_translations_dir/frontend-app-authn/src/i18n/messages/ar.json',
        'mock_translations_dir/frontend-app-authn/src/i18n/messages/zh_CN.json',
    ]


def test_validate_json_translation_file_valid():
    """
    A well-formed JSON translation file without conflict markers should be valid.
    """
    valid_json = os.path.join(
        SCRIPT_DIR,
        'mock_translations_dir/frontend-app-authn/src/i18n/messages/ar.json',
    )
    result = validate_json_translation_file(valid_json)
    assert result['valid'] is True
    assert result['output'] == ''


def test_validate_json_translation_file_with_conflict_markers():
    """
    A JSON file containing git merge conflict markers must be detected as invalid.
    """
    conflicted_json = os.path.join(
        SCRIPT_DIR,
        'mock_translations_dir/frontend-app-authn/src/i18n/messages/zh_CN.json',
    )
    result = validate_json_translation_file(conflicted_json)
    assert result['valid'] is False
    assert 'Git conflict marker' in result['output']
    assert '<<<<<<<' in result['output']
    assert '=======' in result['output']
    assert '>>>>>>>' in result['output']


def test_main_catches_json_conflict_markers(capsys):
    """
    Integration test: validate_translation_files must fail when a JSON file
    contains git merge conflict markers.
    """
    mock_translations_dir = os.path.join(
        SCRIPT_DIR,
        'mock_translations_dir/frontend-app-authn',
    )
    exit_code = validate_translation_files(mock_translations_dir)
    out, err = capsys.readouterr()

    assert 'VALID:' in out, 'Valid JSON file should be printed in stdout'
    assert 'ar.json' in out, 'Arabic JSON file should be found valid'
    assert re.search(r'INVALID: .*zh_CN\.json', err), 'Conflicted JSON should be reported as invalid'
    assert 'Git conflict marker' in err
    assert 'FAILURE: Some translations are invalid.' in err
    assert exit_code == 1
