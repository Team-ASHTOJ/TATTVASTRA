"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { OperatorConsole } from "./operator-console";
export function DemoScreen({
  section,
}: {
  section: string;
  children?: React.ReactNode;
}) {
  return <OperatorConsole section={section} />;
}
export function ModeIndicator() {
  const mode = useQuery({
    queryKey: ["platform-status"],
    queryFn: () => api<{ mode: string }>("status"),
  });
  return (
    <span
      className="environment-indicator"
      title={
        mode.data?.mode === "DEMO"
          ? "Sandbox resources are simulated. Compiler and verification operations are real."
          : "Authenticated control plane"
      }
    >
      {mode.data?.mode === "DEMO" ? "LOCAL SANDBOX" : "REAL"}
    </span>
  );
}
