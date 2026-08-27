import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from 'react-native';

const API_BASE = process.env.EXPO_PUBLIC_API_BASE || 'http://localhost:3000/api';
const TABS = ['Overview', 'Capture', 'Review', 'System'];

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'x-actor-role': 'owner', ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.reason || body.error || `Request failed (${response.status})`);
  return body;
}

function EntryCard({ entry, onConfirm }) {
  return (
    <View style={styles.entryCard} accessibilityLabel={`Entry ${entry.content || entry.notes || 'untitled'}`}>
      <View style={styles.rowBetween}><Text style={styles.eyebrow}>{entry.domain}</Text><Text style={[styles.status, entry.status === 'committed' ? styles.statusCommitted : styles.statusStaged]}>{entry.status}</Text></View>
      <Text style={styles.entryTitle}>{entry.content || entry.notes || 'Untitled capture'}</Text>
      <Text style={styles.muted}>{new Date(entry.timestamp).toLocaleString()} · {entry.source || 'manual'}</Text>
      <View style={styles.facts}>
        {entry.value !== null && entry.value !== undefined && <Text style={styles.fact}>Value <Text style={styles.factValue}>{String(entry.value)}{entry.unit ? ` ${entry.unit}` : ''}</Text></Text>}
        {entry.energy !== null && entry.energy !== undefined && <Text style={styles.fact}>Energy <Text style={styles.factValue}>{entry.energy}/10</Text></Text>}
      </View>
      {entry.status === 'staged' && <Pressable onPress={() => onConfirm(entry.id)} style={({ pressed }) => [styles.smallButton, pressed && styles.pressed]} accessibilityRole="button" accessibilityLabel="Confirm entry"><Text style={styles.smallButtonText}>Confirm entry</Text></Pressable>}
    </View>
  );
}

