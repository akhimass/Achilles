// Typed API client. One place that knows the backend base URL and endpoint shapes.
import type {
  LineageGraph,
  EvidenceEdge,
  EvidenceSubgraph,
  CollateralPair,
  StrainDetail,
  StructureResult,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<{ status: string }>("/health"),
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
  cycle: (organism: string) =>
    get<{ cycle: string[]; narrative: string | null; rcs?: CollateralPair[] }>(
      `/api/treatment/cycle?organism=${encodeURIComponent(organism)}`,
    ),
};
