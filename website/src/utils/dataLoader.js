// Data loader utility
// This loads the JSON data exported from Python
//
// COORDINATE SYSTEM (RAW METERS):
// - Origin (0,0,0) at center of pitch
// - X-axis: along touchlines, increases left to right (range: -52.5m to 52.5m for 105m pitch)
// - Y-axis: along end lines, increases bottom to top (range: -34m to 34m for 68m pitch)
// - Z-axis: points vertically upward from pitch plane
// - Units: meters
// - Time: relative to sequence start (in seconds)
// - Downsampled to 1Hz (1 sample per second)

import playDataJson from '../../public/data/play_data.json';

export async function loadPlayData() {
  try {
    // Return the imported JSON data directly
    // Coordinates are already normalized to 0-100 range
    return playDataJson;
  } catch (error) {
    console.error('Error loading play data:', error);
    
    // Return sample data for development
    return getSampleData();
  }
}

// Sample data for development/testing
function getSampleData() {
  const generateFrames = (startX, startY, points = 10) => {
    const frames = [];
    let x = startX;
    let y = startY;
    
    for (let i = 0; i < points; i++) {
      frames.push({
        time: i * 1.0,
        ball: {
          x: x,
          y: y,
          z: 0
        },
        homePlayers: Array.from({ length: 5 }, (_, j) => ({
          x: x - 10 + j * 5,
          y: y - 10,
          jerseyNum: j + 1,
          playerId: j + 1
        })),
        awayPlayers: Array.from({ length: 5 }, (_, j) => ({
          x: x - 10 + j * 5,
          y: y + 10,
          jerseyNum: j + 1,
          playerId: j + 100
        }))
      });
      x += 5;
      y += (Math.random() - 0.5) * 3;
    }
    
    return frames;
  };
  
  const targetPlay = {
    id: 'target',
    matchId: '10517',
    sequenceId: '148.0',
    frames: generateFrames(0, 0, 10),
    duration: 10.0,
    videoUrl: null
  };
  
  const similarPlays = [
    {
      id: '3827_216.0_subset0',
      matchId: '3827',
      sequenceId: '216.0',
      dtwScore: 0.102374,
      frames: generateFrames(5, -5, 8),
      duration: 8.0,
      videoUrl: null
    },
    {
      id: '3855_108.0_subset1',
      matchId: '3855',
      sequenceId: '108.0',
      dtwScore: 0.105326,
      frames: generateFrames(10, 5, 9),
      duration: 9.0,
      videoUrl: null
    },
    {
      id: '3814_241.0_subset0',
      matchId: '3814',
      sequenceId: '241.0',
      dtwScore: 0.111630,
      frames: generateFrames(-5, 10, 10),
      duration: 10.0,
      videoUrl: null
    },
    {
      id: '3822_100.0_subset0',
      matchId: '3822',
      sequenceId: '100.0',
      dtwScore: 0.114118,
      frames: generateFrames(-10, -10, 7),
      duration: 7.0,
      videoUrl: null
    },
    {
      id: '3855_18.0_subset1',
      matchId: '3855',
      sequenceId: '18.0',
      dtwScore: 0.114769,
      frames: generateFrames(15, 0, 9),
      duration: 9.0,
      videoUrl: null
    },
    {
      id: '3848_80.0',
      matchId: '3848',
      sequenceId: '80.0',
      dtwScore: 0.115374,
      frames: generateFrames(-15, 5, 10),
      duration: 10.0,
      videoUrl: null
    },
    {
      id: '3827_130.0_subset1',
      matchId: '3827',
      sequenceId: '130.0',
      dtwScore: 0.116272,
      frames: generateFrames(20, -5, 8),
      duration: 8.0,
      videoUrl: null
    },
    {
      id: '3816_22.0_subset2',
      matchId: '3816',
      sequenceId: '22.0',
      dtwScore: 0.116997,
      frames: generateFrames(0, 15, 10),
      duration: 10.0,
      videoUrl: null
    },
    {
      id: '10505_223.0_subset1',
      matchId: '10505',
      sequenceId: '223.0',
      dtwScore: 0.119319,
      frames: generateFrames(-20, 0, 7),
      duration: 7.0,
      videoUrl: null
    },
    {
      id: '3856_280.0_subset0',
      matchId: '3856',
      sequenceId: '280.0',
      dtwScore: 0.120704,
      frames: generateFrames(10, 10, 9),
      duration: 9.0,
      videoUrl: null
    }
  ];
  
  return {
    targetPlay,
    similarPlays
  };
}
