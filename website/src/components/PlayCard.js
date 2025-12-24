import React, { useState, useEffect, useRef } from 'react';
import SoccerField from './SoccerField';

const PlayCard = ({ play, isTarget, similarityRank, onRemove, globalIsPlaying, globalReset, onPlayFinished }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(3);
  const animationFrameRef = useRef(null);
  const lastTimeRef = useRef(Date.now());
  const playFinishedRef = useRef(false);

  // Sync with global play control
  useEffect(() => {
    if (globalIsPlaying !== undefined) {
      setIsPlaying(globalIsPlaying);
    }
  }, [globalIsPlaying]);

  // Sync with global reset
  useEffect(() => {
    if (globalReset !== undefined && globalReset > 0) {
      setCurrentTime(0);
      setIsPlaying(false);
      playFinishedRef.current = false;
    }
  }, [globalReset]);
  
  const headerClass = `play-card-header${isTarget ? ' target' : ''}`;
  const cardClass = `play-card${isTarget ? ' target' : ''}`;
  
  const getBadgeText = () => {
    if (isTarget) return '🎯 TARGET';
    return `Similar #${similarityRank}`;
  };
  
  const getColor = () => {
    if (isTarget) return '#f43f5e';
    // Vary colors for different similar plays
    const colors = ['#667eea', '#f59e0b', '#10b981', '#ec4899', '#8b5cf6'];
    return colors[(similarityRank - 1) % colors.length];
  };
  
  // Animation loop with adjustable speed
  useEffect(() => {
    if (!isPlaying) {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      return;
    }

    const actualDuration = play.duration || play.frames.length / 10; // Use duration from data, fallback to calculated

    const animate = () => {
      const now = Date.now();
      const delta = (now - lastTimeRef.current) / 1000 * playbackSpeed;
      lastTimeRef.current = now;

      setCurrentTime(prevTime => {
        const newTime = prevTime + delta;
        if (newTime >= actualDuration) {
          setIsPlaying(false);
          return actualDuration;
        }
        return newTime;
      });

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    lastTimeRef.current = Date.now();
    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPlaying, play.frames.length, playbackSpeed]);
  
  // Detect when playback finishes and notify parent
  useEffect(() => {
    const actualDuration = play.duration || play.frames.length / 10;
    
    // When playback reaches end and is stopped, call the callback once
    if (currentTime >= actualDuration && !isPlaying && currentTime > 0) {
      if (!playFinishedRef.current && onPlayFinished) {
        playFinishedRef.current = true;
        onPlayFinished();
      }
    } else if (currentTime < actualDuration) {
      // Reset flag when time goes back (e.g., after reset)
      playFinishedRef.current = false;
    }
  }, [currentTime, isPlaying, play.duration, play.frames.length, onPlayFinished]);
  
  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
  };
  
  const handleStop = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };
  
  return (
    <div className={cardClass}>
      <div className={headerClass}>
        <div>
          <div 
            className="play-card-title"
            title={play.sequenceId.includes('subset') ? 'Subset 0 = First 10 events, Subset 1 = Second 10 events, etc.' : ''}
          >
            Sequence {play.sequenceId}
          </div>
          <div className="play-card-match">
            Match {play.matchId}
          </div>
        </div>
        <div className="play-card-badge">
          {getBadgeText()}
        </div>
      </div>
    
    
      <div className="play-card-field">
        <SoccerField
          frames={play.frames}
          currentTime={currentTime}
          color={getColor()}
        />
      </div>
      
      <div className="play-card-info">
        <div className="info-stats">
          <div className="info-item">
            <div className="info-label">Duration</div>
            <div className="info-value">{play.duration?.toFixed(1) || (play.frames.length / 10).toFixed(1)}s</div>
          </div>
          {!isTarget && (
            <div className="info-item">
              <div className="info-label">Similarity Score</div>
              <div className="info-value">{(1 - play.dtwScore).toFixed(3)}</div>
            </div>
          )}
          <div className="info-item">
            <div className="info-label">Events</div>
            <div className="info-value">10</div>
          </div>
        </div>
        
        <div className="main-controls">
          <button 
            className="card-control-btn main-btn"
            onClick={handlePlayPause}
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? '⏸' : '▶️'}
          </button>
          <button 
            className="card-control-btn main-btn"
            onClick={handleStop}
            title="Reset"
          >
            ⏹
          </button>
        </div>
        
        <div className="card-time-display">
          {currentTime.toFixed(1)}s / {(play.duration || play.frames.length / 10).toFixed(1)}s
        </div>
      </div>
      
      <div className="play-card-controls">
        <div className="speed-control">
          <span className="speed-label">Speed:</span>
          <button 
            className={`speed-btn ${playbackSpeed === 0.5 ? 'active' : ''}`}
            onClick={() => setPlaybackSpeed(0.5)}
            title="0.5x speed"
          >
            0.5x
          </button>
          <button 
            className={`speed-btn ${playbackSpeed === 1 ? 'active' : ''}`}
            onClick={() => setPlaybackSpeed(1)}
            title="1x speed"
          >
            1x
          </button>
          <button 
            className={`speed-btn ${playbackSpeed === 2 ? 'active' : ''}`}
            onClick={() => setPlaybackSpeed(2)}
            title="2x speed"
          >
            2x
          </button>
          <button 
            className={`speed-btn ${playbackSpeed === 3 ? 'active' : ''}`}
            onClick={() => setPlaybackSpeed(3)}
            title="3x speed"
          >
            3x
          </button>
          <button 
            className={`speed-btn ${playbackSpeed === 5 ? 'active' : ''}`}
            onClick={() => setPlaybackSpeed(5)}
            title="5x speed"
          >
            5x
          </button>
        </div>
        
        {play.videoUrl && (
          <a
            href={play.videoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="open-video-btn"
          >
            <span>🔗</span>
            Open Video
          </a>
        )}
      </div>
    </div>
    
    
    
  );
};

export default PlayCard;
