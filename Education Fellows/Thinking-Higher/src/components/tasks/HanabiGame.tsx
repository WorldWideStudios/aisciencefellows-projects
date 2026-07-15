"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import type { HanabiTrialData, HanabiAction, TaskSummary } from "@/lib/types";

// ---------------------------------------------------------------------------
// Constants & Colors
// ---------------------------------------------------------------------------

const COLORS = ["Red", "Blue", "Green", "Yellow", "White"] as const;
type CardColor = (typeof COLORS)[number];

const COLOR_HEX: Record<CardColor, string> = {
  Red: "#FF4136",
  Blue: "#0074D9",
  Green: "#2ECC40",
  Yellow: "#FFDC00",
  White: "#FFFFFF",
};

const VALUES = [1, 2, 3, 4, 5] as const;
type CardValue = (typeof VALUES)[number];

// Card distribution per color: three 1s, two 2s, two 3s, two 4s, one 5
const VALUE_COUNTS: Record<CardValue, number> = { 1: 3, 2: 2, 3: 2, 4: 2, 5: 1 };

const HAND_SIZE = 5;
const MAX_HINTS = 8;
const MAX_MISTAKES = 3;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Card {
  id: number;
  color: CardColor;
  value: CardValue;
}

interface CardKnowledge {
  knownColor: CardColor | null;
  knownValue: CardValue | null;
  possibleColors: Set<CardColor>;
  possibleValues: Set<CardValue>;
}

interface GameState {
  deck: Card[];
  humanHand: Card[];
  aiHand: Card[];
  humanKnowledge: CardKnowledge[];
  aiKnowledge: CardKnowledge[];
  fireworks: Record<CardColor, number>;
  hints: number;
  mistakes: number;
  discardPile: Card[];
  currentPlayer: "human" | "ai";
  gameOver: boolean;
  finalRoundTriggered: boolean;
  finalRoundPlayer: "human" | "ai" | null;
  turnNumber: number;
}

type HintType = "color" | "value";

interface LogEntry {
  player: "human" | "ai";
  text: string;
  turnNumber: number;
}

