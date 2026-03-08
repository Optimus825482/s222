"""
Shared Workspace
Faz 10.6 — Çoklu kullanıcı için ortak Qdrant hafıza sistemi
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import hashlib
import json


class SharedWorkspace:
    """Çoklu kullanıcı ve agent için ortak çalışma alanı"""
    
    def __init__(self, qdrant_url: str = None, collection_name: str = "shared_workspace"):
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.collection_name = collection_name
        self.client = QdrantClient(url=self.qdrant_url)
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Collection yoksa oluştur"""
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
    
    def _generate_id(self, workspace_id: str, item_type: str, content: str) -> str:
        """Unique ID üret"""
        data = f"{workspace_id}:{item_type}:{content}:{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def create_workspace(self, workspace_id: str, owner_id: str, name: str, metadata: Dict = None) -> Dict:
        """Yeni workspace oluştur"""
        workspace_data = {
            "workspace_id": workspace_id,
            "owner_id": owner_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "members": [owner_id],
            "metadata": metadata or {}
        }
        
        point_id = self._generate_id(workspace_id, "workspace", name)
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=[0.0] * 1536,  # Dummy vector
                    payload={
                        "type": "workspace",
                        "workspace_id": workspace_id,
                        **workspace_data
                    }
                )
            ]
        )
        
        return workspace_data
    
    def add_member(self, workspace_id: str, user_id: str, role: str = "member") -> bool:
        """Workspace'e üye ekle"""
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return False
        
        if user_id not in workspace["members"]:
            workspace["members"].append(user_id)
            
            # Güncelle
            self.client.set_payload(
                collection_name=self.collection_name,
                payload={"members": workspace["members"]},
                points=[workspace["_point_id"]]
            )
        
        return True
    
    def remove_member(self, workspace_id: str, user_id: str) -> bool:
        """Workspace'den üye çıkar"""
        workspace = self.get_workspace(workspace_id)
        if not workspace or user_id not in workspace["members"]:
            return False
        
        workspace["members"].remove(user_id)
        
        self.client.set_payload(
            collection_name=self.collection_name,
            payload={"members": workspace["members"]},
            points=[workspace["_point_id"]]
        )
        
        return True
    
    def get_workspace(self, workspace_id: str) -> Optional[Dict]:
        """Workspace bilgilerini al"""
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="type", match=MatchValue(value="workspace")),
                    FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
                ]
            ),
            limit=1
        )
        
        if results[0]:
            point = results[0][0]
            data = dict(point.payload)
            data["_point_id"] = point.id
            return data
        
        return None
    
    def list_workspaces(self, user_id: str) -> List[Dict]:
        """Kullanıcının erişebildiği workspace'leri listele"""
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="type", match=MatchValue(value="workspace"))
                ]
            ),
            limit=100
        )
        
        workspaces = []
        for point in results[0]:
            data = dict(point.payload)
            if user_id in data.get("members", []):
                data["_point_id"] = point.id
                workspaces.append(data)
        
        return workspaces
    
    def add_item(
        self,
        workspace_id: str,
        item_type: str,
        content: str,
        vector: List[float],
        author_id: str,
        metadata: Dict = None
    ) -> str:
        """Workspace'e item ekle (mesaj, dosya, not vb.)"""
        item_id = self._generate_id(workspace_id, item_type, content)
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=item_id,
                    vector=vector,
                    payload={
                        "type": "item",
                        "item_type": item_type,
                        "workspace_id": workspace_id,
                        "content": content,
                        "author_id": author_id,
                        "created_at": datetime.now().isoformat(),
                        "metadata": metadata or {}
                    }
                )
            ]
        )
        
        return item_id
    
    def get_items(
        self,
        workspace_id: str,
        item_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Workspace item'larını al"""
        filter_conditions = [
            FieldCondition(key="type", match=MatchValue(value="item")),
            FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
        ]
        
        if item_type:
            filter_conditions.append(
                FieldCondition(key="item_type", match=MatchValue(value=item_type))
            )
        
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(must=filter_conditions),
            limit=limit,
            offset=offset
        )
        
        items = []
        for point in results[0]:
            data = dict(point.payload)
            data["_item_id"] = point.id
            items.append(data)
        
        return items
    
    def search_items(
        self,
        workspace_id: str,
        query_vector: List[float],
        item_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Workspace içinde semantik arama"""
        filter_conditions = [
            FieldCondition(key="type", match=MatchValue(value="item")),
            FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
        ]
        
        if item_type:
            filter_conditions.append(
                FieldCondition(key="item_type", match=MatchValue(value=item_type))
            )
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=Filter(must=filter_conditions),
            limit=limit
        )
        
        items = []
        for scored_point in results:
            data = dict(scored_point.payload)
            data["_item_id"] = scored_point.id
            data["_score"] = scored_point.score
            items.append(data)
        
        return items
    
    def delete_item(self, item_id: str) -> bool:
        """Item sil"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[item_id]
            )
            return True
        except:
            return False
    
    def get_workspace_stats(self, workspace_id: str) -> Dict:
        """Workspace istatistikleri"""
        items = self.get_items(workspace_id, limit=1000)
        
        item_types = {}
        authors = {}
        
        for item in items:
            item_type = item.get("item_type", "unknown")
            author = item.get("author_id", "unknown")
            
            item_types[item_type] = item_types.get(item_type, 0) + 1
            authors[author] = authors.get(author, 0) + 1
        
        return {
            "workspace_id": workspace_id,
            "total_items": len(items),
            "item_types": item_types,
            "contributors": authors,
            "last_activity": max([item.get("created_at", "") for item in items]) if items else None
        }
    
    def sync_to_cli(self, workspace_id: str, cli_memory_path: str) -> bool:
        """CLI hafızasına senkronize et"""
        items = self.get_items(workspace_id, limit=1000)
        
        sync_data = {
            "workspace_id": workspace_id,
            "synced_at": datetime.now().isoformat(),
            "items": items
        }
        
        try:
            with open(cli_memory_path, "w") as f:
                json.dump(sync_data, f, indent=2)
            return True
        except:
            return False
    
    def sync_from_cli(self, workspace_id: str, cli_memory_path: str, author_id: str) -> int:
        """CLI hafızasından senkronize et"""
        try:
            with open(cli_memory_path, "r") as f:
                sync_data = json.load(f)
            
            count = 0
            for item in sync_data.get("items", []):
                # Dummy vector (gerçek implementasyonda embedding gerekir)
                vector = [0.0] * 1536
                
                self.add_item(
                    workspace_id=workspace_id,
                    item_type=item.get("item_type", "note"),
                    content=item.get("content", ""),
                    vector=vector,
                    author_id=author_id,
                    metadata=item.get("metadata", {})
                )
                count += 1
            
            return count
        except:
            return 0


# Global instance
_workspace = None


def get_workspace() -> SharedWorkspace:
    """Global workspace instance'ı al"""
    global _workspace
    if _workspace is None:
        _workspace = SharedWorkspace()
    return _workspace
