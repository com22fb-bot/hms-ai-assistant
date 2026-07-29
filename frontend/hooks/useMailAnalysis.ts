"use client";

import { useMemo } from "react";

import type { GmailMessage } from "@/types/mail";
import type {
  MailAnalysis,
  MailAnalysisMetrics,
} from "@/types/analysis";
import { analyzeMails } from "@/utils/mailAnalyzer";

type UseMailAnalysisResult = {
  analyses: MailAnalysis[];
  analysisByMessageId: Map<string, MailAnalysis>;
  metrics: MailAnalysisMetrics;
};

export function useMailAnalysis(
  messages: GmailMessage[],
): UseMailAnalysisResult {
  const analyses = useMemo(
    () => analyzeMails(messages),
    [messages],
  );

  const analysisByMessageId = useMemo(() => {
    return new Map(
      analyses.map((analysis) => [
        analysis.messageId,
        analysis,
      ]),
    );
  }, [analyses]);

  const metrics = useMemo<MailAnalysisMetrics>(() => {
    return {
      total: analyses.length,
      highPriority: analyses.filter(
        (analysis) => analysis.priority === "high",
      ).length,
      requiresReply: analyses.filter(
        (analysis) => analysis.requiresReply,
      ).length,
      requiresAction: analyses.filter(
        (analysis) => analysis.requiresAction,
      ).length,
      withDeadline: analyses.filter(
        (analysis) => analysis.hasDeadline,
      ).length,
    };
  }, [analyses]);

  return {
    analyses,
    analysisByMessageId,
    metrics,
  };
}