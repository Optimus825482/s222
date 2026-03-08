"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { fetcher } from "@/lib/api";
import {
  GitBranch,
  GitMerge,
  GitPullRequest,
  Trash2,
  RefreshCw,
  FileCode,
} from "lucide-react";

interface Worktree {
  path: string;
  branch: string;
  agent_id: string;
  created_at: string;
  is_active: boolean;
}

export function WorktreePanel() {
  const [worktrees, setWorktrees] = useState<Worktree[]>([]);
  const [agentId, setAgentId] = useState("");
  const [branchName, setBranchName] = useState("");
  const [selectedWorktree, setSelectedWorktree] = useState<string | null>(null);
  const [diff, setDiff] = useState("");

  useEffect(() => {
    fetchWorktrees();
  }, []);

  const fetchWorktrees = async () => {
    try {
      const data = await fetcher<{ worktrees?: Worktree[] }>("/api/worktrees");
      setWorktrees(data.worktrees ?? []);
    } catch {
      // API not available yet
    }
  };

  const createWorktree = async () => {
    if (!agentId || !branchName) return;

    await fetcher("/api/worktrees", {
      method: "POST",
      body: JSON.stringify({
        agent_id: agentId,
        branch_name: branchName,
        base_branch: "main",
      }),
    });

    setAgentId("");
    setBranchName("");
    fetchWorktrees();
  };

  const removeWorktree = async (agentId: string) => {
    await fetcher(`/api/worktrees/${agentId}`, {
      method: "DELETE",
    });
    fetchWorktrees();
    if (selectedWorktree === agentId) {
      setSelectedWorktree(null);
      setDiff("");
    }
  };

  const commitChanges = async (agentId: string) => {
    const message = prompt("Commit message:");
    if (!message) return;

    await fetcher(`/api/worktrees/${agentId}/commit`, {
      method: "POST",
      body: JSON.stringify({ message }),
    });
  };

  const mergeWorktree = async (agentId: string) => {
    if (!confirm("Merge to main?")) return;

    await fetcher(`/api/worktrees/${agentId}/merge`, {
      method: "POST",
    });

    fetchWorktrees();
  };

  const syncWorktree = async (agentId: string) => {
    await fetcher(`/api/worktrees/${agentId}/sync`, {
      method: "POST",
    });
  };

  const viewDiff = async (agentId: string) => {
    const data = await fetcher<{ diff: string }>(
      `/api/worktrees/${agentId}/diff`,
    );
    setDiff(data.diff);
    setSelectedWorktree(agentId);
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitBranch className="w-5 h-5" />
          <h2 className="text-lg font-semibold">Worktree Collaboration</h2>
        </div>
        <Button onClick={fetchWorktrees} size="sm" variant="outline">
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      <Card className="p-4">
        <h3 className="font-semibold mb-3">Create Worktree</h3>
        <div className="flex gap-2">
          <Input
            placeholder="Agent ID"
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
          />
          <Input
            placeholder="Branch name"
            value={branchName}
            onChange={(e) => setBranchName(e.target.value)}
          />
          <Button onClick={createWorktree}>Create</Button>
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-4 flex-1">
        <Card className="p-4">
          <h3 className="font-semibold mb-3">Active Worktrees</h3>
          <ScrollArea className="h-[calc(100%-2rem)]">
            <div className="space-y-2">
              {worktrees.map((wt) => (
                <div
                  key={wt.agent_id}
                  className={`p-3 rounded border ${
                    selectedWorktree === wt.agent_id ? "bg-accent" : ""
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <GitBranch className="w-4 h-4" />
                      <span className="font-medium">{wt.agent_id}</span>
                    </div>
                    <Badge variant={wt.is_active ? "default" : "secondary"}>
                      {wt.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </div>

                  <div className="text-sm text-muted-foreground mb-3">
                    <div>Branch: {wt.branch}</div>
                    <div>Path: {wt.path}</div>
                  </div>

                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => viewDiff(wt.agent_id)}
                    >
                      <FileCode className="w-3 h-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => commitChanges(wt.agent_id)}
                    >
                      <GitPullRequest className="w-3 h-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => syncWorktree(wt.agent_id)}
                    >
                      <RefreshCw className="w-3 h-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => mergeWorktree(wt.agent_id)}
                    >
                      <GitMerge className="w-3 h-3" />
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => removeWorktree(wt.agent_id)}
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </Card>

        <Card className="p-4">
          <h3 className="font-semibold mb-3">Diff Viewer</h3>
          {selectedWorktree ? (
            <ScrollArea className="h-[calc(100%-2rem)]">
              <pre className="text-xs font-mono whitespace-pre-wrap">
                {diff || "No changes"}
              </pre>
            </ScrollArea>
          ) : (
            <div className="flex items-center justify-center h-[calc(100%-2rem)] text-muted-foreground">
              Select a worktree to view diff
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
