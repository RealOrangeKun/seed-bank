import { Film, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { useI18n } from "@/i18n";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";

interface VideoDropzoneProps {
  file: File | null;
  onChange: (file: File | null) => void;
  /** Max size in bytes (defaults to 200 MB, matching the server cap). */
  maxBytes?: number;
  disabled?: boolean;
}

/** Single-video picker with a preview and a client-side size check. */
export function VideoDropzone({
  file,
  onChange,
  maxBytes = 200_000_000,
  disabled,
}: VideoDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [rejected, setRejected] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const { t } = useI18n();

  // Object-URL preview, revoked when the file changes / unmounts.
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const pick = useCallback(
    (incoming: FileList | null) => {
      const next = incoming?.[0];
      if (!next) return;
      if (!next.type.startsWith("video/")) {
        setRejected(t("dropzone.notVideo", { name: next.name }));
        return;
      }
      if (next.size > maxBytes) {
        setRejected(
          t("dropzone.tooLarge", { name: next.name, size: formatBytes(maxBytes) }),
        );
        return;
      }
      setRejected(null);
      onChange(next);
    },
    [maxBytes, onChange, t],
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
          pick(e.dataTransfer.files);
        }}
        className={cn(
          "flex w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed bg-card/50 px-6 py-10 text-center transition-colors",
          dragging
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/60",
          disabled && "pointer-events-none opacity-60",
        )}
      >
        <Film className="h-8 w-8 text-primary" />
        <span className="text-sm font-medium">{t("dropzone.videoCta")}</span>
        <span className="text-xs text-muted-foreground">
          {t("dropzone.videoLimits", { size: formatBytes(maxBytes) })}
        </span>
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          className="hidden"
          onChange={(e) => {
            pick(e.target.files);
            e.target.value = "";
          }}
        />
      </button>

      {rejected ? <p className="text-xs text-destructive">{rejected}</p> : null}

      {file && previewUrl ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="truncate" title={file.name}>
              {file.name} · {formatBytes(file.size)}
            </span>
            {!disabled ? (
              <button
                type="button"
                className="inline-flex items-center gap-1 hover:text-destructive"
                onClick={() => onChange(null)}
              >
                <X className="h-3 w-3" />
                {t("dropzone.clearAll")}
              </button>
            ) : null}
          </div>
          {/* eslint-disable-next-line jsx-a11y/media-has-caption -- user-supplied clip, no caption track */}
          <video
            src={previewUrl}
            controls
            className="max-h-64 w-full rounded-md border bg-black"
          />
        </div>
      ) : null}
    </div>
  );
}
