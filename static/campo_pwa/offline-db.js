/**
 * offline-db.js — SQLite WASM via @sqlite.org/sqlite-wasm com OPFS
 * Banco offline persistente para o Portal Campo PWA.
 *
 * Uso (módulo ES):
 *   import CampoDB from '/static/campo_pwa/offline-db.js';
 *   const db = await CampoDB.init();
 *   await db.upsertOS([...]);
 *   const lista = await db.listOS('EM_ANDAMENTO');
 *   await db.enqueueSync('/portal/campo/os/5/concluir/', 'POST', { foto_url: '...' });
 */

const SQLITE_CDN = 'https://cdn.jsdelivr.net/npm/@sqlite.org/sqlite-wasm@3.46.1-build1/sqlite-wasm/jswasm/';

let _db = null;

const SCHEMA = `
  CREATE TABLE IF NOT EXISTS os (
    id               INTEGER PRIMARY KEY,
    numero           TEXT,
    tipo             TEXT,
    status           TEXT,
    descricao        TEXT,
    talhao_nome      TEXT,
    safra_nome       TEXT,
    data_prevista    TEXT,
    data_inicio      TEXT,
    observacoes      TEXT,
    synced_at        TEXT
  );

  CREATE TABLE IF NOT EXISTS os_insumo (
    id                  INTEGER PRIMARY KEY,
    os_id               INTEGER,
    produto_nome        TEXT,
    quantidade_planejada REAL,
    quantidade_aplicada REAL
  );

  CREATE TABLE IF NOT EXISTS sync_queue (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint    TEXT    NOT NULL,
    method      TEXT    NOT NULL DEFAULT 'POST',
    payload     TEXT    NOT NULL DEFAULT '{}',
    tentativas  INTEGER NOT NULL DEFAULT 0,
    criado_em   TEXT    NOT NULL
  );
`;

async function _loadSqlite3() {
  /* Tenta OPFS primeiro (Chrome/Edge); cai para in-memory se não suportado */
  const { default: sqlite3InitModule } = await import(
    SQLITE_CDN + 'sqlite3.mjs'
  );
  const sqlite3 = await sqlite3InitModule({ print: () => {}, printErr: () => {} });

  let db;
  if (sqlite3.oo1.OpfsDb && await hasOPFS()) {
    db = new sqlite3.oo1.OpfsDb('/campo-pwa.db');
  } else {
    db = new sqlite3.oo1.DB('/campo-pwa.db', 'ct');
  }
  return db;
}

async function hasOPFS() {
  try {
    await navigator.storage.getDirectory();
    return true;
  } catch (_) {
    return false;
  }
}

const CampoDB = {
  async init() {
    if (_db) return this;
    _db = await _loadSqlite3();
    _db.exec(SCHEMA);
    return this;
  },

  /* Salva/atualiza lista de OS recebidas do servidor */
  upsertOS(lista) {
    const stmt = _db.prepare(`
      INSERT INTO os (id, numero, tipo, status, descricao, talhao_nome, safra_nome,
                      data_prevista, data_inicio, observacoes, synced_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(id) DO UPDATE SET
        status=excluded.status, descricao=excluded.descricao,
        data_inicio=excluded.data_inicio, observacoes=excluded.observacoes,
        synced_at=excluded.synced_at
    `);
    const now = new Date().toISOString();
    _db.exec('BEGIN');
    try {
      for (const o of lista) {
        stmt.bind([
          o.id, o.numero, o.tipo, o.status, o.descricao,
          o.talhao_nome, o.safra_nome || '',
          o.data_prevista || '', o.data_inicio || '',
          o.observacoes || '', now,
        ]).step();
        stmt.reset();
      }
      _db.exec('COMMIT');
    } catch (e) {
      _db.exec('ROLLBACK');
      throw e;
    } finally {
      stmt.finalize();
    }
  },

  /* Lista OS por status (null = todos) */
  listOS(status) {
    const rows = [];
    const sql = status
      ? `SELECT * FROM os WHERE status = '${status.replace(/'/g, "''")}' ORDER BY data_prevista`
      : 'SELECT * FROM os ORDER BY data_prevista';
    _db.exec({ sql, rowMode: 'object', callback: r => rows.push(r) });
    return rows;
  },

  /* Busca OS por id */
  getOS(id) {
    const rows = [];
    _db.exec({ sql: `SELECT * FROM os WHERE id = ${id}`, rowMode: 'object', callback: r => rows.push(r) });
    return rows[0] || null;
  },

  /* Atualiza status de uma OS localmente (antes de sincronizar) */
  updateOSStatus(id, status) {
    _db.exec(`UPDATE os SET status = '${status}' WHERE id = ${id}`);
  },

  /* Adiciona mutação na fila de sincronização */
  enqueueSync(endpoint, method, payload) {
    const stmt = _db.prepare(
      'INSERT INTO sync_queue (endpoint, method, payload, criado_em) VALUES (?,?,?,?)'
    );
    stmt.bind([endpoint, method, JSON.stringify(payload), new Date().toISOString()]).step();
    stmt.finalize();
  },

  /* Retorna todos os itens pendentes na fila */
  getSyncQueue() {
    const rows = [];
    _db.exec({ sql: 'SELECT * FROM sync_queue ORDER BY id', rowMode: 'object', callback: r => rows.push(r) });
    return rows;
  },

  /* Remove item da fila após sincronizar */
  removeSyncItem(id) {
    _db.exec(`DELETE FROM sync_queue WHERE id = ${id}`);
  },

  /* Incrementa contador de tentativas */
  incrementTentativas(id) {
    _db.exec(`UPDATE sync_queue SET tentativas = tentativas + 1 WHERE id = ${id}`);
  },
};

export default CampoDB;
