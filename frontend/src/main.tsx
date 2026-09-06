import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import Dashboard from "./App";
import Landing from "./Landing";
import "./style.css";

function Router() {
  const [path, setPath] = useState(window.location.pathname || "/");
  useEffect(() => {
    const onPop = () => setPath(window.location.pathname || "/");
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  if (path === "/dashboard") return <Dashboard />;
  return <Landing />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Router />
  </React.StrictMode>,
);
