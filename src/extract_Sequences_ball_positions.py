import json
import argparse
import os
from pathlib import Path


def load_sequences(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # handle wrapper keys
    if isinstance(data, dict):
        for k in ('sequences', 'items'):
            if k in data and isinstance(data[k], list):
                return data[k]
        # maybe it's a dict of sequences
        return data.get('sequences', []) or []
    return data


def find_sequence_by_id(sequences, seq_id):
    for s in sequences:
        if not isinstance(s, dict):
            continue
        # try common id keys
        for k in ('sequence_id', 'id', 'uid', 'sequenceId'):
            if k in s:
                try:
                    if int(s[k]) == int(seq_id):
                        return s
                except Exception:
                    pass
    # fallback: if seq_id can be used as index
    try:
        idx = int(seq_id)
        if 0 <= idx < len(sequences):
            return sequences[idx]
    except Exception:
        pass
    return None


def _get_int_from_event_field(event, keys):
    for k in keys:
        if k in event and event[k] is not None:
            try:
                return int(event[k])
            except Exception:
                try:
                    return int(float(event[k]))
                except Exception:
                    return None
    return None


def extract_frame_numbers_from_sequence(sequence):
    """Return sorted unique frame numbers: all event start frames, and
    additionally the last event's end frame if present.
    """
    if not sequence or 'events' not in sequence or not isinstance(sequence['events'], list):
        return []

    starts = []
    events = sequence['events']
    for ev in events:
        if isinstance(ev, dict):
            start = _get_int_from_event_field(ev, ('frame_start', 'start_frame', 'start', 'frame'))
        elif isinstance(ev, (list, tuple)) and len(ev) > 0:
            try:
                start = int(ev[0])
            except Exception:
                start = None
        else:
            start = None

        if start is not None:
            starts.append(start)

    # last event end
    last_end = None
    if len(events) > 0:
        last = events[-1]
        if isinstance(last, dict):
            last_end = _get_int_from_event_field(last, ('frame_end', 'end_frame', 'end'))
        elif isinstance(last, (list, tuple)) and len(last) > 1:
            try:
                last_end = int(last[1])
            except Exception:
                last_end = None

    frames = set(starts)
    if last_end is not None:
        frames.add(last_end)

    return sorted(frames)


def load_tracking_positions(tracking_path, wanted_frames):
    """Read JSONL tracking file from URL or local path and return dict frame->(x,y,z) for wanted_frames."""
    import pandas as pd
    results = {}
    wanted = set(wanted_frames)
    found = set()

    # Check if tracking_path is a URL
    if isinstance(tracking_path, str) and (tracking_path.startswith('http://') or tracking_path.startswith('https://')):
        # Fetch from URL using pandas
        try:
            print(f"  Fetching tracking data from URL...")
            raw_data = pd.read_json(tracking_path, lines=True)
        except Exception as e:
            print(f"  Error fetching tracking data from URL: {e}")
            # Mark all wanted frames as missing
            for f in wanted:
                results[f] = (None, None, None)
            return results
        
        # Process the DataFrame
        for _, obj in raw_data.iterrows():
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
            found.add(frame)
            
            if found == wanted:
                break
    
    else:
        # Read from local file
        with open(tracking_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue

                # Determine frame index
                frame = None
                for k in ('frame', 'frame_idx', 'frame_index'):
                    if k in obj:
                        try:
                            frame = int(obj[k])
                        except Exception:
                            try:
                                frame = int(float(obj[k]))
                            except Exception:
                                frame = None
                        break

                if frame is None:
                    continue

                if frame not in wanted:
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
                found.add(frame)

                if found == wanted:
                    break

    # Mark missing frames explicitly
    for f in wanted:
        if f not in results:
            results[f] = (None, None, None)

    return results


def save_positions(out_path, positions):
    outp = Path(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with open(outp, 'w', encoding='utf-8') as f:
        json.dump(positions, f, indent=2)








def process_all_sequences(sequences, tracking_path, output_file):
    """Extract ball positions for all sequences and save to a single aggregate file."""
    
    print(f"\nProcessing {len(sequences)} sequences...")
    
    all_sequence_data = []
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
            print(f"  Warning: Sequence {idx} has no ID, skipping")
            fail_count += 1
            continue
        
        # Extract frames
        frames = extract_frame_numbers_from_sequence(seq)
        if len(frames) == 0:
            print(f"  Warning: Sequence {seq_id} has no frames, skipping")
            fail_count += 1
            continue
        
        # Load positions
        positions = load_tracking_positions(tracking_path, frames)
        
        # Convert to serializable format
        positions_serializable = {
            str(k): list(v) for k, v in positions.items()
        }
        
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
        all_sequence_data.append(seq_out)
        
        success_count += 1
        
        if (idx + 1) % 10 == 0 or idx == len(sequences) - 1:
            print(f"  Processed {idx + 1}/{len(sequences)} sequences")
    
    # Save aggregate file with all sequences
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total_sequences': len(all_sequence_data),
            'sequences': all_sequence_data
        }, f, indent=2)
    
    print(f"\nBatch processing complete!")
    print(f"  Success: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Output file: {output_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sequence-id', type=int, default=None,
                   help='Process a single sequence ID')
    p.add_argument('--all', action='store_true',
                   help='Process all sequences in batch mode')
    p.add_argument('--sequences', default='output_json/sequences_excluding_offball_onball.json')
    p.add_argument('--tracking', default='data/1886347_tracking_extrapolated.jsonl')
    p.add_argument('--positions-out', default='output_json/extracted_positions.json')
    p.add_argument('--batch-output', default='output_json/all_sequences_positions.json',
                   help='Output file for batch mode')
    args = p.parse_args()

    seq_path = Path(args.sequences)
    tracking_path = Path(args.tracking)

    print('Reading sequences from:', seq_path)
    if not seq_path.exists():
        print('Sequences file not found:', seq_path)
        return
    print('Reading tracking from:', tracking_path)
    if not tracking_path.exists():
        print('Tracking file not found:', tracking_path)
        return

    sequences = load_sequences(seq_path)

    # Batch mode
    if args.all:
        process_all_sequences(sequences, tracking_path, args.batch_output)
        return

    # Single sequence mode
    if args.sequence_id is None:
        print("Error: Must specify either --sequence-id <ID> or --all")
        return

    seq = find_sequence_by_id(sequences, args.sequence_id)
    if seq is None:
        print('Sequence id not found:', args.sequence_id)
        return

    frames = extract_frame_numbers_from_sequence(seq)
    print('Extracted frames to query:', frames)

    positions = load_tracking_positions(tracking_path, frames)

    # print results
    printable = {str(k): positions[k] for k in sorted(positions.keys())}
    print('Frame -> (x,y,z):')
    for k in sorted(positions.keys()):
        print(k, '->', positions[k])

    # save positions
    out_pos = Path(args.positions_out)
    out_pos.parent.mkdir(parents=True, exist_ok=True)
    save_positions(out_pos, printable)
    print('Saved extracted positions to', out_pos)


if __name__ == '__main__':
    main()