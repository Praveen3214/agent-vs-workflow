# Deploy the live demo (Hugging Face Spaces)

This puts the tool online as a public URL anyone can use. The demo gives each
visitor **4 free briefs** on your shared key, then asks them to paste **their own
free Groq key** to continue — so it stays effectively free for you and can never
run up a bill.

> Why it's safe: your shared key is a Groq **free-tier** key, which Groq itself
> caps at **100K tokens/day**. Worst case, the demo simply asks visitors for
> their own key for the rest of the day. There is no paid surprise.

---

## What's already set up for you

| File | Purpose |
|---|---|
| `Dockerfile` | Builds the app, serves it on port 7860 (the HF default) |
| `README.md` front-matter | Tells HF this is a Docker Space (`sdk: docker`, `app_port: 7860`) |
| `webapp/app.py` | Free-quota + bring-your-own-key logic, `/healthz`, `/api/quota` |
| `.dockerignore` | Keeps secrets and dev files out of the image |

Tunable limits (set as Space **Variables**, optional):
`FREE_PER_VISITOR` (default 4) · `GLOBAL_DAILY_CAP` (default 30).

---

## Steps (~10 minutes)

1. **Create the Space**
   - Go to <https://huggingface.co/new-space>
   - Name it (e.g. `competitive-brief-generator`)
   - **SDK: Docker** → **Blank** template → choose **Public** → Create.

2. **Add your Groq key as a secret** (this is the shared free-tier key)
   - In the Space: **Settings → Variables and secrets → New secret**
   - Name: `GROQ_API_KEY`  ·  Value: your `gsk_...` key → Save.
   - *(Optional)* add Variables `FREE_PER_VISITOR` / `GLOBAL_DAILY_CAP` to tune limits.

3. **Push the code to the Space**

   The Space is a git repo. From this project folder:

   ```bash
   git init                 # if not already a repo
   git add .
   git commit -m "Live demo: brief generator"
   git remote add space https://huggingface.co/spaces/<your-username>/competitive-brief-generator
   git push space main      # use 'master' if that's your branch
   ```

   *(HF will prompt for your username + an access token as the password — create a
   token at <https://huggingface.co/settings/tokens> with "write" scope.)*

4. **Watch it build**
   - The Space shows a build log, then "Running". First load may take a minute.
   - Your live URL: `https://huggingface.co/spaces/<your-username>/competitive-brief-generator`

5. **Test it**
   - Generate a few briefs (free quota counts down), then confirm it asks for a
     key on the 5th. Paste any visitor's own `gsk_...` key to continue unlimited.

---

## Notes & gotchas

- **Free DuckDuckGo search rate-limits under load.** If a public visitor sees
  "no sources", the **Source URLs** box (paste links directly) is the robust path.
- **Counters are in-memory** and reset when the Space restarts/sleeps — fine for a
  demo. For durable per-user limits you'd add a small datastore (out of scope).
- **Agent mode is token-hungry** — a single agent run on the shared key can use a
  big slice of the daily budget. The per-visitor and global caps protect you, and
  visitors can always run the agent on their own key.
- **GitHub + HF together:** the YAML block at the top of `README.md` is HF config
  and is ignored by GitHub's renderer (it shows as a small table). Keep both
  remotes (`origin` = GitHub, `space` = Hugging Face) and push to each.

---

## Alternative host: Render

If you'd rather use Render: create a **Web Service** from the repo, it auto-detects
the `Dockerfile`, set the `GROQ_API_KEY` env var, and set the start command to
`uvicorn webapp.app:app --host 0.0.0.0 --port $PORT`. Free tier sleeps after 15
min idle (~30s cold start).
