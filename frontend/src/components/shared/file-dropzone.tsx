import { ImagePlus, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";

interface FileDropzoneProps {
  files: File[];
  onChange: (files: File[]) => void;
  maxFiles?: number;
  maxBytes?: number;
  accept?: string;
  disabled?: boolean;
}

/** Drag-and-drop / click image picker with client-side size & count limits. */
export function FileDropzone({
  files,
  onChange,
  maxFiles = 50,
  maxBytes = 10_000_000,
  accept = "image/*",
  disabled,
}: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [rejected, setRejected] = useState<string[]>([]);

  const addFiles = useCallback(
    (incoming: FileList | null) => {
      if (!incoming) return;
      const bad: string[] = [];
      const ok: File[] = [];
      for (const f of Array.from(incoming)) {
        if (!f.type.startsWith("image/")) bad.push(`${f.name}: not an image`);
        else if (f.size > maxBytes)
          bad.push(`${f.name}: exceeds ${formatBytes(maxBytes)}`);
        else ok.push(f);
      }
      setRejected(bad);
      onChange([...files, ...ok].slice(0, maxFiles));
    },
    [files, maxBytes, maxFiles, onChange],
  );

  return (
    <div className="space-y-3">
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          addFiles(e.dataTransfer.files);
        }}
        className={cn(
          "flex w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed bg-card/50 px-6 py-10 text-center transition-colors",
          dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/60",
          disabled && "pointer-events-none opacity-60",
        )}
      >
        <ImagePlus className="h-8 w-8 text-primary" />
        <span className="text-sm font-medium">
          Drop seed images here, or click to browse
        </span>
        <span className="text-xs text-muted-foreground">
          Up to {maxFiles} images, {formatBytes(maxBytes)} each
        </span>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={accept}
          className="hidden"
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </button>

      {rejected.length > 0 ? (
        <ul className="space-y-1 text-xs text-destructive">
          {rejected.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      ) : null}

      {files.length > 0 ? (
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {files.map((f, i) => (
            <li
              key={`${f.name}-${i}`}
              className="flex items-center justify-between gap-2 rounded-md border bg-background px-3 py-2 text-sm"
            >
              <span className="truncate" title={f.name}>
                {f.name}
              </span>
              <span className="shrink-0 text-xs text-muted-foreground">
                {formatBytes(f.size)}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-6 w-6 shrink-0"
                aria-label={`Remove ${f.name}`}
                onClick={() => onChange(files.filter((_, idx) => idx !== i))}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
