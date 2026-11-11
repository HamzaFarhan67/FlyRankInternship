# Task CRUD API

This project stores tasks in SQLite using `better-sqlite3`. SQLite was chosen because it stores persistent data in one local file without requiring a separate database server.

The database file is created at `assignment2/tasks.db` when the application starts. The `tasks` table and three example tasks are created automatically when needed.

## Start

```bash
npm install
npm run dev
```

The API is available at `http://localhost:3000/api/tasks`.

## SQL example

```sql
SELECT * FROM tasks WHERE done = 1;
```
