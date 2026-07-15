"use client";

const ARC_COLORS: string[] = [
  "#000000", // 0: black
  "#0074D9", // 1: blue
  "#FF4136", // 2: red
  "#2ECC40", // 3: green
  "#FFDC00", // 4: yellow
  "#AAAAAA", // 5: grey
  "#F012BE", // 6: magenta
  "#FF851B", // 7: orange
  "#7FDBFF", // 8: cyan
  "#870C25", // 9: maroon
];

export { ARC_COLORS };

interface ARCColorPaletteProps {
  selectedColor: number;
  onSelectColor: (color: number) => void;
}

export default function ARCColorPalette({
  selectedColor,
  onSelectColor,
}: ARCColorPaletteProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        gap: 4,
        alignItems: "center",
      }}
    >
      {ARC_COLORS.map((hex, i) => {
        const isSelected = i === selectedColor;
        // Use light text for dark backgrounds, dark text for light ones
        const textColor = [0, 1, 2, 6, 9].includes(i) ? "#ffffff" : "#000000";
        return (
          <button
            key={i}
            onClick={() => onSelectColor(i)}
            style={{
              width: 36,
              height: 36,
              backgroundColor: hex,
              border: isSelected
                ? "2px solid var(--accent)"
                : "2px solid var(--border)",
              borderRadius: 4,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 11,
              fontWeight: 600,
              color: textColor,
              transition: "border-color 0.15s, transform 0.1s",
              transform: isSelected ? "scale(1.1)" : "scale(1)",
              boxShadow: isSelected
                ? "0 0 0 1px var(--accent)"
                : "none",
              padding: 0,
              outline: "none",
            }}
            aria-label={`Color ${i}`}
          >
            {i}
          </button>
        );
      })}
    </div>
  );
}
