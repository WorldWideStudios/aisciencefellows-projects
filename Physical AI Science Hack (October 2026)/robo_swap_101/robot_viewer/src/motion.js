export const JOINTS = ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll', 'gripper'];
export const HOME = Object.fromEntries(JOINTS.map(j => [j, j === 'gripper' ? 35 : 0]));
export const label = joint => joint.replaceAll('_', ' ').replace(/^./, x => x.toUpperCase());
export const timeLabel = seconds => `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, '0')}`;

// Evaluate the same server-planned polynomials, including Cartesian IK splines.
export function samplePlan(plan, time) {
  const t = Math.min(plan.duration, Math.max(0, time));
  let index = plan.segments.findIndex(s => t < s.start + s.move + s.dwell);
  if (index < 0) index = plan.segments.length - 1;
  const segment = plan.segments[index];
  const u = Math.min(1, Math.max(0, (t - segment.start) / segment.move));
  const s = u * u * u * (10 + u * (-15 + 6 * u));
  if (segment.curve) {
    if (u === 0) return { pose: { ...segment.from }, index };
    if (u === 1) return { pose: { ...segment.to }, index };
    const scaled = Math.min(1, Math.max(0, segment.reverse ? 1 - s : s)) * segment.curve.length;
    const piece = Math.min(Math.floor(scaled), segment.curve.length - 1);
    const v = scaled - piece;
    return { pose: Object.fromEntries(JOINTS.map(j => {
      const [a, b, c, d] = segment.curve[piece][j];
      return [j, ((a * v + b) * v + c) * v + d];
    })), index };
  }
  return { pose: Object.fromEntries(JOINTS.map(j => [j, segment.from[j] + (segment.to[j] - segment.from[j]) * s])), index };
}
