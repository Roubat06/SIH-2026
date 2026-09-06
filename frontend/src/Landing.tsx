import React from "react";
import { ArrowRight } from "lucide-react";
import Graph from "./Graph";
import { demoAlerts } from "./data";

function Nav() {
  const nav = ["Product", "How it works", "Capabilities"];
  const goDashboard = () => {
    window.history.pushState({}, "Dashboard", "/dashboard");
    window.dispatchEvent(new PopStateEvent("popstate"));
  };
  function scrollToId(id: string) {
    const el = document.getElementById(id);
    const header = document.querySelector(".landing-nav") as HTMLElement | null;
    const offset = header ? header.offsetHeight + 12 : 72;
    if (!el) return;
    const top = el.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top, behavior: "smooth" });
  }
  return (
    <header className="landing-nav">
      <div className="landing-brand">
        <div className="brand-symbol">B</div>
        <div>
          <div className="brand-name">SENTINEL</div>
          <small>BITCOIN INTELLIGENCE</small>
        </div>
      </div>
      <nav className="landing-nav-links">
        <a
          href="#product"
          onClick={(e) => {
            e.preventDefault();
            scrollToId("capabilities");
          }}
        >
          Product
        </a>
        <a
          href="#how"
          onClick={(e) => {
            e.preventDefault();
            scrollToId("how");
          }}
        >
          How it works
        </a>
        <a
          href="#capabilities"
          onClick={(e) => {
            e.preventDefault();
            scrollToId("capabilities");
          }}
        >
          Capabilities
        </a>
        <button className="button primary" onClick={goDashboard}>
          Launch Sentinel <ArrowRight size={14} />
        </button>
      </nav>
    </header>
  );
}

function Hero() {
  const goDashboard = () => {
    window.history.pushState({}, "Dashboard", "/dashboard");
    window.dispatchEvent(new PopStateEvent("popstate"));
  };
  return (
    <section className="hero">
      <div className="hero-inner">
        <div className="eyebrow">SENTINEL / BITCOIN INTELLIGENCE</div>
        <h1>
          See the signals.
          <br />
          Understand the chain.
        </h1>
        <p>
          AI-powered monitoring and analysis of Bitcoin transaction traffic.
          Detect unusual activity, investigate suspicious patterns, and turn
          blockchain data into actionable evidence.
        </p>
        <div className="hero-actions">
          <button className="button primary" onClick={goDashboard}>
            Launch Sentinel →
          </button>
          <button
            className="button"
            onClick={(e) => {
              e.preventDefault();
              const header = document.querySelector(
                ".landing-nav",
              ) as HTMLElement | null;
              const offset = header ? header.offsetHeight + 12 : 72;
              const el = document.getElementById("capabilities");
              if (!el) return;
              const top = el.getBoundingClientRect().top + window.scrollY - offset;
              window.scrollTo({ top, behavior: "smooth" });
            }}
          >
            Explore capabilities
          </button>
        </div>
      </div>
      <div className="hero-visual" aria-hidden />
    </section>
  );
}

function StatusStrip() {
  const items = [
    "LIVE MONITORING",
    "TRANSACTION ANALYSIS",
    "AI SIGNAL DETECTION",
    "INVESTIGATION WORKSPACE",
  ];
  return (
    <div className="status-strip">
      {items.map((t) => (
        <div key={t} className="status-item">
          {t}
        </div>
      ))}
    </div>
  );
}

