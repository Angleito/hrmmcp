import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

import aiosqlite

from .models import HModuleState, LModuleTrace, ReasoningSession, SessionStatus


class StateManager:
    def __init__(self, db_path: Path | str = Path("hrm_reasoning.db")) -> None:
        self.db_path = db_path
    
    async def initialize(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS h_module_states (
                    state_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    iteration INTEGER NOT NULL,
                    state_data TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS l_module_traces (
                    trace_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    h_iteration INTEGER NOT NULL,
                    l_iteration INTEGER NOT NULL,
                    trace_data TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS reasoning_results (
                    result_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    final_solution TEXT NOT NULL,
                    reasoning_trace TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    total_iterations INTEGER NOT NULL,
                    computation_time REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            
            await db.commit()
    
    async def save_session(self, session: ReasoningSession) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO sessions 
                (session_id, status, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                str(session.session_id),
                session.status.value,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                json.dumps({
                    "h_state": session.h_module_state.model_dump() if session.h_module_state else None,
                    "l_state": session.l_module_state.model_dump() if session.l_module_state else None,
                    "solution": session.final_solution
                })
            ))
            await db.commit()
    
    async def load_session(self, session_id: UUID) -> Optional[ReasoningSession]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT session_id, status, created_at, updated_at, metadata
                FROM sessions WHERE session_id = ?
            ''', (str(session_id),))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            metadata = json.loads(row[4]) if row[4] else {}
            
            return ReasoningSession(
                session_id=UUID(row[0]),
                status=SessionStatus(row[1]),
                created_at=datetime.fromisoformat(row[2]),
                updated_at=datetime.fromisoformat(row[3]),
                h_module_state=HModuleState.model_validate(metadata["h_state"]) if metadata.get("h_state") else None,
                final_solution=metadata.get("solution")
            )
    
    async def save_h_state(self, session_id: UUID, state: HModuleState) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO h_module_states
                (state_id, session_id, iteration, state_data, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                f"{session_id}_{state.iteration}",
                str(session_id),
                state.iteration,
                state.model_dump_json(),
                datetime.now(timezone.utc).isoformat()
            ))
            await db.commit()
    
    async def save_l_trace(self, session_id: UUID, h_iteration: int, l_iteration: int, trace: LModuleTrace) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO l_module_traces
                (trace_id, session_id, h_iteration, l_iteration, trace_data, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                f"{session_id}_{h_iteration}_{l_iteration}",
                str(session_id),
                h_iteration,
                l_iteration,
                trace.model_dump_json(),
                datetime.now(timezone.utc).isoformat()
            ))
            await db.commit()
    
    async def cleanup_old_sessions(self, retention_days: int = 7) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                DELETE FROM sessions 
                WHERE updated_at < ? AND status != ?
            ''', (cutoff.isoformat(), SessionStatus.ACTIVE.value))
            
            deleted_count = cursor.rowcount or 0
            await db.commit()
            return deleted_count
    
    async def get_active_sessions(self) -> List[UUID]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT session_id FROM sessions 
                WHERE status = ?
            ''', (SessionStatus.ACTIVE.value,))
            
            rows = await cursor.fetchall()
            return [UUID(row[0]) for row in rows]