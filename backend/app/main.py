import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

from .database.schema import init_schema
from .database.seed import seed_database
from .api.routes import auth, dashboard, transactions, alerts, cases, graph, bitcoin, models, rag, ai, reports, audit

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database schema and seed data
    init_schema()
    seed_database()
    print('Sentinel Platform initialized successfully on SQLite3.')
    yield

app = FastAPI(
    title='Sentinel — AI-Powered Bitcoin Transaction Monitoring & Investigation Platform',
    version='2.0.0',
    description='SIH 2026 Production Prototype for Bitcoin Transaction Monitoring, Hybrid ML/Rule Anomaly Detection, Transaction Graph Exploration, RAG Security Knowledge, and Grounded AI Security Analyst.',
    lifespan=lifespan
)

# CORS Middleware
origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()] or ['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Mount API Routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(transactions.router)
app.include_router(alerts.router)
app.include_router(cases.router)
app.include_router(graph.router)
app.include_router(bitcoin.router)
app.include_router(models.router)
app.include_router(rag.router)
app.include_router(ai.router)
app.include_router(reports.router)
app.include_router(audit.router)

@app.get('/api/health')
def health_check():
    return {
        'status': 'healthy',
        'platform': 'Sentinel Bitcoin Monitoring & Investigation Platform',
        'version': '2.0.0',
        'database': 'SQLite3 (Thread-Safe WAL)',
        'ai_analyst': 'Google Gemini + RAG (Local FAISS / TF-IDF Vector Index)'
    }
