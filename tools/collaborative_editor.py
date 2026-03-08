"""
Collaborative Document Editing
Faz 10.8 — Çoklu agent eşzamanlı dosya düzenleme
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum


class EditType(str, Enum):
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"


@dataclass
class Edit:
    edit_id: str
    doc_id: str
    user_id: str
    edit_type: EditType
    position: int
    content: str
    timestamp: datetime
    version: int


@dataclass
class DocumentLock:
    doc_id: str
    user_id: str
    locked_at: datetime
    expires_at: datetime


class CollaborativeDocument:
    """Çoklu agent için eşzamanlı doküman düzenleme"""
    
    def __init__(self, doc_id: str, initial_content: str = ""):
        self.doc_id = doc_id
        self.content = initial_content
        self.version = 0
        self.edits: List[Edit] = []
        self.active_users: Set[str] = set()
        self.locks: Dict[int, DocumentLock] = {}  # position -> lock
        self._subscribers: List[asyncio.Queue] = []
    
    def add_user(self, user_id: str) -> None:
        """Kullanıcı ekle"""
        self.active_users.add(user_id)
        asyncio.create_task(self._notify_subscribers({
            "type": "user_joined",
            "user_id": user_id,
            "active_users": list(self.active_users)
        }))
    
    def remove_user(self, user_id: str) -> None:
        """Kullanıcı çıkar"""
        self.active_users.discard(user_id)
        # Kullanıcının lock'larını temizle
        self.locks = {pos: lock for pos, lock in self.locks.items() if lock.user_id != user_id}
        asyncio.create_task(self._notify_subscribers({
            "type": "user_left",
            "user_id": user_id,
            "active_users": list(self.active_users)
        }))
    
    def apply_edit(self, edit: Edit) -> bool:
        """Düzenleme uygula"""
        if edit.version != self.version:
            return False  # Version conflict
        
        try:
            if edit.edit_type == EditType.INSERT:
                self.content = self.content[:edit.position] + edit.content + self.content[edit.position:]
            elif edit.edit_type == EditType.DELETE:
                length = len(edit.content)
                self.content = self.content[:edit.position] + self.content[edit.position + length:]
            elif edit.edit_type == EditType.REPLACE:
                length = len(edit.content)
                self.content = self.content[:edit.position] + edit.content + self.content[edit.position + length:]
            
            self.version += 1
            self.edits.append(edit)
            
            asyncio.create_task(self._notify_subscribers({
                "type": "edit_applied",
                "edit": asdict(edit),
                "new_version": self.version,
                "content": self.content
            }))
            
            return True
        except:
            return False
    
    def lock_region(self, user_id: str, start: int, end: int, duration_seconds: int = 30) -> bool:
        """Bölge kilitle"""
        now = datetime.now()
        
        # Çakışan lock var mı kontrol et
        for pos in range(start, end):
            if pos in self.locks:
                lock = self.locks[pos]
                if lock.expires_at > now and lock.user_id != user_id:
                    return False
        
        # Lock oluştur
        expires_at = datetime.fromtimestamp(now.timestamp() + duration_seconds)
        for pos in range(start, end):
            self.locks[pos] = DocumentLock(
                doc_id=self.doc_id,
                user_id=user_id,
                locked_at=now,
                expires_at=expires_at
            )
        
        asyncio.create_task(self._notify_subscribers({
            "type": "region_locked",
            "user_id": user_id,
            "start": start,
            "end": end
        }))
        
        return True
    
    def unlock_region(self, user_id: str, start: int, end: int) -> None:
        """Bölge kilidini aç"""
        for pos in range(start, end):
            if pos in self.locks and self.locks[pos].user_id == user_id:
                del self.locks[pos]
        
        asyncio.create_task(self._notify_subscribers({
            "type": "region_unlocked",
            "user_id": user_id,
            "start": start,
            "end": end
        }))
    
    def get_state(self) -> Dict:
        """Doküman durumunu al"""
        return {
            "doc_id": self.doc_id,
            "content": self.content,
            "version": self.version,
            "active_users": list(self.active_users),
            "locks": [
                {
                    "position": pos,
                    "user_id": lock.user_id,
                    "expires_at": lock.expires_at.isoformat()
                }
                for pos, lock in self.locks.items()
            ]
        }
    
    async def subscribe(self) -> asyncio.Queue:
        """Değişikliklere abone ol"""
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Abonelikten çık"""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
    
    async def _notify_subscribers(self, event: Dict) -> None:
        """Aboneleri bilgilendir"""
        for queue in self._subscribers:
            try:
                await queue.put(event)
            except:
                pass


class CollaborativeEditor:
    """Çoklu doküman yönetimi"""
    
    def __init__(self):
        self._documents: Dict[str, CollaborativeDocument] = {}
    
    def create_document(self, doc_id: str, initial_content: str = "") -> CollaborativeDocument:
        """Yeni doküman oluştur"""
        if doc_id in self._documents:
            return self._documents[doc_id]
        
        doc = CollaborativeDocument(doc_id, initial_content)
        self._documents[doc_id] = doc
        return doc
    
    def get_document(self, doc_id: str) -> Optional[CollaborativeDocument]:
        """Doküman al"""
        return self._documents.get(doc_id)
    
    def delete_document(self, doc_id: str) -> bool:
        """Doküman sil"""
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False
    
    def list_documents(self) -> List[Dict]:
        """Tüm dokümanları listele"""
        return [
            {
                "doc_id": doc_id,
                "version": doc.version,
                "active_users": list(doc.active_users),
                "content_length": len(doc.content)
            }
            for doc_id, doc in self._documents.items()
        ]


# Global instance
_editor = CollaborativeEditor()


def get_editor() -> CollaborativeEditor:
    """Global editor instance'ı al"""
    return _editor
