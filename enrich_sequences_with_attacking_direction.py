import json
import argparse
from pathlib import Path
import pandas as pd
import re


def infer_events_csv(positions_path: Path) -> Path | None:
    # try to find match id in positions filename
    m = re.search(r"(\d{5,})", positions_path.name)
    if m:
        match_id = m.group(1)
        candidate = positions_path.parent.parent / 'data' / f"{match_id}_dynamic_events.csv"
        if candidate.exists():
            return candidate
    # fallback: look for any dynamic events file in data/
    data_dir = positions_path.parent.parent / 'data'
    if data_dir.exists():
        for p in data_dir.glob("*_dynamic_events.csv"):
            return p
    return None


def load_positions_json(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_positions_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def get_first_frame_from_sequence(seq: dict):
    frames = seq.get('frames')
    if frames and isinstance(frames, (list, tuple)) and len(frames) > 0:
        return int(frames[0])
    # fallback: extract from positions keys
    positions = seq.get('positions')
    if isinstance(positions, dict) and len(positions) > 0:
        try:
            keys = sorted(int(k) for k in positions.keys())
            return keys[0]
        except Exception:
            return None
    return None


def enrich(positions_file: Path, events_csv: Path | None = None, attacking_column: str = 'attacking_side'):
    data = load_positions_json(positions_file)
    sequences = data.get('sequences') or []

    # resolve events CSV
    if events_csv is None:
        events_csv = infer_events_csv(positions_file)
    if events_csv is None or not Path(events_csv).exists():
        print('Events CSV not found. Aborting enrichment.')
        return

    df = pd.read_csv(events_csv)
    # ensure numeric frame_start for robust matching
    df['frame_start_num'] = pd.to_numeric(df.get('frame_start', pd.Series()), errors='coerce')

    updated = 0
    for seq in sequences:
        first_frame = get_first_frame_from_sequence(seq)
        attacking_val = None
        if first_frame is not None:
            matches = df[df['frame_start_num'].notna() & (df['frame_start_num'].astype(int) == int(first_frame))]
            if not matches.empty:
                # take first matching row
                row = matches.iloc[0]
                attacking_val = row.get(attacking_column)
                # normalize NaN -> None
                if pd.isna(attacking_val):
                    attacking_val = None
        # set value (None will be serialized as null)
        seq['attacking_side'] = attacking_val if attacking_val is not None else None
        if attacking_val is not None:
            updated += 1

    # Save back to same file
    save_positions_json(positions_file, data)
    print(f'Enriched {updated}/{len(sequences)} sequences with attacking_side and saved to {positions_file}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--match-id', required=True, help='Match id to locate files in output_json/ and Data/')
    p.add_argument('--attacking-column', default='attacking_side', help='Column name for attacking side in CSV')
    p.add_argument('--base-dir', default='.', help='Project base directory (defaults to current working directory)')
    args = p.parse_args()

    base = Path(args.base_dir)
    match_id = str(args.match_id)

    # construct paths
    positions_file = base / 'output_json' / f"{match_id}_sequences_positions.json"
    events_csv = base / 'Data' / f"{match_id}_dynamic_events.csv"

    if not positions_file.exists():
        print('Positions file not found:', positions_file)
        return
    if not events_csv.exists():
        print('Events CSV not found:', events_csv)
        return

    enrich(positions_file, events_csv, attacking_column=args.attacking_column)


if __name__ == '__main__':
    main()
