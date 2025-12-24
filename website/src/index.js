import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import './styles.css';
import PlayCard from './components/PlayCard';
import PlayList from './components/PlayList';
import MatchPlaySelector from './components/MatchPlaySelector';
import { loadPlayData } from './utils/dataLoader';

function App() {
  const [plays, setPlays] = useState([]);
  const [selectedPlays, setSelectedPlays] = useState([]);
  const [targetPlay, setTargetPlay] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [globalIsPlaying, setGlobalIsPlaying] = useState(false);
  const [globalReset, setGlobalReset] = useState(0);
  const [bothPlayFinished, setBothPlayFinished] = useState(false);
  const [playFinishCount, setPlayFinishCount] = useState(0);

  const handlePlaySelect = (play) => {
    // Replace current selection with new play (only one similar play at a time)
    if (selectedPlays.find(p => p.id === play.id)) {
      // If clicking the same play, deselect it
      setSelectedPlays([]);
    } else {
      // Replace with new selection
      setSelectedPlays([play]);
    }
  };

  const handlePlayRemove = (playId) => {
    setSelectedPlays(selectedPlays.filter(p => p.id !== playId));
  };

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const handleGlobalPlayPause = () => {
    // If both plays finished, auto-reset before playing again
    if (bothPlayFinished) {
      setGlobalReset(prev => prev + 1);
      setBothPlayFinished(false);
      setPlayFinishCount(0);
      // Delay play start to allow reset to complete first
      setTimeout(() => {
        setGlobalIsPlaying(true);
      }, 50);
    } else {
      setGlobalIsPlaying(!globalIsPlaying);
    }
  };

  const handleGlobalReset = () => {
    setGlobalIsPlaying(false);
    setGlobalReset(prev => prev + 1);
    setBothPlayFinished(false);
    setPlayFinishCount(0);
  };

  const handlePlayFinished = () => {
    const newCount = playFinishCount + 1;
    setPlayFinishCount(newCount);
    
    // Count expected plays (target + similar if exists)
    const expectedPlays = selectedPlays.length > 0 ? 2 : 1;
    
    // When both plays finish, mark as finished and stop playing
    if (newCount >= expectedPlays) {
      setGlobalIsPlaying(false);
      setBothPlayFinished(true);
      setPlayFinishCount(0);
    }
  };

  return (
    <div className="app">
      <button 
        className={`sidebar-toggle ${sidebarCollapsed ? 'collapsed' : ''}`}
        onClick={toggleSidebar}
        title={sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
      >
        <span className="hamburger-line"></span>
        <span className="hamburger-line"></span>
        <span className="hamburger-line"></span>
      </button>
      
      <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          <h1>⚽ Play Comparison</h1>
          <p>Skill Corner Open Data – 2024/2025 A-League</p>
        </div>
        <div className="play-list-container">
          <MatchPlaySelector
            onPlayDataLoad={(data) => {
              setPlays(data.similarPlays || []);
              setTargetPlay(data.targetPlay);
              setSelectedPlays(data.similarPlays || []);
            }}
          />
          {targetPlay && (
            <PlayList
              plays={plays}
              selectedPlays={selectedPlays}
              targetPlay={targetPlay}
              onPlaySelect={handlePlaySelect}
            />
          )}
        </div>
      </aside>

      <main className="main-content">
        {targetPlay ? (
          <>
            <div className="top-bar">
              <div className="top-bar-left">
                <h2>Target Sequence</h2>
                <div className="target-info">
                  <span><strong>Match:</strong> {targetPlay.matchId}</span>
                  <span 
                    title={targetPlay.sequenceId.includes('subset') ? 'Subset 0 = First 10 events, Subset 1 = Second 10 events, etc.' : ''}
                  >
                    <strong>Sequence:</strong> {targetPlay.sequenceId}
                  </span>
                  <span><strong>Duration:</strong> {targetPlay.duration.toFixed(1)}s</span>
                </div>
              </div>
              
              <div className="global-controls">
                <button 
                  className="global-control-btn"
                  onClick={handleGlobalPlayPause}
                  title={globalIsPlaying ? 'Pause Both' : 'Play Both'}
                >
                  {globalIsPlaying ? '⏸' : '▶️'}
                </button>
                <button 
                  className="global-control-btn"
                  onClick={handleGlobalReset}
                  title="Reset Both"
                >
                  ⏹
                </button>
              </div>
            </div>

            <div className="grid-container">
              {/* Target Play */}
              <PlayCard
                play={targetPlay}
                isTarget={true}
                onRemove={null}
                globalIsPlaying={globalIsPlaying}
                globalReset={globalReset}
                onPlayFinished={handlePlayFinished}
              />

              {/* Only First Similar Play */}
              {selectedPlays.length > 0 && (
                <PlayCard
                  key={selectedPlays[0].id}
                  play={selectedPlays[0]}
                  isTarget={false}
                  similarityRank={1}
                  onRemove={() => handlePlayRemove(selectedPlays[0].id)}
                  globalIsPlaying={globalIsPlaying}
                  globalReset={globalReset}
                  onPlayFinished={handlePlayFinished}
                />
              )}
            </div>
          </>
        ) : (
          <div className="empty-state-main">
            <div className="empty-state-icon">⚽</div>
            <h2>Select a Play to Begin</h2>
            <p>Choose a match and sequence from the selector on the left to view tracking data and similar plays.</p>
          </div>
        )}
        
        <footer className="app-footer">
          <div className="footer-content">
            <div className="footer-links">
              <a href="mailto:shehab_100@outlook.com" target="_blank" rel="noopener noreferrer" title="Email">
                📧 Email
              </a>
              <a href="https://www.linkedin.com/in/shehap-elhadary-682373251/" target="_blank" rel="noopener noreferrer" title="LinkedIn">
                💼 LinkedIn
              </a>
              <a href="https://github.com/shehab400" target="_blank" rel="noopener noreferrer" title="GitHub">
                🐙 GitHub
              </a>
            </div>
            <div className="footer-copyright">
              <p>© {new Date().getFullYear()} Football Play Similarity Analysis. All rights reserved.</p>
              <p className="footer-subtitle">Football Tracking Data Comparison Tool</p>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
