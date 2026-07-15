"use client";

import { setup, assign } from 'xstate';
import { useActor } from '@xstate/react';

// Define a simple bandit trial machine inline (will later import from jsPsych2)
const banditTrialMachine = setup({
  actions: {
    recordStimulusOnset: assign({
      stimulusOnsetTime: () => performance.now(),
    }),
    processChoice: assign(({ context, event }: any) => {
      const arm = event.arm as 0 | 1;
      const reward = Math.random() < context.rewardProbabilities[arm] ? 1 : 0;
      const rt = performance.now() - context.stimulusOnsetTime;
      const newQ = [...context.qValues] as [number, number];
      newQ[arm] += context.alpha * (reward - newQ[arm]);
      return {
        chosenArm: arm,
        reward,
        rt,
        updatedQValues: newQ,
      };
    }),
  },
}).createMachine({
  id: 'banditTrial',
  initial: 'fixation',
  context: ({ input }: any) => ({
    trialIndex: input.trialIndex,
    rewardProbabilities: input.rewardProbabilities,
    qValues: input.qValues,
    alpha: input.alpha ?? 0.1,
    stimulusOnsetTime: null as number | null,
    chosenArm: null as 0 | 1 | null,
    reward: null as 0 | 1 | null,
    rt: null as number | null,
    updatedQValues: input.qValues,
  }),
  states: {
    fixation: {
      after: { 500: 'stimulus' },
    },
    stimulus: {
      entry: 'recordStimulusOnset',
      on: {
        CHOOSE: {
          target: 'feedback',
          actions: 'processChoice',
        },
      },
    },
    feedback: {
      after: { 1500: 'done' },
    },
    done: { type: 'final' },
  },
  output: ({ context }: any) => ({
    trialIndex: context.trialIndex,
    chosenArm: context.chosenArm,
    reward: context.reward,
    rt: context.rt,
    rewardProbabilities: context.rewardProbabilities,
    qValues: context.qValues,
    updatedQValues: context.updatedQValues,
  }),
});

// The React component just renders based on machine state
export default function BanditXState() {
  const [snapshot, send] = useActor(banditTrialMachine, {
    input: {
      trialIndex: 0,
      rewardProbabilities: [0.7, 0.3] as [number, number],
      qValues: [0.5, 0.5] as [number, number],
      alpha: 0.1,
    },
  });

  const state = snapshot.value;
  const ctx = snapshot.context;

  // Fixation
  if (state === 'fixation') {
    return (
      <div className="task-container">
        <div style={{ fontSize: 48, color: 'var(--text)', textAlign: 'center' }}>+</div>
      </div>
    );
  }

  // Stimulus (choose)
  if (state === 'stimulus') {
    return (
      <div className="task-container">
        <div style={{ display: 'flex', gap: 40, justifyContent: 'center' }}>
          <button
            onClick={() => send({ type: 'CHOOSE', arm: 0 })}
            style={{
              width: 140, height: 140, borderRadius: 16,
              background: 'var(--accent)', border: 'none',
              fontSize: 24, fontWeight: 700, cursor: 'pointer',
              color: 'var(--bg)', fontFamily: "'Syne', sans-serif",
            }}
          >
            A
          </button>
          <button
            onClick={() => send({ type: 'CHOOSE', arm: 1 })}
            style={{
              width: 140, height: 140, borderRadius: 16,
              background: 'var(--accent2)', border: 'none',
              fontSize: 24, fontWeight: 700, cursor: 'pointer',
              color: 'var(--bg)', fontFamily: "'Syne', sans-serif",
            }}
          >
            B
          </button>
        </div>
      </div>
    );
  }

  // Feedback
  if (state === 'feedback') {
    return (
      <div className="task-container">
        <div style={{
          fontSize: 48, fontWeight: 700, textAlign: 'center',
          color: ctx.reward ? 'var(--success)' : 'var(--danger)',
          fontFamily: "'Syne', sans-serif",
        }}>
          {ctx.reward ? '+1' : '0'}
        </div>
      </div>
    );
  }

  // Done
  return (
    <div className="task-container">
      <div className="task-card" style={{ textAlign: 'center' }}>
        <div className="task-tag">TRIAL COMPLETE</div>
        <p className="task-text">
          Chose arm {ctx.chosenArm === 0 ? 'A' : 'B'},
          reward: {ctx.reward},
          RT: {ctx.rt?.toFixed(0)}ms
        </p>
      </div>
    </div>
  );
}
