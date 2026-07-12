import type { Config } from "tailwindcss";

/** Token-driven theme. Colors resolve to CSS variables (RGB channels) so a single
 *  `.dark` class flips the whole surface, and opacity modifiers still work. */
const withVar = (v: string) => `rgb(var(${v}) / <alpha-value>)`;

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Semantic, theme-aware tokens.
        bg: withVar("--bg"),
        surface: withVar("--surface"),
        surface2: withVar("--surface-2"),
        surface3: withVar("--surface-3"),
        line: withVar("--line"),
        text: withVar("--text"),
        muted: withVar("--muted"),
        faint: withVar("--faint"),
        accent: withVar("--accent"),
        accentStrong: withVar("--accent-strong"),
        accent2: withVar("--accent-2"),
        danger: withVar("--danger"),
        amber: withVar("--amber"),

        // Fixed domain palette (kept for continuity / non-themed marks).
        ink: "#15201c",
        paper: "#f6f7f4",
        flip: "#1d9e75", // teal — reversal / sensitivity
        resist: "#d85a30", // coral — resistance
      },
      fontFamily: {
        // Geist (shadcn default), self-hosted via next/font.
        sans: ["var(--font-geist-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["var(--font-geist-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.03em",
      },
      boxShadow: {
        card: "0 1px 2px rgb(var(--shadow-color) / 0.04), 0 8px 24px -12px rgb(var(--shadow-color) / 0.12)",
        lift: "0 2px 4px rgb(var(--shadow-color) / 0.06), 0 18px 48px -18px rgb(var(--shadow-color) / 0.22)",
        glow: "0 0 0 1px rgb(var(--accent) / 0.35), 0 10px 40px -10px rgb(var(--accent) / 0.4)",
        "glow-sm": "0 0 0 1px rgb(var(--accent) / 0.25), 0 6px 22px -10px rgb(var(--accent) / 0.3)",
      },
      borderRadius: {
        xl: "0.9rem",
        "2xl": "1.25rem",
      },
      transitionTimingFunction: {
        spring: "cubic-bezier(0.16, 1, 0.3, 1)",
      },
    },
  },
  plugins: [],
};
export default config;
