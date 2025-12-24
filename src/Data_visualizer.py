import json
import argparse
import pandas as pd
from pathlib import Path
from matplotlib.animation import FuncAnimation, FFMpegWriter
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def load_match_metadata(match_id, metadata_dir):
    """Load match metadata to get team information"""
    metadata_file = Path(metadata_dir) / f"{match_id}_match.json"
    
    if not metadata_file.exists():
        print(f"Warning: Metadata file not found: {metadata_file}")
        return None, None
    
    print(f"Loading metadata from: {metadata_file}")
    
    with open(metadata_file, 'r', encoding='utf-8') as f:
        raw_match_data = json.load(f)
    
    raw_match_df = pd.json_normalize(raw_match_data, max_level=2)
    
    players_df = pd.json_normalize(
        raw_match_df.to_dict("records"),
        record_path="players",
        meta=[
            "home_team.name",
            "home_team.id",
            "away_team.name",
            "away_team.id",
        ]
    )
    
    players_metadata = players_df[['id', 'team_id', 'short_name', 'number']].copy()
    players_metadata.rename(columns={'id': 'player_id'}, inplace=True)
    
    metadata_dict = {
        'home_team_id': raw_match_df['home_team.id'].iloc[0] if not raw_match_df.empty else None,
        'away_team_id': raw_match_df['away_team.id'].iloc[0] if not raw_match_df.empty else None,
        'home_team_name': raw_match_df['home_team.name'].iloc[0] if not raw_match_df.empty else 'Home',
        'away_team_name': raw_match_df['away_team.name'].iloc[0] if not raw_match_df.empty else 'Away'
    }
    
    print(f"Home Team: {metadata_dict['home_team_name']} (ID: {metadata_dict['home_team_id']})")
    print(f"Away Team: {metadata_dict['away_team_name']} (ID: {metadata_dict['away_team_id']})")
    
    return metadata_dict, players_metadata

def load_sequence_data(match_id, sequence_id, sequences_dir):
    """Load sequence data and extract frame range"""
    seq_file = Path(sequences_dir) / f"{match_id}_sequences_excluding_offball_onball.json"
    
    if not seq_file.exists():
        seq_file = Path(sequences_dir) / f"{match_id}_sequences.json"
    
    if not seq_file.exists():
        raise FileNotFoundError(f"Sequences file not found for match {match_id} in {sequences_dir}")
    
    print(f"Loading sequences from: {seq_file}")
    
    with open(seq_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict) and 'sequences' in data:
        sequences = data['sequences']
    elif isinstance(data, list):
        sequences = data
    else:
        raise ValueError('Unrecognized JSON structure')
    
    target_seq = None
    for seq in sequences:
        if seq.get('sequence_id') == sequence_id:
            target_seq = seq
            break
    
    if target_seq is None:
        raise ValueError(f'Sequence {sequence_id} not found in match {match_id}')
    
    events = target_seq.get('events', [])
    if not events:
        raise ValueError(f'No events found in sequence {sequence_id}')
    
    first_event = events[0]
    last_event = events[-1]
    
    min_frame = first_event['frame_start']
    max_frame = last_event['frame_end']
    
    print(f"Sequence {sequence_id}: frames {min_frame} to {max_frame} ({len(events)} events)")
    print(f"  First event: {first_event.get('event_id', 'unknown')} at frame {min_frame}")
    print(f"  Last event: {last_event.get('event_id', 'unknown')} at frame {max_frame}")
    
    return target_seq, min_frame, max_frame

