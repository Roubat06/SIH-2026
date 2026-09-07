import React, { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import { ZoomIn, ZoomOut, RotateCcw, AlertTriangle, Shield, CheckCircle } from "lucide-react";
import { type GraphResponse, short, btc, sats } from "./data";

interface GraphProps {
  graphData: GraphResponse | null;
  loading: boolean;
  selectedNodeId?: string | null;
  onSelectNode?: (nodeId: string, nodeType: "transaction" | "address") => void;
}

export default function Graph({ graphData, loading, selectedNodeId, onSelectNode }: GraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!containerRef.current || !graphData || !graphData.elements) return;

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const elements: cytoscape.ElementDefinition[] = [];

    // Add nodes
    graphData.elements.nodes.forEach((n) => {
      const isTx = n.data.type === "transaction";
      const risk = n.data.risk_level || "LOW";
      elements.push({
        group: "nodes",
        data: {
          id: n.data.id,
          label: isTx ? `TX: ${short(n.data.id, 4)}` : short(n.data.id, 5),
          fullId: n.data.id,
          type: n.data.type,
          riskLevel: risk,
          riskScore: n.data.risk_score || 0,
          isTarget: n.data.is_target || false,
          valueSats: n.data.value_sats || n.data.total_sats || 0,
        },
      });
    });

    // Add edges
    graphData.elements.edges.forEach((e) => {
      elements.push({
        group: "edges",
        data: {
          id: `${e.data.source}->${e.data.target}`,
          source: e.data.source,
          target: e.data.target,
          valueSats: e.data.value_sats || 0,
          label: e.data.value_sats ? `${btc(e.data.value_sats)} BTC` : "",
        },
      });
    });

    try {
      const cy = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: "node",
            style: {
              label: "data(label)",
              color: "#9aabbc",
              "font-size": "10px",
              "font-family": "SFMono-Regular, Consolas, monospace",
              "text-valign": "bottom",
              "text-margin-y": 6,
              "background-color": "#1e293b",
              "border-width": 2,
              "border-color": "#475569",
              width: 32,
              height: 32,
            },
          },
          {
            selector: 'node[type = "transaction"]',
            style: {
              shape: "round-rectangle",
              width: 48,
              height: 32,
              "border-color": "#79dfb8",
              "background-color": "#0d2b26",
            },
          },
          {
            selector: 'node[type = "address"]',
            style: {
              shape: "ellipse",
              width: 32,
              height: 32,
              "border-color": "#38bdf8",
              "background-color": "#082f49",
            },
          },
          {
            selector: 'node[riskLevel = "HIGH"]',
            style: {
              "border-color": "#fb923c",
              "background-color": "#431407",
              color: "#fdba74",
            },
          },
          {
            selector: 'node[riskLevel = "CRITICAL"]',
            style: {
              "border-color": "#f87171",
              "background-color": "#450a0a",
              color: "#fca5a5",
              "border-width": 3,
            },
          },
          {
            selector: "node[?isTarget]",
            style: {
              "border-width": 4,
              "border-color": "#e8b36a",
              "background-color": "#422006",
              color: "#fde047",
            },
          },
          {
            selector: "node:selected",
            style: {
              "border-width": 4,
              "border-color": "#ffffff",
              "shadow-blur": 12,
              "shadow-color": "#79dfb8",
              "shadow-opacity": 0.8,
            },
          },
          {
            selector: "edge",
            style: {
              width: 1.5,
              "line-color": "#334155",
              "target-arrow-color": "#64748b",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              "arrow-scale": 0.9,
              label: "data(label)",
              "font-size": "8px",
              color: "#64748b",
              "text-rotation": "autorotate",
              "text-margin-y": -6,
            },
          },
        ],
        layout: {
          name: "breadthfirst",
          directed: true,
          padding: 30,
          spacingFactor: 1.25,
          animate: true,
          animationDuration: 400,
        },
      });

      cy.on("tap", "node", (evt) => {
        const node = evt.target;
        const id = node.data("fullId");
        const type = node.data("type");
        if (onSelectNode) {
          onSelectNode(id, type);
        }
      });

      cyRef.current = cy;
    } catch (err) {
      console.error("Cytoscape init error:", err);
    }

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [graphData]);

  // Handle selectedNodeId highlight
  useEffect(() => {
    if (!cyRef.current || !selectedNodeId) return;
    const cy = cyRef.current;
    cy.nodes().unselect();
    const target = cy.nodes(`[fullId = "${selectedNodeId}"]`);
    if (target.length > 0) {
      target.select();
      cy.animate({
        center: { eles: target },
        zoom: Math.max(cy.zoom(), 1.2),
        duration: 300,
      });
    }
  }, [selectedNodeId]);

  const handleZoomIn = () => {
    if (cyRef.current) cyRef.current.zoom(cyRef.current.zoom() * 1.25);
  };

  const handleZoomOut = () => {
    if (cyRef.current) cyRef.current.zoom(cyRef.current.zoom() * 0.8);
  };

  const handleFit = () => {
    if (cyRef.current) cyRef.current.fit(undefined, 30);
  };

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", minHeight: "520px", background: "#0a0f16", borderRadius: "8px", border: "1px solid #1e293b", overflow: "hidden" }}>
      {/* Controls Overlay */}
      <div style={{ position: "absolute", top: "12px", right: "12px", zIndex: 10, display: "flex", gap: "6px" }}>
        <button className="button small" onClick={handleZoomIn} title="Zoom In">
          <ZoomIn size={14} />
        </button>
        <button className="button small" onClick={handleZoomOut} title="Zoom Out">
          <ZoomOut size={14} />
        </button>
        <button className="button small" onClick={handleFit} title="Reset View">
          <RotateCcw size={14} />
        </button>
      </div>

      {/* Legend Overlay */}
      <div style={{ position: "absolute", bottom: "12px", left: "12px", zIndex: 10, background: "rgba(15, 23, 42, 0.85)", backdropFilter: "blur(6px)", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", display: "flex", gap: "14px", fontSize: "11px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ width: "12px", height: "10px", borderRadius: "3px", background: "#0d2b26", border: "1.5px solid #79dfb8", display: "inline-block" }} />
          <span>Transaction</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#082f49", border: "1.5px solid #38bdf8", display: "inline-block" }} />
          <span>Address</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ width: "10px", height: "10px", borderRadius: "3px", background: "#422006", border: "1.5px solid #e8b36a", display: "inline-block" }} />
          <span>Target Subject</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ width: "10px", height: "10px", borderRadius: "3px", background: "#450a0a", border: "1.5px solid #f87171", display: "inline-block" }} />
          <span>High / Critical Risk</span>
        </div>
      </div>

      {/* Loading indicator */}
      {loading && (
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(10, 15, 22, 0.7)", zIndex: 20 }}>
          <div style={{ color: "#79dfb8", display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
            <span className="spinner" /> Loading graph topology...
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && (!graphData || !graphData.elements || graphData.elements.nodes.length === 0) && (
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: "#64748b", padding: "20px", textAlign: "center" }}>
          <AlertTriangle size={32} style={{ marginBottom: "8px", opacity: 0.5 }} />
          <p style={{ margin: 0, fontWeight: 500 }}>No transaction graph loaded</p>
          <small>Select a transaction or alert to visualize multi-hop UTXO flow.</small>
        </div>
      )}

      {/* Canvas */}
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}
