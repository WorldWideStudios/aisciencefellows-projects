// Pixel-art grey wizard: the Athelas Apothecary mark. Drawn on a 16 x 18 grid.
const PIXELS = [
  ".......h........",
  "......hh........",
  "......hhH....y..",
  ".....hhhH...yGy.",
  ".....hhhH....y..",
  "...hhhhhhhH..w..",
  "..hhhhhhhhhH.w..",
  ".....sssss...w..",
  ".....sesek...w..",
  ".....bssskb..w..",
  "....bbbbbbbbrw..",
  "...rbbbbbbbrrw..",
  "...rrbbbbbrr.w..",
  "..rrrrbbbrrrRw..",
  "..rrrrrbrrrrRw..",
  "..rrrrrrrrrrRw..",
  "..rrrrrrrrrrRw..",
  "..RRRR...RRRRw..",
];
const PALETTE: Record<string, string> = {
  h: "#8d969e", H: "#6c757d", s: "#e9c6a3", e: "#22302d", k: "#d7ac87", b: "#f3f3ef",
  r: "#a3abb2", R: "#7d858c", w: "#7a5532", y: "#ffe9a3", G: "#ffcf5c",
};

const GLOW = new Set(["y", "G"]);

export default function WizardMark({ size = 40 }: { size?: number }) {
  const pixel = (keep: (ch: string) => boolean) =>
    PIXELS.flatMap((row, y) =>
      [...row].map((ch, x) => (PALETTE[ch] && keep(ch)
        ? <rect key={`${x}-${y}`} x={x} y={y} width={1} height={1} fill={PALETTE[ch]} /> : null)),
    );
  return (
    <svg width={size} height={(size * 18) / 16} viewBox="0 0 16 18" shapeRendering="crispEdges" aria-hidden="true" overflow="visible">
      {pixel((ch) => !GLOW.has(ch))}
      {/* the lamp at the top of the staff glows on its own (see .staff-glow) */}
      <g className="staff-glow">{pixel((ch) => GLOW.has(ch))}</g>
    </svg>
  );
}
