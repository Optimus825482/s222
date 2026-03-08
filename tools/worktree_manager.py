"""
Real-time Collaboration with Git Worktree
Faz 10.7 — Worktree bazlı paralel geliştirme
"""

import os
import subprocess
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Worktree:
    path: str
    branch: str
    agent_id: str
    created_at: datetime
    is_active: bool


class WorktreeManager:
    """Git worktree bazlı paralel geliştirme yöneticisi"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.worktrees: Dict[str, Worktree] = {}
    
    def create_worktree(self, agent_id: str, branch_name: str, base_branch: str = "main") -> Optional[Worktree]:
        """Agent için yeni worktree oluştur"""
        worktree_path = self.repo_path / ".worktrees" / agent_id
        
        try:
            # Base branch'ten yeni branch oluştur
            subprocess.run(
                ["git", "checkout", "-b", branch_name, base_branch],
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
            
            # Worktree oluştur
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), branch_name],
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
            
            worktree = Worktree(
                path=str(worktree_path),
                branch=branch_name,
                agent_id=agent_id,
                created_at=datetime.now(),
                is_active=True
            )
            
            self.worktrees[agent_id] = worktree
            return worktree
            
        except subprocess.CalledProcessError:
            return None
    
    def remove_worktree(self, agent_id: str) -> bool:
        """Worktree'yi kaldır"""
        if agent_id not in self.worktrees:
            return False
        
        worktree = self.worktrees[agent_id]
        
        try:
            subprocess.run(
                ["git", "worktree", "remove", worktree.path, "--force"],
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
            
            del self.worktrees[agent_id]
            return True
            
        except subprocess.CalledProcessError:
            return False
    
    def commit_changes(self, agent_id: str, message: str) -> bool:
        """Worktree'deki değişiklikleri commit et"""
        if agent_id not in self.worktrees:
            return False
        
        worktree = self.worktrees[agent_id]
        
        try:
            subprocess.run(
                ["git", "add", "."],
                cwd=worktree.path,
                check=True
            )
            
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=worktree.path,
                check=True
            )
            
            return True
            
        except subprocess.CalledProcessError:
            return False
    
    def merge_to_main(self, agent_id: str) -> bool:
        """Worktree branch'ini main'e merge et"""
        if agent_id not in self.worktrees:
            return False
        
        worktree = self.worktrees[agent_id]
        
        try:
            # Main'e geç
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=self.repo_path,
                check=True
            )
            
            # Merge
            subprocess.run(
                ["git", "merge", worktree.branch, "--no-ff"],
                cwd=self.repo_path,
                check=True
            )
            
            return True
            
        except subprocess.CalledProcessError:
            return False
    
    def get_diff(self, agent_id: str) -> Optional[str]:
        """Worktree'deki değişiklikleri göster"""
        if agent_id not in self.worktrees:
            return None
        
        worktree = self.worktrees[agent_id]
        
        try:
            result = subprocess.run(
                ["git", "diff", "main", worktree.branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            return result.stdout
            
        except subprocess.CalledProcessError:
            return None
    
    def list_worktrees(self) -> List[Worktree]:
        """Tüm worktree'leri listele"""
        return list(self.worktrees.values())
    
    def sync_with_main(self, agent_id: str) -> bool:
        """Main branch'teki değişiklikleri worktree'ye çek"""
        if agent_id not in self.worktrees:
            return False
        
        worktree = self.worktrees[agent_id]
        
        try:
            # Main'i pull et
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=self.repo_path,
                check=True
            )
            
            subprocess.run(
                ["git", "pull"],
                cwd=self.repo_path,
                check=True
            )
            
            # Worktree branch'ine rebase
            subprocess.run(
                ["git", "checkout", worktree.branch],
                cwd=worktree.path,
                check=True
            )
            
            subprocess.run(
                ["git", "rebase", "main"],
                cwd=worktree.path,
                check=True
            )
            
            return True
            
        except subprocess.CalledProcessError:
            return False


# Global instance
_manager: Optional[WorktreeManager] = None


def get_worktree_manager(repo_path: str = ".") -> WorktreeManager:
    """Global worktree manager instance'ı al"""
    global _manager
    if _manager is None:
        _manager = WorktreeManager(repo_path)
    return _manager
