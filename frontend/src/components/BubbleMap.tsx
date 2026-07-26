import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as d3 from 'd3';
import type { BubbleNode } from '../lib/api';

type Mode = 'industry' | 'relationships' | 'rate';

type Props = {
  nodes: BubbleNode[];
  rateSensitivity?: Record<string, number>;
  focusTicker?: string | null;
  relatedTickers?: Set<string>;
  mode: Mode;
  onSelect?: (ticker: string) => void;
  /** Drop chrome — used when the map is the full-bleed home composition */
  bare?: boolean;
};

const SECTOR_COLORS: Record<string, string> = {
  'Information Technology': '#ff6b4a',
  'Health Care': '#2a9d8f',
  Financials: '#e9a820',
  'Consumer Discretionary': '#e76f51',
  'Communication Services': '#457b9d',
  Industrials: '#6a994e',
  'Consumer Staples': '#bc6c25',
  Energy: '#d62828',
  Utilities: '#4a6fa5',
  'Real Estate': '#9b5de5',
  Materials: '#c9a227',
};

function changeColor(pct: number): string {
  const t = Math.max(-1, Math.min(1, pct / 3));
  if (t >= 0) return d3.interpolateRgb('#c5c9d2', '#007a4d')(t);
  return d3.interpolateRgb('#c5c9d2', '#c8102e')(-t);
}

