"use client";
// Tracks the `dark` class on <html> so canvas/SVG code (which can't use Tailwind
// classes) can recolor when the user flips the theme.
import { useEffect, useState } from "react";

export function useIsDark(): boolean {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const el = document.documentElement;
    const update = () => setDark(el.classList.contains("dark"));
    update();
    const obs = new MutationObserver(update);
    obs.observe(el, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

  return dark;
}

/** Read an RGB-channel CSS variable (e.g. "45 194 141") as an rgb()/rgba() string. */
export function cssVarColor(name: string, alpha = 1): string {
  if (typeof window === "undefined") return "#888";
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  if (!raw) return "#888";
  return alpha >= 1 ? `rgb(${raw})` : `rgb(${raw} / ${alpha})`;
}
