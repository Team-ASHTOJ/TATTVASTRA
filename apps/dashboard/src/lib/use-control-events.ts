"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

const topics = [
  "compiler.started",
  "compiler.stage",
  "compiler.completed",
  "variant.generated",
  "hunt.started",
  "hunt.progress",
  "hunt.cancelled",
  "hunt.job.created",
  "hunt.job.retry",
  "agent.state",
  "endpoint.enrolled",
  "endpoint.revoked",
  "observation.created",
  "finding.created",
  "timeline.created",
  "artifact.created",
  "manifest.verified",
  "benchmark.started",
  "benchmark.sample",
  "benchmark.completed",
  "benchmark.failed",
  "case.created",
  "case.updated",
  "script.created",
  "script.version.created",
  "report.generated",
  "compatibility.recorded",
];

export function useControlEvents(enabled: boolean) {
  const client = useQueryClient();
  const router = useRouter();
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [status, setStatus] = useState(
    "Connecting to committed backend events…",
  );
  useEffect(() => {
    if (!enabled) return;
    let sequence = -1;
    let refresh: ReturnType<typeof setTimeout> | undefined;
    const stream = new EventSource("/api/control/domain/events");
    stream.onopen = () => setStatus("Connected — committed events only");
    stream.onerror = () =>
      setStatus("Disconnected; reconnecting from the durable event cursor.");
    const expired = () => {
      stream.close();
      client.clear();
      router.replace("/login");
    };
    stream.addEventListener("auth.expired", expired);
    const consume = (event: MessageEvent<string>) => {
      const next = Number(event.lastEventId);
      if (!Number.isSafeInteger(next) || next <= sequence) return;
      try {
        const record = JSON.parse(event.data) as Record<string, unknown>;
        sequence = next;
        setEvents((prior) => [record, ...prior].slice(0, 100));
        // A replay batch can contain many committed events. Refresh once per
        // batch instead of queuing competing API requests for every event.
        if (refresh === undefined) {
          refresh = setTimeout(() => {
            refresh = undefined;
            void client.invalidateQueries({ queryKey: ["resources"] });
            void client.invalidateQueries({ queryKey: ["cases"] });
            void client.invalidateQueries({ queryKey: ["children"] });
          }, 100);
        }
      } catch {
        setStatus("Invalid event payload rejected");
      }
    };
    for (const topic of topics) stream.addEventListener(topic, consume);
    return () => {
      stream.close();
      clearTimeout(refresh);
    };
  }, [enabled, client, router]);
  return { events, status };
}
