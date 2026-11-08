// Clipboard feedback for the download fingerprint. Without JavaScript the code remains selectable.
import { useEffect, useState } from "react";
import { Button } from "./ui/button";

export default function CopyHash({ value }: { value: string }) {
  const [ready, setReady] = useState(false);
  const [available, setAvailable] = useState(false);
  const [status, setStatus] = useState<"idle" | "copying" | "copied" | "failed">("idle");
  useEffect(() => {
    setAvailable(typeof navigator !== "undefined" && typeof navigator.clipboard?.writeText === "function");
    setReady(true);
  }, []);
  // A placeholder gives client:visible something to observe inside the closed disclosure.
  if (!ready) return <span aria-hidden="true" className="inline-block h-px w-px" />;
  const message = !available || status === "failed"
    ? "Couldn't copy the code. You can select and copy the code above."
    : status === "copied" ? "Copied" : status === "copying" ? "Copying…" : "";
  async function copy() {
    setStatus("copying");
    try {
      await navigator.clipboard.writeText(value);
      setStatus("copied");
    } catch {
      setStatus("failed");
    }
  }
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      {available && <Button type="button" variant="secondary" size="sm"
        disabled={status === "copying"} onClick={copy}>
        Copy the code
      </Button>}
      <span role="status" aria-live="polite" className="text-small text-text">{message}</span>
    </span>
  );
}
