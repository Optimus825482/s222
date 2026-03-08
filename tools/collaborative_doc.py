"""
Collaborative Document Editing Engine
Faz 10.7 — Çoklu agent'ın eşzamanlı dosya düzenleme desteği
CRDT (Conflict-Free Replicated Data Types) tabanlı senkronizasyon
"""

import os
import json
import uuid
import hashlib
import time
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from threading import Lock


class OperationType(Enum):
    INSERT = "insert"
    DELETE = "delete"
    UPDATE = "update"
    STYLE = "style"


@dataclass
class DocumentOp:
    """CRDT operation represents"""
    id: str  # unique op ID (agent_id:timestamp:counter)
    op_type: str
    position: int  # insertion/deletion position
    text: str = ""  # text for insert, ignored for delete
    length: int = 0  # length for delete
    agent_id: str = ""
    timestamp: float = field(default_factory=time.time)
    version: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class DocumentVersion:
    """Document version with metadata"""
    version_id: str
    parent_id: Optional[str]
    ops_applied: List[str]
    state_hash: str
    created_at: str
    created_by: str
    message: str = ""


@dataclass
class CollaborativeDocument:
    """Main collaborative document model"""
    doc_id: str
    title: str
    content: str  # current content
    ops: List[DocumentOp]  # all operations (business logic)
    versions: List[DocumentVersion]
    collaborators: List[str]  # agent/user IDs
    created_at: str
    updated_at: str
    language: str = "python"
    readonly: bool = False
    metadata: Dict = field(default_factory=dict)


# ── CRDT Logic ────────────────────────────────────────────────────

