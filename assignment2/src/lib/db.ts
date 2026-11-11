import Database from "better-sqlite3";
import path from "path";

export type Task = {
  id: number;
  title: string;
  done: boolean;
};

const database = new Database(path.join(process.cwd(), "tasks.db"));

database.exec(`
  CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0
  )
`);

const count = database.prepare("SELECT COUNT(*) AS count FROM tasks").get() as { count: number };

if (count.count === 0) {
  const insert = database.prepare("INSERT INTO tasks (title, done) VALUES (?, ?)");
  const seed = database.transaction(() => {
    insert.run("Learn SQLite", 0);
    insert.run("Build a CRUD API", 0);
    insert.run("Test the endpoints", 0);
  });
  seed();
}

export function toTask(row: { id: number; title: string; done: number }): Task {
  return { id: row.id, title: row.title, done: Boolean(row.done) };
}

export default database;
