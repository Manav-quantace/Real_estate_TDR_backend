from __future__ import annotations

import csv
import io
from typing import Dict, Iterable, Iterator, List, Any


def csv_stream(rows: Iterable[Dict[str, Any]], fieldnames: List[str]) -> Iterator[bytes]:
    """
    Stream CSV as bytes without holding full file in memory.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    yield buf.getvalue().encode("utf-8")
    buf.seek(0)
    buf.truncate(0)

    for r in rows:
        writer.writerow(r)
        yield buf.getvalue().encode("utf-8")
        buf.seek(0)
        buf.truncate(0)