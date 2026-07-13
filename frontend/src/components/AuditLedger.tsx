"use client";
// Tamper-evident receipt for the prove-it result. Each control adjudication is an entry in
// a sha256 hash-CHAIN (every entry folds in the previous), so the whole validation reduces
// to one head fingerprint. "Re-verify" re-walks the ledger on the server and confirms it;
// "Tamper test" flips one verdict WITHOUT recomputing its hash, and re-verify then reports
// exactly where the chain breaks. An AI you can check, not one you take on trust.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AuditReport, AuditVerify, AuditEntry } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export function AuditLedger() {
  const [report, setReport] = useState<AuditReport | null>(null);
  const [ledger, setLedger] = useState<AuditEntry[] | null>(null);
  const [verify, setVerify] = useState<AuditVerify | null>(null);
  const [tampered, setTampered] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let live = true;
    api
      .audit()
      .then((d) => {
        if (!live) return;
        setReport(d);
        setLedger(d.ledger);
        setVerify({ valid: true, checked: d.entries, break_at: null, head: d.head });
        setStatus("ready");
      })
      .catch(() => live && setStatus("error"));
    return () => {
      live = false;
    };
  }, []);

  const reverify = async (l: AuditEntry[]) => {
    setBusy(true);
    try {
      setVerify(await api.auditVerify(l));
    } catch {
      /* leave prior state */
    } finally {
      setBusy(false);
    }
  };

  const tamper = () => {
    if (!ledger) return;
    // Flip a middle entry's verdict but leave its stored hash — a forged report.
    const i = Math.min(1, ledger.length - 1);
    const next = ledger.map((e, idx) =>
      idx === i
        ? { ...e, verdict: e.verdict === "refused" ? "fabricated" : "refused" }
        : e,
    );
    setLedger(next);
    setTampered(true);
    reverify(next);
  };

  const reset = () => {
    if (!report) return;
    setLedger(report.ledger);
    setTampered(false);
    setVerify({ valid: true, checked: report.entries, break_at: null, head: report.head });
  };

  const downloadLedger = () => {
    if (!ledger) return;
    const blob = new Blob([JSON.stringify({ ledger }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "achilles-audit-ledger.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  if (status === "loading") return <div className="skeleton mt-4 h-24 rounded-xl" />;
  if (status === "error" || !report || !ledger || !verify) return null;

  return (
    <div className="mt-4 rounded-xl border border-line/12 bg-surface2/40 p-3">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-faint">
          Tamper-evident audit ledger
        </span>
        <span
          className={
            "rounded-full px-2 py-0.5 text-[0.58rem] font-semibold uppercase " +
            (verify.valid
              ? "bg-accent/12 text-accentStrong"
              : "bg-rose-500/15 text-rose-400")
          }
        >
          {verify.valid ? "chain verified" : `broken @ entry ${verify.break_at}`}
        </span>
      </div>
      <p className="mb-2 text-[0.72rem] leading-relaxed text-muted">
        Each of the {report.entries} control verdicts is an entry in a sha256 hash-chain, so
        the whole prove-it result reduces to one fingerprint. Re-verify recomputes it; edit
        any verdict and the chain breaks at that entry. You can check it, not trust it.
      </p>

      <div className="flex items-center gap-2 rounded-lg border border-line/12 bg-surface/50 px-2.5 py-1.5">
        <span className="text-[0.58rem] uppercase tracking-wide text-faint">head</span>
        <code className="min-w-0 flex-1 truncate font-mono text-[0.68rem] text-text">
          {verify.head}
        </code>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <button
          onClick={() => reverify(ledger)}
          disabled={busy}
          className="rounded-md bg-accent/12 px-2.5 py-1 text-[0.72rem] font-medium text-accentStrong ring-1 ring-inset ring-accent/25 transition hover:bg-accent/20 disabled:opacity-50"
        >
          {busy ? "…" : "Re-verify chain"}
        </button>
        {!tampered ? (
          <button
            onClick={tamper}
            className="rounded-md border border-line/15 px-2.5 py-1 text-[0.72rem] text-muted transition hover:border-rose-500/40 hover:text-text"
          >
            Tamper test
          </button>
        ) : (
          <button
            onClick={reset}
            className="rounded-md border border-line/15 px-2.5 py-1 text-[0.72rem] text-muted transition hover:border-line/30 hover:text-text"
          >
            Reset ledger
          </button>
        )}
        <span className="font-mono text-[0.62rem] text-faint">
          {verify.checked} entries checked
        </span>
      </div>

      <div className="mt-1.5 flex flex-wrap items-center gap-3 text-[0.68rem]">
        <a
          href={`${API_BASE}/api/report/validation`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-accentStrong hover:underline"
        >
          ↓ Download audit report (HTML)
        </a>
        <button onClick={downloadLedger} className="text-muted transition hover:text-text">
          ↓ ledger (JSON, re-verifiable)
        </button>
      </div>

      {!verify.valid && verify.break_at !== null && (
        <p className="mt-2 rounded-lg border border-rose-500/25 bg-rose-500/[0.06] px-2.5 py-1.5 text-[0.7rem] text-rose-300">
          Tamper detected: entry {verify.break_at} ({ledger[verify.break_at]?.gene} →{" "}
          {ledger[verify.break_at]?.verdict}) no longer matches its hash — a forged report
          fails verification.
        </p>
      )}

      <div className="mt-2 max-h-32 space-y-1 overflow-y-auto">
        {ledger.slice(0, 6).map((e) => (
          <div
            key={e.index}
            className={
              "flex items-center justify-between gap-2 rounded-md px-2 py-1 text-[0.66rem] " +
              (!verify.valid && verify.break_at === e.index
                ? "bg-rose-500/[0.08]"
                : "bg-surface/40")
            }
          >
            <span className="min-w-0 truncate text-muted">
              <span className="font-mono text-faint">#{e.index}</span>{" "}
              <span className="text-text">{e.gene}</span>{" "}
              <span className="text-faint">{e.verdict}</span>
            </span>
            <code className="shrink-0 font-mono text-[0.6rem] text-faint">
              {e.entry_hash.slice(0, 10)}…
            </code>
          </div>
        ))}
      </div>
    </div>
  );
}
