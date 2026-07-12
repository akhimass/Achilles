"use client";
// Bring your own strains: drop a genotype CSV and the SAME deterministic core that
// powers the demo reconstructs your lineage and detects reversible (flipper) loci —
// stateless, no upload stored. Turns "does it work on my data?" into a 5-second yes.
import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { Panel, Badge } from "./ui";
import { LineageTree } from "./LineageTree";
import type { UploadResult } from "@/lib/types";

type Status = "idle" | "loading" | "ready" | "error";

export function UploadPanel() {
  const [result, setResult] = useState<UploadResult | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function run(csv: string) {
    setStatus("loading");
    setError(null);
    setSelectedId(null);
    try {
      const r = await api.uploadStrains(csv);
      setResult(r);
      setStatus("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  }

  async function onFile(file: File) {
    if (file.size > 4_000_000) {
      setError("File too large (max ~4 MB).");
      setStatus("error");
      return;
    }
    run(await file.text());
  }

  async function tryExample() {
    try {
      setStatus("loading");
      run(await api.ingestExample());
    } catch {
      setError("Could not load the example.");
      setStatus("error");
    }
  }

  const s = result?.summary;

  return (
    <Panel
      title="Bring your own strains"
      aside={
        s ? (
          <span className="flex items-center gap-1.5">
            <Badge tone="accent">{s.strains} isolates</Badge>
            <Badge tone="accent">{s.flipper_carrying} flipper-carrying</Badge>
          </span>
        ) : (
          <span className="font-mono text-[0.68rem] text-faint">CSV → your lineage, deterministic</span>
        )
      }
    >
      <input
        ref={fileRef}
        type="file"
        accept=".csv,.tsv,.txt,text/csv"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
          e.target.value = "";
        }}
      />

      {(status === "idle" || status === "error") && (
        <Dropzone
          onPick={() => fileRef.current?.click()}
          onExample={tryExample}
          onDropFile={onFile}
          error={error}
        />
      )}

      {status === "loading" && (
        <div className="space-y-2">
          <div className="skeleton h-8 w-64 rounded-lg" />
          <div className="skeleton h-64 rounded-xl" />
        </div>
      )}

      {status === "ready" && result && s && (
        <div className="animate-fade">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-[0.78rem] text-muted">
              Reconstructed a lineage over{" "}
              <span className="text-text">{s.strains} isolates</span> ·{" "}
              <span className="text-text">{s.loci} loci</span>, and detected reversible loci —{" "}
              <span className="text-accentStrong">{s.flipper_carrying}</span> isolates carry a
              flipper (max {s.max_flipper}). Nothing was stored.
              {s.warnings?.dropped_rows ? (
                <span className="text-faint"> {s.warnings.dropped_rows} row(s) skipped.</span>
              ) : null}
            </p>
            <button
              onClick={() => {
                setResult(null);
                setStatus("idle");
              }}
              className="rounded-md border border-line/12 px-2 py-1 text-[0.68rem] text-muted transition hover:border-line/25 hover:text-text"
            >
              analyze another
            </button>
          </div>
          <LineageTree
            graph={result}
            status="ready"
            error={null}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </div>
      )}
    </Panel>
  );
}

function Dropzone({
  onPick,
  onExample,
  onDropFile,
  error,
}: {
  onPick: () => void;
  onExample: () => void;
  onDropFile: (f: File) => void;
  error: string | null;
}) {
  const [over, setOver] = useState(false);
  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) onDropFile(f);
        }}
        className={`flex flex-col items-center justify-center rounded-xl border border-dashed px-4 py-8 text-center transition ${
          over ? "border-accent/50 bg-accent/[0.06]" : "border-line/15 bg-surface2/40"
        }`}
      >
        <Cloud />
        <div className="mt-2 text-sm font-medium text-text">Drop a genotype CSV, or</div>
        <div className="mt-2 flex items-center gap-2">
          <button
            onClick={onPick}
            className="rounded-lg bg-accent/12 px-3 py-1.5 text-xs font-medium text-accentStrong ring-1 ring-inset ring-accent/25 transition hover:bg-accent/20"
          >
            Choose file
          </button>
          <button
            onClick={onExample}
            className="rounded-lg border border-line/12 px-3 py-1.5 text-xs text-muted transition hover:border-line/25 hover:text-text"
          >
            Try an example
          </button>
        </div>
        <p className="mt-3 max-w-md text-[0.68rem] leading-relaxed text-faint">
          One row per isolate: an <span className="font-mono text-muted">id</span> column plus one
          column per locus (MLST alleles, gene presence/absence, or SNP calls). Optional{" "}
          <span className="font-mono text-muted">year</span> /{" "}
          <span className="font-mono text-muted">country</span>. Runs locally &amp; deterministically —
          your data is never stored.
        </p>
      </div>
      {error && (
        <p className="mt-2 rounded-lg border border-danger/25 bg-danger/[0.06] px-3 py-2 text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

function Cloud() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="rgb(var(--faint))" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 13v8m0-8 3 3m-3-3-3 3" />
      <path d="M20 16.6A5 5 0 0 0 18 7h-1.3A8 8 0 1 0 4 15" />
    </svg>
  );
}
