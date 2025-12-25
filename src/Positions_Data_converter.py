import pandas as pd
import json
import os
from pathlib import Path
from typing import Dict, List, Any


# ============================================================================
# ORIENTATION NORMALIZATION FUNCTIONS
# ============================================================================

def should_flip_coordinates(attacking_side: str) -> bool:
    """
    Determine if coordinates should be flipped.
    Logic: Normalize all sequences to attack left-to-right (positive x direction).
    Flip if attacking right-to-left.
    """
    return attacking_side == 'right_to_left'


def flip_x_coordinate(x: float) -> float:
    """Flip x-coordinate by negating it."""
    return -x


def flip_y_coordinate(y: float) -> float:
    """Flip y-coordinate by negating it."""
    return -y


def normalize_sequence_positions(sequence: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a sequence's positions based on attacking_side.
    
    Parameters:
    -----------
    sequence : dict
        Sequence dictionary with positions and attacking_side
    
    Returns:
    --------
    dict
        Normalized sequence with flipped coordinates if needed
    """
    normalized_sequence = sequence.copy()
    attacking_side = sequence.get('attacking_side')
    
    if attacking_side is None:
        print(f"  Warning: Sequence {sequence.get('sequence_id')} missing attacking_side, skipping normalization")
        return normalized_sequence
    
    should_flip = should_flip_coordinates(attacking_side)
    
    if should_flip:
        normalized_positions = {}
        for frame, coords in sequence['positions'].items():
            if len(coords) >= 2:
                x, y = coords[0], coords[1]
                z = coords[2] if len(coords) > 2 else None
                
                # Flip coordinates
                x_flipped = flip_x_coordinate(x)
                y_flipped = flip_y_coordinate(y)
                
                normalized_coords = [x_flipped, y_flipped]
                if z is not None:
                    normalized_coords.append(z)
                
                normalized_positions[frame] = normalized_coords
            else:
                normalized_positions[frame] = coords
        
        normalized_sequence['positions'] = normalized_positions
        normalized_sequence['normalized'] = True
    else:
        normalized_sequence['normalized'] = False
    
    return normalized_sequence


# ============================================================================
# EXTRACTION FUNCTIONS
# ============================================================================

def extract_ball_coordinates(match_ids: List[str], fixed_num_events: int, 
                            input_dir: str, output_dir: str = None) -> str:
    """
     It extracts, normalizes, and exports ball trajectory data for sequences of a fixed length from multiple matches, 
     ready for further analysis or visualization.
    
    Parameters:
    -----------
    match_ids : list
        List of match IDs to process
    fixed_num_events : int
        The exact number of positions a sequence must have to be included
    input_dir : str
        Path to directory containing position JSON files
    output_dir : str, optional
        Directory to save output CSV files. If None, saves in input_dir.
    
    Returns:
    --------
    str
        Path to the combined output CSV file
    """
    
    if output_dir is None:
        output_dir = input_dir
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    all_data = []
    frame_ranges = []
    total_sequences = 0
    normalized_count = 0
    
    for match_id in match_ids:
        print(f"\nProcessing match {match_id}...")
        
        # Construct file path
        match_file = os.path.join(input_dir, f"{match_id}_sequences_positions.json")
        
        if not os.path.exists(match_file):
            print(f"  Warning: File not found: {match_file}")
            continue
        
        # Load the match data
        try:
            with open(match_file, 'r') as f:
                match_data = json.load(f)
        except Exception as e:
            print(f"  Error loading file: {e}")
            continue
        
        sequences = match_data.get('sequences', [])
        print(f"  Found {len(sequences)} sequences")
        
        # Extract ball coordinates with orientation normalization
        extracted_data, extracted_ranges = extract_sequences_with_n_positions(
            sequences, fixed_num_events, match_id, return_frame_ranges=True)
        
        if extracted_data:
            all_data.extend(extracted_data)
            frame_ranges.extend(extracted_ranges)
            total_sequences += len(sequences)
            normalized_count += sum(1 for seq in sequences if seq.get('attacking_side') == 'right_to_left')
            print(f"  Extracted sequences: {len(extracted_data)}")
        else:
            print(f"  No sequences with {fixed_num_events} positions found")
    
    # Save all data to a single file
    if all_data:
        df = pd.DataFrame(all_data)
        output_file = os.path.join(output_dir, 
            f"all_matches_{fixed_num_events}_positions_normalized.csv")
        df.to_csv(output_file, index=False)

        # Save frame ranges to a separate file
        if frame_ranges:
            df_ranges = pd.DataFrame(frame_ranges)
            frame_range_file = os.path.join(output_dir, f"all_matches_{fixed_num_events}_frame_ranges.csv")
            df_ranges.to_csv(frame_range_file, index=False)
            print(f"Saved frame ranges: {frame_range_file}")

        print(f"\n{'='*60}")
        print(f"Saved combined data: {output_file}")
        print(f"Total sequences processed: {total_sequences}")
        print(f"Sequences normalized (flipped): {normalized_count}")
        print(f"Total extracted subsets: {len(df)}")
        print(f"{'='*60}")
        return output_file
    else:
        print("\nNo data extracted from any match")
        return None


def extract_sequences_with_n_positions(sequences: List[Dict], fixed_num_positions: int, 
                                      match_id: str, return_frame_ranges: bool = False) -> List[Dict]:
    """
    Extract ball coordinates from sequences and normalize orientation.
    
    Parameters:
    -----------
    sequences : list
        List of sequence dictionaries
    fixed_num_positions : int
        Number of positions to filter by
    match_id : str
        Match identifier
    
    Returns:
    --------
    list
        List of dictionaries containing sequence_id and ball coordinates
    """
    
    extracted_sequences = []
    frame_ranges = []
    
    for sequence in sequences:
        seq_id = sequence.get('sequence_id')
        frames = sequence.get('frames', [])
        positions = sequence.get('positions', {})
        
        if len(frames) < fixed_num_positions:
            continue
        
        # Normalize the sequence
        normalized_seq = normalize_sequence_positions(sequence)
        normalized_positions = normalized_seq['positions']
        
        # Extract coordinates in frame order
        all_coords = []
        all_frames_in_order = []
        for frame in frames:
            frame_key = str(frame)
            if frame_key in normalized_positions:
                coords = normalized_positions[frame_key]
                if len(coords) >= 2:
                    x, y = coords[0], coords[1]
                    z = coords[2] if len(coords) > 2 else None
                    coord = {'x': x, 'y': y}
                    if z is not None:
                        coord['z'] = z
                    all_coords.append(coord)
                    all_frames_in_order.append(frame)
        # Only process if we found coordinates for all frames
        if len(all_coords) >= fixed_num_positions:
            # Create non-overlapping subsets
            num_subsets = len(all_coords) // fixed_num_positions
            # If we have leftover positions after dividing, we ignore them (non-overlapping)
            for subset_idx in range(num_subsets):
                start_idx = subset_idx * fixed_num_positions
                end_idx = start_idx + fixed_num_positions
                subset_coords = all_coords[start_idx:end_idx]
                subset_frames = all_frames_in_order[start_idx:end_idx]
                # Format sequence_id: if only one subset, keep original id; otherwise add subset{i}
                if num_subsets == 1:
                    final_seq_id = seq_id
                else:
                    final_seq_id = f"{seq_id}_subset{subset_idx}"
                extracted_sequences.append({
                    'match_id': match_id,
                    'sequence_id': final_seq_id,
                    'team_id': sequence.get('team_id'),
                    'attacking_side': sequence.get('attacking_side'),
                    'normalized': normalized_seq.get('normalized', False),
                    'num_positions': fixed_num_positions,
                    'coordinates_json': json.dumps(subset_coords)
                })
                if return_frame_ranges:
                    if subset_frames:
                        frame_ranges.append({
                            'match_id': match_id,
                            'sequence_id': final_seq_id,
                            'start_frame': subset_frames[0],
                            'end_frame': subset_frames[-1]
                        })
    if return_frame_ranges:
        return extracted_sequences, frame_ranges
    return extracted_sequences


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract and normalize ball coordinates from position sequences')
    parser.add_argument('--match-ids', nargs='+', default=None,
                       help='List of match IDs to process (auto-discover if not specified)')
    parser.add_argument('--fixed-num-positions', type=int, default=10,
                       help='Number of positions a sequence must have (default: 4)')
    parser.add_argument('--input-dir', default=r'D:\college\pysport analytics cup\output_json',
                       help='Directory containing position JSON files (default: D:\\college\\pysport analytics cup\\output_json)')
    parser.add_argument('--output-dir', default=r'D:\college\pysport analytics cup\output_json\extracted_sequences',
                       help='Output directory for CSV (default: D:\\college\\pysport analytics cup\\output_json\\extracted_sequences)')
    
    args = parser.parse_args()
    
    # Configuration
    INPUT_DIR = args.input_dir
    OUTPUT_DIR = args.output_dir
    FIXED_NUM_POSITIONS = args.fixed_num_positions
    
    print("="*60)
    print("Ball Coordinates Extraction & Normalization Tool")
    print("="*60)
    print(f"\nInput directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Target positions per sequence: {FIXED_NUM_POSITIONS}")
    
    # Auto-discover match IDs if not provided
    if args.match_ids:
        MATCH_IDS = args.match_ids
    else:
        print(f"\nAuto-discovering match files in: {INPUT_DIR}")
        all_files = os.listdir(INPUT_DIR)
        position_files = [f for f in all_files if f.endswith('_sequences_positions.json')]
        
        MATCH_IDS = []
        for file in position_files:
            # Extract match ID from filename: "1886347_sequences_positions.json" -> "1886347"
            match_id = file.replace('_sequences_positions.json', '')
            MATCH_IDS.append(match_id)
        
        print(f"Found {len(MATCH_IDS)} match files: {MATCH_IDS}")
    
    if not MATCH_IDS:
        print("\nNo match files found!")
        exit(1)
    
    # Extract and normalize
    print("\nExtracting sequences with orientation normalization...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = extract_ball_coordinates(
        match_ids=MATCH_IDS,
        fixed_num_events=FIXED_NUM_POSITIONS,
        input_dir=INPUT_DIR,
        output_dir=OUTPUT_DIR
    )
    
    if output_file:
        print("\n" + "="*60)
        print("Extraction complete!")
        print(f"Output saved to: {output_file}")
        print("="*60)