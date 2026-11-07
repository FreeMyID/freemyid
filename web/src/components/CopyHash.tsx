// "Copy" button next to the download fingerprint (SHA256). React island (client:visible) using
// the shadcn/ui Button. With JS off the button is not rendered and the code stays selectable text.
import { useEffect, useState } from "react";
import { Button } from "./ui/button";

export default function CopyHash({ value }: { value: string }) {
  const [ready, setReady] = useState(false);
  const [done, setDone] = useState(false);
  useEffect(() => setReady(typeof navigator !== "undefined" && Boolean(navigator.clipboard)), []);
  // a 1px placeholder gives client:visible something to observe (astro-island is display: contents)
  if (!ready) return <span aria-hidden="true" className="inline-block h-px w-px" />;
  return (
    <span className="inline-flex items-center gap-2">
      <Button type="button" variant="secondary" size="sm"
        onClick={() => navigator.clipboard.writeText(value).then(() => setDone(true), () => setDone(false))}>
        Copy the code
      </Button>
      <span role="status" className="text-small text-ok">{done ? "Copied" : ""}</span>
    </span>
  );
}
