"""
Validate translation files using GNU gettext `msgfmt` command.
"""

import argparse
import json
import os
import os.path
import subprocess
import sys
import textwrap

import i18n.validate

# Git merge conflict markers that must never appear in committed translation files.
GIT_CONFLICT_MARKERS = ('<<<<<<<', '=======', '>>>>>>>')

def get_translation_files(translation_directory):
    """
    List all translations '*.po' files in the specified directory.
    """
    po_files = []
    for root, _dirs, files in os.walk(translation_directory):
        for file_name in files:
            pofile_path = os.path.join(root, file_name)
            if file_name.endswith('.po') and '/en/LC_MESSAGES/' not in pofile_path:
                po_files.append(pofile_path)
    return po_files


def validate_translation_file(po_file):
    """
    Validate a translation file and return errors if any.

    This function combines both stderr and stdout output of the `msgfmt` in a
    single variable.
    """
    valid = True
    output = ""

    completed_process = subprocess.run(
        ['msgfmt', '-v', '--strict', '--check', po_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if completed_process.returncode != 0:
        valid = False

    msgfmt_stdout = completed_process.stdout.decode(encoding='utf-8', errors='replace')
    msgfmt_stderr = completed_process.stderr.decode(encoding='utf-8', errors='replace')
    output += f'{msgfmt_stdout}\n{msgfmt_stderr}\n'

    try:
      problems = i18n.validate.check_messages(po_file)
    except Exception as e:
      output += f'{e} {traceback.format_exc()}'
      valid = False
      problems = []
    if problems:
        valid = False

    id_filler = textwrap.TextWrapper(width=79, initial_indent="  msgid: ", subsequent_indent=" " * 9)
    tx_filler = textwrap.TextWrapper(width=79, initial_indent="  -----> ", subsequent_indent=" " * 9)
    for problem in problems:
        desc, msgid = problem[:2]
        output += f"{desc}\n{id_filler.fill(msgid)}\n"
        for translation in problem[2:]:
            output += f"{tx_filler.fill(translation)}\n"
        output += "\n"

    return {
        'valid': valid,
        'output': output,
    }


def get_json_translation_files(translation_directory):
    """
    List all '*.json' translation files in the specified directory.
    """
    json_files = []
    for root, _dirs, files in os.walk(translation_directory):
        for file_name in files:
            if file_name.endswith('.json'):
                json_files.append(os.path.join(root, file_name))
    return json_files


def validate_json_translation_file(json_file):
    """
    Validate a JSON translation file.

    Checks for:
      - Git merge conflict markers (e.g. left by an unresolved merge)
      - Valid JSON syntax
    """
    valid = True
    output = ""

    with open(json_file, encoding='utf-8') as f:
        content = f.read()

    for line_no, line in enumerate(content.splitlines(), 1):
        for marker in GIT_CONFLICT_MARKERS:
            if line.startswith(marker):
                valid = False
                output += f"Git conflict marker at line {line_no}: {line.strip()}\n"

    try:
        json.loads(content)
    except json.JSONDecodeError as exc:
        valid = False
        output += f"Invalid JSON: {exc}\n"

    return {
        'valid': valid,
        'output': output,
    }


def validate_translation_files(
    translations_dir='translations',
    formats=None,
):
    """
    Validate translation files and print errors to stderr.

    Returns integer OS Exit code:

      return 0 for valid translations.
      return 1 for invalid translations.

    The `formats` argument is a set of strings controlling which file types to
    validate. Supported values: 'po', 'json'. Defaults to both.
    """
    if formats is None:
        formats = {'po', 'json'}

    translations_valid = True
    invalid_lines = []

    if 'po' in formats:
        po_files = get_translation_files(translations_dir)
        for po_file in po_files:
            result = validate_translation_file(po_file)

            if result['valid']:
                print('VALID: ' + po_file)
                print(result['output'], '\n' * 2)
            else:
                invalid_lines.append('INVALID: ' + po_file)
                invalid_lines.append(result['output'] + '\n' * 2)
                translations_valid = False

    if 'json' in formats:
        json_files = get_json_translation_files(translations_dir)
        for json_file in json_files:
            result = validate_json_translation_file(json_file)

            if result['valid']:
                print('VALID: ' + json_file)
            else:
                invalid_lines.append('INVALID: ' + json_file)
                invalid_lines.append(result['output'] + '\n' * 2)
                translations_valid = False

    # Print validation errors in the bottom for easy reading
    print('\n'.join(invalid_lines), file=sys.stderr)

    if translations_valid:
        print('-----------------------------------------')
        print('SUCCESS: All translation files are valid.')
        print('-----------------------------------------')
        exit_code = 0
    else:
        print('---------------------------------------', file=sys.stderr)
        print('FAILURE: Some translations are invalid.', file=sys.stderr)
        print('---------------------------------------', file=sys.stderr)
        exit_code = 1

    return exit_code


def main():  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', action='store', type=str, default='translations')
    parser.add_argument(
        '--formats',
        action='store',
        type=str,
        default='po,json',
        help='Comma-separated list of formats to validate (po, json). Default: po,json',
    )
    args = parser.parse_args()
    formats = {f.strip() for f in args.formats.split(',')}
    sys.exit(validate_translation_files(
        translations_dir=args.dir,
        formats=formats,
    ))


if __name__ == '__main__':
    main()  # pragma: no cover
