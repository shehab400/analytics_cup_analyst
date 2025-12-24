import json
import argparse
import pandas as pd
from pathlib import Path

from src.Data_visualizer import (
    load_match_metadata,
    load_tracking_data,
    process_tracking_data
)

def parse_sequence_identifier(seq_id):
    """
    Parse sequence identifier like '1886347_6' or '1886347_7_subset0'.
    Returns (match_id:int, sequence_id:str).
    Note: output sequence_id includes the subset part if present for matching the CSV.
    """
    parts = seq_id.split('_')
    match_id = int(parts[0])
    # Rejoin the rest to get '6' or '7_subset0'
    sequence_id_str = '_'.join(parts[1:])
    return match_id, sequence_id_str

def load_frames_lookup(csv_path):
    """
    Load the new CSV with start/end frames and create a lookup dictionary.
    Returns: dict { "matchId_sequenceId": {"start": int, "end": int} }
    """
    print(f"Loading Frames CSV from: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Clean column names just in case (strip whitespace)
    df.columns = [c.strip() for c in df.columns]
    
    # Ensure correct column mapping based on your image
    # Image shows: match_id, sequence_, start_frame, end_frame
    # We rename 'sequence_' or similar to 'sequence_id' for consistency
    if 'sequence_' in df.columns:
        df.rename(columns={'sequence_': 'sequence_id'}, inplace=True)
        
    lookup = {}
    for _, row in df.iterrows():
        # Create a unique key: "1886347_7_subset0"
        key = f"{row['match_id']}_{row['sequence_id']}"
        lookup[key] = {
            "start": int(row['start_frame']),
            "end": int(row['end_frame'])
        }
    return lookup

def load_dtw_matrix(csv_path):
    """Load DTW distance matrix from CSV"""
    print(f"Loading DTW matrix from: {csv_path}")
    df = pd.read_csv(csv_path, index_col=0)
    return df

def extract_sequence_frames(tracking_df, metadata):
    """
    Extract frame data in unified format where each frame contains:
    - time: timestamp (seconds)
    - ball: ball position (x, y, z) or null
    - homePlayers: array of home team player positions
    - awayPlayers: array of away team player positions
    
    All objects in the same frame share the same timestamp.
    """
    frames = []
    
    # Debug: Print DataFrame info
    print(f"  DEBUG: tracking_df shape = {tracking_df.shape}")
    print(f"  DEBUG: tracking_df columns = {list(tracking_df.columns)}")
    if len(tracking_df) > 0:
        print(f"  DEBUG: First row:\n{tracking_df.iloc[0]}")
    
    # Get unique frames sorted
    unique_frames = sorted(tracking_df['frame'].unique())
    if not unique_frames:
        print("  WARNING: No frames found in tracking_df")
        return frames
    
    print(f"  Extracting {len(unique_frames)} frames...")
    
    # Calculate time based on frame numbers (assuming 10 fps)
    fps = 10
    start_frame = unique_frames[0]

    # Build player_id to team_id mapping from metadata (including substitutes)
    home_player_ids = set()
    away_player_ids = set()
    home_team_id = None
    away_team_id = None
    
    if metadata:
        home_team_id = metadata.get('home_team_id')
        away_team_id = metadata.get('away_team_id')
        
        if 'players_metadata' in metadata:
            players_metadata = metadata['players_metadata']
            if isinstance(players_metadata, pd.DataFrame):
                home_player_ids = set(players_metadata[players_metadata['team_id'] == home_team_id]['player_id'].unique())
                away_player_ids = set(players_metadata[players_metadata['team_id'] == away_team_id]['player_id'].unique())
    
    # Fallback: build from tracking_df if metadata players not available
    if not home_player_ids or not away_player_ids:
        if 'player_id' in tracking_df.columns and 'team_id' in tracking_df.columns:
            all_player_team_map = tracking_df[['player_id', 'team_id']].drop_duplicates()
            for _, row in all_player_team_map.iterrows():
                player_id = row['player_id']
                team_id = row['team_id']
                if pd.notna(player_id) and pd.notna(team_id):
                    if team_id == home_team_id:
                        home_player_ids.add(player_id)
                    elif team_id == away_team_id:
                        away_player_ids.add(player_id)

    print(f"  Home player IDs: {len(home_player_ids)} | Away player IDs: {len(away_player_ids)}")
    if len(home_player_ids) > 0:
        print(f"    Sample home players: {list(home_player_ids)[:3]}")
    if len(away_player_ids) > 0:
        print(f"    Sample away players: {list(away_player_ids)[:3]}")

    # Extract frames with unified structure
    for frame_idx, frame_num in enumerate(unique_frames):
        frame_df = tracking_df[tracking_df['frame'] == frame_num]
        time_offset = (frame_num - start_frame) / fps
        
        # Extract ball position (take from first row, it's the same for all rows in frame)
        ball_data = None
        if len(frame_df) > 0:
            first_row = frame_df.iloc[0]
            ball_x = first_row.get('ball_x')
            ball_y = first_row.get('ball_y')
            ball_z = first_row.get('ball_z')
            
            if pd.notna(ball_x) and pd.notna(ball_y):
                ball_data = {
                    "x": round(float(ball_x), 2),
                    "y": round(float(ball_y), 2),
                    "z": round(float(ball_z), 2) if pd.notna(ball_z) else 0.5
                }
        
        # Extract players by team
        # Each row in frame_df is a player (not a ball row)
        home_players = []
        away_players = []
        
        for _, row in frame_df.iterrows():
            player_id = row.get('player_id')
            
            # Skip rows without player_id
            if pd.isna(player_id):
                continue
            
            # Get position
            x_val = row.get('x')
            y_val = row.get('y')
            
            if pd.isna(x_val) or pd.isna(y_val):
                continue
            
            player_pos = {
                "x": round(float(x_val), 2),
                "y": round(float(y_val), 2),
                "playerId": str(int(player_id))
            }
            
            # Add jersey number if available
            jersey_col = None
            if 'jersey_number' in row and pd.notna(row['jersey_number']):
                jersey_col = 'jersey_number'
            elif 'number' in row and pd.notna(row['number']):
                jersey_col = 'number'
            
            if jersey_col:
                try:
                    player_pos["jerseyNum"] = str(int(row[jersey_col]))
                except (ValueError, TypeError):
                    pass
            
            # Assign to home or away based on player_id
            if player_id in home_player_ids:
                home_players.append(player_pos)
            elif player_id in away_player_ids:
                away_players.append(player_pos)
            # else: unknown player, skip
        
        # Create unified frame structure (always include all fields)
        frame_data = {
            "time": round(time_offset, 3),
            "ball": ball_data,
            "homePlayers": home_players,
            "awayPlayers": away_players
        }
        
        frames.append(frame_data)
        
        # Debug first few frames
        if frame_idx < 3:
            print(f"    Frame {frame_idx}: time={frame_data['time']}, ball={ball_data is not None}, home={len(home_players)}, away={len(away_players)}")
    
    print(f"  Extracted {len(frames)} frames")
    return frames

def generate_play_data(match_id, sequence_id, start_frame, end_frame, tracking_dir, metadata_dir, is_target=True, dtw_distance=None, external_id=None):
    """
    Generate play data using explicit start and end frames from the new CSV.
    Removes the logic for subsets and event slicing since frames are provided.
    """
    try:
        # Load metadata
        metadata, players_metadata = load_match_metadata(match_id, metadata_dir)
        # Attach players_metadata to metadata for downstream use
        if metadata is not None and players_metadata is not None:
            metadata['players_metadata'] = players_metadata
        
        # Load tracking data directly for the specific frame range
        tracking_data = load_tracking_data(match_id, tracking_dir, start_frame, end_frame)
        
        if not tracking_data:
            print(f"Warning: No tracking data for match {match_id}, sequence {sequence_id} (Frames {start_frame}-{end_frame})")
            return None
        
        # Process tracking data
        tracking_df = process_tracking_data(tracking_data, metadata, players_metadata)
        
        if tracking_df.empty:
            print(f"Warning: Empty tracking dataframe for match {match_id}, sequence {sequence_id}")
            return None
        
        # Extract frames
        frames = extract_sequence_frames(tracking_df, metadata)
        
        # Calculate duration
        duration = round((end_frame - start_frame) / 10.0, 1)  # Assuming 10 fps
        
        play_data = {
            "id": "target" if is_target else (external_id if external_id is not None else f"{match_id}_{sequence_id}"),
            "matchId": str(match_id),
            "sequenceId": str(sequence_id),
            "frames": frames,
            "duration": duration
        }

        if not is_target and dtw_distance is not None:
            play_data["dtwScore"] = float(dtw_distance)
        
        return play_data
        
    except Exception as e:
        print(f"Error processing match {match_id}, sequence {sequence_id}: {e}")
        return None

def process_match_sequences(target_match_id, dtw_matrix, frames_lookup, tracking_dir, metadata_dir, output_dir, top_n=5):
    """Process all sequences for a target match using the frames CSV lookup"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get all sequences for this match from DTW matrix columns
    # We expect columns to be named like "1886347_6" or "1886347_7_subset0"
    target_sequences = [col for col in dtw_matrix.columns if col.startswith(f"{target_match_id}_")]
    
    print(f"\nFound {len(target_sequences)} sequences for match {target_match_id}")
    
    for target_full_id in target_sequences:
        try:
            match_id, sequence_id = parse_sequence_identifier(target_full_id)
            
            # Lookup start/end frames from the loaded CSV map
            if target_full_id not in frames_lookup:
                print(f"Skipping {target_full_id} - Not found in Frames CSV")
                continue

            target_frames = frames_lookup[target_full_id]
            print(f"\nProcessing {target_full_id} (Frames: {target_frames['start']}-{target_frames['end']})...")
            
            # Generate target play data
            target_play = generate_play_data(
                match_id, sequence_id, 
                target_frames['start'], target_frames['end'],
                tracking_dir, metadata_dir, 
                is_target=True
            )
            
            if not target_play:
                continue
            
            # Get DTW distances for this sequence
            similar_plays = []
            
            if target_full_id in dtw_matrix.index:
                distances = dtw_matrix.loc[target_full_id].sort_values()
                distances = distances[distances > 0] # Remove self
                
                # Get top N similar plays
                top_similar_ids = distances.head(top_n).index.tolist()
                top_distances = distances.head(top_n).values.tolist()
                
                for similar_full_id, distance in zip(top_similar_ids, top_distances):
                    # Check if similar play exists in our frames CSV
                    if similar_full_id not in frames_lookup:
                        print(f"  Skipping similar play {similar_full_id} - missing frame data")
                        continue

                    sim_match_id, sim_seq_id = parse_sequence_identifier(similar_full_id)
                    sim_frames = frames_lookup[similar_full_id]

                    print(f"  Loading similar play: {similar_full_id} (Frames: {sim_frames['start']}-{sim_frames['end']}, dist: {distance:.4f})")

                    similar_play = generate_play_data(
                        sim_match_id, sim_seq_id,
                        sim_frames['start'], sim_frames['end'],
                        tracking_dir, metadata_dir,
                        is_target=False, dtw_distance=distance, external_id=similar_full_id
                    )
                    
                    if similar_play:
                        similar_plays.append(similar_play)
            
            # Create final output
            output_data = {
                "targetPlay": target_play,
                "similarPlays": similar_plays
            }
            
            # Save to JSON file
            output_filename = f"{target_full_id}.json"
            output_file = output_path / output_filename
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"  Saved: {output_file}")
            print(f"  Found {len(similar_plays)} similar plays")
                
        except Exception as e:
            print(f"Error processing sequence {target_full_id}: {e}")
            import traceback
            traceback.print_exc()
            continue

def main():
    parser = argparse.ArgumentParser(description='Generate similar plays JSON from DTW matrix and Frames CSV')
    parser.add_argument('--match-id', type=int, required=True, help='Target match ID')
    parser.add_argument('--dtw-csv', default=r'D:\college\pysport analytics cup\output_json\extracted_sequences\dtw_distance_matrix_10_positions_normalized.csv', help='Path to DTW distance matrix CSV')
    # ADDED: New argument for the frames CSV
    parser.add_argument('--frames-csv', default=rf'D:\college\pysport analytics cup\output_json\extracted_sequences\all_matches_10_frame_ranges.csv', help='Path to CSV containing start_frame and end_frame columns')
    
    parser.add_argument('--tracking-dir', default=r'D:\college\pysport analytics cup\Data',
                        help='Directory containing tracking JSONL files')
    parser.add_argument('--metadata-dir', default=r'D:\college\pysport analytics cup\Data',
                        help='Directory containing match metadata JSON files')
    parser.add_argument('--top-n', type=int, default=5,
                        help='Number of top similar plays to include')
    
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print(f"Generating Similar Plays JSON for Match {args.match_id}")
    print(f"{'='*80}\n")
    
    # Output directory
    output_dir = Path(rf'D:\college\pysport analytics cup\website\public\{args.match_id}')
    
    # Load Data
    dtw_matrix = load_dtw_matrix(args.dtw_csv)
    frames_lookup = load_frames_lookup(args.frames_csv)
    
    # Process
    process_match_sequences(
        args.match_id,
        dtw_matrix,
        frames_lookup,
        args.tracking_dir,
        args.metadata_dir,
        output_dir,
        args.top_n
    )
    
    print(f"\n{'='*80}")
    print(f"Done! JSON files saved to: {output_dir}")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()