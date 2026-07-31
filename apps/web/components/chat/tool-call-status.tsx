"use client";

export interface ToolCall {
  name: string;
  display: string;
  status: "calling" | "done";
  summary: string;
}

interface ToolCallStatusProps {
  toolCalls: ToolCall[];
}

export function ToolCallStatus({ toolCalls }: ToolCallStatusProps) {
  return (
    <div className="space-y-1.5 mt-2">
      {toolCalls.map((tc, i) =>
        tc.status === "calling" ? (
          <div
            key={`${tc.name}-${i}`}
            className="bg-yellow-50 border border-yellow-200 rounded-lg px-3.5 py-2 flex items-center gap-2 text-sm"
          >
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-yellow-400 border-t-transparent" />
            <span>{tc.display}</span>
          </div>
        ) : (
          <div
            key={`${tc.name}-${i}`}
            className="bg-green-50 border border-green-200 rounded-lg px-3.5 py-2 flex items-center gap-2 text-sm"
          >
            <span className="text-green-600">&#10003;</span>
            <span>{tc.summary}</span>
          </div>
        )
      )}
    </div>
  );
}
