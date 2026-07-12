"use client";
// The Nextstrain-style spine. A horizontal D3 cluster/dendrogram laid out from the
// parent edges: nodes colored by flipper_count (neutral → teal), pan/zoom, hover
// detail, and click to lift the selected strain. Colors come from CSS variables so
// the tree recolors when the theme flips. Selection updates in place — no relayout,
// so the user's pan/zoom is preserved.
import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import { cssVarColor, useIsDark } from "@/lib/useIsDark";
import { Empty } from "./ui";
import type { LineageStatus } from "@/lib/useLineage";
import type { LineageGraph, LineageNode } from "@/lib/types";

type Hover = { node: LineageNode; x: number; y: number } | null;
type NodeSel = d3.Selection<SVGGElement, d3.HierarchyPointNode<LineageNode>, SVGGElement, unknown>;

const VIRTUAL = "__root__";

export function LineageTree({
  graph,
  status,
  error,
  selectedId,
  onSelect,
}: {
  graph: LineageGraph | null;
  status: LineageStatus;
  error?: string | null;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}) {
  const [hover, setHover] = useState<Hover>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const nodeSelRef = useRef<NodeSel | null>(null);
  const resetRef = useRef<() => void>(() => {});
  const selectedRef = useRef<string | null>(selectedId);
  const onSelectRef = useRef(onSelect);
  const isDark = useIsDark();

  selectedRef.current = selectedId;
  onSelectRef.current = onSelect;

  const maxFlip = useMemo(
    () => (graph ? Math.max(1, ...graph.nodes.map((n) => n.flipper_count)) : 1),
    [graph],
  );

  // Build / rebuild the tree (on data, theme, or resize) — not on selection.
  useEffect(() => {
    if (!graph || graph.nodes.length === 0 || !svgRef.current || !wrapRef.current) return;

    const neutral = cssVarColor("--tree-neutral");
    const accent = cssVarColor("--accent");
    const linkColor = cssVarColor("--line", 0.2);
    const labelColor = cssVarColor("--text", 0.72);
    const halo = cssVarColor("--surface");
    const ringColor = cssVarColor("--text");

    const width = wrapRef.current.clientWidth || 720;
    const height = 520;
    const margin = { top: 18, right: 108, bottom: 18, left: 26 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    const ids = new Set(graph.nodes.map((n) => n.id));
    const virtualNode = { id: VIRTUAL, label: "", flipper_count: 0 } as LineageNode;
    const data = [virtualNode, ...graph.nodes];

    let root: d3.HierarchyPointNode<LineageNode>;
    try {
      root = d3
        .stratify<LineageNode>()
        .id((d) => d.id)
        .parentId((d) =>
          d.id === VIRTUAL
            ? null
            : !d.parent_id || !ids.has(d.parent_id)
              ? VIRTUAL
              : d.parent_id,
        )(data) as unknown as d3.HierarchyPointNode<LineageNode>;
    } catch {
      return;
    }

    const color = d3.scaleLinear<string>().domain([0, maxFlip]).range([neutral, accent]).clamp(true);
    d3.cluster<LineageNode>().size([innerH, innerW])(root);

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${width} ${height}`).attr("width", "100%").attr("height", height);

    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
    const zoomLayer = g.append("g");

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 6])
      .on("zoom", (ev) => zoomLayer.attr("transform", ev.transform.toString()));
    svg.call(zoom).on("dblclick.zoom", null);
    resetRef.current = () =>
      svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity);

    // Links (skip the synthetic root's own links).
    zoomLayer
      .append("g")
      .attr("fill", "none")
      .attr("stroke", linkColor)
      .attr("stroke-width", 1)
      .selectAll("path")
      .data(root.links().filter((l) => (l.source.data as LineageNode).id !== VIRTUAL))
      .join("path")
      .attr("d", (d) => {
        const s = d.source as d3.HierarchyPointNode<LineageNode>;
        const t = d.target as d3.HierarchyPointNode<LineageNode>;
        const mx = (s.y + t.y) / 2;
        return `M${s.y},${s.x}C${mx},${s.x} ${mx},${t.x} ${t.y},${t.x}`;
      });

    const nodes = root
      .descendants()
      .filter((d) => (d.data as LineageNode).id !== VIRTUAL) as d3.HierarchyPointNode<LineageNode>[];

    const node: NodeSel = zoomLayer
      .append("g")
      .selectAll<SVGGElement, d3.HierarchyPointNode<LineageNode>>("g")
      .data(nodes)
      .join("g")
      .attr("transform", (d) => `translate(${d.y},${d.x})`)
      .attr("cursor", "pointer")
      .on("mouseenter", (ev, d) => {
        const [mx, my] = d3.pointer(ev, wrapRef.current);
        setHover({ node: d.data, x: mx, y: my });
      })
      .on("mouseleave", () => setHover(null))
      .on("click", (_ev, d) =>
        onSelectRef.current(selectedRef.current === d.data.id ? null : d.data.id),
      );

    node
      .append("circle")
      .attr("class", "lt-dot")
      .attr("r", (d) => (d.children ? 3.5 : 4.5))
      .attr("fill", (d) => color(d.data.flipper_count))
      .attr("stroke", halo)
      .attr("stroke-width", 1.4);

    node
      .filter((d) => !d.children)
      .append("text")
      .attr("class", "lt-label")
      .attr("dy", "0.31em")
      .attr("x", 8)
      .attr("font-size", 9)
      .attr("font-family", "var(--font-mono)")
      .attr("fill", labelColor)
      .text((d) => d.data.label)
      .clone(true)
      .lower()
      .attr("stroke", halo)
      .attr("stroke-width", 3);

    nodeSelRef.current = node;
    // Apply current selection styling immediately after (re)build.
    applySelection(node, selectedRef.current, ringColor, halo);
  }, [graph, maxFlip, isDark]);

  // Selection styling only — no relayout, so pan/zoom is preserved.
  useEffect(() => {
    if (!nodeSelRef.current) return;
    applySelection(nodeSelRef.current, selectedId, cssVarColor("--text"), cssVarColor("--surface"));
  }, [selectedId]);

  if (status === "error")
    return (
      <Empty title="API not reachable" icon={<Plug />}>
        Start the backend (<code className="font-mono text-accentStrong">make backend</code>) and
        reload. {error ? <span className="mt-1 block text-faint">{error}</span> : null}
      </Empty>
    );
  if (status === "loading" || !graph)
    return (
      <div className="space-y-2">
        <div className="skeleton h-[480px] rounded-xl" />
      </div>
    );
  if (status === "empty")
    return (
      <Empty title="No strains loaded" icon={<Plug />}>
        Run <code className="font-mono text-accentStrong">make seed</code> to load the demo
        cohort, then reload.
      </Empty>
    );

  return (
    <div ref={wrapRef} className="relative">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span className="text-[0.7rem] text-faint">
          {graph.nodes.length} strains · {graph.edges.length} edges · drag to pan · scroll to zoom
        </span>
        <div className="flex items-center gap-3">
          <Legend maxFlip={maxFlip} />
          <button
            onClick={() => resetRef.current()}
            className="rounded-md border border-line/12 px-2 py-0.5 text-[0.68rem] text-muted transition hover:border-line/25 hover:text-text"
          >
            reset view
          </button>
        </div>
      </div>
      <svg ref={svgRef} className="bg-grid rounded-xl border border-line/10 bg-surface2/40" />
      {hover && (
        <div
          className="pointer-events-none absolute z-20 rounded-lg border border-line/12 bg-surface px-2.5 py-1.5 text-xs shadow-lift"
          style={{ left: Math.min(hover.x + 14, (wrapRef.current?.clientWidth ?? 999) - 170), top: hover.y + 14 }}
        >
          <div className="font-mono font-medium text-text">{hover.node.label}</div>
          <div className="mt-0.5 flex items-center gap-1.5 text-[0.7rem] text-muted">
            <span className="inline-flex items-center gap-1">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: cssVarColor("--accent", 0.4 + 0.6 * (hover.node.flipper_count / maxFlip)) }}
              />
              {hover.node.flipper_count} flipper{hover.node.flipper_count === 1 ? "" : "s"}
            </span>
            {hover.node.st != null && <span>· ST {hover.node.st}</span>}
            {hover.node.year != null && <span>· {hover.node.year}</span>}
          </div>
          {hover.node.country && (
            <div className="mt-0.5 text-[0.68rem] text-faint">{hover.node.country}</div>
          )}
        </div>
      )}
    </div>
  );
}

function applySelection(node: NodeSel, selectedId: string | null, ring: string, halo: string) {
  node
    .select<SVGCircleElement>("circle.lt-dot")
    .attr("r", (d) => (d.data.id === selectedId ? 6.5 : d.children ? 3.5 : 4.5))
    .attr("stroke", (d) => (d.data.id === selectedId ? ring : halo))
    .attr("stroke-width", (d) => (d.data.id === selectedId ? 2 : 1.4));
}

function Legend({ maxFlip }: { maxFlip: number }) {
  return (
    <span className="flex items-center gap-1.5 text-[0.68rem] text-faint">
      <span>0</span>
      <span
        className="inline-block h-2 w-16 rounded-full"
        style={{
          background: `linear-gradient(90deg, ${cssVarColor("--tree-neutral")}, ${cssVarColor("--accent")})`,
        }}
      />
      <span className="text-accentStrong">{maxFlip} flippers</span>
    </span>
  );
}

function Plug() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 2v6M15 2v6M7 8h10v3a5 5 0 0 1-10 0zM12 16v6" />
    </svg>
  );
}
