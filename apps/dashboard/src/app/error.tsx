"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <div role="alert" className="panel">
      <h1>Unable to load this page</h1>
      <p>Please retry. No successful operation is implied by this error.</p>
      <button onClick={reset}>Retry</button>
    </div>
  );
}
