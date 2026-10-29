"""Bounded deterministic CSV summaries; no model, code execution or data retention."""
import argparse
import csv
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat

MAX_BYTES = 256 * 1024
MAX_ROWS = 10000
MAX_COLUMNS = 64
NUMBER = re.compile(r'[+-]?\d{1,30}(?:\.\d{1,30})?(?:[eE][+-]?\d{1,2})?\Z', re.ASCII)


def numeric(text):
    text = text.strip()
    if not NUMBER.fullmatch(text):
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    if not value.is_finite() or value.copy_abs() > Decimal('1e30') or value.as_tuple().exponent < -30:
        return None
    return value


def rendered(value):
    return format(value, 'f')


def analyze_csv(text, delimiter=','):
    if not isinstance(text, str) or not 0 < len(text.encode('utf-8')) <= MAX_BYTES:
        raise ValueError('CSV input must contain 1–262144 UTF-8 bytes')
    if delimiter not in (',', ';', '\t'):
        raise ValueError('Choose comma, semicolon or tab delimiter')
    if '\x00' in text:
        raise ValueError('NUL characters are not allowed in CSV input')
    reader = csv.reader(io.StringIO(text.lstrip('\ufeff'), newline=''), delimiter=delimiter, strict=True)
    try:
        header = next(reader, [])
        header = [name.strip() for name in header]
        if not 1 <= len(header) <= MAX_COLUMNS or any(not name or len(name) > 100 for name in header):
            raise ValueError('CSV needs 1–64 nonempty column names, at most 100 characters each')
        if len({name.casefold() for name in header}) != len(header):
            raise ValueError('Column names must be unique after trimming and case folding')
        columns = [[] for _ in header]
        seen, duplicates, row_count, formula_cells = set(), 0, 0, 0
        for row in reader:
            # A blank physical record is not silently removed from the dataset.
            if len(row) != len(header):
                raise ValueError('Every CSV record must have the same number of fields as its header')
            row_count += 1
            if row_count > MAX_ROWS:
                raise ValueError('CSV input exceeds the 10000-record limit')
            if any(len(value) > 4096 for value in row):
                raise ValueError('A CSV cell exceeds 4096 characters')
            key = tuple(row)
            duplicates += key in seen
            seen.add(key)
            for values, value in zip(columns, row):
                values.append(value)
                formula_cells += value.lstrip().startswith(('=', '@', '+', '-')) and numeric(value) is None
    except csv.Error as exc:
        raise ValueError('Malformed CSV; check quoting, delimiter and field sizes') from exc
    summaries = []
    with localcontext() as context:
        # Given the bounded input magnitude/scale and row count, sums/medians
        # fit this precision exactly. Division is explicitly rounded separately.
        context.prec = 96
        for name, values in zip(header, columns):
            nonempty = [value for value in values if value.strip()]
            numbers = [number for value in nonempty if (number := numeric(value)) is not None]
            excluded = len(nonempty) - len(numbers)
            item = {'name': name, 'present': len(nonempty), 'missing': len(values) - len(nonempty),
                    'numeric_count': len(numbers), 'excluded_non_numeric': excluded,
                    'kind': 'empty' if not nonempty else 'numeric' if not excluded else 'mixed' if numbers else 'text'}
            if numbers:
                numbers.sort()
                total = sum(numbers, Decimal(0))
                half = len(numbers) // 2
                median = numbers[half] if len(numbers) % 2 else (numbers[half - 1] + numbers[half]) / 2
                with localcontext() as mean_context:
                    mean_context.prec = 28
                    mean = total / len(numbers)
                item.update(sum=rendered(total), minimum=rendered(numbers[0]), maximum=rendered(numbers[-1]),
                            median=rendered(median), mean=str(mean), mean_significant_digits=28)
            summaries.append(item)
    return {'kind': 'deterministic-csv-summary', 'input_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'rows': row_count, 'columns': len(header), 'duplicate_rows': duplicates,
            'duplicate_definition': 'Exact parsed field values, including whitespace; original rows are not removed.',
            'formula_like_cells': formula_cells, 'column_summaries': summaries,
            'model_calls': 0, 'stored_dataset': False,
            'limitations': ['Only empty/whitespace fields count as missing; NA/null/NaN are text.',
                'Numeric summaries cover numeric cells only; excluded nonnumeric cells are counted.',
                'Numbers use bounded decimal syntax, scale and magnitude; currencies, grouped numbers and dates are text.',
                'Sums and medians are exact within input bounds; means are rounded to 28 significant digits.',
                'No formulas or CSV instructions are executed. No causal, predictive or investment conclusions are inferred.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--delimiter', choices=('comma', 'semicolon', 'tab'), default='comma')
    args = parser.parse_args()
    try:
        fd = os.open(args.file, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(fd, 'rb') as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise ValueError('Select a regular UTF-8 CSV file')
            data = handle.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('CSV exceeds the input byte limit')
        result = analyze_csv(data.decode('utf-8-sig'), {'comma': ',', 'semicolon': ';', 'tab': '\t'}[args.delimiter])
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
