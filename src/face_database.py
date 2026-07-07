import json
from pathlib import Path
from typing import Dict


class FaceDatabase:
    """A minimal face database shim used by the Streamlit UI.

    This provides just enough functionality for `app/main.py` to read
    expression stats. It's intentionally lightweight (JSON file store)
    to avoid adding heavier DB dependencies.
    """

    def __init__(self, storage_dir: Path = None):
        root = Path(__file__).parent.parent
        self.data_dir = storage_dir or (root / "data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_file = self.data_dir / "faces.json"

        # Ensure file exists and has a basic structure
        if not self.db_file.exists():
            self._write({'expressions': []})

    def _read(self) -> Dict:
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {'expressions': []}

    def _write(self, data: Dict) -> None:
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def add_face_record(self, timestamp: str, expression: str, neutrality: float) -> None:
        d = self._read()
        d.setdefault('expressions', []).append({
            'timestamp': timestamp,
            'expression': expression,
            'neutrality': neutrality
        })
        self._write(d)

    def get_expression_stats(self) -> Dict:
        """Return a small summary used by the UI.

        Returns a dict with an `expression_counts` mapping.
        """
        d = self._read()
        counts = {}
        for rec in d.get('expressions', []):
            expr = rec.get('expression', 'unknown')
            counts[expr] = counts.get(expr, 0) + 1

        return {
            'expression_counts': counts,
            'total_records': sum(counts.values())
        }
