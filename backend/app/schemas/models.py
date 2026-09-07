from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = 'ANALYST'

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: str
    created_at: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: UserResponse

class TxInputSchema(BaseModel):
    prev_txid: Optional[str] = None
    prev_vout: Optional[int] = None
    address: Optional[str] = None
    value_sats: int = 0
    sequence: Optional[int] = None
    script_type: Optional[str] = None

class TxOutputSchema(BaseModel):
    output_index: int
    address: Optional[str] = None
    value_sats: int
    script_type: Optional[str] = None

class TransactionSchema(BaseModel):
    txid: str
    block_hash: Optional[str] = None
    block_height: Optional[int] = None
    block_time: Optional[str] = None
    observed_at: Optional[str] = None
    size_bytes: Optional[int] = None
    vsize: Optional[int] = None
    weight: Optional[int] = None
    fee_sats: Optional[int] = None
    fee_rate: Optional[float] = None
    total_input_sats: int = 0
    total_output_sats: int = 0
    input_count: int = 0
    output_count: int = 0
    confirmed: bool = True
    risk_score: float = 0.0
    risk_level: str = 'LOW'
    anomaly_score: float = 0.0
    anomaly_label: int = 1
    is_flagged: bool = False
    source: str = 'seed'
    inputs: List[TxInputSchema] = []
    outputs: List[TxOutputSchema] = []

class AlertSchema(BaseModel):
    id: str
    txid: str
    severity: str
    risk_score: float
    anomaly_score: float
    detection_method: str
    title: str
    reason: str
    evidence_json: Optional[str] = None
    status: str = 'NEW'
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class AlertStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None

class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = 'MEDIUM'
    txids: List[str] = []

class CaseNoteCreate(BaseModel):
    note: str

class CaseResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    lead_investigator_id: Optional[str] = None
    lead_investigator_name: Optional[str] = None
    transaction_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class RAGSearchRequest(BaseModel):
    query: str
    limit: int = 5
    category: Optional[str] = None

class RAGSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_matches: int

class AIAnalyzeRequest(BaseModel):
    txid: Optional[str] = None
    case_id: Optional[str] = None
    prompt: str
    include_rag: bool = True

class AIAnalyzeResponse(BaseModel):
    summary: str
    evidence: List[str]
    why_it_matters: str
    recommended_steps: List[str]
    limitations: str
    facts: List[str]
    model_indications: List[str]
    suggestions: List[str]
    model_used: str
    rag_sources: List[str]

class SyncRequest(BaseModel):
    count: int = 25
    use_live_api: bool = True

