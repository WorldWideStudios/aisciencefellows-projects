"use client";

import { useRef, useCallback } from "react";
import { ARC_COLORS } from "./ARCColorPalette";

interface ARCGridProps {
  grid: number[][];
  editable?: boolean;
  selectedColor?: number;
  onCellClick?: (row: number, col: number) => void;
  label?: string;
  maxCellSize?: number;
}

export default function ARCGrid({
  grid,
  editable = false,
  selectedColor = 0,
  onCellClick,
  label,
  maxCellSize = 30,
}: ARCGridProps) {
  const isPaintingRef = useRef(false);

  const rows = grid.length;
  const cols = rows > 0 ? grid[0].length : 0;

  // Auto-size: shrink cells for grids larger than 10x10
  const maxDim = Math.max(rows, cols);
  const cellSize = maxDim > 10 ? Math.max(12, Math.floor(maxCellSize * 10 / maxDim)) : maxCellSize;

  const handleCellInteraction = useCallback(
    (row: number, col: number) => {
      if (editable && onCellClick) {
        onCellClick(row, col);
      }
    },
    [editable, onCellClick]
  );

  const handleMouseDown = useCallback(
    (row: number, col: number) => {
      if (!editable) return;
      isPaintingRef.current = true;
      handleCellInteraction(row, col);
    },
    [editable, handleCellInteraction]
  );

  const handleMouseEnter = useCallback(
    (row: number, col: number) => {
      if (!editable || !isPaintingRef.current) return;
      handleCellInteraction(row, col);
    },
    [editable, handleCellInteraction]
  );

  const handleMouseUp = useCallback(() => {
    isPaintingRef.current = false;
  }, []);

  // Stop painting if mouse leaves grid entirely
  const handleMouseLeave = useCallback(() => {
    isPaintingRef.current = false;
  }, []);

  return (
    <div style={{ display: "inline-flex", flexDirection: "column", gap: 6 }}>
      {label && (
        <div
          style={{
            fontFamily: "'Syne', sans-serif",
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase" as const,
            color: "var(--muted)",
          }}
        >
          {label}
        </div>
      )}
      <div
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        style={{
          display: "inline-grid",
          gridTemplateColumns: `repeat(${cols}, ${cellSize}px)`,
          gridTemplateRows: `repeat(${rows}, ${cellSize}px)`,
          gap: 1,
          background: "#111113",
          border: "1px solid var(--border)",
          borderRadius: 4,
          padding: 1,
          cursor: editable ? "crosshair" : "default",
          userSelect: "none",
        }}
      >
        {grid.map((row, r) =>
          row.map((val, c) => (
            <div
              key={`${r}-${c}`}
              onMouseDown={() => handleMouseDown(r, c)}
              onMouseEnter={() => handleMouseEnter(r, c)}
              style={{
                width: cellSize,
                height: cellSize,
                backgroundColor: ARC_COLORS[val] ?? ARC_COLORS[0],
                transition: "background-color 0.05s",
              }}
            />
          ))
        )}
      </div>
    </div>
  );
}
