# run_video_from_positions.py
import json
import argparse
from pathlib import Path
from extract_and_plot_ball_positions import save_trajectory_video

def load_sequence_positions(file_path, seq_id):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # case: top-level dict with "sequences" list
    seqs = None
    if isinstance(data, dict) and 'sequences' in data:
        seqs = data['sequences']
    elif isinstance(data, list):
        seqs = data
    else:
        # maybe mapping sequence_id -> positions
        key = str(seq_id)
        if key in data:
            return {int(k): tuple(v) for k, v in data[key].items()}
        raise ValueError('Unrecognized JSON structure')

    # find matching sequence
    for s in seqs:
        for k in ('sequence_id','id','uid','sequenceId'):
            if k in s and str(s[k]) == str(seq_id):
                # prefer a 'positions' mapping if present
                if 'positions' in s:
                    pos = s['positions']
                    if isinstance(pos, dict):
                        return {int(k): tuple(v) for k, v in pos.items()}
                # else if frames+positions present
                if 'frames' in s and 'positions' in s:
                    frames = s['frames']
                    poss = s['positions']
                    # assume poss is dict-like or list-like matching frames
                    if isinstance(poss, dict):
                        return {int(k): tuple(v) for k, v in poss.items()}
                    elif isinstance(poss, list) and len(poss) == len(frames):
                        return {int(fr): tuple(poss[i]) for i, fr in enumerate(frames)}
                # fallback: maybe events list with x,y
                if 'events' in s:
                    out = {}
                    for ev in s['events']:
                        fr = ev.get('frame_start') or ev.get('frame')
                        bx = ev.get('ball_x') or ev.get('x')
                        by = ev.get('ball_y') or ev.get('y')
                        if fr is not None and bx is not None and by is not None:
                            out[int(fr)] = (float(bx), float(by), None)
                    if out:
                        return out
    raise ValueError(f'Sequence {seq_id} not found or has no usable positions')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--positions-file', required=True, help='Path to positions JSON')
    p.add_argument('--sequence-id', type=int, required=True, help='Sequence id to render')
    p.add_argument('--video-out', default='output_videos/sequence_{id}.mp4', help='Output mp4 path')
    p.add_argument('--fps', type=float, default=10.0)
    args = p.parse_args()

    pos_file = Path(args.positions_file)
    if not pos_file.exists():
        raise SystemExit(f'Positions file not found: {pos_file}')

    positions = load_sequence_positions(str(pos_file), args.sequence_id)
    out_path = args.video_out.format(id=args.sequence_id) if '{id}' in args.video_out else args.video_out
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    save_trajectory_video(positions, args.sequence_id, out_path, fps=args.fps)
    print('Wrote video to', out_path)

if __name__ == '__main__':
    main()