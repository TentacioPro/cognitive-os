// Same backend contract as web/ — this is deliberate (specs/api.spec.md).
// The CUA-importer and any camera/photo-capture flows (multi-modal ingestion,
// per the plan doc) live here first, since mobile is where photos originate.
import React, { useEffect, useState } from 'react';
import { View, Text } from 'react-native';

const API_BASE = process.env.EXPO_PUBLIC_API_BASE || 'http://localhost:3000';

export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: 'unreachable' }));
  }, []);

  return (
    <View>
      <Text>Personal Cognitive OS (mobile)</Text>
      <Text>backend status: {health ? health.status : 'checking...'}</Text>
      {/* TODO: photo capture -> multi-modal ingestion staging flow, per plan doc Section 4 */}
    </View>
  );
}
