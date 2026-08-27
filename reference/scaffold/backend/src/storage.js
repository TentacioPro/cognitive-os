'use strict';

const fs = require('fs');
const path = require('path');
const { DatabaseSync } = require('node:sqlite');

class JournalStore {
  constructor(databasePath) {
    const resolvedPath = databasePath || path.join(__dirname, '..', 'data', 'cognitive-os.db');
    if (resolvedPath !== ':memory:') fs.mkdirSync(path.dirname(resolvedPath), { recursive: true });
    this.db = new DatabaseSync(resolvedPath);
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS journal_entries (
        id TEXT PRIMARY KEY,
        content TEXT NOT NULL,
        domain TEXT NOT NULL,
        value_json TEXT,
        unit TEXT,
        sentiment REAL,
        energy INTEGER,
        timestamp TEXT NOT NULL,
        created_at TEXT NOT NULL,
        committed_at TEXT,
        source TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('staged', 'committed'))
      );
      CREATE INDEX IF NOT EXISTS idx_journal_timestamp ON journal_entries(timestamp);
      CREATE INDEX IF NOT EXISTS idx_journal_status ON journal_entries(status);
    `);
  }

  create(entry) {
    this.db.prepare(`
      INSERT INTO journal_entries
        (id, content, domain, value_json, unit, sentiment, energy, timestamp,
         created_at, source, status)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      entry.id,
      entry.content,
      entry.domain,
      JSON.stringify(entry.value),
      entry.unit,
      entry.sentiment,
      entry.energy,
      entry.timestamp,
      entry.created_at,
      entry.source,
      entry.status,
    );
    return entry;
  }

  list() {
    return this.db.prepare(`
      SELECT id, content, domain, value_json, unit, sentiment, energy,
             timestamp, created_at, committed_at, source, status
      FROM journal_entries ORDER BY timestamp ASC, id ASC
    `).all().map((row) => this.deserialize(row));
  }

  get(id) {
    const row = this.db.prepare('SELECT * FROM journal_entries WHERE id = ?').get(id);
    return row ? this.deserialize(row) : null;
  }

  commit(id, committedAt) {
    const result = this.db.prepare(`
      UPDATE journal_entries SET status = 'committed', committed_at = ?
      WHERE id = ? AND status = 'staged'
    `).run(committedAt, id);
    return result.changes === 1 ? this.get(id) : null;
  }

  close() {
    this.db.close();
  }

  deserialize(row) {
    return {
      id: row.id,
      content: row.content,
      domain: row.domain,
      value: row.value_json === null ? null : JSON.parse(row.value_json),
      unit: row.unit,
      sentiment: row.sentiment,
      energy: row.energy,
      timestamp: row.timestamp,
      created_at: row.created_at,
      committed_at: row.committed_at,
      source: row.source,
      status: row.status,
    };
  }
}

module.exports = { JournalStore };