def load_tracking_data(match_id, tracking_dir, min_frame, max_frame):
    """Load tracking data for specified frame range"""
    tracking_file = Path(tracking_dir) / f"{match_id}_tracking_extrapolated.jsonl"
    
    if not tracking_file.exists():
        raise FileNotFoundError(f"Tracking file not found: {tracking_file}")
    
    print(f"Loading tracking data from: {tracking_file}")
    print(f"Looking for frames between {min_frame} and {max_frame}")
    
    data = []
    with open(tracking_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                row = json.loads(line)
                frame = row.get('frame')
                
                if frame is not None and min_frame <= frame <= max_frame:
                    data.append(row)
            except json.JSONDecodeError:
                continue
    
    print(f"Loaded {len(data)} tracking frames")
    return data

def process_tracking_data(tracking_data, metadata, players_metadata):
    """Process tracking data into pandas DataFrame with team assignments"""
    rows = []
    
    for frame_data in tracking_data:
        frame = frame_data.get('frame')
        if frame is None:
            continue
        
        ball_data = frame_data.get('ball_data', {})
        # Use ball coordinates if available, regardless of is_detected flag
        ball_x = ball_data.get('x')
        ball_y = ball_data.get('y')
        ball_z = ball_data.get('z')
        is_detected_ball = ball_data.get('is_detected', False)
        
        player_data = frame_data.get('player_data', [])
        for player in player_data:
            if 'x' in player and 'y' in player:
                row = {
                    'frame': frame,
                    'x': player['x'],
                    'y': player['y'],
                    'player_id': player.get('player_id'),
                    'is_detected': player.get('is_detected', True),
                    'ball_x': ball_x,
                    'ball_y': ball_y,
                    'ball_z': ball_z,
                    'is_detected_ball': is_detected_ball
                }
                rows.append(row)
    
    if not rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(rows)
    
    if players_metadata is not None:
        df = df.merge(players_metadata, on='player_id', how='left')
    
    return df

def draw_pitch(ax, pitch_length=105, pitch_width=68):
    """
    Draw a football pitch using matplotlib.
    Coordinate system: Origin (0,0) at center
    X-axis: -52.5 to +52.5 (left to right)
    Y-axis: -34 to +34 (bottom to top)
    All units in meters.
    """
    # Set the pitch color
    ax.set_facecolor('#001400')
    
    # Calculate half dimensions
    half_length = pitch_length / 2
    half_width = pitch_width / 2
    
    # Pitch outline
    pitch_outline = patches.Rectangle(
        (-half_length, -half_width), pitch_length, pitch_width,
        linewidth=1.5, edgecolor='white', facecolor='none'
    )
    ax.add_patch(pitch_outline)
    
    # Center line
    ax.plot([0, 0], [-half_width, half_width], color='white', linewidth=1.5)
    
    # Center circle
    center_circle = patches.Circle((0, 0), 9.15, linewidth=1.5, edgecolor='white', facecolor='none')
    ax.add_patch(center_circle)
    
    # Center spot
    center_spot = patches.Circle((0, 0), 0.3, color='white')
    ax.add_patch(center_spot)
    
    # Penalty areas (16.5m from goal line, 40.3m wide)
    penalty_area_length = 16.5
    penalty_area_width = 40.3
    
    # Left penalty area
    left_penalty = patches.Rectangle(
        (-half_length, -penalty_area_width/2), penalty_area_length, penalty_area_width,
        linewidth=1.5, edgecolor='white', facecolor='none'
    )
    ax.add_patch(left_penalty)
    
    # Right penalty area
    right_penalty = patches.Rectangle(
        (half_length - penalty_area_length, -penalty_area_width/2), penalty_area_length, penalty_area_width,
        linewidth=1.5, edgecolor='white', facecolor='none'
    )
    ax.add_patch(right_penalty)
    
    # Goal areas (5.5m from goal line, 18.3m wide)
    goal_area_length = 5.5
    goal_area_width = 18.3
    
    # Left goal area
    left_goal_area = patches.Rectangle(
        (-half_length, -goal_area_width/2), goal_area_length, goal_area_width,
        linewidth=1.5, edgecolor='white', facecolor='none'
    )
    ax.add_patch(left_goal_area)
    
    # Right goal area
    right_goal_area = patches.Rectangle(
        (half_length - goal_area_length, -goal_area_width/2), goal_area_length, goal_area_width,
        linewidth=1.5, edgecolor='white', facecolor='none'
    )
    ax.add_patch(right_goal_area)
    
    # Penalty spots (11m from goal line)
    left_penalty_spot = patches.Circle((-half_length + 11, 0), 0.3, color='white')
    right_penalty_spot = patches.Circle((half_length - 11, 0), 0.3, color='white')
    ax.add_patch(left_penalty_spot)
    ax.add_patch(right_penalty_spot)
    
    # Penalty arcs (9.15m radius from penalty spot)
    # Left penalty arc
    left_arc = patches.Arc(
        (-half_length + 11, 0), 2*9.15, 2*9.15,
        angle=0, theta1=308, theta2=52,
        linewidth=1.5, edgecolor='white', facecolor='none'
    )
    ax.add_patch(left_arc)
    
    # Right penalty arc
    right_arc = patches.Arc(
        (half_length - 11, 0), 2*9.15, 2*9.15,
        angle=0, theta1=128, theta2=232,
        linewidth=1.5, edgecolor='white', facecolor='none'
    )
    ax.add_patch(right_arc)
    
    # Corner arcs (1m radius)
    corner_radius = 1
    corners = [
        (-half_length, -half_width, 0, 90),
        (-half_length, half_width, 270, 360),
        (half_length, -half_width, 90, 180),
        (half_length, half_width, 180, 270)
    ]
    
    for x, y, theta1, theta2 in corners:
        corner_arc = patches.Arc(
            (x, y), 2*corner_radius, 2*corner_radius,
            angle=0, theta1=theta1, theta2=theta2,
            linewidth=1.5, edgecolor='white', facecolor='none'
        )
        ax.add_patch(corner_arc)
    
    # Set axis limits with some padding
    padding = 2
    ax.set_xlim(-half_length - padding, half_length + padding)
    ax.set_ylim(-half_width - padding, half_width + padding)
    
    # CRITICAL: Ensure Y-axis increases from bottom to top (default matplotlib behavior)
    # This matches the coordinate system specification
    ax.set_aspect('equal')
    ax.axis('off')

def create_animation(match_id, sequence_id, tracking_df, min_frame, max_frame, metadata, output_path, fps=10):
    """Create animation with correct coordinate system using pure matplotlib"""
    frames = sorted(tracking_df['frame'].unique())
    
    if not frames:
        raise ValueError("No frames to animate")
    
    # Coordinate system verification
    print(f"\nCoordinate System:")
    print(f"  Origin: (0, 0) at pitch center")
    print(f"  X-axis: -52.5 to +52.5 meters (left to right)")
    print(f"  Y-axis: -34 to +34 meters (bottom to top)")
    print(f"  Units: meters")
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 8), facecolor='#001400')
    
    # Draw the pitch
    draw_pitch(ax)
    
    # Verify data coordinate ranges
    if not tracking_df.empty:
        print(f"\nData coordinate ranges:")
        print(f"  X: {tracking_df['x'].min():.2f} to {tracking_df['x'].max():.2f} meters")
        print(f"  Y: {tracking_df['y'].min():.2f} to {tracking_df['y'].max():.2f} meters")
        if 'ball_x' in tracking_df.columns:
            ball_data = tracking_df[tracking_df['is_detected_ball'] == True]
            if not ball_data.empty:
                print(f"  Ball X: {ball_data['ball_x'].min():.2f} to {ball_data['ball_x'].max():.2f} meters")
                print(f"  Ball Y: {ball_data['ball_y'].min():.2f} to {ball_data['ball_y'].max():.2f} meters")
    
    # Color map for teams
    team_ids = list(tracking_df['team_id'].dropna().unique()) if 'team_id' in tracking_df.columns else []
    colors_palette = ['#084D42', '#E51717', '#E5BA21', '#32FE6B']
    color_map = {tid: colors_palette[i % len(colors_palette)] for i, tid in enumerate(team_ids)}
    
    player_artists = []
    ball_artist = None
    ball_trail_artist = None
    title_text = None
    
    # Store ball trajectory
    ball_trajectory = []
    
    def update(frame):
        nonlocal player_artists, ball_artist, ball_trail_artist, ball_trajectory, title_text
        
        # Remove previous artists
        for art in player_artists:
            try:
                art.remove()
            except Exception:
                pass
        player_artists = []
        
        if ball_artist is not None:
            try:
                ball_artist.remove()
            except Exception:
                pass
            ball_artist = None
        
        if ball_trail_artist is not None:
            try:
                ball_trail_artist.remove()
            except Exception:
                pass
            ball_trail_artist = None
        
        if title_text is not None:
            try:
                title_text.remove()
            except Exception:
                pass
        
        # Get frame data
        frame_df = tracking_df[tracking_df['frame'] == frame]
        
        if frame_df.empty:
            title_text = ax.text(
                0, 38, f'Match {match_id} — Sequence {sequence_id} — Frame {frame} (no data)',
                ha='center', va='top', fontsize=12, color='white', weight='bold'
            )
            return player_artists
        
        # Plot players by team
        if not frame_df.empty and 'team_id' in frame_df.columns:
            cols = [color_map.get(t, '#999999') for t in frame_df['team_id']]
            
            art = ax.scatter(
                frame_df['x'], frame_df['y'],
                c=cols,
                s=120,
                edgecolors='white',
                linewidths=1,
                zorder=10
            )
            player_artists.append(art)
        elif not frame_df.empty:
            art = ax.scatter(
                frame_df['x'], frame_df['y'],
                c='#084D42',
                s=120,
                edgecolors='white',
                linewidths=1,
                zorder=10
            )
            player_artists.append(art)
        
        # Plot ball and trajectory
        ball_rows = frame_df[frame_df['is_detected_ball'] == True]
        if not ball_rows.empty:
            ball_x = ball_rows['ball_x'].iloc[0]
            ball_y = ball_rows['ball_y'].iloc[0]
            
            if pd.notna(ball_x) and pd.notna(ball_y):
                ball_trajectory.append((ball_x, ball_y))
                
                # Plot trajectory
                if len(ball_trajectory) > 1:
                    traj_x = [pos[0] for pos in ball_trajectory]
                    traj_y = [pos[1] for pos in ball_trajectory]
                    
                    ball_trail_artist, = ax.plot(
                        traj_x, traj_y,
                        color='#32FE6B',
                        linewidth=2,
                        linestyle='-',
                        alpha=0.6,
                        zorder=11
                    )
                
                # Plot current ball position
                ball_artist = ax.scatter(
                    [ball_x], [ball_y],
                    c='#32FE6B',
                    s=220,
                    edgecolors='black',
                    linewidths=1.5,
                    zorder=12
                )
        
        # Add title
        title_text = ax.text(
            0, 38, f'Match {match_id} — Sequence {sequence_id} — Frames {min_frame}-{max_frame} — Frame {frame}',
            ha='center', va='top', fontsize=12, color='white', weight='bold'
        )
        
        artists_to_return = player_artists.copy()
        if ball_trail_artist is not None:
            artists_to_return.append(ball_trail_artist)
        if ball_artist is not None:
            artists_to_return.append(ball_artist)
        if title_text is not None:
            artists_to_return.append(title_text)
        
        return artists_to_return
    
    anim = FuncAnimation(fig, update, frames=frames, interval=100, blit=False)
    
    try:
        writer = FFMpegWriter(fps=fps)
        anim.save(output_path, writer=writer)
        print(f'\n✓ Saved video to {output_path}')
    except Exception as e:
        print(f'\n✗ Could not save MP4. Error: {e}')
        raise
    
    plt.close(fig)

