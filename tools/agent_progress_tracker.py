"""
Live Agent Progress Tracker
Faz 10.5 — Diğer ajanların ilerleme durumunu canlı görüntüleme
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class AgentStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ProgressStep:
    step_id: str
    description: str
    status: AgentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress_percent: int = 0
    metadata: Dict = None


@dataclass
class AgentProgress:
    agent_id: str
    agent_name: str
    task_id: str
    status: AgentStatus
    current_step: Optional[ProgressStep] = None
    steps: List[ProgressStep] = None
    overall_progress: int = 0
    started_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []
        if self.started_at is None:
            self.started_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class AgentProgressTracker:
    """Gerçek zamanlı agent ilerleme takibi"""
    
    def __init__(self):
        self._progress: Dict[str, AgentProgress] = {}
        self._subscribers: List[asyncio.Queue] = []
    
    def start_task(self, agent_id: str, agent_name: str, task_id: str) -> None:
        """Yeni görev başlat"""
        progress = AgentProgress(
            agent_id=agent_id,
            agent_name=agent_name,
            task_id=task_id,
            status=AgentStatus.THINKING
        )
        self._progress[agent_id] = progress
        asyncio.create_task(self._notify_subscribers(agent_id))
    
    def update_step(
        self,
        agent_id: str,
        step_id: str,
        description: str,
        status: AgentStatus,
        progress_percent: int = 0,
        metadata: Dict = None
    ) -> None:
        """Adım güncelle"""
        if agent_id not in self._progress:
            return
        
        progress = self._progress[agent_id]
        step = ProgressStep(
            step_id=step_id,
            description=description,
            status=status,
            started_at=datetime.now(),
            progress_percent=progress_percent,
            metadata=metadata or {}
        )
        
        progress.current_step = step
        progress.steps.append(step)
        progress.status = status
        progress.updated_at = datetime.now()
        
        # Genel ilerleme hesapla
        if progress.steps:
            progress.overall_progress = sum(s.progress_percent for s in progress.steps) // len(progress.steps)
        
        asyncio.create_task(self._notify_subscribers(agent_id))
    
    def complete_step(self, agent_id: str, step_id: str) -> None:
        """Adımı tamamla"""
        if agent_id not in self._progress:
            return
        
        progress = self._progress[agent_id]
        for step in progress.steps:
            if step.step_id == step_id:
                step.completed_at = datetime.now()
                step.status = AgentStatus.COMPLETED
                step.progress_percent = 100
        
        progress.updated_at = datetime.now()
        asyncio.create_task(self._notify_subscribers(agent_id))
    
    def complete_task(self, agent_id: str) -> None:
        """Görevi tamamla"""
        if agent_id not in self._progress:
            return
        
        progress = self._progress[agent_id]
        progress.status = AgentStatus.COMPLETED
        progress.overall_progress = 100
        progress.updated_at = datetime.now()
        
        if progress.current_step:
            progress.current_step.status = AgentStatus.COMPLETED
            progress.current_step.completed_at = datetime.now()
        
        asyncio.create_task(self._notify_subscribers(agent_id))
    
    def set_error(self, agent_id: str, error_msg: str) -> None:
        """Hata durumu"""
        if agent_id not in self._progress:
            return
        
        progress = self._progress[agent_id]
        progress.status = AgentStatus.ERROR
        progress.updated_at = datetime.now()
        
        if progress.current_step:
            progress.current_step.status = AgentStatus.ERROR
            progress.current_step.metadata = {"error": error_msg}
        
        asyncio.create_task(self._notify_subscribers(agent_id))
    
    def get_progress(self, agent_id: str) -> Optional[Dict]:
        """Agent ilerlemesini al"""
        if agent_id not in self._progress:
            return None
        
        progress = self._progress[agent_id]
        return {
            "agent_id": progress.agent_id,
            "agent_name": progress.agent_name,
            "task_id": progress.task_id,
            "status": progress.status.value,
            "current_step": asdict(progress.current_step) if progress.current_step else None,
            "steps": [asdict(s) for s in progress.steps],
            "overall_progress": progress.overall_progress,
            "started_at": progress.started_at.isoformat(),
            "updated_at": progress.updated_at.isoformat()
        }
    
    def get_all_progress(self) -> List[Dict]:
        """Tüm agent ilerlemelerini al"""
        return [self.get_progress(aid) for aid in self._progress.keys()]
    
    async def subscribe(self) -> asyncio.Queue:
        """İlerleme güncellemelerine abone ol"""
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Abonelikten çık"""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
    
    async def _notify_subscribers(self, agent_id: str) -> None:
        """Aboneleri bilgilendir"""
        progress = self.get_progress(agent_id)
        if not progress:
            return
        
        for queue in self._subscribers:
            try:
                await queue.put(progress)
            except:
                pass
    
    def clear_completed(self, max_age_minutes: int = 60) -> None:
        """Tamamlanmış görevleri temizle"""
        now = datetime.now()
        to_remove = []
        
        for agent_id, progress in self._progress.items():
            if progress.status == AgentStatus.COMPLETED:
                age = (now - progress.updated_at).total_seconds() / 60
                if age > max_age_minutes:
                    to_remove.append(agent_id)
        
        for agent_id in to_remove:
            del self._progress[agent_id]


# Global instance
_tracker = AgentProgressTracker()


def get_tracker() -> AgentProgressTracker:
    """Global tracker instance'ı al"""
    return _tracker
