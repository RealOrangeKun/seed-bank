import { ImagePlus, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Build and maintain object-URL thumbnails for the selected files, revoking
 * them when the selection changes or the component unmounts. Keyed by file
 * identity so re-renders don't churn URLs for files that didn't change.
 */
function useThumbnails(files: File[]): string[] {
  const [urls, setUrls] = useState<string[]>([]);

  useEffect(() => {
    const next = files.map((f) => URL.createObjectURL(f));
    setUrls(next);
    return () => {
      next.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [files]);

  return urls;
}

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
  const thumbnails = useThumbnails(files);

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
          dragging
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/60",
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
        <>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {files.length} image{files.length === 1 ? "" : "s"} ·{" "}
              {formatBytes(files.reduce((sum, f) => sum + f.size, 0))}
            </span>
            {!disabled ? (
              <button
                type="button"
                className="hover:text-destructive"
                onClick={() => onChange([])}
              >
                Clear all
              </button>
            ) : null}
          </div>
          <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5">
            {files.map((f, i) => (
              <li
                key={`${f.name}-${i}`}
                className="group relative aspect-square overflow-hidden rounded-md border bg-muted"
              >
                {thumbnails[i] ? (
                  <img
                    src={thumbnails[i]}
                    alt={f.name}
                    className="h-full w-full object-cover transition-transform group-hover:scale-105"
                  />
                ) : null}
                <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent px-1.5 pb-1 pt-4">
                  <p
                    className="truncate text-[10px] font-medium text-white"
                    title={f.name}
                  >
                    {f.name}
                  </p>
                  <p className="text-[9px] text-white/70">{formatBytes(f.size)}</p>
                </div>
                {!disabled ? (
                  <Button
                    type="button"
                    variant="destructive"
                    size="icon"
                    className="absolute right-1 top-1 h-5 w-5 opacity-0 shadow transition-opacity group-hover:opacity-100"
                    aria-label={`Remove ${f.name}`}
                    onClick={() => onChange(files.filter((_, idx) => idx !== i))}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}
