import pandas as pd
import json
import os
from pathlib import Path

# import helper functions to extract frames and tracking positions
from src.extract_Sequences_ball_positions import (
    extract_frame_numbers_from_sequence,
    load_tracking_positions,
)


def export_sequences_for_match(match_id, DATA_DIR, OUTPUT_DIR):
    """
    Export sequences from dynamic events for a single match.
    Returns: (sequences, filtered_dataframe)
    """
    print(f"\n{'='*60}")
    print(f"Processing Match ID: {match_id}")
    print(f"{'='*60}")
    
    # Load dynamic events data
    url = f'https://raw.githubusercontent.com/SkillCorner/opendata/d276a0901fbe80b4790396b9bac93c0bdfaf694a/data/matches/{match_id}/{match_id}_dynamic_events.csv'
    local_path = os.path.join(DATA_DIR, f'{match_id}_dynamic_events.csv')
    
    if os.path.exists(local_path):
        print(f'✓ Reading events from local file: {local_path}')
        de_match = pd.read_csv(local_path)
    else:
        print(f'⚠ Downloading events from URL: {url}')
        de_match = pd.read_csv(url)
    
    # Filter out 'on_ball_engagement' events
    filtered_initial = de_match[de_match['event_type'] != 'on_ball_engagement'].copy()
    filtered_initial = filtered_initial.sort_values(['frame_start', 'frame_end']).reset_index(drop=True)
    
    print(f"Events after filtering: {len(filtered_initial)}")
    
    # Build sequences
    sequences = []
    current = None
    seq_counter = 1
    seq_ids = []
    included_idx = []
    off_run_included = 0
    off_run_excluded = 0
    
    for idx, row in filtered_initial.iterrows():
        team = row.get('team_id')
        ev_type = row.get('event_type')
        event = {
            'event_id': row.get('event_id'),
            'player_id': row.get('player_id'),
            'frame_start': int(row['frame_start']) if not pd.isna(row.get('frame_start')) else None,
            'frame_end': int(row['frame_end']) if not pd.isna(row.get('frame_end')) else None,
        }
        
        # Start new sequence if no current sequence
        if current is None:
            current = {
                'sequence_id': seq_counter,
                'team_id': team,
                'events': [event],
                'attacking_side': row.get('attacking_side')
            }
            seq_ids.append(seq_counter)
            included_idx.append(idx)
            seq_counter += 1
            if ev_type == 'off_ball_run':
                off_run_included += 1
            continue
        
        # Handle off_ball_run: include only if same team
        if ev_type == 'off_ball_run' and team != current['team_id']:
            off_run_excluded += 1
            continue
        
        # Group by team
        if team == current['team_id']:
            current['events'].append(event)
            seq_ids.append(current['sequence_id'])
            included_idx.append(idx)
            if ev_type == 'off_ball_run':
                off_run_included += 1
        else:
            sequences.append(current)
            current = {
                'sequence_id': seq_counter,
                'team_id': team,
                'events': [event],
                'attacking_side': row.get('attacking_side')
            }
            seq_ids.append(seq_counter)
            included_idx.append(idx)
            seq_counter += 1
            if ev_type == 'off_ball_run':
                off_run_included += 1
    
    if current is not None:
        sequences.append(current)
    
    # Attach sequence IDs to filtered dataframe
    filtered = filtered_initial.loc[included_idx].copy().reset_index(drop=True)
    filtered['sequence_id'] = seq_ids
    
    # Save sequences to JSON
    output_file = os.path.join(OUTPUT_DIR, f'{match_id}_sequences_excluding_offball_onball.json')
    with open(output_file, 'w', encoding='utf-8') as fh:
        json.dump({'sequences': sequences}, fh, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Exported {len(sequences)} sequences to {output_file}")
    print(f"  - Included events: {len(filtered)}")
    print(f"  - off_ball_run included: {off_run_included}")
    print(f"  - off_ball_run excluded: {off_run_excluded}")
    
    return sequences, filtered

def extract_ball_positions_for_match(match_id, sequences, OUTPUT_DIR):
    """
    Extract ball positions for all sequences in a match by fetching from URL.
    Fetches tracking data ONCE and reuses it for all sequences.
    Returns: list of sequence position data
    """
    print(f"\n{'='*60}")
    print(f"Extracting Ball Positions for Match ID: {match_id}")
    print(f"{'='*60}")
    
    # Construct tracking URL
    tracking_url = f"https://media.githubusercontent.com/media/SkillCorner/opendata/master/data/matches/{match_id}/{match_id}_tracking_extrapolated.jsonl"
    positions_output_file = os.path.join(OUTPUT_DIR, f'{match_id}_sequences_positions.json')
    
    print(f"📡 Fetching tracking data from: {tracking_url}")
    print(f"⏳ This may take a moment (large file)...")
    
    # Fetch tracking data ONCE for all sequences
    try:
        tracking_data = pd.read_json(tracking_url, lines=True)
        print(f"✓ Tracking data loaded: {len(tracking_data)} frames")
    except Exception as e:
        print(f"✗ Error fetching tracking data: {str(e)}")
        return None
    
    all_seq_positions = []
    success_count = 0
    fail_count = 0
    
    for idx, seq in enumerate(sequences):
        if not isinstance(seq, dict):
            continue
        
        # Get sequence ID
        seq_id = None
        for k in ('sequence_id', 'id', 'uid', 'sequenceId'):
            if k in seq:
                seq_id = seq[k]
                break
        
        if seq_id is None:
            print(f"  ⚠ Sequence {idx} has no ID, skipping")
            fail_count += 1
            continue
        
        # Extract frames for this sequence
        frames = extract_frame_numbers_from_sequence(seq)
        
        if not frames:
            print(f"  ⚠ Sequence {seq_id} has no frames, skipping")
            fail_count += 1
            continue
        
        # Extract positions from pre-loaded tracking data
        positions = extract_positions_from_dataframe(tracking_data, frames)
        
        # Convert to serializable format
        positions_serializable = {str(k): list(v) for k, v in positions.items()}
        
        # Attach positions to sequence
        seq['positions'] = positions_serializable
        
        # Collect for aggregate file
        seq_out = {
            'sequence_id': seq_id,
            'team_id': seq.get('team_id'),
            'frames': frames,
            'positions': positions_serializable
        }
        # Add attacking_side if present in the input sequence
        if 'attacking_side' in seq:
            seq_out['attacking_side'] = seq['attacking_side']
        
        all_seq_positions.append(seq_out)
        
        success_count += 1
        
        # Progress update every 50 sequences
        if (idx + 1) % 50 == 0:
            print(f"  Processed {idx + 1}/{len(sequences)} sequences...")
    
    # Final progress if not already shown
    if len(sequences) % 50 != 0:
        print(f"  Processed {len(sequences)}/{len(sequences)} sequences")
    
    # Save positions to JSON
    output_path = Path(positions_output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as fh:
        json.dump({
            'total_sequences': len(all_seq_positions),
            'sequences': all_seq_positions
        }, fh, indent=2)
    
    print(f"\n✓ Saved positions for {len(all_seq_positions)} sequences to {positions_output_file}")
    print(f"  - Success: {success_count}")
    print(f"  - Failed: {fail_count}")
    
    return all_seq_positions


def extract_positions_from_dataframe(tracking_df, wanted_frames):
    """
    Extract ball positions from a pre-loaded tracking DataFrame.
    Returns: dict frame->(x,y,z) for wanted_frames
    """
    results = {}
    wanted = set(wanted_frames)
    
    for _, obj in tracking_df.iterrows():
        # Determine frame index
        frame = None
        for k in ('frame', 'frame_idx', 'frame_index'):
            if k in obj and pd.notnull(obj[k]):
                try:
                    frame = int(obj[k])
                except Exception:
                    try:
                        frame = int(float(obj[k]))
                    except Exception:
                        frame = None
                break
        
        if frame is None or frame not in wanted:
            continue
        
        # Extract ball positions
        bx = by = bz = None
        if 'ball_data' in obj and isinstance(obj['ball_data'], dict):
            bd = obj['ball_data']
            bx = bd.get('x')
            by = bd.get('y')
            bz = bd.get('z')
        elif 'ball' in obj and isinstance(obj['ball'], dict):
            b = obj['ball']
            bx = b.get('x')
            by = b.get('y')
            bz = b.get('z')
        
        # Normalize numeric types
        def _safe_float(v):
            try:
                return None if v is None else float(v)
            except Exception:
                return None
        
        bx = _safe_float(bx)
        by = _safe_float(by)
        bz = _safe_float(bz)
        
        results[frame] = (bx, by, bz)
        
        # Early exit if all frames found
        if len(results) == len(wanted):
            break
    
    # Mark missing frames explicitly
    for f in wanted:
        if f not in results:
            results[f] = (None, None, None)
    
    return results

