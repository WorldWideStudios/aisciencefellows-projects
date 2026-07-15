import { NextRequest, NextResponse } from "next/server";
import type { BanditTrialData, TwoStepTrialData } from "@/lib/types";
import {
  compareBanditWithCentaur,
  compareTwoStepWithCentaur,
} from "@/lib/centaur-comparison";

/**
 * POST /api/compare
 *
 * Run the Centaur comparison pipeline for a set of cognitive task trials.
 * Returns NLL-based comparison statistics (the primary metric from the
 * Centaur Nature 2025 paper).
 *
 * Request body:
 *   { taskType: string, trials: any[], options?: { offline?: boolean, skipFirst?: number } }
 *
 * Supported taskTypes:
 *   - "two-armed-bandit" — runs bandit comparison with RW baseline
 *   - "two-step" — runs two-step comparison (stage 1 predictions)
 *
 * Response:
 *   { comparison: CentaurComparisonResult }
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { taskType, trials, options } = body as {
      taskType: string;
      trials: unknown[];
      options?: { offline?: boolean; skipFirst?: number };
    };

    if (!taskType || !Array.isArray(trials) || trials.length === 0) {
      return NextResponse.json(
        { error: "taskType and non-empty trials array are required" },
        { status: 400 }
      );
    }

    if (taskType === "two-armed-bandit") {
      const comparison = await compareBanditWithCentaur(
        trials as BanditTrialData[],
        {
          skipFirst: options?.skipFirst,
          offline: options?.offline,
        }
      );
      return NextResponse.json({ comparison });
    }

    if (taskType === "two-step") {
      const comparison = await compareTwoStepWithCentaur(
        trials as TwoStepTrialData[],
        {
          skipFirst: options?.skipFirst,
          offline: options?.offline,
        }
      );
      return NextResponse.json({ comparison });
    }

    return NextResponse.json(
      { error: `Unsupported taskType: ${taskType}. Supported: two-armed-bandit, two-step` },
      { status: 400 }
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