export default function App() {
  const { width } = useWindowDimensions();
  const [tab, setTab] = useState('Overview');
  const [health, setHealth] = useState(null);
  const [entries, setEntries] = useState([]);
  const [domains, setDomains] = useState([]);
  const [audit, setAudit] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [content, setContent] = useState('');
  const [domain, setDomain] = useState('health');
  const [energy, setEnergy] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [healthData, journalData, domainData, auditData] = await Promise.all([api('/health'), api('/journal'), api('/domains'), api('/audit')]);
      setHealth(healthData);
      setEntries(journalData.entries || []);
      setDomains(domainData.domains || []);
      setAudit(auditData.entries || []);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const stats = useMemo(() => ({ total: entries.length, staged: entries.filter((entry) => entry.status === 'staged').length, committed: entries.filter((entry) => entry.status === 'committed').length }), [entries]);

  const submit = async () => {
    if (!content.trim()) return;
    setSaving(true);
    setError('');
    try {
      await api('/journal', { method: 'POST', body: JSON.stringify({ content: content.trim(), domain, energy: energy ? Number(energy) : undefined, source: 'manual', timestamp: new Date().toISOString() }) });
      setContent('');
      setEnergy('');
      await refresh();
      setTab('Review');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  };

  const confirmEntry = async (id) => {
    try {
      await api(`/journal/${id}/confirm`, { method: 'POST', body: '{}' });
      await refresh();
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const contentView = tab === 'Capture' ? (
    <View style={styles.panel}>
      <Text style={styles.eyebrow}>Capture layer</Text>
      <Text style={styles.heading}>What is present?</Text>
      <Text style={styles.mutedLarge}>Record one observation before it disappears.</Text>
      <Text style={styles.label}>Observation</Text>
      <TextInput value={content} onChangeText={setContent} placeholder="I noticed..." placeholderTextColor="#8d989d" multiline numberOfLines={5} style={[styles.textInput, { minHeight: width < 390 ? 110 : 135 }]} accessibilityLabel="Observation" />
      <Text style={styles.label}>Domain</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
        {domains.filter((item) => item.active).map((item) => <Pressable key={item.name} onPress={() => setDomain(item.name)} style={[styles.chip, domain === item.name && styles.chipActive]} accessibilityRole="button"><Text style={[styles.chipText, domain === item.name && styles.chipTextActive]}>{item.name}</Text></Pressable>)}
      </ScrollView>
      <Text style={styles.label}>Energy / 10</Text>
      <TextInput value={energy} onChangeText={setEnergy} placeholder="7" placeholderTextColor="#8d989d" keyboardType="number-pad" style={styles.textInput} accessibilityLabel="Energy" />
      <Pressable onPress={submit} disabled={saving} style={({ pressed }) => [styles.primaryButton, pressed && styles.pressed, saving && styles.disabled]} accessibilityRole="button"><Text style={styles.primaryButtonText}>{saving ? 'Saving...' : 'Stage observation'}</Text></Pressable>
      <Text style={styles.helper}>Saved through the shared API to the local system.</Text>
    </View>
  ) : tab === 'Review' ? (
    <View><View style={styles.rowBetween}><View><Text style={styles.eyebrow}>Review layer</Text><Text style={styles.heading}>See the pattern.</Text></View><Pressable onPress={refresh} accessibilityRole="button"><Text style={styles.link}>Refresh</Text></Pressable></View>{entries.length ? entries.slice().reverse().map((entry) => <EntryCard key={entry.id} entry={entry} onConfirm={confirmEntry} />) : <View style={styles.empty}><Text style={styles.emptyTitle}>Nothing to review yet</Text><Text style={styles.muted}>Capture your first observation to start a history.</Text></View>}</View>
  ) : tab === 'System' ? (
    <View><Text style={styles.eyebrow}>System layer</Text><Text style={styles.heading}>How it holds.</Text><View style={styles.systemGrid}>{['Capture', 'Extract', 'Store', 'Review'].map((item, index) => <View key={item} style={[styles.systemCard, { width: width < 390 ? '100%' : '47%' }]}><Text style={styles.eyebrow}>0{index + 1}</Text><Text style={styles.systemTitle}>{item}</Text><Text style={styles.muted}>{['VoxLog · Telegram · Logseq', 'Gemini Flash', 'SQLite · JSONL · Git', 'Weekly markdown'][index]}</Text></View>)}</View><View style={styles.panel}><View style={styles.rowBetween}><Text style={styles.sectionTitle}>Audit trace</Text><Text style={[styles.status, health?.status === 'ok' ? styles.statusCommitted : styles.statusStaged]}>{health?.status || 'offline'}</Text></View>{audit.slice(-5).reverse().map((event, index) => <View style={styles.auditRow} key={`${event.request_id}-${index}`}><Text style={styles.auditTime}>{new Date(event.timestamp).toLocaleTimeString()}</Text><Text style={styles.auditAction} numberOfLines={1}>{event.action}</Text><Text style={styles.muted}>{event.result}</Text></View>)}</View></View>
  ) : (
    <View><View style={styles.hero}><Text style={styles.eyebrowLight}>Personal operating system</Text><Text style={styles.heroTitle}>Make your life legible.</Text><Text style={styles.heroCopy}>A quiet command center for the signals you capture and the decisions you want to remember.</Text><Pressable onPress={() => setTab('Capture')} style={({ pressed }) => [styles.primaryButton, pressed && styles.pressed]} accessibilityRole="button"><Text style={styles.primaryButtonText}>Capture a moment  →</Text></Pressable></View><View style={styles.statGrid}>{[['Entries', stats.total], ['Review', stats.staged], ['Committed', stats.committed]].map(([label, value]) => <View key={label} style={styles.statCard}><Text style={styles.eyebrow}>{label}</Text><Text style={styles.statValue}>{value}</Text><Text style={styles.muted}>in your system</Text></View>)}</View><Text style={styles.sectionTitle}>Recent entries</Text>{entries.length ? entries.slice(-3).reverse().map((entry) => <EntryCard key={entry.id} entry={entry} onConfirm={confirmEntry} />) : <View style={styles.empty}><Text style={styles.emptyTitle}>Your system is quiet</Text><Text style={styles.muted}>Capture a moment to begin.</Text></View>}</View>
  );

  return <SafeAreaView style={styles.safe}><StatusBar barStyle="light-content" backgroundColor="#0d1726" /><View style={styles.app}><View style={styles.header}><Text style={styles.logo}>◒ <Text style={styles.logoAccent}>Cognitive OS</Text></Text>{loading ? <ActivityIndicator color="#ef784b" /> : <Text style={styles.online}>{health?.status === 'ok' ? 'Online' : 'Offline'}</Text>}</View><View style={styles.nav}>{TABS.map((item) => <Pressable key={item} onPress={() => setTab(item)} style={[styles.navItem, tab === item && styles.navItemActive]} accessibilityRole="tab" accessibilityState={{ selected: tab === item }}><Text style={[styles.navText, tab === item && styles.navTextActive]}>{item}</Text></Pressable>)}</View><ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">{error ? <View style={styles.error}><Text style={styles.errorText}>{error}</Text></View> : null}{contentView}</ScrollView></View></SafeAreaView>;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#0d1726' },
  app: { flex: 1, backgroundColor: '#f6f5f1' },
  header: { minHeight: 64, paddingHorizontal: 20, backgroundColor: '#0d1726', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  logo: { color: '#fff', fontFamily: 'monospace', fontSize: 16 },
  logoAccent: { color: '#ef784b' },
  online: { color: '#8bc7a9', fontFamily: 'monospace', fontSize: 11 },
  nav: { paddingHorizontal: 13, paddingVertical: 10, backgroundColor: '#0d1726', flexDirection: 'row', gap: 5 },
  navItem: { paddingHorizontal: 10, paddingVertical: 8, borderRadius: 5 },
  navItemActive: { backgroundColor: 'rgba(255,255,255,.12)' },
  navText: { color: '#aeb9bb', fontSize: 12 },
  navTextActive: { color: '#fff' },
  scroll: { padding: 18, paddingBottom: 44 },
  eyebrow: { color: '#74808a', fontFamily: 'monospace', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 },
  eyebrowLight: { color: '#81909a', fontFamily: 'monospace', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 },
  hero: { backgroundColor: '#0d1726', padding: 25, borderRadius: 3, marginBottom: 17 },
  heroTitle: { color: '#f4f1e9', fontSize: 42, lineHeight: 46, fontFamily: 'serif', marginTop: 15, marginBottom: 14 },
  heroCopy: { color: '#b7c1c0', fontSize: 14, lineHeight: 22, marginBottom: 22 },
  heading: { color: '#162235', fontSize: 40, lineHeight: 44, fontFamily: 'serif', marginTop: 12, marginBottom: 10 },
  mutedLarge: { color: '#74808a', fontSize: 14, lineHeight: 21, marginBottom: 24 },
  panel: { backgroundColor: '#fffefa', borderWidth: 1, borderColor: '#dcdedc', padding: 20, borderRadius: 3 },
  primaryButton: { alignSelf: 'flex-start', backgroundColor: '#ef784b', paddingHorizontal: 16, paddingVertical: 13, borderRadius: 3 },
  primaryButtonText: { color: '#fff', fontWeight: '700', fontSize: 13 },
  pressed: { opacity: 0.82, transform: [{ scale: 0.98 }] },
  disabled: { opacity: 0.55 },
  helper: { color: '#74808a', fontSize: 11, marginTop: 16 },
  label: { color: '#162235', fontFamily: 'monospace', fontSize: 10, textTransform: 'uppercase', letterSpacing: .6, marginTop: 12, marginBottom: 7 },
  textInput: { borderWidth: 1, borderColor: '#dcdedc', backgroundColor: '#fbfaf7', color: '#162235', borderRadius: 2, padding: 13, fontSize: 14, textAlignVertical: 'top' },
  chips: { gap: 8, paddingBottom: 3 },
  chip: { borderWidth: 1, borderColor: '#dcdedc', paddingHorizontal: 12, paddingVertical: 9, borderRadius: 20 },
  chipActive: { borderColor: '#ef784b', backgroundColor: '#fff0e9' },
  chipText: { color: '#74808a', fontSize: 12, textTransform: 'capitalize' },
  chipTextActive: { color: '#b4664e', fontWeight: '600' },
  statGrid: { flexDirection: 'row', gap: 8, marginBottom: 35 },
  statCard: { flex: 1, minHeight: 105, padding: 14, backgroundColor: '#fffefa', borderWidth: 1, borderColor: '#dcdedc' },
  statValue: { color: '#162235', fontFamily: 'monospace', fontSize: 30, marginTop: 20, marginBottom: 4 },
  sectionTitle: { color: '#162235', fontFamily: 'serif', fontSize: 25, marginBottom: 14 },
  entryCard: { backgroundColor: '#fffefa', borderWidth: 1, borderColor: '#dcdedc', padding: 17, marginBottom: 10, borderRadius: 2 },
  rowBetween: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  status: { paddingHorizontal: 7, paddingVertical: 4, borderRadius: 16, overflow: 'hidden', fontFamily: 'monospace', fontSize: 9, textTransform: 'uppercase' },
  statusCommitted: { color: '#3f876e', backgroundColor: '#e8f3ec' },
  statusStaged: { color: '#b4664e', backgroundColor: '#fff0e9' },
  entryTitle: { color: '#162235', fontSize: 16, fontWeight: '600', marginTop: 10, marginBottom: 6 },
  muted: { color: '#74808a', fontSize: 12, lineHeight: 18 },
  facts: { flexDirection: 'row', flexWrap: 'wrap', gap: 14, marginTop: 13, marginBottom: 14 },
  fact: { color: '#74808a', fontFamily: 'monospace', fontSize: 11 },
  factValue: { color: '#162235' },
  smallButton: { alignSelf: 'flex-start', backgroundColor: '#ef784b', paddingHorizontal: 12, paddingVertical: 9, borderRadius: 3 },
  smallButtonText: { color: '#fff', fontSize: 11, fontWeight: '600' },
  link: { color: '#ef784b', fontFamily: 'monospace', fontSize: 11 },
  empty: { padding: 35, borderWidth: 1, borderColor: '#dcdedc', borderStyle: 'dashed', alignItems: 'center' },
  emptyTitle: { color: '#162235', fontFamily: 'serif', fontSize: 22, marginBottom: 7 },
  systemGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: 10, marginVertical: 22 },
  systemCard: { minHeight: 130, backgroundColor: '#fffefa', borderWidth: 1, borderColor: '#dcdedc', padding: 15 },
  systemTitle: { color: '#162235', fontFamily: 'serif', fontSize: 22, marginTop: 21, marginBottom: 8 },
  auditRow: { flexDirection: 'row', gap: 8, paddingVertical: 11, borderTopWidth: 1, borderTopColor: '#dcdedc' },
  auditTime: { color: '#74808a', fontFamily: 'monospace', fontSize: 10, width: 65 },
  auditAction: { color: '#162235', fontFamily: 'monospace', fontSize: 10, flex: 1 },
  error: { padding: 12, marginBottom: 16, borderWidth: 1, borderColor: '#efc4b5', backgroundColor: '#fff0e9' },
  errorText: { color: '#8d3f2b', fontSize: 12 },
});
