// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
/** Poll persistent agent jobs. The legacy exported names preserve existing page integrations. */

import { useState, useCallback, useRef } from "react";
import { invokeAgentCore, isAgentCoreAvailable } from "../agentcore";

export interface ProgressStep {
  step: string;
  tool?: string;
  agent?: string;
  timestamp: number;
}

interface AgentStreamState {
  isRunning: boolean;
  progress: string[];
  progressSteps: ProgressStep[];
  result: unknown | null;
  meta: { tools_used?: unknown[]; metrics?: Record<string, number> } | null;
  error: string | null;
  source: "agentcore";
}

const INITIAL_STATE: AgentStreamState = {
  isRunning: false,
  progress: [],
  progressSteps: [],
  result: null,
  meta: null,
  error: null,
  source: "agentcore",
};

export function useAgentStream() {
  const [state, setState] = useState<AgentStreamState>(INITIAL_STATE);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState(INITIAL_STATE);
  }, []);

  const invoke = useCallback(async (agentName: string, documentId: string, extraPayload?: Record<string, string>) => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    const controller = abortRef.current;

    setState({ ...INITIAL_STATE, isRunning: true });

    if (!isAgentCoreAvailable(agentName)) {
      setState((s) => ({ ...s, isRunning: false, error: `Agent unavailable for: ${agentName}` }));
      return;
    }

    try {
      for await (const event of invokeAgentCore(agentName, documentId, extraPayload, controller.signal)) {
        if (controller.signal.aborted) return;

        if (event.type === "progress" && event.step) {
          setState((s) => ({
            ...s,
            progress: [...s.progress, event.step!],
            progressSteps: [...s.progressSteps, {
              step: event.step!,
              tool: event.tool,
              agent: event.agent,
              timestamp: Date.now(),
            }],
          }));
        } else if (event.type === "result") {
          setState((s) => ({
            ...s,
            isRunning: false,
            result: event.result || event,
            meta: { tools_used: event.tools_used, metrics: event.metrics },
          }));
          return;
        } else if (event.type === "error") {
          setState((s) => ({ ...s, isRunning: false, error: event.message || event.error || "Agent error" }));
          return;
        }
      }

      setState((s) => {
        if (s.result) return s;
        return { ...s, isRunning: false, error: "Agent stream ended without a result" };
      });
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      console.error("Agent invocation failed:", err);
      const message = err instanceof Error ? err.message : "Agent invocation failed";
      setState((s) => ({ ...s, isRunning: false, error: message }));
    }
  }, []);

  return { ...state, invoke, reset };
}
