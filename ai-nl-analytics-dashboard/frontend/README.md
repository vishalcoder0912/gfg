# Frontend (Next.js)

## Requirements
- Node.js **20 LTS** (recommended) or **18 LTS**

If you see `Error: spawn EPERM` (especially during `next dev` / `next build`), you're most likely on **Node 23+** on Windows. Switch to Node 20.

Example (nvm-windows):
```bash
nvm install 20
nvm use 20
```

## Setup
```bash
npm install
```

Create env:
- Copy `.env.example` to `.env.local`

## Run
```bash
npm run dev
```

Open `http://localhost:3000`.

## Backend API
Recommended local setup uses same-origin requests via Next rewrites:
- `NEXT_PUBLIC_API_URL=/api`
- `API_URL=http://localhost:8000`
