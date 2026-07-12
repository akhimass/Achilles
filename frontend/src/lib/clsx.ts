// Tiny classname joiner — no dependency needed for this app's scale.
export type ClassValue = string | false | null | undefined;

export function clsx(...values: ClassValue[]): string {
  return values.filter(Boolean).join(" ");
}
