const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [0, 17], [17, 18], [18, 19], [19, 20],
];

export function clear(ctx) {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
}

/** Draw the 21-point hand skeleton (normalised coordinates). */
export function drawHand(ctx, landmarks, { color = '#5eead4', highlight = null } = {}) {
  if (!landmarks) return;
  const { width, height } = ctx.canvas;

  ctx.lineWidth = 3;
  ctx.strokeStyle = color;
  ctx.beginPath();
  for (const [a, b] of HAND_CONNECTIONS) {
    ctx.moveTo(landmarks[a][0] * width, landmarks[a][1] * height);
    ctx.lineTo(landmarks[b][0] * width, landmarks[b][1] * height);
  }
  ctx.stroke();

  landmarks.forEach(([x, y], index) => {
    ctx.beginPath();
    ctx.fillStyle = index === highlight ? '#f97316' : '#ffffff';
    ctx.arc(x * width, y * height, index === highlight ? 9 : 4, 0, Math.PI * 2);
    ctx.fill();
  });
}

/** Draw a trajectory of [t, x, y, z] points as a glowing ink line. */
export function drawTrajectory(ctx, points, { color = '#f97316', width: lineWidth = 5 } = {}) {
  if (!points || points.length < 2) return;
  const { width, height } = ctx.canvas;

  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.shadowColor = color;
  ctx.shadowBlur = 12;
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.beginPath();
  ctx.moveTo(points[0][1] * width, points[0][2] * height);
  for (let i = 1; i < points.length; i += 1) {
    ctx.lineTo(points[i][1] * width, points[i][2] * height);
  }
  ctx.stroke();
  ctx.restore();
}

/**
 * Build an SVG path for a small preview of a trajectory, fitted into a
 * size x size box and mirrored to match the selfie view.
 */
export function trajectoryPreviewPath(points, size = 80, padding = 8) {
  if (!points || points.length < 2) return '';
  const xs = points.map((p) => p[1]);
  const ys = points.map((p) => p[2]);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const span = Math.max(Math.max(...xs) - minX, Math.max(...ys) - minY) || 1;
  const scale = (size - 2 * padding) / span;

  return points
    .map((p, i) => {
      const x = size - (padding + (p[1] - minX) * scale);
      const y = padding + (p[2] - minY) * scale;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * canvasDrawing.js contains the drawing helpers for the camera overlay: the
 * 21-landmark hand skeleton (with an optional highlighted landmark such as
 * the index fingertip), the live air-signature ink trail, and an SVG path
 * generator for the small mirrored signature thumbnails shown during
 * registration.
 * ========================================================================== */
