import React, { useRef, useEffect } from 'react';

const SoccerField = ({ frames, currentTime, color = '#fbbf24' }) => {
  const canvasRef = useRef(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
      if (!canvas || !frames || frames.length === 0) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Field dimensions matching Python script
    const padding = 20;
    const fieldWidth = width - padding * 2;
    const fieldHeight = height - padding * 2;
    const fieldX = padding;
    const fieldY = padding;
    
    // Draw field
    drawField(ctx, fieldX, fieldY, fieldWidth, fieldHeight);
    
    // Draw frames (ball and players)
    drawFrames(ctx, frames, fieldX, fieldY, fieldWidth, fieldHeight, currentTime);
    
  }, [frames, currentTime]);
  
  const drawField = (ctx, x, y, width, height) => {
    // 1. BACKGROUND: Removed the dark green fill to match Code B.
    // If you need a background, uncomment the next two lines:
    // ctx.fillStyle = '#001400';
    // ctx.fillRect(x, y, width, height);
    
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1.5;
    ctx.globalAlpha = 0.6; // Changed from 0.75 to 0.6 to match Code B
    
    // Pitch dimensions: 105m x 68m
    // For proportional drawing
    const pitchLength = 105; // meters
    const pitchWidth = 68;   // meters
    
    // Helper to convert meters to canvas pixels
    const meterToPixelX = (meters) => (meters / pitchLength) * width;
    const meterToPixelY = (meters) => (meters / pitchWidth) * height;
    
    // Outer boundary
    ctx.strokeRect(x, y, width, height);
    
    // Center line (vertical line at x=0 in field coordinates)
    const centerX = x + width / 2;
    ctx.beginPath();
    ctx.moveTo(centerX, y);
    ctx.lineTo(centerX, y + height);
    ctx.stroke();
    
    // Center circle (radius 9.15m)
    const centerY = y + height / 2;
    const centerRadius = Math.min(meterToPixelX(9.15), meterToPixelY(9.15));
    ctx.beginPath();
    ctx.arc(centerX, centerY, centerRadius, 0, Math.PI * 2);
    ctx.stroke();
    
    // Center spot (0.3m radius)
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(centerX, centerY, 2, 0, Math.PI * 2);
    ctx.fill();
    
    // Penalty areas (16.5m from goal line, 40.3m wide)
    const penaltyLength = meterToPixelX(16.5);
    const penaltyWidth = meterToPixelY(40.3);
    const penaltyY = y + (height - penaltyWidth) / 2;
    
    // Left penalty box
    ctx.strokeRect(x, penaltyY, penaltyLength, penaltyWidth);
    
    // Right penalty box
    ctx.strokeRect(x + width - penaltyLength, penaltyY, penaltyLength, penaltyWidth);
    
    // Goal areas (5.5m from goal line, 18.3m wide)
    const goalLength = meterToPixelX(5.5);
    const goalWidth = meterToPixelY(18.3);
    const goalY = y + (height - goalWidth) / 2;
    
    // Left goal area
    ctx.strokeRect(x, goalY, goalLength, goalWidth);
    
    // Right goal area
    ctx.strokeRect(x + width - goalLength, goalY, goalLength, goalWidth);
    
    // Penalty spots (11m from goal line)
    const penaltySpotDist = meterToPixelX(11);
    
    // Left penalty spot
    ctx.beginPath();
    ctx.arc(x + penaltySpotDist, centerY, 2, 0, Math.PI * 2);
    ctx.fill();
    
    // Right penalty spot
    ctx.beginPath();
    ctx.arc(x + width - penaltySpotDist, centerY, 2, 0, Math.PI * 2);
    ctx.fill();
    
    // Penalty arcs (9.15m radius from penalty spot)
    const arcRadius = Math.min(meterToPixelX(9.15), meterToPixelY(9.15));
    
    // Left penalty arc (visible part outside the box)
    ctx.beginPath();
    ctx.arc(x + penaltySpotDist, centerY, arcRadius, -Math.PI * 52/180, Math.PI * 52/180);
    ctx.stroke();
    
    // Right penalty arc
    ctx.beginPath();
    ctx.arc(x + width - penaltySpotDist, centerY, arcRadius, Math.PI * 128/180, Math.PI * 232/180);
    ctx.stroke();
    
    // Corner arcs (1m radius)
    const cornerRadius = Math.min(meterToPixelX(1), meterToPixelY(1));
    
    // Bottom-left corner
    ctx.beginPath();
    ctx.arc(x, y + height, cornerRadius, -Math.PI/2, 0);
    ctx.stroke();
    
    // Top-left corner
    ctx.beginPath();
    ctx.arc(x, y, cornerRadius, 0, Math.PI/2);
    ctx.stroke();
    
    // Bottom-right corner
    ctx.beginPath();
    ctx.arc(x + width, y + height, cornerRadius, Math.PI, Math.PI * 3/2);
    ctx.stroke();
    
    // Top-right corner
    ctx.beginPath();
    ctx.arc(x + width, y, cornerRadius, Math.PI/2, Math.PI);
    ctx.stroke();
    
    ctx.globalAlpha = 1;
  };
  
  const drawFrames = (ctx, frames, fieldX, fieldY, fieldWidth, fieldHeight, time) => {
    if (!frames || frames.length === 0) return;
    
    const toCanvasCoords = (x, y) => {
      // X: -52.5 to +52.5 -> 0 to fieldWidth
      const canvasX = fieldX + ((x + 52.5) / 105) * fieldWidth;
      // Y: -34 to +34 -> fieldHeight to 0
      const canvasY = fieldY + fieldHeight - ((y + 34) / 68) * fieldHeight;
      return { x: canvasX, y: canvasY };
    };
    
    // Find current frame based on time
    let currentIdx = 0;
    for (let i = 0; i < frames.length - 1; i++) {
      if (frames[i].time <= time && time < frames[i + 1].time) {
        currentIdx = i;
        break;
      }
    }
    
    if (time >= frames[frames.length - 1].time) {
      currentIdx = frames.length - 1;
    }
    
    const currentFrame = frames[currentIdx];
    if (!currentFrame || !currentFrame.ball || typeof currentFrame.ball.x !== 'number' || typeof currentFrame.ball.y !== 'number') return;
    
    // 2. BALL COLORS: Changed Green to Gold (#FFD700)
    
    // Draw full ball trajectory (all frames) - lighter for preview
    ctx.strokeStyle = '#FFD700';  // Gold color
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.3;
    
    ctx.beginPath();
    let first = true;
    for (let i = 0; i < frames.length; i++) {
      const ball = frames[i].ball;
      if (!ball || typeof ball.x !== 'number' || typeof ball.y !== 'number') continue;
      const pos = toCanvasCoords(ball.x, ball.y);
      if (first) {
        ctx.moveTo(pos.x, pos.y);
        first = false;
      } else {
        ctx.lineTo(pos.x, pos.y);
      }
    }
    ctx.stroke();
    
    // Draw dots for full trajectory - lighter
    ctx.fillStyle = 'rgba(255, 215, 0, 0.3)';
    for (let i = 0; i < frames.length; i++) {
      const ball = frames[i].ball;
      if (!ball || typeof ball.x !== 'number' || typeof ball.y !== 'number') continue;
      const pos = toCanvasCoords(ball.x, ball.y);
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 1.5, 0, Math.PI * 2);
      ctx.fill();
    }
    
    // Draw ball trajectory (past frames up to current) - more visible
    ctx.strokeStyle = '#FFD700';  // Gold color for trail
    ctx.lineWidth = 3;
    ctx.globalAlpha = 0.8; // Increased alpha to match Code B
    
    ctx.beginPath();
    first = true;
    for (let i = 0; i <= currentIdx; i++) {
      const ball = frames[i].ball;
      if (!ball || typeof ball.x !== 'number' || typeof ball.y !== 'number') continue;
      const pos = toCanvasCoords(ball.x, ball.y);
      if (first) {
        ctx.moveTo(pos.x, pos.y);
        first = false;
      } else {
        ctx.lineTo(pos.x, pos.y);
      }
    }
    ctx.stroke();
    
    // Add dots at each frame position for current trajectory
    ctx.fillStyle = '#FFD700';
    for (let i = 0; i <= currentIdx; i++) {
      const ball = frames[i].ball;
      if (!ball || typeof ball.x !== 'number' || typeof ball.y !== 'number') continue;
      const pos = toCanvasCoords(ball.x, ball.y);
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 2, 0, Math.PI * 2);
      ctx.fill();
    }
    
    // 3. TEAM COLORS: Changed Teal->Red and Red->Blue
    
    // Draw players - Home team (Red)
    ctx.globalAlpha = 0.8;
    if (currentFrame.homePlayers) {
      currentFrame.homePlayers.forEach(player => {
        const pos = toCanvasCoords(player.x, player.y);
        
        // Player circle
        ctx.fillStyle = '#EF4444';  // Red (Home)
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 6, 0, Math.PI * 2);
        ctx.fill();
        
        // Player border
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 1.5; // Thicker border from Code B
        ctx.stroke();
        
        // Jersey number
        if (player.jerseyNum) {
          ctx.fillStyle = '#FFFFFF';
          ctx.font = 'bold 8px Arial';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(player.jerseyNum, pos.x, pos.y);
        }
      });
    }
    
    // Draw players - Away team (Blue)
    if (currentFrame.awayPlayers) {
      currentFrame.awayPlayers.forEach(player => {
        const pos = toCanvasCoords(player.x, player.y);
        
        // Player circle
        ctx.fillStyle = '#3B82F6';  // Blue (Away)
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 6, 0, Math.PI * 2);
        ctx.fill();
        
        // Player border
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        
        // Jersey number
        if (player.jerseyNum) {
          ctx.fillStyle = '#FFFFFF';
          ctx.font = 'bold 8px Arial';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(player.jerseyNum, pos.x, pos.y);
        }
      });
    }
    
    // 4. MARKERS: Updated text labels to match Code B
    
    // Draw start position marker (GREEN ARROW)
    const startBall = frames[0].ball;
    if (startBall && typeof startBall.x === 'number' && typeof startBall.y === 'number') {
      const startPos = toCanvasCoords(startBall.x, startBall.y);
      drawPositionMarker(ctx, startPos.x, startPos.y, '#22C55E', 'START POSITION');
    }
    
    // Draw end position marker (RED ARROW)
    const endBall = frames[frames.length - 1].ball;
    if (endBall && typeof endBall.x === 'number' && typeof endBall.y === 'number') {
      const endPos = toCanvasCoords(endBall.x, endBall.y);
      drawPositionMarker(ctx, endPos.x, endPos.y, '#EF4444', 'END POSITION');
    }
    
    // 5. BALL OBJECT: Changed Green to Gold
    
    // Draw ball (GOLD) - on top of everything
    if (currentFrame.ball && typeof currentFrame.ball.x === 'number' && typeof currentFrame.ball.y === 'number') {
      const ballPos = toCanvasCoords(currentFrame.ball.x, currentFrame.ball.y);
      ctx.globalAlpha = 1;
      
      // Outer glow
      const gradient = ctx.createRadialGradient(
        ballPos.x, ballPos.y, 0,
        ballPos.x, ballPos.y, 12
      );
      gradient.addColorStop(0, '#FFD700');
      gradient.addColorStop(0.5, '#FFD70080');
      gradient.addColorStop(1, '#FFD70000');
      
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(ballPos.x, ballPos.y, 12, 0, Math.PI * 2);
      ctx.fill();
      
      // Inner ball
      ctx.fillStyle = '#FFD700';  // Gold
      ctx.beginPath();
      ctx.arc(ballPos.x, ballPos.y, 5, 0, Math.PI * 2);
      ctx.fill();
      
      // Ball highlight
      ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
      ctx.beginPath();
      ctx.arc(ballPos.x - 2, ballPos.y - 2, 2, 0, Math.PI * 2);
      ctx.fill();
    }
  };
  
  const drawPositionMarker = (ctx, x, y, color, label) => {
    ctx.globalAlpha = 0.9;
    
    // Draw arrow pointing down to the position
    const arrowSize = 20;
    const arrowY = y - 25;
    
    // Arrow shape
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(x, y - 10); // Point
    ctx.lineTo(x - arrowSize / 2, arrowY); // Left
    ctx.lineTo(x - arrowSize / 4, arrowY); // Inner left
    ctx.lineTo(x - arrowSize / 4, arrowY - 15); // Top left
    ctx.lineTo(x + arrowSize / 4, arrowY - 15); // Top right
    ctx.lineTo(x + arrowSize / 4, arrowY); // Inner right
    ctx.lineTo(x + arrowSize / 2, arrowY); // Right
    ctx.closePath();
    ctx.fill();
    
    // Arrow outline
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // Label background
    ctx.fillStyle = color;
    const labelY = arrowY - 30;
    const labelWidth = ctx.measureText(label).width + 16;
    const labelHeight = 20;
    const labelX = x - labelWidth / 2;
    
    // Rounded rectangle for label
    const radius = 4;
    ctx.beginPath();
    ctx.moveTo(labelX + radius, labelY);
    ctx.lineTo(labelX + labelWidth - radius, labelY);
    ctx.quadraticCurveTo(labelX + labelWidth, labelY, labelX + labelWidth, labelY + radius);
    ctx.lineTo(labelX + labelWidth, labelY + labelHeight - radius);
    ctx.quadraticCurveTo(labelX + labelWidth, labelY + labelHeight, labelX + labelWidth - radius, labelY + labelHeight);
    ctx.lineTo(labelX + radius, labelY + labelHeight);
    ctx.quadraticCurveTo(labelX, labelY + labelHeight, labelX, labelY + labelHeight - radius);
    ctx.lineTo(labelX, labelY + radius);
    ctx.quadraticCurveTo(labelX, labelY, labelX + radius, labelY);
    ctx.closePath();
    ctx.fill();
    
    // Label outline
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    
    // Label text
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 10px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, x, labelY + labelHeight / 2);
    
    ctx.globalAlpha = 1;
  };
  
  return (
    <canvas
      ref={canvasRef}
      width={600}
      height={400}
      className="soccer-field-canvas"
    />
  );
};

export default SoccerField;