export function BubbleMap({
  nodes,
  rateSensitivity = {},
  focusTicker,
  relatedTickers,
  mode,
  onSelect,
  bare = false,
}: Props) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();
  const [dims, setDims] = useState({ w: 1100, h: 720 });
  const [colorByChange, setColorByChange] = useState(true);
  const zoomScaleRef = useRef(1);

  type SimNode = BubbleNode & { x?: number; y?: number; vx?: number; vy?: number; r: number };

  const prepared = useMemo(() => {
    const maxCap = d3.max(nodes, (d) => d.market_cap) ?? 1;
    const r = d3.scaleSqrt().domain([0, maxCap]).range([4, 42]);
    return nodes.map((n) => ({ ...n, r: r(n.market_cap) }));
  }, [nodes]);

  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (cr) setDims({ w: Math.max(640, cr.width), h: Math.max(520, cr.height) });
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!svgRef.current || prepared.length === 0) return;
    const { w, h } = dims;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    svg.attr('viewBox', `0 0 ${w} ${h}`);

    const g = svg.append('g');
    zoomScaleRef.current = 1;

    const sectors = Array.from(new Set(prepared.map((d) => d.sector)));
    const angle = d3.scalePoint().domain(sectors).range([0, Math.PI * 2 - 0.01]);

    const simNodes: SimNode[] = prepared.map((d) => ({ ...d }));

    const clusterForce = (alpha: number) => {
      for (const d of simNodes) {
        let tx = w / 2;
        let ty = h / 2;
        if (mode === 'industry' || mode === 'rate') {
          const a = angle(d.sector) ?? 0;
          const radius = mode === 'rate' ? 220 : 260;
          tx = w / 2 + Math.cos(a) * radius;
          ty = h / 2 + Math.sin(a) * radius;
        } else if (mode === 'relationships' && focusTicker) {
          if (d.ticker === focusTicker) {
            tx = w / 2;
            ty = h / 2;
          } else if (relatedTickers?.has(d.ticker)) {
            const idx = Array.from(relatedTickers).indexOf(d.ticker);
            const a = (idx / Math.max(relatedTickers.size, 1)) * Math.PI * 2;
            tx = w / 2 + Math.cos(a) * 180;
            ty = h / 2 + Math.sin(a) * 180;
          } else {
            // park non-related nodes in a quiet outer ring
            const a = (d.ticker.charCodeAt(0) / 90) * Math.PI * 2;
            tx = w / 2 + Math.cos(a) * 420;
            ty = h / 2 + Math.sin(a) * 420;
          }
        }
        d.vx = (d.vx ?? 0) + (tx - (d.x ?? tx)) * 0.05 * alpha;
        d.vy = (d.vy ?? 0) + (ty - (d.y ?? ty)) * 0.05 * alpha;
      }
    };

    const simulation = d3
      .forceSimulation(simNodes)
      .force('charge', d3.forceManyBody().strength(-8))
      .force(
        'collide',
        d3
          .forceCollide<SimNode>()
          .radius((d) => d.r + 1.5)
          .iterations(2),
      )
      .force('x', d3.forceX(w / 2).strength(0.02))
      .force('y', d3.forceY(h / 2).strength(0.02))
      .on('tick', ticked);

    simulation.force('cluster', clusterForce as never);

    const linkLayer = g.append('g').attr('class', 'links');
    const node = g
      .append('g')
      .selectAll('g')
      .data(simNodes)
      .join('g')
      .attr('class', 'bubble-node')
      .style('cursor', 'pointer')
      .on('click', (_, d) => {
        onSelect?.(d.ticker);
        // In relationships mode, click focuses the network; open detail on second click
        if (mode === 'relationships') {
          if (focusTicker === d.ticker) navigate(`/company/${d.ticker}`);
          return;
        }
        navigate(`/company/${d.ticker}`);
      });

    node
      .append('circle')
      .attr('r', (d) => d.r)
      .attr('fill', (d) => {
        if (mode === 'rate') {
          const s = rateSensitivity[d.sector] ?? 0;
          return s < 0
            ? d3.interpolateRgb('#c5c9d2', '#c8102e')(Math.min(1, Math.abs(s)))
            : d3.interpolateRgb('#c5c9d2', '#007a4d')(Math.min(1, s * 2));
        }
        return colorByChange ? changeColor(d.change_pct) : SECTOR_COLORS[d.sector] ?? '#7a8799';
      })
      .attr('stroke', (d) => {
        if (d.ticker === focusTicker) return '#ff2400';
        if (relatedTickers?.has(d.ticker)) return '#0a0b0e';
        return 'rgba(10,11,14,0.18)';
      })
      .attr('stroke-width', (d) => (d.ticker === focusTicker || relatedTickers?.has(d.ticker) ? 2.5 : 0.7))
      .attr('opacity', (d) => {
        if (mode === 'relationships' && focusTicker) {
          if (d.ticker === focusTicker || relatedTickers?.has(d.ticker)) return 1;
          return 0.12;
        }
        return 0.9;
      });

    node
      .append('title')
      .text(
        (d) =>
          `${d.ticker} · ${d.name}\n${d.sector}\n${d.change_pct >= 0 ? '+' : ''}${d.change_pct.toFixed(2)}% · mkt ${d3.format('.3s')(d.market_cap)}`,
      );

    // Labels on every bubble; visibility gated by zoom × radius in updateLabels()
    const labels = node
      .append('text')
      .attr('class', 'bubble-label')
      .text((d) => d.ticker)
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', '#0a0b0e')
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('font-weight', 600)
      .attr('pointer-events', 'none')
      .attr('opacity', 0);

    function updateLabels(k: number) {
      labels
        .attr('font-size', (d) => Math.max(6, Math.min(12, d.r * 0.55)))
        .attr('opacity', (d) => {
          const screenR = d.r * k;
          // Labels appear once the bubble is large enough on screen
          if (screenR >= 6.5) return 1;
          if (mode === 'relationships' && (d.ticker === focusTicker || relatedTickers?.has(d.ticker))) {
            return screenR >= 4 ? 1 : 0;
          }
          // Mid/large bubbles stay labeled even when zoomed out
          if (d.r >= 9) return 0.95;
          return 0;
        });
    }

    updateLabels(1);

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.35, 12])
      .on('zoom', (event) => {
        const k = event.transform.k;
        zoomScaleRef.current = k;
        g.attr('transform', event.transform);
        updateLabels(k);
      });
    svg.call(zoom);

    function ticked() {
      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
      if (mode === 'relationships' && focusTicker && relatedTickers) {
        const focus = simNodes.find((n) => n.ticker === focusTicker);
        if (!focus) return;
        const links = Array.from(relatedTickers).map((t) => {
          const other = simNodes.find((n) => n.ticker === t);
          return { focus, other };
        });
        linkLayer
          .selectAll('line')
          .data(links.filter((l) => l.other))
          .join('line')
          .attr('x1', (d) => d.focus.x ?? 0)
          .attr('y1', (d) => d.focus.y ?? 0)
          .attr('x2', (d) => d.other!.x ?? 0)
          .attr('y2', (d) => d.other!.y ?? 0)
          .attr('stroke', 'rgba(255,36,0,0.45)')
          .attr('stroke-width', 1.4);
      } else {
        linkLayer.selectAll('line').remove();
      }
    }

    if (mode !== 'relationships') {
      const labelG = g.append('g');
      sectors.forEach((s) => {
        const a = angle(s) ?? 0;
        const radius = 320;
        labelG
          .append('text')
          .attr('x', w / 2 + Math.cos(a) * radius)
          .attr('y', h / 2 + Math.sin(a) * radius)
          .attr('text-anchor', 'middle')
          .attr('fill', 'rgba(90,98,112,0.9)')
          .attr('font-size', 11)
          .attr('font-family', 'JetBrains Mono, monospace')
          .text(s.replace('Consumer ', 'Cons. ').replace('Communication ', 'Comm. '));
      });
    }

    return () => {
      simulation.stop();
    };
  }, [prepared, dims, mode, colorByChange, focusTicker, relatedTickers, rateSensitivity, navigate, onSelect]);

  return (
    <div className={`relative h-full flex flex-col ${bare ? 'min-h-0' : 'min-h-[560px]'}`} ref={wrapRef}>
      <div
        className={`absolute z-10 flex flex-wrap gap-2 ${
          bare ? 'bottom-[7.5rem] left-4 md:left-6 lg:left-8' : 'top-3 right-3 justify-end'
        }`}
      >
        <button
          type="button"
          onClick={() => setColorByChange((v) => !v)}
          className="btn-ghost bg-terminal-panel/90 backdrop-blur-sm"
        >
          Color: {colorByChange ? 'Change' : 'Sector'}
        </button>
      </div>
      <svg ref={svgRef} className="w-full flex-1 touch-none" />
      {!bare && (
        <p className="px-4 pb-2 text-[11px] font-mono text-terminal-muted">
          Scroll to zoom · drag to pan · click a bubble
          {mode === 'relationships'
            ? ' to map its connections · click again to open detail'
            : ' for company detail'}
          {' '}
          · size = market cap
        </p>
      )}
    </div>
  );
}
