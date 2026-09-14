"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";
import type { LoginRequest } from "@jocky/contracts";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <>
      <div className="eyebrow">CONTROL PLANE / AUTHENTICATION</div>
      <h1>Operator sign in</h1>
      <p>
        Use your organization UUID and operator credentials. Local bootstrap
        credentials are stored in the ignored .env file; the organization UUID
        is printed in the control-plane startup log.
      </p>
      <form
        className="panel control-form"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError("");
          const form = new FormData(event.currentTarget);
          const payload: LoginRequest = {
            organization_id: String(form.get("organization")),
            username: String(form.get("username")),
            password: String(form.get("password")),
          };
          try {
            await api("domain/auth/login", {
              method: "POST",
              body: JSON.stringify(payload),
            });
            router.push("/cases");
            router.refresh();
          } catch (failure) {
            setError(
              failure instanceof Error ? failure.message : "Sign in failed",
            );
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Organization UUID
          <input name="organization" required autoComplete="organization" />
        </label>
        <label>
          Username
          <input name="username" required autoComplete="username" />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            required
            autoComplete="current-password"
          />
        </label>
        <button className="button" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        {error && <p role="alert">{error}</p>}
      </form>
      <p>
        Sessions expire after one hour. Session tokens stay in an HttpOnly,
        same-site cookie.
      </p>
    </>
  );
}