function HowItWorks() {
  const steps = [
    ["01", "MONITOR", "Track Bitcoin transaction activity."],
    ["02", "ANALYZE", "Analyze transaction behavior and relationships."],
    ["03", "DETECT", "Identify anomalies and suspicious patterns."],
    ["04", "INVESTIGATE", "Give analysts the evidence needed to investigate."],
  ];
  return (
    <section id="how" className="how">
      <h2>From transaction traffic to evidence.</h2>
      <div className="how-grid">
        {steps.map(([num, title, desc]) => (
          <div className="how-card" key={String(num)}>
            <div className="how-num">{num}</div>
            <h3>{title}</h3>
            <p>{desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Capabilities() {
  const [expanded, setExpanded] = React.useState<string | null>(null);

  const caps = [
    {
      name: "Transaction Monitoring",
      description:
        "Continuously analyze Bitcoin transaction traffic to track flows, identify unusual activity, and surface transactions requiring investigation.",
    },
    {
      name: "AI Anomaly Detection",
      description:
        "Use AI-driven behavioral analysis to identify transaction patterns that deviate from expected activity and may indicate suspicious behavior.",
    },
    {
      name: "Risk & Priority Signals",
      description:
        "Assign priority to detected signals so investigators can focus first on transactions and entities requiring immediate attention.",
    },
    {
      name: "Transaction Graph Explorer",
      description:
        "Visualize relationships between Bitcoin addresses and transactions, making complex fund flows easier to trace.",
    },
    {
      name: "Investigation Timeline",
      description:
        "Organize important events chronologically so investigators can reconstruct how suspicious activity developed.",
    },
    {
      name: "Dataset Analysis",
      description:
        "Analyze imported transaction datasets to uncover patterns, anomalies, and relationships within large volumes of blockchain data.",
    },
  ];

  return (
    <section id="capabilities" className="caps">
      <h2>Built for transaction intelligence.</h2>
      <div className="caps-grid">
        {caps.map(({ name, description }) => {
          const isExpanded = expanded === name;

          return (
            <button
              key={name}
              type="button"
              className={`cap-card${isExpanded ? " expanded" : ""}`}
              aria-expanded={isExpanded}
              aria-controls={`capability-panel-${name}`}
              onClick={() => setExpanded((current) => (current === name ? null : name))}
            >
              <span className="cap-card-header">
                <span className="cap-card-title">{name}</span>
                <span className="cap-card-toggle" aria-hidden="true">
                  {isExpanded ? "−" : "+"}
                </span>
              </span>
              <span
                id={`capability-panel-${name}`}
                className={`cap-card-body${isExpanded ? " expanded" : ""}`}
              >
                {description}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function ProductPreview() {
  const open = () => {
    window.history.pushState({}, "Dashboard", "/dashboard");
    window.dispatchEvent(new PopStateEvent("popstate"));
  };
  return (
    <section id="product" className="preview">
      <div className="preview-text">
        <h2>One command center for the entire investigation.</h2>
        <p className="muted">Open the full Sentinel command center to investigate.</p>
        <button className="button" onClick={open}>
          Open Command Center →
        </button>
      </div>
      <div className="preview-frame">
        <div className="preview-screenshot">
          {/* reuse existing Graph component for a live demo preview (read-only) */}
          <div style={{ width: "92%", height: "86%" }}>
            <Graph txid={demoAlerts[0].txid} caseId={"demo"} demo={true} />
          </div>
        </div>
      </div>
    </section>
  );
}

function FinalCTA() {
  const go = () => {
    window.history.pushState({}, "Dashboard", "/dashboard");
    window.dispatchEvent(new PopStateEvent("popstate"));
  };
  return (
    <section className="final-cta">
      <h2>Follow the signals.</h2>
      <p>Turn transaction activity into evidence you can investigate.</p>
      <button className="button primary" onClick={go}>
        Launch Sentinel →
      </button>
    </section>
  );
}

function Footer() {
  return (
    <footer className="landing-footer">
      <div>
        <div className="brand-name">SENTINEL</div>
        <small>BITCOIN INTELLIGENCE</small>
      </div>
      <div className="muted">
        IF-LOOP — AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic
      </div>
    </footer>
  );
}

export default function Landing() {
  return (
    <div className="landing-root">
      <Nav />
      <main className="landing-main">
        <Hero />
        <StatusStrip />
        <HowItWorks />
        <Capabilities />
        <ProductPreview />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  );
}
