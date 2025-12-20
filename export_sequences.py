import pandas as pd
import json
import os
from pathlib import Path

# import helper functions to extract frames and tracking positions
from extract_and_plot_ball_positions import (
    extract_frame_numbers_from_sequence,
    load_tracking_positions,
    save_positions,
)

match_id = 2017461
url = f'https://raw.githubusercontent.com/SkillCorner/opendata/d276a0901fbe80b4790396b9bac93c0bdfaf694a/data/matches/{match_id}/{match_id}_dynamic_events.csv'

# Prefer local data file under data/ if present, otherwise fall back to remote URL
local_path = os.path.join(os.getcwd(), 'data', f'{match_id}_dynamic_events.csv')
if os.path.exists(local_path):
    print('Reading events from local file:', local_path)
    de_match = pd.read_csv(local_path)
else:
    print('Downloading events from URL:', url)
    de_match = pd.read_csv(url)

# Filter out only 'on_ball_engagement' up-front; keep 'off_ball_run' for conditional handling
filtered_initial = de_match[de_match['event_type'] != 'on_ball_engagement'].copy()
filtered_initial = filtered_initial.sort_values(['frame_start', 'frame_end']).reset_index(drop=True)

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

    # If no current sequence, start one with this event (include regardless)
    if current is None:
        current = {
            'sequence_id': seq_counter,
            'team_id': team,
            'events': [event]
        }
        seq_ids.append(seq_counter)
        included_idx.append(idx)
        seq_counter += 1
        # if this was an off_ball_run, count it as included
        if ev_type == 'off_ball_run':
            off_run_included += 1
        continue

    # Conditional handling for off_ball_run: include only if same team as current sequence
    if ev_type == 'off_ball_run' and team != current['team_id']:
        off_run_excluded += 1
        # skip this event entirely
        continue

    # normal grouping: append to current if same team, otherwise start new sequence
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
            'events': [event]
        }
        seq_ids.append(seq_counter)
        included_idx.append(idx)
        seq_counter += 1
        if ev_type == 'off_ball_run':
            off_run_included += 1

if current is not None:
    sequences.append(current)

# attach sequence ids to the dataframe of actually included events
filtered = filtered_initial.loc[included_idx].copy().reset_index(drop=True)
filtered['sequence_id'] = seq_ids

out = {'sequences': sequences}
output_dir = os.path.join(os.getcwd(), 'output_json')
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, rf'{match_id}_sequences_excluding_offball_onball.json')
with open(output_file, 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2)

print(f'Wrote {len(out["sequences"])} sequences to {output_file}')
print('Included filtered rows:', len(filtered))
print('First 5 included rows:')
print(filtered.head().to_string())
print(f"off_ball_run included: {off_run_included}, excluded: {off_run_excluded}")

# --- Extract ball positions for each sequence if tracking data is available ---
# Attempt to locate tracking file under data/<match_id>_tracking_extrapolated.jsonl
tracking_local = os.path.join(os.getcwd(), 'data', f'{match_id}_tracking_extrapolated.jsonl')
positions_output_file = os.path.join(output_dir, f'{match_id}_sequences_positions.json')

if os.path.exists(tracking_local):
    print('Found tracking file; extracting ball positions for each sequence from:', tracking_local)
    all_seq_positions = []
    for seq in sequences:
        # compute frames for this sequence
        frames = extract_frame_numbers_from_sequence(seq)
        if not frames:
            print(f"  Sequence {seq.get('sequence_id')} has no frames, skipping positions")
            continue
        positions = load_tracking_positions(tracking_local, frames)
        # serialize positions to lists for JSON
        positions_serializable = {str(k): list(v) for k, v in positions.items()}
        # attach positions to the sequence record
        seq['positions'] = positions_serializable
        all_seq_positions.append({
            'sequence_id': seq.get('sequence_id'),
            'team_id': seq.get('team_id'),
            'frames': frames,
            'positions': positions_serializable,
        })

    # write aggregate positions file
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(positions_output_file, 'w', encoding='utf-8') as fh:
        json.dump({'sequences': all_seq_positions}, fh, indent=2)
    print(f'Saved positions for {len(all_seq_positions)} sequences to {positions_output_file}')
else:
    print('Tracking file not found; skipping positions extraction:', tracking_local)
