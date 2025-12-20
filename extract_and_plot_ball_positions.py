import json
import argparse
import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import cv2
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas


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
    """Read JSONL tracking file and return dict frame->(x,y,z) for wanted_frames."""
    results = {}
    wanted = set(wanted_frames)
    found = set()
    with open(tracking_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue

            # determine frame index
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

            # extract ball positions
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
            # normalize numeric types
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

    # mark missing frames explicitly
    for f in wanted:
        if f not in results:
            results[f] = (None, None, None)

    return results


def save_positions(out_path, positions):
    outp = Path(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with open(outp, 'w', encoding='utf-8') as f:
        json.dump(positions, f, indent=2)


def plot_trajectory(positions_dict, sequence_id, out_png=None, show_plot=False):
    # positions_dict: {frame: (x,y,z)}
    frames = sorted(positions_dict.keys())
    xs = []
    ys = []
    labels = []
    for fr in frames:
        x, y, z = positions_dict[fr]
        if x is None or y is None:
            continue
        xs.append(x)
        ys.append(y)
        labels.append(fr)

    if len(xs) == 0:
        print('No valid (x,y) positions to plot for sequence', sequence_id)
        return None

    plt.figure(figsize=(8, 6))
    plt.plot(xs, ys, '-o', linewidth=2)
    for xi, yi, fr in zip(xs, ys, labels):
        plt.annotate(str(fr), (xi, yi), textcoords="offset points", xytext=(5,5), ha='left')
    plt.title(f'Ball Trajectory for Sequence {sequence_id}')
    plt.xlabel('Ball X')
    plt.ylabel('Ball Y')
    plt.grid(True)
    if out_png:
        plt.savefig(out_png, dpi=200, bbox_inches='tight')
        print('Saved plot to', out_png)
    if show_plot:
        plt.show()
    plt.close()


def fig_to_bgr_image(fig, dpi=100):
    canvas = FigureCanvas(fig)
    canvas.draw()
    # Get the RGBA buffer from the canvas
    buf = np.frombuffer(canvas.buffer_rgba(), dtype=np.uint8)
    w, h = fig.canvas.get_width_height()
    img = buf.reshape((h, w, 4))
    # RGBA -> BGR (drop alpha channel and convert)
    bgr = cv2.cvtColor(img[:, :, :3], cv2.COLOR_RGB2BGR)
    return bgr


def save_trajectory_video(positions_dict, sequence_id, video_out, fps=2, figsize=(10,7), dpi=100):
    # Build ordered list of frames
    # Ensure output directory exists
    if video_out is not None:
        Path(video_out).parent.mkdir(parents=True, exist_ok=True)

    frames = sorted(positions_dict.keys())

    # collect valid points (x,y present)
    valid = [(f, positions_dict[f]) for f in frames if positions_dict[f][0] is not None and positions_dict[f][1] is not None]
    if len(valid) == 0:
        print('No valid points to write video for sequence', sequence_id)
        return

    # standard pitch sizes (centered coordinate system)
    PITCH_LENGTH = 105.0
    PITCH_WIDTH = 68.0

    xs_all = [p[0] for _, p in valid]
    ys_all = [p[1] for _, p in valid]

    # Detect coordinate system
    # Check if centered around (0,0)
    if (min(xs_all) >= -PITCH_LENGTH/2 - 5 and max(xs_all) <= PITCH_LENGTH/2 + 5 and 
        min(ys_all) >= -PITCH_WIDTH/2 - 5 and max(ys_all) <= PITCH_WIDTH/2 + 5):
        # Centered coordinate system
        x_min, x_max = -PITCH_LENGTH/2, PITCH_LENGTH/2
        y_min, y_max = -PITCH_WIDTH/2, PITCH_WIDTH/2
        centered = True
        print(f"Detected centered coordinate system: x=[{x_min}, {x_max}], y=[{y_min}, {y_max}]")
    elif (min(xs_all) >= 0 and max(xs_all) <= PITCH_LENGTH and 
          min(ys_all) >= 0 and max(ys_all) <= PITCH_WIDTH):
        # Standard coordinate system
        x_min, x_max = 0.0, PITCH_LENGTH
        y_min, y_max = 0.0, PITCH_WIDTH
        centered = False
        print(f"Detected standard coordinate system: x=[{x_min}, {x_max}], y=[{y_min}, {y_max}]")
    else:
        # Custom range - use data bounds with padding
        x_min, x_max = min(xs_all), max(xs_all)
        y_min, y_max = min(ys_all), max(ys_all)
        x_pad = (x_max - x_min) * 0.15 if x_max > x_min else 5.0
        y_pad = (y_max - y_min) * 0.15 if y_max > y_min else 5.0
        x_min -= x_pad
        x_max += x_pad
        y_min -= y_pad
        y_max += y_pad
        centered = False
        print(f"Using custom coordinate system: x=[{x_min:.2f}, {x_max:.2f}], y=[{y_min:.2f}, {y_max:.2f}]")

    # prepare matplotlib figure
    fig = plt.figure(figsize=figsize, dpi=dpi)
    ax = fig.add_subplot(111)
    pitch_color = '#195905'  # Dark green
    line_color = 'white'
    fig.patch.set_facecolor(pitch_color)
    ax.set_facecolor(pitch_color)

    # Dynamic pitch drawing function
    def draw_pitch(ax, centered_mode):
        if centered_mode:
            # Draw pitch for centered coordinates
            # Outer rectangle
            rect = plt.Rectangle(
                (-PITCH_LENGTH/2, -PITCH_WIDTH/2), 
                PITCH_LENGTH, 
                PITCH_WIDTH, 
                fill=False, 
                edgecolor=line_color, 
                linewidth=2
            )
            ax.add_patch(rect)
            
            # Halfway line
            ax.plot([0, 0], [-PITCH_WIDTH/2, PITCH_WIDTH/2], color=line_color, linewidth=2)
            
            # Center circle
            circle = plt.Circle((0, 0), 9.15, fill=False, edgecolor=line_color, linewidth=2)
            ax.add_patch(circle)
            
            # Center spot
            ax.scatter([0], [0], c=line_color, s=30, zorder=3)
            
        else:
            # Draw pitch for standard coordinates (0 to 105, 0 to 68)
            # Outer rectangle
            rect = plt.Rectangle(
                (0, 0), 
                PITCH_LENGTH, 
                PITCH_WIDTH, 
                fill=False, 
                edgecolor=line_color, 
                linewidth=2
            )
            ax.add_patch(rect)
            
            # Halfway line
            ax.plot([PITCH_LENGTH/2, PITCH_LENGTH/2], [0, PITCH_WIDTH], color=line_color, linewidth=2)
            
            # Center circle
            circle = plt.Circle((PITCH_LENGTH/2, PITCH_WIDTH/2), 9.15, fill=False, edgecolor=line_color, linewidth=2)
            ax.add_patch(circle)
            
            # Center spot
            ax.scatter([PITCH_LENGTH/2], [PITCH_WIDTH/2], c=line_color, s=30, zorder=3)

    # Set up axes
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect('equal', adjustable='box')
    # DO NOT invert y-axis: positive y is top of pitch per coordinate system definition
    ax.tick_params(left=False, right=False, labelleft=False, labelbottom=False, bottom=False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Render one frame to get dimensions
    draw_pitch(ax, centered)
    canvas_img = fig_to_bgr_image(fig, dpi=dpi)
    h, w = canvas_img.shape[:2]
    
    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(video_out, fourcc, float(fps), (w, h))

    # Precompute all positions
    mapped = [positions_dict[f] for f in frames]

    print(f"Rendering {len(frames)} frames to video...")
    
    # Render each frame
    for i, fr in enumerate(frames):
        ax.cla()
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_aspect('equal', adjustable='box')
        # DO NOT invert y-axis: positive y is top of pitch per coordinate system definition
        ax.set_facecolor(pitch_color)
        ax.tick_params(left=False, right=False, labelleft=False, labelbottom=False, bottom=False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        # Draw pitch
        draw_pitch(ax, centered)

        # Draw trajectory trail up to current frame
        trail_x = []
        trail_y = []
        for j in range(0, i+1):
            x, y, z = mapped[j]
            if x is None or y is None:
                continue
            trail_x.append(x)
            trail_y.append(y)
        
        if len(trail_x) > 1:
            ax.plot(trail_x, trail_y, '-', color='#FFD700', linewidth=3, zorder=5, alpha=0.8)
        
        if len(trail_x) > 0:
            ax.scatter(trail_x[:-1], trail_y[:-1], c='white', s=40, zorder=6, 
                      edgecolors='black', linewidths=1)

        # Highlight current ball position
        bx, by, bz = positions_dict[fr]
        if bx is not None and by is not None:
            ax.scatter([bx], [by], c='#FF4444', s=300, edgecolors='white', 
                      linewidths=2, zorder=10)

        ax.set_title(f'Sequence {sequence_id} - Frame {fr}', 
                    color='white', fontsize=14, fontweight='bold', pad=10)

        # Render to image and write
        img = fig_to_bgr_image(fig, dpi=dpi)
        writer.write(img)
        
        if (i + 1) % 10 == 0 or i == len(frames) - 1:
            print(f"  Rendered {i+1}/{len(frames)} frames")

    writer.release()
    plt.close(fig)
    print(f'Saved video to {video_out}')


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
        all_sequence_data.append({
            'sequence_id': seq_id,
            'team_id': seq.get('team_id'),
            'frames': frames,
            'positions': positions_serializable
        })
        
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
    p.add_argument('--plot-out', default='output_videos/trajectory.png')
    p.add_argument('--show', action='store_true')
    p.add_argument('--video-out', default='output_videos/trajectory.mp4', help='Write trajectory video (mp4)')
    p.add_argument('--video-fps', type=float, default=10.0, help='FPS for output video')
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

    # plot
    out_plot = Path(args.plot_out)
    out_plot.parent.mkdir(parents=True, exist_ok=True)
    plot_trajectory(positions, args.sequence_id, out_png=str(out_plot), show_plot=args.show)

    if args.video_out:
        video_path = Path(args.video_out if isinstance(args.video_out, str) else args.video_out)
        video_path.parent.mkdir(parents=True, exist_ok=True)
        save_trajectory_video(positions, args.sequence_id, str(video_path), fps=args.video_fps)


if __name__ == '__main__':
    main()