import { useEffect, useRef, useState } from "react";

interface CountUpProps {
  value: number;
  /** Animation duration in ms. */
  durationMs?: number;
  /** Decimal places to render. */
  decimals?: number;
  suffix?: string;
}

/**
 * Animates a number from 0 to `value` once on mount (and again whenever the
 * target changes). Eased with a cubic-out curve so it decelerates into the
 * final figure — the small flourish that makes results feel "computed".
 * Respects `prefers-reduced-motion`: snaps straight to the value.
 */
export function CountUp({
  value,
  durationMs = 900,
  decimals = 0,
  suffix = "",
}: CountUpProps) {
  const [display, setDisplay] = useState(0);
  const frame = useRef<number | null>(null);

  useEffect(() => {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) {
      setDisplay(value);
      return;
    }

    const start = performance.now();
    const from = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - (1 - t) ** 3; // cubic-out
      setDisplay(from + (value - from) * eased);
      if (t < 1) {
        frame.current = requestAnimationFrame(tick);
      }
    };
    frame.current = requestAnimationFrame(tick);
    return () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current);
    };
  }, [value, durationMs]);

  return (
    <span>
      {display.toFixed(decimals)}
      {suffix}
    </span>
  );
}
