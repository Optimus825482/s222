"use client";

import { useState, useEffect, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileText, Users, Lock, Trash2 } from "lucide-react";
import { collabDocApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";

// Extract base WS host — strip any path like /ws/chat to avoid double /ws/
const _rawWs =
  process.env.NEXT_PUBLIC_WS_URL ||
  (typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}:8001`
    : "ws://localhost:8001");
const WS_BASE = _rawWs.replace(/\/ws\/.*$/, "");

interface DocumentState {
  doc_id: string;
  title: string;
  content: string;
  version: number;
  active_users: string[];
  locks: Array<{ position: number; user_id: string; expires_at: string }>;
  collaborators: string[];
  language: string;
}

export function CollaborativeEditorPanel() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<DocumentState[]>([]);
  const [activeDoc, setActiveDoc] = useState<DocumentState | null>(null);
  const [content, setContent] = useState("");
  const [cursorPos, setCursorPos] = useState(0);
  const [, setWs] = useState<WebSocket | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetchDocuments();
  }, []);

  useEffect(() => {
    if (!activeDoc?.doc_id) return;
    const userId = user?.user_id ?? "anonymous";
    const qs = new URLSearchParams({ doc_id: activeDoc.doc_id, user_id: userId });
    const socket = new WebSocket(`${WS_BASE}/ws/collab-docs?${qs}`);
    socket.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        if (event.type === "edit_applied") {
          setActiveDoc((prev) =>
            prev
              ? { ...prev, content: event.content, version: event.new_version ?? prev.version }
              : null,
          );
          setContent(event.content ?? "");
        } else if (event.type === "user_joined" || event.type === "user_left") {
          setActiveDoc((prev) =>
            prev ? { ...prev, active_users: event.active_users ?? [] } : null,
          );
        }
      } catch {
        /* ignore parse errors */
      }
    };
    setWs(socket);
    return () => socket.close();
  }, [activeDoc?.doc_id, user?.user_id]);

  const fetchDocuments = async () => {
    try {
      const data = await collabDocApi.listDocs();
      setDocuments(data.documents || []);
    } catch {
      /* API not available yet */
    }
  };

  const createDocument = async () => {
    try {
      await collabDocApi.createDoc(`doc_${Date.now()}`, "", "markdown");
      fetchDocuments();
    } catch {
      /* silent */
    }
  };

  const openDocument = async (docId: string) => {
    try {
      const doc = await collabDocApi.getDoc(docId);
      setActiveDoc({
        ...doc,
        active_users: doc.active_users ?? doc.collaborators ?? [],
        locks: doc.locks ?? [],
      });
      setContent(doc.content || "");
    } catch {
      /* silent */
    }
  };

  const applyEdit = async (
    editType: string,
    position: number,
    text: string,
  ) => {
    if (!activeDoc) return;
    try {
      await collabDocApi.updateDoc(activeDoc.doc_id, editType, position, text);
    } catch {
      /* silent */
    }
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    const pos = e.target.selectionStart || 0;
    if (newContent.length > content.length) {
      const inserted = newContent.slice(
        pos - (newContent.length - content.length),
        pos,
      );
      applyEdit("insert", pos - inserted.length, inserted);
    } else if (newContent.length < content.length) {
      applyEdit(
        "delete",
        pos,
        content.slice(pos, pos + (content.length - newContent.length)),
      );
    }
    setContent(newContent);
    setCursorPos(pos);
  };

  const deleteDocument = async (docId: string) => {
    try {
      await collabDocApi.deleteDoc(docId);
      fetchDocuments();
      if (activeDoc?.doc_id === docId) setActiveDoc(null);
    } catch {
      /* silent */
    }
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5" />
          <h2 className="text-lg font-semibold">Collaborative Editor</h2>
        </div>
        <Button onClick={createDocument} size="sm">
          <FileText className="w-4 h-4 mr-2" />
          New Document
        </Button>
      </div>

      <div className="grid grid-cols-4 gap-4 flex-1">
        <Card className="col-span-1 p-4">
          <h3 className="font-semibold mb-3">Documents</h3>
          <ScrollArea className="h-[calc(100%-2rem)]">
            <div className="space-y-2">
              {documents.map((doc) => (
                <div
                  key={doc.doc_id}
                  className={`p-3 rounded border cursor-pointer hover:bg-accent ${
                    activeDoc?.doc_id === doc.doc_id ? "bg-accent" : ""
                  }`}
                  onClick={() => openDocument(doc.doc_id)}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium truncate">
                      {doc.title || doc.doc_id}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e: React.MouseEvent) => {
                        e.stopPropagation();
                        deleteDocument(doc.doc_id);
                      }}
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Users className="w-3 h-3" />
                    <span>{(doc.collaborators || []).length} users</span>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </Card>

        <Card className="col-span-3 p-4 flex flex-col">
          {activeDoc ? (
            <>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <h3 className="font-semibold">
                    {activeDoc.title || activeDoc.doc_id}
                  </h3>
                  <Badge>v{activeDoc.version}</Badge>
                </div>
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  <span className="text-sm">
                    {activeDoc.active_users.length} active
                  </span>
                  {activeDoc.active_users.map((user) => (
                    <Badge key={user} variant="secondary" className="text-xs">
                      {user}
                    </Badge>
                  ))}
                </div>
              </div>
              <textarea
                ref={textareaRef}
                value={content}
                onChange={handleTextChange}
                className="flex-1 w-full p-4 border rounded font-mono text-sm resize-none focus:outline-none focus:ring-2"
                placeholder="Start typing..."
              />
              <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground">
                <span>Position: {cursorPos}</span>
                <span>{content.length} characters</span>
                {activeDoc.locks.length > 0 && (
                  <div className="flex items-center gap-1">
                    <Lock className="w-3 h-3" />
                    <span>{activeDoc.locks.length} locked regions</span>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">
              <div className="text-center">
                <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Select a document to start editing</p>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
