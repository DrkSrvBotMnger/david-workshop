# utils/csv_export.py
from io import StringIO
import csv

def tablevm_to_csv_bytes(title: str, columns: list[str], rows: list[list[str]]) -> bytes:
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow([title])
    writer.writerow([])  # spacer
    writer.writerow(columns)
    for r in rows:
        writer.writerow(r)
    return buf.getvalue().encode("utf-8")