def main():
    p = argparse.ArgumentParser(description='Create video visualization for a match sequence')
    p.add_argument('--match-id', type=int, required=True, help='Match ID')
    p.add_argument('--sequence-id', type=int, required=True, help='Sequence ID to render')
    p.add_argument('--sequences-dir', default=r'D:\college\pysport analytics cup\output_json', 
                   help='Directory containing sequence JSON files')
    p.add_argument('--tracking-dir', default=r'D:\college\pysport analytics cup\Data',
                   help='Directory containing tracking JSONL files')
    p.add_argument('--metadata-dir', default=r'D:\college\pysport analytics cup\Data',
                   help='Directory containing match metadata JSON files')
    p.add_argument('--output-dir', default='output_videos', help='Output directory for videos')
    p.add_argument('--fps', type=int, default=10, help='Frames per second')
    args = p.parse_args()

    print(f"\n{'='*60}")
    print(f"Creating video for Match {args.match_id}, Sequence {args.sequence_id}")
    print(f"{'='*60}\n")

    metadata, players_metadata = load_match_metadata(args.match_id, args.metadata_dir)
    
    sequence, min_frame, max_frame = load_sequence_data(
        args.match_id, args.sequence_id, args.sequences_dir
    )
    
    tracking_data = load_tracking_data(
        args.match_id, args.tracking_dir, min_frame, max_frame
    )
    
    if not tracking_data:
        raise ValueError("No tracking data found for the specified frame range")
    
    print("Processing tracking data...")
    tracking_df = process_tracking_data(tracking_data, metadata, players_metadata)
    print(f"Processed {len(tracking_df)} player records")
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f'match_{args.match_id}_seq_{args.sequence_id}.mp4'
    
    print("\nCreating animation...")
    create_animation(
        args.match_id, args.sequence_id, tracking_df, 
        min_frame, max_frame, metadata, str(output_path), fps=args.fps
    )
    
    print(f"\n{'='*60}")
    print(f"✓ Done! Video saved to: {output_path}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()