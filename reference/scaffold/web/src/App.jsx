// Talks ONLY to backend/ — never directly to agent-service (see docs/ARCHITECTURE.md).
// Shares the exact same API contract as mobile/ (specs/api.spec.md) — no
// web-specific endpoints, so behavior can never silently diverge by platform.
import React, { useEffect, useState } from 'react';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:3000';

export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: 'unreachable' }));
  }, []);

  return (
    <div>
      <h1>Personal Cognitive OS</h1>
      <p>backend status: {health ? health.status : 'checking...'}</p>
      {/* TODO: journal capture UI, staging confirmation flow, etc. — see specs/ */}
    </div>
  );
}