interface HanabiGameProps {
  onComplete: (trials: HanabiTrialData[], summary: TaskSummary) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildDeck(): Card[] {
  const cards: Card[] = [];
  let id = 0;
  for (const color of COLORS) {
    for (const value of VALUES) {
      const count = VALUE_COUNTS[value];
      for (let i = 0; i < count; i++) {
        cards.push({ id: id++, color, value });
      }
    }
  }
  return shuffle(cards);
}

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function freshKnowledge(): CardKnowledge {
  return {
    knownColor: null,
    knownValue: null,
    possibleColors: new Set(COLORS),
    possibleValues: new Set(VALUES),
  };
}

function computeScore(fireworks: Record<CardColor, number>): number {
  return COLORS.reduce((s, c) => s + fireworks[c], 0);
}

function isPlayable(card: Card, fireworks: Record<CardColor, number>): boolean {
  return fireworks[card.color] === card.value - 1;
}

function initGame(): GameState {
  const deck = buildDeck();
  const humanHand = deck.splice(0, HAND_SIZE);
  const aiHand = deck.splice(0, HAND_SIZE);
  const fireworks: Record<CardColor, number> = {
    Red: 0,
    Blue: 0,
    Green: 0,
    Yellow: 0,
    White: 0,
  };
  return {
    deck,
    humanHand,
    aiHand,
    humanKnowledge: Array.from({ length: HAND_SIZE }, freshKnowledge),
    aiKnowledge: Array.from({ length: HAND_SIZE }, freshKnowledge),
    fireworks,
    hints: MAX_HINTS,
    mistakes: 0,
    discardPile: [],
    currentPlayer: "human",
    gameOver: false,
    finalRoundTriggered: false,
    finalRoundPlayer: null,
    turnNumber: 1,
  };
}

function drawCard(state: GameState): Card | null {
  if (state.deck.length === 0) return null;
  return state.deck.shift()!;
}

// ---------------------------------------------------------------------------
// AI Partner Logic
// ---------------------------------------------------------------------------

function aiDecide(state: GameState): {
  type: HanabiAction["type"];
  cardIndex?: number;
  hintTarget?: "human" | "ai";
  hintValue?: string;
} {
  const { aiHand, aiKnowledge, humanHand, fireworks, hints } = state;

  // 1. Play definitely playable card (known color + value)
  for (let i = 0; i < aiHand.length; i++) {
    const k = aiKnowledge[i];
    if (k.knownColor && k.knownValue) {
      const val = k.knownValue;
      const col = k.knownColor;
      if (fireworks[col] === val - 1) {
        return { type: "play", cardIndex: i };
      }
    }
  }

  // 1b. Play card if known value is 1 and some firework needs a 1
  for (let i = 0; i < aiHand.length; i++) {
    const k = aiKnowledge[i];
    if (k.knownValue === 1) {
      // Check if the actual card is playable (AI doesn't know color, but
      // if every possible color for this slot needs a 1, it's safe)
      const possibleColors = Array.from(k.possibleColors);
      const allPlayable = possibleColors.every((c) => fireworks[c] === 0);
      if (allPlayable) {
        return { type: "play", cardIndex: i };
      }
    }
  }

  // 2. Give hint to partner if they have a playable card and hints > 0
  if (hints > 0) {
    for (let i = 0; i < humanHand.length; i++) {
      const card = humanHand[i];
      if (isPlayable(card, fireworks)) {
        // Prefer hinting value for 1s, color for others
        if (card.value === 1) {
          return { type: "hint-value", hintTarget: "human", hintValue: String(card.value) };
        } else {
          return { type: "hint-color", hintTarget: "human", hintValue: card.color };
        }
      }
    }
  }

  // 3. Discard a known non-useful card if hints < MAX_HINTS
  if (hints < MAX_HINTS) {
    for (let i = 0; i < aiHand.length; i++) {
      const k = aiKnowledge[i];
      if (k.knownColor && k.knownValue) {
        const col = k.knownColor;
        const val = k.knownValue;
        // Already played or can never be played
        if (fireworks[col] >= val) {
          return { type: "discard", cardIndex: i };
        }
      }
    }
  }

  // 4. Discard oldest card
  if (hints < MAX_HINTS) {
    return { type: "discard", cardIndex: 0 };
  }

  // 5. If hints are full, give a useful hint or just hint about anything
  if (hints > 0) {
    for (let i = 0; i < humanHand.length; i++) {
      const card = humanHand[i];
      if (isPlayable(card, fireworks)) {
        return { type: "hint-color", hintTarget: "human", hintValue: card.color };
      }
    }
    // Hint about highest value card
    const card = humanHand[0];
    return { type: "hint-color", hintTarget: "human", hintValue: card.color };
  }

  // Fallback: discard oldest
  return { type: "discard", cardIndex: 0 };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function HanabiGame({ onComplete }: HanabiGameProps) {
  const [phase, setPhase] = useState<"instructions" | "playing" | "debrief">("instructions");
  const [game, setGame] = useState<GameState>(initGame);
  const [selectedCard, setSelectedCard] = useState<number | null>(null);
  const [hintMode, setHintMode] = useState(false);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [aiThinking, setAiThinking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const trialsRef = useRef<HanabiTrialData[]>([]);
  const turnStartRef = useRef<number>(Date.now());
  const hintsGivenRef = useRef(0);
  const hintsReceivedRef = useRef(0);
  const hintsLeadingToPlayRef = useRef(new Set<number>());
  const hintedCardIdsRef = useRef(new Set<number>());
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [log]);

  // ------ Trial recording ------

  const recordTrial = useCallback(
    (action: HanabiAction, gs: GameState) => {
      const now = Date.now();
      const trial: HanabiTrialData = {
        taskType: "hanabi",
        trialIndex: trialsRef.current.length,
        startedAt: turnStartRef.current,
        respondedAt: now,
        rt: now - turnStartRef.current,
        stimulusOnsetAt: turnStartRef.current,
        turnNumber: gs.turnNumber,
        action,
        gameState: {
          score: computeScore(gs.fireworks),
          hintsRemaining: gs.hints,
          mistakesRemaining: MAX_MISTAKES - gs.mistakes,
          fireworks: { ...gs.fireworks },
        },
      };
      trialsRef.current.push(trial);
    },
    []
  );

  // ------ Apply action to game state ------

  const applyAction = useCallback(
    (
      prev: GameState,
      actionType: HanabiAction["type"],
      cardIndex?: number,
      hintValue?: string
    ): { next: GameState; logText: string; action: HanabiAction } => {
      const state: GameState = {
        ...prev,
        deck: [...prev.deck],
        humanHand: [...prev.humanHand],
        aiHand: [...prev.aiHand],
        humanKnowledge: prev.humanKnowledge.map((k) => ({
          ...k,
          possibleColors: new Set(k.possibleColors),
          possibleValues: new Set(k.possibleValues),
        })),
        aiKnowledge: prev.aiKnowledge.map((k) => ({
          ...k,
          possibleColors: new Set(k.possibleColors),
          possibleValues: new Set(k.possibleValues),
        })),
        fireworks: { ...prev.fireworks },
        discardPile: [...prev.discardPile],
      };

      const player = state.currentPlayer;
      const hand = player === "human" ? state.humanHand : state.aiHand;
      const knowledge = player === "human" ? state.humanKnowledge : state.aiKnowledge;
      let logText = "";
      const now = Date.now();

      const action: HanabiAction = {
        type: actionType,
        player,
        cardIndex,
        hintValue,
        hintTarget: actionType.startsWith("hint") ? (player === "human" ? "ai" : "human") : undefined,
        timestamp: now,
      };

      if (actionType === "play" && cardIndex != null) {
        const card = hand[cardIndex];
        if (isPlayable(card, state.fireworks)) {
          state.fireworks[card.color] = card.value;
          logText = `${player === "human" ? "You" : "AI"} played ${card.color} ${card.value} -- success!`;
          // Track if this card was previously hinted
          if (hintedCardIdsRef.current.has(card.id)) {
            hintsLeadingToPlayRef.current.add(card.id);
          }
          // Bonus hint for completing a firework
          if (card.value === 5 && state.hints < MAX_HINTS) {
            state.hints++;
          }
        } else {
          state.mistakes++;
          state.discardPile.push(card);
          logText = `${player === "human" ? "You" : "AI"} played ${card.color} ${card.value} -- mistake! (${MAX_MISTAKES - state.mistakes} fuses left)`;
        }
        hand.splice(cardIndex, 1);
        knowledge.splice(cardIndex, 1);
        const drawn = drawCard(state);
        if (drawn) {
          hand.push(drawn);
          knowledge.push(freshKnowledge());
        }
        if (!state.finalRoundTriggered && state.deck.length === 0) {
          state.finalRoundTriggered = true;
          state.finalRoundPlayer = state.currentPlayer;
        }
      } else if (actionType === "discard" && cardIndex != null) {
        const card = hand[cardIndex];
        state.discardPile.push(card);
        if (state.hints < MAX_HINTS) state.hints++;
        logText = `${player === "human" ? "You" : "AI"} discarded ${card.color} ${card.value} (+1 hint)`;
        hand.splice(cardIndex, 1);
        knowledge.splice(cardIndex, 1);
        const drawn = drawCard(state);
        if (drawn) {
          hand.push(drawn);
          knowledge.push(freshKnowledge());
        }
        if (!state.finalRoundTriggered && state.deck.length === 0) {
          state.finalRoundTriggered = true;
          state.finalRoundPlayer = state.currentPlayer;
        }
      } else if (actionType === "hint-color" && hintValue) {
        const targetHand = player === "human" ? state.aiHand : state.humanHand;
        const targetKnowledge = player === "human" ? state.aiKnowledge : state.humanKnowledge;
        const color = hintValue as CardColor;
        const matchIndices: number[] = [];
        for (let i = 0; i < targetHand.length; i++) {
          if (targetHand[i].color === color) {
            targetKnowledge[i].knownColor = color;
            targetKnowledge[i].possibleColors = new Set([color]);
            matchIndices.push(i + 1);
            hintedCardIdsRef.current.add(targetHand[i].id);
          } else {
            targetKnowledge[i].possibleColors.delete(color);
          }
        }
        state.hints--;
        if (player === "human") hintsGivenRef.current++;
        else hintsReceivedRef.current++;
        logText = `${player === "human" ? "You" : "AI"} hinted: "${color}" cards at position(s) ${matchIndices.join(", ")}`;
      } else if (actionType === "hint-value" && hintValue) {
        const targetHand = player === "human" ? state.aiHand : state.humanHand;
        const targetKnowledge = player === "human" ? state.aiKnowledge : state.humanKnowledge;
        const val = Number(hintValue) as CardValue;
        const matchIndices: number[] = [];
        for (let i = 0; i < targetHand.length; i++) {
          if (targetHand[i].value === val) {
            targetKnowledge[i].knownValue = val;
            targetKnowledge[i].possibleValues = new Set([val]);
            matchIndices.push(i + 1);
            hintedCardIdsRef.current.add(targetHand[i].id);
          } else {
            targetKnowledge[i].possibleValues.delete(val);
          }
        }
        state.hints--;
        if (player === "human") hintsGivenRef.current++;
        else hintsReceivedRef.current++;
        logText = `${player === "human" ? "You" : "AI"} hinted: "${val}" cards at position(s) ${matchIndices.join(", ")}`;
      }

      // Check game end conditions
      const score = computeScore(state.fireworks);
      if (score === 25) {
        state.gameOver = true;
      } else if (state.mistakes >= MAX_MISTAKES) {
        state.gameOver = true;
      } else if (
        state.finalRoundTriggered &&
        state.currentPlayer !== state.finalRoundPlayer &&
        // The other player has had their final turn
        player !== state.finalRoundPlayer
      ) {
        state.gameOver = true;
      }

      // Advance turn
      if (!state.gameOver) {
        state.currentPlayer = state.currentPlayer === "human" ? "ai" : "human";
        if (state.currentPlayer === "human") {
          state.turnNumber++;
        }
      }

      // Reassign mutated arrays back
      if (player === "human") {
        state.humanHand = hand;
        state.humanKnowledge = knowledge;
      } else {
        state.aiHand = hand;
        state.aiKnowledge = knowledge;
      }

      return { next: state, logText, action };
    },
    []
  );

  // ------ End game ------

  const endGame = useCallback(
    (finalState: GameState) => {
      const score = computeScore(finalState.fireworks);
      const totalTurns = finalState.turnNumber;
      const totalHintsGiven = hintsGivenRef.current;
      const totalHintsReceived = hintsReceivedRef.current;
      const mistakesMade = finalState.mistakes;
      const cardsPlayed = COLORS.reduce((s, c) => s + finalState.fireworks[c], 0);
      const totalHintedCards = hintedCardIdsRef.current.size;
      const hintEfficiency =
        totalHintedCards > 0
          ? Math.round((hintsLeadingToPlayRef.current.size / totalHintedCards) * 100)
          : 0;

      const trials = trialsRef.current;
      const rts = trials.filter((t) => t.action.player === "human").map((t) => t.rt);
      const meanRT = rts.length > 0 ? Math.round(rts.reduce((a, b) => a + b, 0) / rts.length) : 0;

      const summary: TaskSummary = {
        totalTrials: trials.length,
        completedTrials: trials.length,
        meanRT,
        accuracy: Math.round((score / 25) * 100),
        finalScore: score,
        totalTurns,
        hintsGiven: totalHintsGiven,
        hintsReceived: totalHintsReceived,
        mistakes: mistakesMade,
        cardsPlayed,
        hintEfficiency,
      };

      onComplete(trials, summary);
    },
    [onComplete]
  );

  // ------ Human actions ------

  const handlePlay = useCallback(() => {
    if (selectedCard == null || game.currentPlayer !== "human" || game.gameOver || aiThinking) return;
    const { next, logText, action } = applyAction(game, "play", selectedCard);
    recordTrial(action, next);
    setLog((prev) => [...prev, { player: "human", text: logText, turnNumber: next.turnNumber }]);
    setSelectedCard(null);
    setHintMode(false);
    setGame(next);
    if (next.gameOver) {
      endGame(next);
      setPhase("debrief");
      return;
    }
    if (next.currentPlayer === "ai") {
      turnStartRef.current = Date.now();
      runAiTurn(next);
    }
  }, [selectedCard, game, aiThinking, applyAction, recordTrial, endGame]);

  const handleDiscard = useCallback(() => {
    if (selectedCard == null || game.currentPlayer !== "human" || game.gameOver || aiThinking) return;
    const { next, logText, action } = applyAction(game, "discard", selectedCard);
    recordTrial(action, next);
    setLog((prev) => [...prev, { player: "human", text: logText, turnNumber: next.turnNumber }]);
    setSelectedCard(null);
    setHintMode(false);
    setGame(next);
    if (next.gameOver) {
      endGame(next);
      setPhase("debrief");
      return;
    }
    if (next.currentPlayer === "ai") {
      turnStartRef.current = Date.now();
      runAiTurn(next);
    }
  }, [selectedCard, game, aiThinking, applyAction, recordTrial, endGame]);

  const handleHint = useCallback(
    (hintType: HintType, hintValue: string) => {
      if (game.currentPlayer !== "human" || game.gameOver || aiThinking || game.hints <= 0) return;
      const actionType = hintType === "color" ? "hint-color" : "hint-value";
      const { next, logText, action } = applyAction(game, actionType, undefined, hintValue);
      recordTrial(action, next);
      setLog((prev) => [...prev, { player: "human", text: logText, turnNumber: next.turnNumber }]);
      setSelectedCard(null);
      setHintMode(false);
      setGame(next);
      if (next.gameOver) {
        endGame(next);
        setPhase("debrief");
        return;
      }
      if (next.currentPlayer === "ai") {
        turnStartRef.current = Date.now();
        runAiTurn(next);
      }
    },
    [game, aiThinking, applyAction, recordTrial, endGame]
  );

  // ------ AI turn ------

  const runAiTurn = useCallback(
    (currentState: GameState) => {
      setAiThinking(true);
      // Brief delay so the player can see what's happening
      setTimeout(() => {
        const decision = aiDecide(currentState);
        const { next, logText, action } = applyAction(
          currentState,
          decision.type,
          decision.cardIndex,
          decision.hintValue
        );
        recordTrial(action, next);
        setLog((prev) => [...prev, { player: "ai", text: logText, turnNumber: next.turnNumber }]);
        setGame(next);
        setAiThinking(false);
        turnStartRef.current = Date.now();
        if (next.gameOver) {
          endGame(next);
          setPhase("debrief");
        }
      }, 800);
    },
    [applyAction, recordTrial, endGame]
  );

  // eslint-disable-next-line react-hooks/exhaustive-deps -- runAiTurn depends on stable refs
  const handlePlayMemo = handlePlay;
  const handleDiscardMemo = handleDiscard;

  const showMessage = useCallback((msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(null), 2000);
  }, []);

  // ------ Styles ------

  const styles = {
    container: {
      display: "flex",
      flexDirection: "column" as const,
      height: "100%",
      background: "var(--bg)",
      color: "var(--text)",
      fontFamily: "'IBM Plex Mono', monospace",
      overflow: "hidden",
    },
    header: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "12px 20px",
      borderBottom: "1px solid var(--border)",
      background: "var(--surface)",
      flexShrink: 0,
    },
    title: {
      fontFamily: "'Syne', sans-serif",
      fontWeight: 700,
      fontSize: "16px",
      color: "var(--accent)",
    },
    statusBar: {
      display: "flex",
      gap: "20px",
      alignItems: "center",
      fontSize: "11px",
    },
    tokenRow: {
      display: "flex",
      gap: "4px",
      alignItems: "center",
    },
    tokenDot: (active: boolean, color: string) => ({
      width: "10px",
      height: "10px",
      borderRadius: "50%",
      background: active ? color : "var(--border)",
      transition: "background 0.3s",
    }),
    gameArea: {
      flex: 1,
      display: "flex",
      flexDirection: "column" as const,
      overflow: "hidden",
      padding: "12px 20px",
      gap: "12px",
    },
    sectionLabel: {
      fontSize: "9px",
      letterSpacing: "0.2em",
      textTransform: "uppercase" as const,
      color: "var(--muted)",
      marginBottom: "6px",
    },
    fireworksRow: {
      display: "flex",
      gap: "8px",
      justifyContent: "center",
      flexWrap: "wrap" as const,
    },
    fireworkPile: (color: string) => ({
      width: "56px",
      height: "72px",
      borderRadius: "8px",
      border: `2px solid ${color}44`,
      background: "var(--surface)",
      display: "flex",
      flexDirection: "column" as const,
      alignItems: "center",
      justifyContent: "center",
      gap: "2px",
    }),
    fireworkValue: (color: string) => ({
      fontSize: "20px",
      fontWeight: 700,
      color,
      fontFamily: "'Syne', sans-serif",
    }),
    fireworkLabel: (color: string) => ({
      fontSize: "8px",
      color,
      textTransform: "uppercase" as const,
      letterSpacing: "0.1em",
    }),
    handRow: {
      display: "flex",
      gap: "8px",
      justifyContent: "center",
      flexWrap: "wrap" as const,
    },
    card: (color: string, selected: boolean, faceUp: boolean) => ({
      width: "60px",
      height: "84px",
      borderRadius: "8px",
      border: selected
        ? "2px solid var(--accent)"
        : faceUp
          ? `2px solid ${color}88`
          : "2px solid var(--border)",
      background: faceUp ? `${color}22` : "var(--surface2)",
      display: "flex",
      flexDirection: "column" as const,
      alignItems: "center",
      justifyContent: "center",
      cursor: "pointer",
      transition: "border-color 0.2s, transform 0.15s",
      transform: selected ? "translateY(-4px)" : "none",
      position: "relative" as const,
    }),
    cardValue: (color: string, faceUp: boolean) => ({
      fontSize: "22px",
      fontWeight: 700,
      fontFamily: "'Syne', sans-serif",
      color: faceUp ? color : "var(--muted)",
    }),
    cardColor: (color: string) => ({
      fontSize: "8px",
      color,
      textTransform: "uppercase" as const,
      letterSpacing: "0.05em",
    }),
    knowledgeTag: {
      position: "absolute" as const,
      bottom: "4px",
      fontSize: "7px",
      color: "var(--accent)",
      maxWidth: "52px",
      textAlign: "center" as const,
      lineHeight: "1.2",
    },
    actionBar: {
      display: "flex",
      gap: "8px",
      justifyContent: "center",
      flexWrap: "wrap" as const,
      padding: "8px 0",
    },
    btn: (disabled: boolean, variant: "default" | "accent" | "danger" = "default") => ({
      padding: "8px 16px",
      borderRadius: "8px",
      border:
        variant === "accent"
          ? "1px solid var(--accent)"
          : variant === "danger"
            ? "1px solid var(--danger)"
            : "1px solid var(--border)",
      background:
        variant === "accent"
          ? "var(--accent)"
          : variant === "danger"
            ? "var(--danger)"
            : "transparent",
      color:
        variant === "accent" || variant === "danger"
          ? "var(--bg)"
          : "var(--text)",
      fontFamily: "'Syne', sans-serif",
      fontSize: "11px",
      fontWeight: 600,
      cursor: disabled ? "not-allowed" : "pointer",
      opacity: disabled ? 0.3 : 1,
      letterSpacing: "0.05em",
      transition: "opacity 0.2s",
    }),
    hintPanel: {
      display: "flex",
      gap: "6px",
      justifyContent: "center",
      flexWrap: "wrap" as const,
      padding: "8px",
      background: "var(--surface)",
      borderRadius: "8px",
      border: "1px solid var(--border)",
    },
    hintBtn: (color?: string) => ({
      padding: "6px 12px",
      borderRadius: "6px",
      border: "1px solid var(--border)",
      background: color ? `${color}22` : "var(--surface2)",
      color: color || "var(--text)",
      fontFamily: "'IBM Plex Mono', monospace",
      fontSize: "11px",
      fontWeight: 500,
      cursor: "pointer",
      transition: "background 0.2s",
    }),
    logContainer: {
      flex: 1,
      minHeight: "80px",
      maxHeight: "140px",
      overflowY: "auto" as const,
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "8px",
      padding: "8px 12px",
      fontSize: "10px",
      lineHeight: "1.6",
    },
    logEntry: (player: "human" | "ai") => ({
      color: player === "human" ? "var(--accent)" : "var(--accent2)",
      marginBottom: "2px",
    }),
    messageOverlay: {
      position: "fixed" as const,
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      background: "var(--surface)",
      border: "1px solid var(--accent)",
      borderRadius: "12px",
      padding: "16px 28px",
      fontSize: "14px",
      fontWeight: 600,
      color: "var(--accent)",
      fontFamily: "'Syne', sans-serif",
      zIndex: 100,
      animation: "fadeUp 0.3s ease forwards",
    },
    turnIndicator: {
      fontSize: "11px",
      color: "var(--muted)",
      textAlign: "center" as const,
      padding: "4px",
    },
    instructionsCard: {
      maxWidth: "600px",
      margin: "0 auto",
      padding: "32px",
    },
    instructionsTitle: {
      fontFamily: "'Syne', sans-serif",
      fontWeight: 700,
      fontSize: "24px",
      color: "var(--accent)",
      marginBottom: "16px",
    },
    instructionsBody: {
      fontSize: "12.5px",
      lineHeight: "1.75",
      color: "var(--muted)",
      marginBottom: "24px",
      whiteSpace: "pre-line" as const,
    },
  };

