import React, { useState, useEffect, useCallback } from 'react';

const MatchPlaySelector = ({ onPlayDataLoad }) => {
  const [matches, setMatches] = useState([]);
  // Force the app to load only match 1886347 from public/1886347
  const [selectedMatch, setSelectedMatch] = useState('1886347');
  const [plays, setPlays] = useState([]);
  const [selectedPlay, setSelectedPlay] = useState('');
  const [loading, setLoading] = useState(false);
  const [isInitialMount, setIsInitialMount] = useState(true);

  // Load available plays for the selected match
  useEffect(() => {
    if (!selectedMatch) return;
    setLoading(true);

    (async () => {
      const candidates = [
        `/${selectedMatch}/manifest.json`,
        `${selectedMatch}/manifest.json`,
        `./${selectedMatch}/manifest.json`,
        `/public/${selectedMatch}/manifest.json`
      ];

      let manifest = null;
      let triedPaths = [];

      for (const path of candidates) {
        try {
          const res = await fetch(path);
          triedPaths.push(path + ` (status ${res.status})`);
          if (!res.ok) continue;

          const text = await res.text();
          try {
            const data = JSON.parse(text);
            manifest = data;
            break;
          } catch (jsonErr) {
            // Log the non-JSON body (usually HTML index page)
            console.warn(`Manifest at ${path} is not valid JSON. Response snippet:`);
            console.warn(text.slice(0, 500));
            continue;
          }
        } catch (err) {
          triedPaths.push(path + ` (fetch error: ${err.message})`);
          continue;
        }
      }

      if (!manifest) {
        console.warn('Failed to load manifest from any candidate path:', triedPaths);
        // Fallback to default plays
        setPlays([
          { id: '148.0', name: 'Sequence 148.0 – Argentina Attacking Play' },
          { id: '101.0', name: 'Sequence 101.0 – France Counter Attack' },
          { id: '133.0', name: 'Sequence 133.0 – Argentina Build-Up' }
        ]);
        setSelectedPlay('148.0');
        setLoading(false);
        return;
      }

      try {
        if (!manifest.plays || !Array.isArray(manifest.plays)) {
          throw new Error('Invalid manifest structure: missing plays array');
        }
        setPlays(manifest.plays);
        if (manifest.plays.length > 0) {
          setSelectedPlay(manifest.plays[0].id);
        }
      } catch (err) {
        console.warn('Invalid manifest content:', err.message);
        setPlays([]);
      }

      setLoading(false);
    })();
  }, [selectedMatch]);

  const handleLoadPlay = useCallback(() => {
    if (!selectedMatch || !selectedPlay) {
      return;
    }

    setLoading(true);
    // Prefer explicit filename from the manifest if provided, otherwise
    // fall back to the legacy convention: <match>_<playId>.json
    const playObj = plays.find(p => p.id === selectedPlay) || {};
    const filename = playObj.filename || `${selectedMatch}_${selectedPlay}.json`;
    const filePath = `/${selectedMatch}/${filename}`;
    console.log(`Loading play data from: ${filePath}`);
    fetch(filePath)
 
      .then(res => {
        // Check HTTP status
        if (!res.ok) {
          if (res.status === 404) {
            throw new Error(`File not found (404): ${filename}`);
          }
          throw new Error(`HTTP ${res.status}: Failed to load play data`);
        }
        
        // Try to parse JSON even if content-type header is missing or incorrect
        return res.json();
      })
      .then(data => {
        // Validate play data structure
        if (!data.targetPlay || !data.targetPlay.frames) {
          throw new Error('Invalid play data structure: missing targetPlay or frames');
        }
        
        setLoading(false);
        if (onPlayDataLoad) {
          onPlayDataLoad(data);
        }
      })
      .catch(err => {
        console.error('Failed to load play:', err.message);
        setLoading(false);
        
        // Show user-friendly error message
        const playName = plays.find(p => p.id === selectedPlay)?.name || `Sequence ${selectedPlay}`;
        
        alert(
          `Unable to load ${playName}\n\n` +
          `Error: ${err.message}\n\n` +
          `Expected location: public${filePath}\n\n` +
          `Please ensure:\n` +
          `1. The file exists in the public folder\n` +
          `2. The dev server is running\n` +
          `3. You've generated the play data using the Python script`
        );
      });
  }, [selectedMatch, selectedPlay, plays, onPlayDataLoad]);

  // Auto-load play when selection changes
  useEffect(() => {
    if (selectedMatch && selectedPlay && !isInitialMount) {
      handleLoadPlay();
    }
    if (isInitialMount) {
      setIsInitialMount(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPlay, selectedMatch, isInitialMount]);

  return (
    <div className="match-play-selector">
      <div className="selector-header">
        <div className="selector-title-group">
          <h2 className="selector-title">Match & Play Selection</h2>
          <p className="selector-subtitle">Australian A-League 2024/2025 Season</p>
        </div>
        <div className="context-badge">
          <span className="badge-icon">AU</span>
          <span className="badge-text">A-League</span>
        </div>
      </div>

      <div className="selector-controls">
        <div className="selector-group">
          <label htmlFor="match-select" className="selector-label">Select Match</label>
          <select
            id="match-select"
            className="selector-dropdown"
            value={selectedMatch}
            onChange={(e) => setSelectedMatch(e.target.value)}
            disabled={loading}
          >
            <option value="1886347">Match 1886347</option>
          </select>
        </div>

        <div className="selector-group">
          <label htmlFor="play-select" className="selector-label">Select Play / Sequence</label>
          <select
            id="play-select"
            className="selector-dropdown"
            value={selectedPlay}
            onChange={(e) => setSelectedPlay(e.target.value)}
            disabled={loading || plays.length === 0}
          >
            {plays.length === 0 ? (
              <option value="">Loading plays...</option>
            ) : (
              plays.map(play => {
                const playName = play.name || `Sequence ${play.id.replace(/^seq_/, '')}`;
                const tooltip = playName.includes('subset') 
                  ? 'Subset 0 = First 10 events, Subset 1 = Second 10 events, etc.' 
                  : '';
                return (
                  <option key={play.id} value={play.id} title={tooltip}>
                    {playName}
                  </option>
                );
              })
            )}
          </select>
        </div>

        {loading && (
          <div className="selector-loading">
            <div className="loading-spinner"></div>
            <span>Loading play data...</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default MatchPlaySelector;
