"use client";
// One fetch of the lineage graph, shared by the tree, the overview stats, and the
// selection rail — so counts stay consistent and the API is hit once per organism.
import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { LineageGraph, LineageNode } from "./types";

export type LineageStatus = "loading" | "ready" | "empty" | "error";

export interface LineageState {
  graph: LineageGraph | null;
  status: LineageStatus;
  error: string | null;
  byId: Map<string, LineageNode>;
  overview: Overview | null;
}

export interface Overview {
  strains: number;
  edges: number;
  flipperCarriers: number;
  maxFlip: number;
  flipperHistogram: number[]; // index = flipper_count, value = #strains
  yearMin: number | null;
  yearMax: number | null;
  countries: { name: string; count: number }[];
  sequenceTypes: number;
  lineages: { name: string; count: number }[]; // BurkData experimental lineages
  founders: number;
}

function summarize(graph: LineageGraph): Overview {
  const nodes = graph.nodes;
  const maxFlip = Math.max(0, ...nodes.map((n) => n.flipper_count));
  const hist = Array(maxFlip + 1).fill(0);
  for (const n of nodes) hist[n.flipper_count] += 1;

  const years = nodes
    .map((n) => (n.year == null ? NaN : Number(n.year)))
    .filter((y) => Number.isFinite(y));

  const countryCounts = new Map<string, number>();
  for (const n of nodes) {
    if (n.country) countryCounts.set(n.country, (countryCounts.get(n.country) ?? 0) + 1);
  }
  const countries = [...countryCounts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);

  const sts = new Set(nodes.map((n) => n.st).filter((s) => s != null));

  // BurkData: experimental-lineage membership ("L1, L2") and founder count.
  const lineageCounts = new Map<string, number>();
  for (const n of nodes) {
    if (!n.lineage) continue;
    for (const raw of String(n.lineage).split(",")) {
      const l = raw.trim();
      if (l) lineageCounts.set(l, (lineageCounts.get(l) ?? 0) + 1);
    }
  }
  const lineages = [...lineageCounts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => {
      const na = Number(a.name.replace(/\D/g, "")) || 0;
      const nb = Number(b.name.replace(/\D/g, "")) || 0;
      return na - nb;
    });

  return {
    strains: nodes.length,
    edges: graph.edges.length,
    flipperCarriers: nodes.filter((n) => n.flipper_count > 0).length,
    maxFlip,
    flipperHistogram: hist,
    yearMin: years.length ? Math.min(...years) : null,
    yearMax: years.length ? Math.max(...years) : null,
    countries,
    sequenceTypes: sts.size,
    lineages,
    founders: nodes.filter((n) => n.founder).length,
  };
}

export function useLineage(organism: string | null): LineageState {
  const [graph, setGraph] = useState<LineageGraph | null>(null);
  const [status, setStatus] = useState<LineageStatus>(organism ? "loading" : "empty");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    // No active dataset (blank console) → don't fetch; sit in an empty/ready state.
    if (!organism) {
      setGraph(null);
      setStatus("empty");
      setError(null);
      return;
    }
    setStatus("loading");
    setGraph(null);
    setError(null);
    api
      .lineage(organism)
      .then((g) => {
        if (!live) return;
        setGraph(g);
        setStatus(g.nodes.length === 0 ? "empty" : "ready");
      })
      .catch((e) => {
        if (!live) return;
        setError(String(e));
        setStatus("error");
      });
    return () => {
      live = false;
    };
  }, [organism]);

  const byId = useMemo(() => {
    const m = new Map<string, LineageNode>();
    if (graph) for (const n of graph.nodes) m.set(n.id, n);
    return m;
  }, [graph]);

  const overview = useMemo(() => (graph ? summarize(graph) : null), [graph]);

  return { graph, status, error, byId, overview };
}