  // ------ Instructions screen ------

  if (phase === "instructions") {
    return (
      <div style={styles.container}>
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "24px" }}>
          <div style={styles.instructionsCard}>
            <div style={{ fontSize: "10px", letterSpacing: "0.2em", textTransform: "uppercase", color: "var(--accent)", marginBottom: "16px" }}>
              Theory of Mind Task
            </div>
            <h1 style={styles.instructionsTitle}>Hanabi</h1>
            <div style={styles.instructionsBody}>
              {`Hanabi is a cooperative card game. You and an AI partner work together to build 5 firework displays (one per color, stacking 1 -> 2 -> 3 -> 4 -> 5).

The catch: you can see your partner's cards but NOT your own! You must use limited hint tokens to communicate.

On your turn, you can:
  - Play a card (if it fits a firework pile, great -- if not, you lose a fuse!)
  - Discard a card (regains a hint token)
  - Give a hint to your partner (costs a hint token)

You have 8 hints and 3 fuses. Perfect score is 25. Good luck!`}
            </div>
            <button
              style={styles.btn(false, "accent")}
              onClick={() => {
                setPhase("playing");
                turnStartRef.current = Date.now();
              }}
            >
              Start Game
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ------ Debrief screen ------

  if (phase === "debrief") {
    const score = computeScore(game.fireworks);
    return (
      <div style={styles.container}>
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "24px" }}>
          <div style={styles.instructionsCard}>
            <div style={{ fontSize: "10px", letterSpacing: "0.2em", textTransform: "uppercase", color: "var(--accent)", marginBottom: "16px" }}>
              Game Complete
            </div>
            <h1 style={styles.instructionsTitle}>
              Final Score: {score} / 25
            </h1>
            <div style={{ ...styles.fireworksRow, marginBottom: "24px" }}>
              {COLORS.map((c) => (
                <div key={c} style={styles.fireworkPile(COLOR_HEX[c])}>
                  <div style={styles.fireworkValue(COLOR_HEX[c])}>
                    {game.fireworks[c] || "-"}
                  </div>
                  <div style={styles.fireworkLabel(COLOR_HEX[c])}>{c}</div>
                </div>
              ))}
            </div>
            <div style={styles.instructionsBody}>
              {`Hanabi measures theory of mind -- your ability to reason about what others know and what information they need.

Key cognitive skills tested:
  - Perspective-taking: Understanding what your partner can see about YOUR cards
  - Information integration: Combining multiple hints to determine your cards
  - Strategic communication: Choosing the most informative hints to give

In human-AI studies, people often preferred playing with rule-based AI partners over more sophisticated RL agents, finding them more predictable and trustworthy.`}
            </div>
            <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", fontSize: "11px", color: "var(--muted)", marginBottom: "24px" }}>
              <span>Turns: {game.turnNumber}</span>
              <span>Hints given: {hintsGivenRef.current}</span>
              <span>Hints received: {hintsReceivedRef.current}</span>
              <span>Mistakes: {game.mistakes}</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ------ Game screen ------

