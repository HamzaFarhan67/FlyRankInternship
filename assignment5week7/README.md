# FlowPilot

FlowPilot is a visual AI workflow editor. Each decision node asks an AI model for exactly `YES` or `NO`, then follows the matching edge.

## Run

```bash
npm install
copy .env.example .env.local
npm run dev
```

Set `OPENAI_API_KEY` in `.env.local` for OpenAI decisions. Without a key, the app uses a small local fallback so the editor can still be tested.

Run the Inngest dev server in a second terminal:

```bash
npm run inngest
```

The editor supports node creation, prompt editing, connections, local storage, JSON export, execution logs, active node styling, and Inngest-compatible workflow functions.
