import requests
from pathlib import Path

def download_match_files(match_id, tracking_dir, metadata_dir):
    tracking_url = f'https://media.githubusercontent.com/media/SkillCorner/opendata/master/data/matches/{match_id}/{match_id}_tracking_extrapolated.jsonl'
    metadata_url = f'https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches/{match_id}/{match_id}_match.json'

    tracking_path = Path(tracking_dir) / f'{match_id}_tracking_extrapolated.jsonl'
    metadata_path = Path(metadata_dir) / f'{match_id}_match.json'

    # Download tracking file
    try:
        r = requests.get(tracking_url)
        r.raise_for_status()
        with open(tracking_path, 'wb') as f:
            f.write(r.content)
        print(f'✓ Downloaded tracking for {match_id} to {tracking_path}')
    except Exception as e:
        print(f'✗ Error downloading tracking for {match_id}: {e}')

    # Download metadata file
    try:
        r = requests.get(metadata_url)
        r.raise_for_status()
        with open(metadata_path, 'wb') as f:
            f.write(r.content)
        print(f'✓ Downloaded metadata for {match_id} to {metadata_path}')
    except Exception as e:
        print(f'✗ Error downloading metadata for {match_id}: {e}')