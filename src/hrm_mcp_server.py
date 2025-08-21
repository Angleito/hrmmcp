import asyncio
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import yaml
from mcp.server.fastmcp import FastMCP

from .models import ReasoningSession, SessionStatus
from .state_manager import StateManager


class HRMServer:
    def __init__(self, config_path: Path = Path("config.yaml")) -> None:
        self.config = self._load_config(config_path)
        self.mcp = FastMCP("hrm-reasoning-server")
        self.state_manager = StateManager(Path(self.config["persistence"]["database_path"]))
        self.active_sessions: Dict[UUID, ReasoningSession] = {}
        self._register_tools()
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        if not config_path.exists():
            return self._default_config()
        
        with open(config_path) as f:
            config: Dict[str, Any] = yaml.safe_load(f)
            return config
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            "server": {
                "max_concurrent_sessions": 10,
                "session_timeout_minutes": 30
            },
            "reasoning": {
                "h_module": {
                    "max_iterations": 10,
                    "min_confidence_threshold": 0.7
                },
                "l_module": {
                    "max_cycles_per_h": 6,
                    "min_cycles_per_h": 3
                },
                "convergence": {
                    "global_threshold": 0.85
                }
            },
            "persistence": {
                "database_path": "hrm_reasoning.db",
                "retention_days": 7
            }
        }
    
    def _register_tools(self) -> None:
        from .tools import register_tools
        register_tools(self.mcp, self)
    
    async def initialize(self) -> None:
        await self.state_manager.initialize()
        
        active_session_ids = await self.state_manager.get_active_sessions()
        for session_id in active_session_ids:
            session = await self.state_manager.load_session(session_id)
            if session:
                self.active_sessions[session_id] = session
    
    async def create_session(self) -> UUID:
        if len(self.active_sessions) >= self.config["server"]["max_concurrent_sessions"]:
            raise RuntimeError("Maximum concurrent sessions reached")
        
        session_id = uuid4()
        session = ReasoningSession(session_id=session_id)
        
        self.active_sessions[session_id] = session
        await self.state_manager.save_session(session)
        
        return session_id
    
    async def get_session(self, session_id: UUID) -> Optional[ReasoningSession]:
        return self.active_sessions.get(session_id)
    
    async def update_session(self, session: ReasoningSession) -> None:
        self.active_sessions[session.session_id] = session
        await self.state_manager.save_session(session)
    
    async def complete_session(self, session_id: UUID, result: Dict[str, Any]) -> None:
        session = self.active_sessions.get(session_id)
        if session:
            session.status = SessionStatus.COMPLETED
            session.final_solution = result
            await self.update_session(session)
    
    async def cleanup_expired_sessions(self) -> None:
        retention_days = self.config["persistence"]["retention_days"]
        deleted_count = await self.state_manager.cleanup_old_sessions(retention_days)
        
        if deleted_count > 0:
            print(f"Cleaned up {deleted_count} expired sessions")
    
    async def start(self) -> None:
        await self.initialize()
        
        cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        try:
            print("HRM MCP Server starting...")
            await self.mcp.run()  # type: ignore[func-returns-value]
        finally:
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _periodic_cleanup(self) -> None:
        while True:
            await asyncio.sleep(3600)  # Run every hour
            await self.cleanup_expired_sessions()


async def main() -> None:
    server = HRMServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())