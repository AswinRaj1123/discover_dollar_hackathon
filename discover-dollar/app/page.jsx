"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [apiStatus, setApiStatus] = useState("Checking API...");

  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then((response) => {
        if (!response.ok) throw new Error("API request failed");
        return response.json();
      })
      .then((data) => setApiStatus(`${data.message} (${data.database})`))
      .catch(() => setApiStatus("API unavailable - start FastAPI on port 8000"));
  }, []);

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">Hackathon starter kit</p>
        <h1>Build fast. Ship clearly.</h1>
        <p className="intro">
          A ready-to-use Next.js + FastAPI + MongoDB foundation for tomorrow&apos;s
          problem statement.
        </p>
        <div className="status-card">
          <span className="status-dot" />
          <div>
            <strong>Backend status</strong>
            <p>{apiStatus}</p>
          </div>
        </div>
      </section>

      <section className="stack-grid" aria-label="Technology stack">
        <article>
          <span className="card-number">01</span>
          <h2>Next.js</h2>
          <p>Frontend screens, forms, loading states, and API calls.</p>
        </article>
        <article>
          <span className="card-number">02</span>
          <h2>FastAPI</h2>
          <p>Typed REST endpoints with automatic Swagger documentation.</p>
        </article>
        <article>
          <span className="card-number">03</span>
          <h2>MongoDB</h2>
          <p>Flexible document storage, ready to connect through Motor.</p>
        </article>
      </section>
    </main>
  );
}
