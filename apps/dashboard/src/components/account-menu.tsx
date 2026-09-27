"use client";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
export function AccountMenu() {
  const router = useRouter(),
    client = useQueryClient();
  const pathname = usePathname();
  const me = useQuery({
    enabled: pathname !== "/login",
    queryKey: ["operator"],
    queryFn: () => api<{ username: string; role: string }>("domain/auth/me"),
    retry: false,
  });
  if (me.error || !me.data) return <Link href="/login">Sign in</Link>;
  return (
    <details className="account-menu">
      <summary>
        {me.data.username} ·{" "}
        {me.data.role === "ADMIN" ? "Administrator" : me.data.role}
      </summary>
      <div className="panel">
        <p>
          {me.data.username} / {me.data.role}
        </p>
        <button
          className="secondary"
          onClick={async () => {
            await api("domain/auth/logout", { method: "POST" });
            client.clear();
            router.push("/login");
            router.refresh();
          }}
        >
          Sign out
        </button>
      </div>
    </details>
  );
}