class CRDTDocument:
    """CRDT-based document for conflict-free synchronization"""

    def __init__(self, doc_id: str, initial_content: str = ""):
        self.doc_id = doc_id
        self.content = initial_content
        self.ops: List[DocumentOp] = []
        self.op_counter: Dict[str, int] = {}  # per-agent counter
        self.version_counter = 0
        self.lock = Lock()

    def _generate_op_id(self, agent_id: str) -> str:
        """Generate unique operation ID"""
        with self.lock:
            self.op_counter[agent_id] = self.op_counter.get(agent_id, 0) + 1
            return f"{agent_id}:{int(time.time()*1000)}:{self.op_counter[agent_id]}"

    def apply_insert(self, agent_id: str, position: int, text: str, metadata: Dict = None) -> DocumentOp:
        """Apply insert operation with CRDT semantics"""
        with self.lock:
            op_id = self._generate_op_id(agent_id)
            op = DocumentOp(
                id=op_id,
                op_type=OperationType.INSERT.value,
                position=position,
                text=text,
                agent_id=agent_id,
                timestamp=time.time(),
                version=self.version_counter,
                metadata=metadata or {}
            )
            self.ops.append(op)
            # Apply to content
            self.content = self.content[:position] + text + self.content[position:]
            self.version_counter += 1
            return op

    def apply_delete(self, agent_id: str, position: int, length: int, metadata: Dict = None) -> DocumentOp:
        """Apply delete operation with CRDT semantics"""
        with self.lock:
            op_id = self._generate_op_id(agent_id)
            op = DocumentOp(
                id=op_id,
                op_type=OperationType.DELETE.value,
                position=position,
                length=length,
                agent_id=agent_id,
                timestamp=time.time(),
                version=self.version_counter,
                metadata=metadata or {}
            )
            self.ops.append(op)
            # Apply to content
            self.content = self.content[:position] + self.content[position + length:]
            self.version_counter += 1
            return op

    def apply_move(self, agent_id: str, from_pos: int, to_pos: int, length: int) -> DocumentOp:
        """Apply move/transform operation for cursor sync"""
        with self.lock:
            op_id = self._generate_op_id(agent_id)
            text = self.content[from_pos:from_pos + length]
            op = DocumentOp(
                id=op_id,
                op_type="move",
                position=to_pos,
                text=text,
                metadata={"from_pos": from_pos, "length": length}
            )
            self.ops.append(op)
            # Apply move
            removed = self.content[:from_pos] + self.content[from_pos + length:]
            self.content = removed[:to_pos] + text + removed[to_pos:]
            return op

    def get_transformed_ops(self, local_ops: List[DocumentOp], remote_ops: List[DocumentOp]) -> List[DocumentOp]:
        """
        Transform remote operations to apply on top of local ops
        Uses operational transformation for concurrent edits
        """
        transformed = list(remote_ops)

        # Sort by timestamp for causal ordering
        all_ops = sorted(local_ops + remote_ops, key=lambda x: x.timestamp)

        # Apply simple OT: adjust positions based on previous insertions/deletions
        for i, remote_op in enumerate(transformed):
            for local_op in all_ops:
                if local_op.id == remote_op.id:
                    continue

                if local_op.op_type == OperationType.INSERT.value:
                    if local_op.position <= remote_op.position:
                        remote_op.position += len(local_op.text)
                elif local_op.op_type == OperationType.DELETE.value:
                    if local_op.position <= remote_op.position:
                        remote_op.position -= min(local_op.length, remote_op.position - local_op.position)
                    elif local_op.position + local_op.length > remote_op.position:
                        # Overlap - need more sophisticated handling
                        pass

        return transformed

    def to_snapshot(self) -> str:
        """Create a content snapshot hash"""
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]

    def get_diff(self, previous_content: str) -> List[Dict]:
        """Get minimal diff from previous content"""
        if previous_content == self.content:
            return []

        # Simple line-based diff for now
        diff = []
        prev_lines = previous_content.split('\n')
        curr_lines = self.content.split('\n')

        # Find changed lines
        min_len = min(len(prev_lines), len(curr_lines))
        for i in range(min_len):
            if prev_lines[i] != curr_lines[i]:
                diff.append({
                    "type": "line_update",
                    "line": i,
                    "old": prev_lines[i],
                    "new": curr_lines[i]
                })

        # Handle extra/missing lines
        if len(curr_lines) > len(prev_lines):
            for i in range(len(prev_lines), len(curr_lines)):
                diff.append({"type": "line_insert", "line": i, "text": curr_lines[i]})
        elif len(curr_lines) < len(prev_lines):
            for i in range(len(curr_lines), len(prev_lines)):
                diff.append({"type": "line_delete", "line": i, "text": prev_lines[i]})

        return diff


# ── Document Manager ──────────────────────────────────────────────

