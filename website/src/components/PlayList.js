import React from 'react';

const PlayList = ({ plays, selectedPlays, targetPlay, onPlaySelect }) => {
  const isSelected = (playId) => {
    return selectedPlays.some(p => p.id === playId);
  };
  
  return (
    <div className="play-list-container">
      {/* Target play info */}
      <div className="play-list-item target">
        <div className="play-item-header">
          <span className="play-item-id">
            🎯 {targetPlay.matchId}_{targetPlay.sequenceId}
          </span>
          <span className="play-item-score">TARGET</span>
        </div>
        <div className="play-item-info">
          Duration: {targetPlay.duration.toFixed(1)}s • {targetPlay.frames.length} frames
        </div>
      </div>
      
      <div style={{ 
        padding: '12px 8px',
        fontSize: '12px',
        fontWeight: '600',
        color: '#94a3b8',
        textTransform: 'uppercase',
        letterSpacing: '0.5px'
      }}>
        Similar Plays ({plays.length})
      </div>
      
      {/* Similar plays list */}
      {plays.map((play, idx) => (
        <div
          key={play.id}
          className={`play-list-item ${isSelected(play.id) ? 'selected' : ''}`}
          onClick={() => onPlaySelect(play)}
          style={{ cursor: 'pointer' }}
          
        >
          
          <div className="play-item-header">
            
            <span className="play-item-id">
              {play.matchId}_{play.sequenceId}
            </span>
            <span className="play-item-score">
              {(1 - play.dtwScore).toFixed(2)}
            </span>
           
          </div>
          <div className="play-item-info">
            Rank #{idx + 1} • {play.duration.toFixed(1)}s • {play.frames.length} frames
          </div>
        </div>
      ))}
      
      {plays.length === 0 && (
        <div style={{
          padding: '40px 20px',
          textAlign: 'center',
          color: '#64748b',
          fontSize: '14px'
        }}>
          No similar plays found
        </div>
      )}
    </div>
  );
};

export default PlayList;
