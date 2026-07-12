// Typed API client. One place that knows the backend base URL and endpoint shapes.
import type {
  LineageGraph,
  EvidenceEdge,
  EvidenceSubgraph,
  StrainDetail,
  StructureResult,
  TargetsResponse,
  CycleResponse,
  TrajectoryEvidence,
  SearchResponse,
  UploadResult,
  ValidationReport,
  RedTeamVerdict,
  RetrodictionReport,
  DockingResponse,
  AskResponse,
  AskPersona,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return res.json() as Promise<T>;
}

/** POST raw CSV text; surfaces the backend's 400 detail as the thrown message. */
async function postCsv<T>(path: string, csv: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "text/csv" },
    body: csv,
    cache: "no-store",
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body?.detail || `${res.status} ${res.statusText}`);
  return body as T;
}

export const api = {
  health: () => get<{ status: string }>("/health"),
  // Direct download URL for the citable evidence-graph export (JSON or CSV).
  exportEvidenceUrl: (
    locus: string,
    format: "json" | "csv",
    organism = "Burkholderia multivorans",
  ) =>
    `${BASE}/api/export/evidence?gene=${encodeURIComponent(locus)}&organism=${encodeURIComponent(
      organism,
    )}&format=${format}`,
  lineage: (organism: string) =>
    get<LineageGraph>(`/api/graph/lineage?organism=${encodeURIComponent(organism)}`),
  strain: (id: string) => get<StrainDetail>(`/api/graph/strain?id=${encodeURIComponent(id)}`),
  structure: (locus: string, organism = "Burkholderia multivorans", submit = false) =>
    get<StructureResult>(
      `/api/structure?locus=${encodeURIComponent(locus)}&organism=${encodeURIComponent(
        organism,
      )}&submit=${submit}`,
    ),
  evidence: (nodeType: string, nodeId: string) =>
    get<{ edges: EvidenceEdge[] }>(
      `/api/graph/evidence?node_type=${nodeType}&node_id=${nodeId}`,
    ),
  geneEvidence: (locus: string, organism = "Burkholderia multivorans") =>
    get<EvidenceSubgraph>(
      `/api/graph/evidence?node_type=gene&node_id=${encodeURIComponent(
        locus,
      )}&organism=${encodeURIComponent(organism)}`,
    ),
  targets: (strainId: string | null, organism = "Burkholderia multivorans") =>
    get<TargetsResponse>(
      strainId
        ? `/api/targets?strain_id=${encodeURIComponent(strainId)}`
        : `/api/targets?organism=${encodeURIComponent(organism)}`,
    ),
  cycle: (organism: string, strainId?: string | null) =>
    get<CycleResponse>(
      `/api/treatment/cycle?organism=${encodeURIComponent(organism)}` +
        (strainId ? `&strain_id=${encodeURIComponent(strainId)}` : ""),
    ),
  search: (q: string) => get<SearchResponse>(`/api/search?q=${encodeURIComponent(q)}`),
  ask: (q: string, persona: AskPersona) =>
    get<AskResponse>(
      `/api/ask?q=${encodeURIComponent(q)}&persona=${persona}&narrate=true`,
    ),
  validation: () => get<ValidationReport>("/api/validation"),
  docking: () => get<DockingResponse>("/api/docking"),
  retrodiction: (cutoff: number) =>
    get<RetrodictionReport>(`/api/validation/retrodiction?cutoff=${cutoff}`),
  redteam: (gene: string, target: string) =>
    get<RedTeamVerdict>(
      `/api/validation/redteam?gene=${encodeURIComponent(gene)}&target=${encodeURIComponent(target)}`,
    ),
  // Bring-your-own-strains: POST a genotype CSV → lineage graph + flippers.
  uploadStrains: (csv: string, organism = "your cohort") =>
    postCsv<UploadResult>(`/api/ingest/upload?organism=${encodeURIComponent(organism)}`, csv),
  ingestExample: () =>
    fetch(`${BASE}/api/ingest/example`, { cache: "no-store" }).then((r) => r.text()),
  trajectory: (strainId: string | null, resisted?: string | null) => {
    const params = new URLSearchParams();
    if (strainId) params.set("strain_id", strainId);
    if (resisted) params.set("resisted", resisted);
    return get<TrajectoryEvidence>(`/api/trajectory?${params.toString()}`);
  },
};