  const score = computeScore(game.fireworks);
  const isHumanTurn = game.currentPlayer === "human" && !aiThinking && !game.gameOver;

  // Determine which colors & values exist in AI's hand (for hint panel)
  const aiColors = new Set(game.aiHand.map((c) => c.color));
  const aiValues = new Set(game.aiHand.map((c) => c.value));

  return (
    <div style={styles.container}>
      {/* Header / Status */}
      <div style={styles.header}>
        <div style={styles.title}>Hanabi</div>
        <div style={styles.statusBar}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ color: "var(--muted)" }}>Score</span>
            <span style={{ color: "var(--accent)", fontWeight: 700 }}>{score}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ color: "var(--muted)" }}>Hints</span>
            <div style={styles.tokenRow}>
              {Array.from({ length: MAX_HINTS }, (_, i) => (
                <div key={i} style={styles.tokenDot(i < game.hints, "var(--accent2)")} />
              ))}
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ color: "var(--muted)" }}>Fuses</span>
            <div style={styles.tokenRow}>
              {Array.from({ length: MAX_MISTAKES }, (_, i) => (
                <div key={i} style={styles.tokenDot(i < MAX_MISTAKES - game.mistakes, "var(--danger)")} />
              ))}
            </div>
          </div>
          <div style={{ color: "var(--muted)" }}>
            Deck: {game.deck.length}
          </div>
        </div>
      </div>

      <div style={styles.gameArea}>
        {/* Fireworks */}
        <div>
          <div style={styles.sectionLabel}>Fireworks</div>
          <div style={styles.fireworksRow}>
            {COLORS.map((c) => (
              <div key={c} style={styles.fireworkPile(COLOR_HEX[c])}>
                <div style={styles.fireworkValue(COLOR_HEX[c])}>
                  {game.fireworks[c] || "-"}
                </div>
                <div style={styles.fireworkLabel(COLOR_HEX[c])}>{c}</div>
              </div>
            ))}
          </div>
        </div>

        {/* AI's hand (visible to human) */}
        <div>
          <div style={styles.sectionLabel}>AI Partner&apos;s Hand (visible to you)</div>
          <div style={styles.handRow}>
            {game.aiHand.map((card, i) => (
              <div
                key={card.id}
                style={styles.card(COLOR_HEX[card.color], false, true)}
              >
                <div style={styles.cardValue(COLOR_HEX[card.color], true)}>
                  {card.value}
                </div>
                <div style={styles.cardColor(COLOR_HEX[card.color])}>
                  {card.color}
                </div>
                {/* Show what AI knows about this card */}
                {(game.aiKnowledge[i]?.knownColor || game.aiKnowledge[i]?.knownValue) && (
                  <div style={styles.knowledgeTag}>
                    {game.aiKnowledge[i]?.knownColor && game.aiKnowledge[i]?.knownValue
                      ? "Known"
                      : game.aiKnowledge[i]?.knownColor
                        ? `Knows: ${game.aiKnowledge[i].knownColor}`
                        : `Knows: ${game.aiKnowledge[i].knownValue}`}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Your hand (face-down with hints) */}
        <div>
          <div style={styles.sectionLabel}>Your Hand (hidden from you)</div>
          <div style={styles.handRow}>
            {game.humanHand.map((card, i) => {
              const k = game.humanKnowledge[i];
              const hasInfo = k && (k.knownColor || k.knownValue);
              const displayColor = k?.knownColor ? COLOR_HEX[k.knownColor] : "var(--muted)";
              return (
                <div
                  key={card.id}
                  style={styles.card(displayColor, selectedCard === i, false)}
                  onClick={() => {
                    if (!isHumanTurn) return;
                    setSelectedCard(selectedCard === i ? null : i);
                    setHintMode(false);
                  }}
                >
                  <div style={styles.cardValue(displayColor, false)}>
                    {k?.knownValue || "?"}
                  </div>
                  {hasInfo && (
                    <div style={{ ...styles.knowledgeTag, color: displayColor }}>
                      {k.knownColor || ""} {k.knownValue || ""}
                    </div>
                  )}
                  {!hasInfo && (
                    <div style={{ ...styles.knowledgeTag, color: "var(--muted)" }}>
                      #{i + 1}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Turn indicator */}
        <div style={styles.turnIndicator}>
          {game.gameOver
            ? "Game Over"
            : aiThinking
              ? "AI is thinking..."
              : isHumanTurn
                ? "Your turn -- select a card or give a hint"
                : ""}
        </div>

        {/* Action buttons */}
        <div style={styles.actionBar}>
          <button
            style={styles.btn(!isHumanTurn || selectedCard == null)}
            onClick={() => {
              if (!isHumanTurn || selectedCard == null) {
                if (isHumanTurn && selectedCard == null) showMessage("Select a card first");
                return;
              }
              handlePlayMemo();
            }}
          >
            Play Card
          </button>
          <button
            style={styles.btn(!isHumanTurn || selectedCard == null)}
            onClick={() => {
              if (!isHumanTurn || selectedCard == null) {
                if (isHumanTurn && selectedCard == null) showMessage("Select a card first");
                return;
              }
              handleDiscardMemo();
            }}
          >
            Discard
          </button>
          <button
            style={styles.btn(!isHumanTurn || game.hints <= 0)}
            onClick={() => {
              if (!isHumanTurn || game.hints <= 0) {
                if (isHumanTurn && game.hints <= 0) showMessage("No hints remaining");
                return;
              }
              setHintMode(!hintMode);
              setSelectedCard(null);
            }}
          >
            Give Hint {hintMode ? "(cancel)" : ""}
          </button>
        </div>

        {/* Hint panel */}
        {hintMode && isHumanTurn && (
          <div style={styles.hintPanel}>
            <span style={{ fontSize: "9px", color: "var(--muted)", letterSpacing: "0.1em", textTransform: "uppercase", alignSelf: "center", marginRight: "8px" }}>
              Color:
            </span>
            {COLORS.filter((c) => aiColors.has(c)).map((c) => (
              <button
                key={c}
                style={styles.hintBtn(COLOR_HEX[c])}
                onClick={() => handleHint("color", c)}
              >
                {c}
              </button>
            ))}
            <span style={{ fontSize: "9px", color: "var(--muted)", letterSpacing: "0.1em", textTransform: "uppercase", alignSelf: "center", marginLeft: "12px", marginRight: "8px" }}>
              Value:
            </span>
            {VALUES.filter((v) => aiValues.has(v)).map((v) => (
              <button
                key={v}
                style={styles.hintBtn()}
                onClick={() => handleHint("value", String(v))}
              >
                {v}
              </button>
            ))}
          </div>
        )}

        {/* Game log */}
        <div>
          <div style={styles.sectionLabel}>Game Log</div>
          <div style={styles.logContainer}>
            {log.length === 0 && (
              <div style={{ color: "var(--muted)" }}>Game started. Your turn!</div>
            )}
            {log.map((entry, i) => (
              <div key={i} style={styles.logEntry(entry.player)}>
                <span style={{ color: "var(--muted)", marginRight: "6px" }}>
                  T{entry.turnNumber}
                </span>
                {entry.text}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      </div>

      {/* Floating message */}
      {message && <div style={styles.messageOverlay}>{message}</div>}
    </div>
  );
}
