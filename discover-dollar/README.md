# Hackathon Starter

Minimal full-stack starter for a Next.js + FastAPI + MongoDB application.

## Run locally

### 1. Frontend

```powershell
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 2. Backend

Create a virtual environment and install the Python dependencies:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API is available at [http://localhost:8000](http://localhost:8000), and interactive docs are at [http://localhost:8000/docs](http://localhost:8000/docs).

### 3. MongoDB

Use your MongoDB Atlas connection string through environment variables. Copy
`.env.example` to `.env.local` and replace the placeholder in `MONGODB_URL`
with your MongoDB connection string. The `.env.local` file is ignored by Git.

```powershell
Copy-Item .env.example .env.local
```

The API health endpoint does not require a live MongoDB connection, so the
hello-world app can still run while you configure the database.

## Where to start during the hackathon

- Add API routes in `backend/app/main.py`.
- Put MongoDB queries and collections in `backend/app/database.py` or a new `backend/app/repositories/` folder.
- Add request/response models in `backend/app/models/`.
- Build screens and call the API from `app/`.
- Keep business logic in backend service modules rather than inside route handlers.
