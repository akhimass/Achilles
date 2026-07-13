// Single source of truth for the demo organism on the frontend.
//
// The public demo loads the flagship domain (Burkholderia multivorans). Components that
// drive API calls for the demo import this instead of re-declaring the string, so the
// operative organism can't drift between panels. It mirrors the backend's authoritative
// value (app/ingestion/domains.py :: DEFAULT_ORGANISM). Override at build time with
// NEXT_PUBLIC_DEMO_ORGANISM if a different flagship is deployed.
export const DEMO_ORGANISM =
  process.env.NEXT_PUBLIC_DEMO_ORGANISM ?? "Burkholderia multivorans";
