/*
 * The guest workspace kept in this browser (IndexedDB): files, folders and notebooks.
 *
 * The server holds each guest's private working copy (what the Python kernel uses). This browser
 * copy is the durable one: when the server has cleaned up an unused guest workspace, or the server
 * was replaced, the next visit restores the workspace from here (see guestSync.ts). Everything is
 * best effort: in a private window or with storage blocked, `isAvailable()` is false and the app
 * keeps working from the server copy alone.
 */

export interface StoredEntry {
  path: string;
  kind: 'file' | 'folder';
  /** Text content, or a Blob for binary files */
  content?: string | Blob;
  /** Server modification time (seconds) of the content we hold */
  modifiedAt?: number;
  updatedAt: number;
}

export interface StoredNotebook {
  id: string;
  title: string;
  kernel_name: string;
  content: unknown;
  updatedAt: number;
}

const DB_NAME = 'pcs-guest-workspace';
const DB_VERSION = 1;

let dbPromise: Promise<IDBDatabase | null> | null = null;

function openDb(): Promise<IDBDatabase | null> {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve) => {
    try {
      if (typeof indexedDB === 'undefined') return resolve(null);
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains('files')) db.createObjectStore('files', { keyPath: 'path' });
        if (!db.objectStoreNames.contains('notebooks')) db.createObjectStore('notebooks', { keyPath: 'id' });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
      req.onblocked = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
  return dbPromise;
}

async function run<T>(store: string, mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T> | void): Promise<T | undefined> {
  const db = await openDb();
  if (!db) return undefined;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(store, mode);
      const req = fn(tx.objectStore(store));
      tx.oncomplete = () => resolve(req ? (req as IDBRequest<T>).result : undefined);
      tx.onerror = () => resolve(undefined);
      tx.onabort = () => resolve(undefined);
    } catch {
      resolve(undefined);
    }
  });
}

function normalize(path: string): string {
  return path.replace(/\\/g, '/').replace(/^\/+|\/+$/g, '');
}

export const guestStore = {
  async isAvailable(): Promise<boolean> {
    return (await openDb()) !== null;
  },

  async putFile(path: string, content: string | Blob, modifiedAt?: number): Promise<void> {
    const entry: StoredEntry = { path: normalize(path), kind: 'file', content, modifiedAt, updatedAt: Date.now() };
    await run('files', 'readwrite', (s) => s.put(entry));
  },

  async putFolder(path: string): Promise<void> {
    const entry: StoredEntry = { path: normalize(path), kind: 'folder', updatedAt: Date.now() };
    await run('files', 'readwrite', (s) => s.put(entry));
  },

  async getEntry(path: string): Promise<StoredEntry | undefined> {
    return run<StoredEntry>('files', 'readonly', (s) => s.get(normalize(path)));
  },

  /** Removes a file, or a folder with everything inside it */
  async deletePath(path: string): Promise<void> {
    const target = normalize(path);
    const all = (await run<StoredEntry[]>('files', 'readonly', (s) => s.getAll())) || [];
    await run('files', 'readwrite', (s) => {
      for (const e of all) if (e.path === target || e.path.startsWith(target + '/')) s.delete(e.path);
    });
  },

  /** Renames or moves a file or folder (and its contents) */
  async renamePath(oldPath: string, newPath: string): Promise<void> {
    const from = normalize(oldPath);
    const to = normalize(newPath);
    const all = (await run<StoredEntry[]>('files', 'readonly', (s) => s.getAll())) || [];
    await run('files', 'readwrite', (s) => {
      for (const e of all) {
        if (e.path !== from && !e.path.startsWith(from + '/')) continue;
        s.delete(e.path);
        s.put({ ...e, path: to + e.path.slice(from.length), updatedAt: Date.now() });
      }
    });
  },

  async putNotebook(nb: Omit<StoredNotebook, 'updatedAt'>): Promise<void> {
    await run('notebooks', 'readwrite', (s) => s.put({ ...nb, updatedAt: Date.now() }));
  },

  async deleteNotebook(id: string): Promise<void> {
    await run('notebooks', 'readwrite', (s) => s.delete(id));
  },

  async snapshot(): Promise<{ entries: StoredEntry[]; notebooks: StoredNotebook[] }> {
    const entries = (await run<StoredEntry[]>('files', 'readonly', (s) => s.getAll())) || [];
    const notebooks = (await run<StoredNotebook[]>('notebooks', 'readonly', (s) => s.getAll())) || [];
    return { entries, notebooks };
  },
};
