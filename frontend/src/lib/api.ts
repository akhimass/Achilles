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
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return res.json() as Promise<T>;
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
  cycle: (organism: string) =>
    get<CycleResponse>(`/api/treatment/cycle?organism=${encodeURIComponent(organism)}`),
  trajectory: (strainId: string | null, resisted?: string | null) => {
    const params = new URLSearchParams();
    if (strainId) params.set("strain_id", strainId);
    if (resisted) params.set("resisted", resisted);
    return get<TrajectoryEvidence>(`/api/trajectory?${params.toString()}`);
  },
};
