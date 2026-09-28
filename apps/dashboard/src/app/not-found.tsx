import Link from "next/link";
export default function NotFound() {
  return (
    <>
      <h1>Page not found</h1>
      <p>This route is not part of the Tattvastra console.</p>
      <Link href="/">Return to Command Center</Link>
    </>
  );
}