class CollaborativeDocManager:
    """Manages all collaborative documents with persistence"""

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.getenv("COLLAB_DOC_PATH", "./data/collab_docs")
        os.makedirs(self.storage_path, exist_ok=True)
        self.documents: Dict[str, CollaborativeDocument] = {}
        self.crdt_docs: Dict[str, CRDTDocument] = {}
        self.lock = Lock()
        self._load_all()

    def _load_all(self):
        """Load all documents from storage"""
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(self.storage_path, filename)) as f:
                        data = json.load(f)
                        doc = self._from_dict(data)
                        self.documents[doc.doc_id] = doc
                        self.crdt_docs[doc.doc_id] = CRDTDocument(doc.doc_id, doc.content)
                except Exception as e:
                    print(f"[CollabDoc] Error loading {filename}: {e}")

    def _to_dict(self, doc: CollaborativeDocument) -> Dict:
        return {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "content": doc.content,
            "ops": [vars(op) for op in doc.ops],
            "versions": [vars(v) for v in doc.versions],
            "collaborators": doc.collaborators,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "language": doc.language,
            "readonly": doc.readonly,
            "metadata": doc.metadata
        }

    def _from_dict(self, data: Dict) -> CollaborativeDocument:
        return CollaborativeDocument(
            doc_id=data["doc_id"],
            title=data["title"],
            content=data["content"],
            ops=[DocumentOp(**op) for op in data.get("ops", [])],
            versions=[DocumentVersion(**v) for v in data.get("versions", [])],
            collaborators=data.get("collaborators", []),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            language=data.get("language", "python"),
            readonly=data.get("readonly", False),
            metadata=data.get("metadata", {})
        )

    def _save_doc(self, doc: CollaborativeDocument):
        """Save document to storage"""
        filepath = os.path.join(self.storage_path, f"{doc.doc_id}.json")
        with open(filepath, 'w') as f:
            json.dump(self._to_dict(doc), f, indent=2)

    def create_document(
        self,
        title: str,
        content: str = "",
        creator_id: str = "orchestrator",
        language: str = "python"
    ) -> CollaborativeDocument:
        """Create a new collaborative document"""
        with self.lock:
            doc_id = f"doc_{uuid.uuid4().hex[:12]}"
            now = datetime.now().isoformat()

            doc = CollaborativeDocument(
                doc_id=doc_id,
                title=title,
                content=content,
                ops=[],
                versions=[],
                collaborators=[creator_id],
                created_at=now,
                updated_at=now,
                language=language
            )

            crdt = CRDTDocument(doc_id, content)
            self.documents[doc_id] = doc
            self.crdt_docs[doc_id] = crdt

            # Create initial version
            version = DocumentVersion(
                version_id=f"v_{uuid.uuid4().hex[:8]}",
                parent_id=None,
                ops_applied=[],
                state_hash=crdt.to_snapshot(),
                created_at=now,
                created_by=creator_id,
                message="Initial version"
            )
            doc.versions.append(version)

            self._save_doc(doc)
            return doc

    def get_document(self, doc_id: str) -> Optional[CollaborativeDocument]:
        """Get document by ID"""
        return self.documents.get(doc_id)

    def get_crdt_document(self, doc_id: str) -> Optional[CRDTDocument]:
        """Get CRDT document for editing"""
        return self.crdt_docs.get(doc_id)

    def update_document(
        self,
        doc_id: str,
        agent_id: str,
        op: DocumentOp
    ) -> Tuple[CollaborativeDocument, List[DocumentOp]]:
        """
        Apply an operation to a document
        Returns updated doc and any transformed ops for other agents
        """
        with self.lock:
            doc = self.documents.get(doc_id)
            if not doc:
                raise ValueError(f"Document {doc_id} not found")

            if doc.readonly:
                raise ValueError("Document is readonly")

            crdt = self.crdt_docs[doc_id]

            # Apply the operation
            if op.op_type == OperationType.INSERT.value:
                crdt.apply_insert(agent_id, op.position, op.text, op.metadata)
            elif op.op_type == OperationType.DELETE.value:
                crdt.apply_delete(agent_id, op.position, op.length, op.metadata)

            # Update document
            doc.content = crdt.content
            doc.ops.append(op)
            doc.updated_at = datetime.now().isoformat()

            # Create new version if content changed significantly
            if len(op.text) > 10 or op.op_type == OperationType.DELETE.value:
                version = DocumentVersion(
                    version_id=f"v_{uuid.uuid4().hex[:8]}",
                    parent_id=doc.versions[-1].version_id if doc.versions else None,
                    ops_applied=[op.id],
                    state_hash=crdt.to_snapshot(),
                    created_at=datetime.now().isoformat(),
                    created_by=agent_id,
                    message=f"Applied {op.op_type} by {agent_id}"
                )
                doc.versions.append(version)

            # Save and return transformed ops
            self._save_doc(doc)
            transformed = crdt.get_transformed_ops(doc.ops, [op])
            return doc, transformed

    def add_collaborator(self, doc_id: str, agent_id: str) -> bool:
        """Add a collaborator to the document"""
        with self.lock:
            doc = self.documents.get(doc_id)
            if not doc:
                return False

            if agent_id not in doc.collaborators:
                doc.collaborators.append(agent_id)
                doc.updated_at = datetime.now().isoformat()
                self._save_doc(doc)
            return True

    def remove_collaborator(self, doc_id: str, agent_id: str) -> bool:
        """Remove a collaborator from the document"""
        with self.lock:
            doc = self.documents.get(doc_id)
            if not doc:
                return False

            if agent_id in doc.collaborators:
                doc.collaborators.remove(agent_id)
                doc.updated_at = datetime.now().isoformat()
                self._save_doc(doc)
            return True

    def get_history(self, doc_id: str) -> List[DocumentVersion]:
        """Get document version history"""
        doc = self.documents.get(doc_id)
        return doc.versions if doc else []

    def revert_to_version(self, doc_id: str, version_id: str, agent_id: str) -> Optional[CollaborativeDocument]:
        """Revert document to a previous version"""
        with self.lock:
            doc = self.documents.get(doc_id)
            if not doc:
                return None

            version = next((v for v in doc.versions if v.version_id == version_id), None)
            if not version:
                return None

            # For now, reload from snapshot - in production, replay ops
            # This is a simplified implementation
            doc.updated_at = datetime.now().isoformat()

            new_version = DocumentVersion(
                version_id=f"v_{uuid.uuid4().hex[:8]}",
                parent_id=version.version_id,
                ops_applied=[],
                state_hash=version.state_hash,
                created_at=datetime.now().isoformat(),
                created_by=agent_id,
                message=f"Reverted to {version.version_id}"
            )
            doc.versions.append(new_version)
            self._save_doc(doc)
            return doc

    def list_documents(self, agent_id: str = None) -> List[CollaborativeDocument]:
        """List accessible documents"""
        with self.lock:
            if agent_id:
                return [d for d in self.documents.values()
                       if agent_id in d.collaborators or not d.collaborators]
            return list(self.documents.values())

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document"""
        with self.lock:
            if doc_id in self.documents:
                del self.documents[doc_id]
            if doc_id in self.crdt_docs:
                del self.crdt_docs[doc_id]

            filepath = os.path.join(self.storage_path, f"{doc_id}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
            return True


# ── Global Instance ───────────────────────────────────────────────

_doc_manager: Optional[CollaborativeDocManager] = None


def get_doc_manager() -> CollaborativeDocManager:
    """Get global document manager instance"""
    global _doc_manager
    if _doc_manager is None:
        _doc_manager = CollaborativeDocManager()
    return _doc_manager


# ── Syntax Highlighting Helpers ───────────────────────────────────

def tokenize_code(code: str, language: str) -> List[Dict]:
    """Simple syntax tokenizer for common languages"""
    tokens = []
    patterns = {
        "python": {
            "keyword": r'\b(def|class|if|elif|else|return|yield|import|from|as|with|try|except|finally|raise|for|while|in|pass|break|continue)\b',
            "string": r'["\'][^\'"]*["\']',
            "comment": r'#[^\n]*',
            "number": r'\b\d+(\.\d+)?\b',
            "function": r'\b(\w+)(?=\s*\()',
            "decorator": r'^\s*@(\w+)',
        },
        "javascript": {
            "keyword": r'\b(function|var|let|const|if|else|return|for|while|do|switch|case|break|continue|try|catch|finally|new|this|class|extends|import|from|export|default|async|await|yield)\b',
            "string": r'["\'`][^\"`\']*["\'`]',
            "comment": r'//.*|/\\*[^*]*\\*/',
            "number": r'\b\d+(\.\d+)?(e[+-]?\d+)?\b',
            "function": r'\b(\w+)(?=\s*\()',
            "promise": r'\b(then|catch|finally)\b',
        }
    }

    regexes = patterns.get(language, patterns.get("python", {}))

    # Simple tokenization
    lines = code.split('\n')
    for line_num, line in enumerate(lines):
        line_tokens = []
        pos = 0

        # Check for comment first
        if '#' in line or '//' in line:
            comment_start = min(line.find('#'), line.find('//')) if '#' in line and '//' in line else max(line.find('#'), line.find('//'))
            if comment_start >= 0:
                line_tokens.append({"type": "comment", "text": line[comment_start:], "start": comment_start})
                line = line[:comment_start]

        # Simple word tokenization
        words = re.split(r'(\s+|[()\[\]{}.,;:])', line)
        for word in words:
            if not word:
                continue
            pos = line.find(word, pos)
            if re.match(regexes.get("keyword", ""), word):
                line_tokens.append({"type": "keyword", "text": word, "start": pos})
            elif re.match(regexes.get("number", ""), word):
                line_tokens.append({"type": "number", "text": word, "start": pos})
            elif re.match(regexes.get("function", ""), word):
                line_tokens.append({"type": "function", "text": word, "start": pos})
            elif word.startswith(('"', "'", '`')):
                line_tokens.append({"type": "string", "text": word, "start": pos})
            elif not word.isspace():
                line_tokens.append({"type": "text", "text": word, "start": pos})

        tokens.append({"line": line_num, "tokens": line_tokens})

    return tokens


def get_syntax_style(token_type: str) -> str:
    """Get CSS class for token type"""
    styles = {
        "keyword": "text-purple-400",
        "string": "text-green-400",
        "comment": "text-slate-500 italic",
        "number": "text-amber-400",
        "function": "text-blue-400",
        "decorator": "text-pink-400",
        "prompt": "text-yellow-400",
    }
    return styles.get(token_type, "text-slate-300")


# ──AGENT Collaboration Protocol ───────────────────────────────────

class AgentCollabProtocol:
    """
    Protocol for agent-to-agent document collaboration
    Defines message types for real-time sync
    """

    @staticmethod
    def create_invite(doc_id: str, from_agent: str, to_agents: List[str]) -> Dict:
        """Create collaboration invitation"""
        return {
            "type": "collab_invite",
            "doc_id": doc_id,
            "from_agent": from_agent,
            "to_agents": to_agents,
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def create_op_sync(op: DocumentOp) -> Dict:
        """Create operation sync message"""
        return {
            "type": "op_sync",
            "op": {
                "id": op.id,
                "op_type": op.op_type,
                "position": op.position,
                "text": op.text,
                "length": op.length,
                "agent_id": op.agent_id,
                "timestamp": op.timestamp,
                "version": op.version,
                "metadata": op.metadata
            },
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def create_cursor_sync(agent_id: str, position: int, selection: Dict = None) -> Dict:
        """Create cursor position sync"""
        return {
            "type": "cursor_sync",
            "agent_id": agent_id,
            "position": position,
            "selection": selection or {"start": position, "end": position},
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def create_version_sync(doc_id: str, version: DocumentVersion) -> Dict:
        """Create version sync message"""
        return {
            "type": "version_sync",
            "doc_id": doc_id,
            "version": {
                "version_id": version.version_id,
                "parent_id": version.parent_id,
                "ops_applied": version.ops_applied,
                "state_hash": version.state_hash,
                "created_at": version.created_at,
                "created_by": version.created_by,
                "message": version.message
            },
            "timestamp": datetime.now().isoformat()
        }


# ── Usage Example ─────────────────────────────────────────────────

if __name__ == "__main__":
    # Example usage
    manager = get_doc_manager()

    # Create a document
    doc = manager.create_document(
        title="Test Code",
        content="def hello():\n    print('Hello')\n",
        creator_id="orchestrator",
        language="python"
    )

    print(f"Created doc: {doc.doc_id}")
    print(f"Content: {doc.content}")

    # Apply an insert
    crdt = manager.get_crdt_document(doc.doc_id)
    op = crdt.apply_insert("speed", 7, "world", {"cursor": 7})
    print(f"After insert: {doc.content}")

    # Get syntax tokens
    tokens = tokenize_code(doc.content, "python")
    print(f"Tokens: {tokens}")
