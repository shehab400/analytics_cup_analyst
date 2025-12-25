import requests
from pathlib import Path
import pandas as pd

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


def find_similar_sequences(sequence_id, dtw_matrix_df, threshold):
    """
    Find all sequences similar to a given sequence based on DTW distance.
    
    Parameters:
    -----------
    sequence_id : str
        The sequence identifier (format: matchid_sequenceid)
    dtw_matrix_df : DataFrame
        The DTW distance matrix
    threshold : float
        The DTW distance threshold for similarity
    
    Returns:
    --------
    DataFrame with similar sequences and their DTW distances, sorted ascending
    """
    
    if sequence_id not in dtw_matrix_df.columns:
        print(f"Error: Sequence '{sequence_id}' not found in DTW matrix")
        return None
    
    # Get distances from the column for the target sequence
    distances = dtw_matrix_df[sequence_id]
    
    # Filter sequences with distance < threshold (excluding itself with distance 0)
    similar = distances[(distances < threshold) & (distances > 0)]
    
    # Sort by distance (ascending - most similar first)
    similar_sorted = similar.sort_values()
    
    # Create a DataFrame with results
    result_df = pd.DataFrame({
        'sequence_id': similar_sorted.index,
        'dtw_distance': similar_sorted.values
    })
    
    return result_df



