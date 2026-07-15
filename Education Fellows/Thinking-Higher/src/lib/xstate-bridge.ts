"use client";

import {
  type AnyStateMachine,
  type AnyMachineSnapshot,
} from 'xstate';
import { useActor } from '@xstate/react';

/**
 * Hook to run a jsPsych2 experiment machine in a React component.
 *
 * Returns the current snapshot and a send function.
 * The component re-renders on every state transition.
 */
export function useExperiment<T extends AnyStateMachine>(
  machine: T,
  options?: { inspect?: boolean }
) {
  const [rawSnapshot, send, actorRef] = useActor(machine);

  // Cast to AnyMachineSnapshot to access .value, .status, .context, .children
  // This is safe because useActor(machine) always yields a MachineSnapshot.
  const snapshot = rawSnapshot as AnyMachineSnapshot;

  // Expose actor for console debugging (like the prototype does)
  if (typeof window !== 'undefined' && options?.inspect) {
    (window as any).__experimentActor = actorRef;
  }

  return {
    /** Current machine state value (e.g., 'instructions', { runningTrials: 'active' }) */
    state: snapshot.value,
    /** Full XState snapshot */
    snapshot,
    /** Send events to the machine */
    send,
    /** The underlying actor reference */
    actorRef,
    /** Whether the machine has reached a final state */
    isDone: snapshot.status === 'done',
    /** Machine context */
    context: snapshot.context,
    /** Get a child actor by ID */
    getChild: (id: string) => snapshot.children[id],
  };
}

/**
 * Helper to check if machine matches a specific state.
 * Works with nested states.
 */
export function matchesState(
  snapshot: AnyMachineSnapshot,
  stateValue: string
): boolean {
  return snapshot.matches(stateValue);
}

/**
 * Extract trial actor from an experiment snapshot.
 * Returns null if no trial is currently active.
 */
export function getTrialActor(snapshot: AnyMachineSnapshot) {
  return snapshot.children.currentTrial ?? null;
}
