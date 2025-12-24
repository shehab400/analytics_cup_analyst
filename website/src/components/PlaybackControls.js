import React from 'react';

const PlaybackControls = ({
  isPlaying,
  currentTime,
  duration,
  playbackSpeed,
  onPlayPause,
  onStop,
  onSpeedChange,
  onTimelineClick
}) => {
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms}`;
  };
  
  const handleTimelineClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const progress = x / rect.width;
    onTimelineClick(Math.max(0, Math.min(1, progress)));
  };
  
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;
  
  const speeds = [0.25, 0.5, 1, 2, 4];
  
  return (
    <div className="playback-controls">
      <div className="controls-row">
        <button
          className="control-button primary"
          onClick={onPlayPause}
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? '⏸' : '▶'}
        </button>
        
        <button
          className="control-button"
          onClick={onStop}
          title="Stop"
        >
          ⏹
        </button>
        
        <button
          className="control-button"
          onClick={() => onTimelineClick(Math.max(0, currentTime - 0.1) / duration)}
          title="Step Back"
        >
          ⏮
        </button>
        
        <button
          className="control-button"
          onClick={() => onTimelineClick(Math.min(1, (currentTime + 0.1) / duration))}
          title="Step Forward"
        >
          ⏭
        </button>
        
        <div className="speed-selector">
          {speeds.map(speed => (
            <button
              key={speed}
              className={`speed-btn ${playbackSpeed === speed ? 'active' : ''}`}
              onClick={() => onSpeedChange(speed)}
            >
              {speed}x
            </button>
          ))}
        </div>
      </div>
      
      <div className="timeline">
        <div className="timeline-bar" onClick={handleTimelineClick}>
          <div className="timeline-progress" style={{ width: `${progress}%` }}>
            <div className="timeline-thumb"></div>
          </div>
        </div>
        <div className="timeline-labels">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>
    </div>
  );
};

export default PlaybackControls;
