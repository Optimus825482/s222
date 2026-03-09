"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown, MessageSquare } from "lucide-react";

interface FeedbackButtonsProps {
  threadId: string;
  agentRole: string;
  messageId?: string;
  taskInput?: string;
  taskOutput?: string;
  onFeedbackSubmitted?: () => void;
}

export function FeedbackButtons({
  threadId,
  agentRole,
  messageId,
  taskInput,
  taskOutput,
  onFeedbackSubmitted,
}: FeedbackButtonsProps) {
  const [rating, setRating] = useState<"positive" | "negative" | "neutral" | null>(null);
  const [showFeedbackInput, setShowFeedbackInput] = useState(false);
  const [feedbackText, setFeedbackText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const submitFeedback = async (ratingValue: "positive" | "negative" | "neutral") => {
    setIsSubmitting(true);
    try {
      const res = await fetch("/api/feedback/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          thread_id: threadId,
          agent_role: agentRole,
          rating: ratingValue,
          message_id: messageId,
          feedback_text: feedbackText || undefined,
          task_input: taskInput?.slice(0, 500),
          task_output: taskOutput?.slice(0, 2000),
        }),
      });
      
      const data = await res.json();
      
      if (data.success) {
        setRating(ratingValue);
        setSubmitted(true);
        setShowFeedbackInput(false);
        onFeedbackSubmitted?.();
      }
    } catch (err) {
      console.error("Failed to submit feedback:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleThumbsUp = () => {
    if (!submitted) {
      submitFeedback("positive");
    }
  };

  const handleThumbsDown = () => {
    if (!submitted) {
      setShowFeedbackInput(true);
    }
  };

  const submitNegativeFeedback = () => {
    submitFeedback("negative");
  };

  if (submitted && rating) {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-500 mt-2">
        {rating === "positive" ? (
          <span className="flex items-center gap-1 text-green-500">
            <ThumbsUp className="w-3 h-3" />
            Teşekkürler! Geri bildiriminiz kaydedildi.
          </span>
        ) : (
          <span className="flex items-center gap-1 text-amber-500">
            <ThumbsDown className="w-3 h-3" />
            Geri bildiriminiz için teşekkürler. Geliştirmeler yapacağız.
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1 mt-2">
      <button
        onClick={handleThumbsUp}
        disabled={isSubmitting}
        className={`p-1.5 rounded transition-colors ${
          rating === "positive"
            ? "bg-green-500/20 text-green-500"
            : "text-slate-500 hover:text-green-500 hover:bg-green-500/10"
        }`}
        title="İyi yanıt"
      >
        <ThumbsUp className="w-4 h-4" />
      </button>
      
      <button
        onClick={handleThumbsDown}
        disabled={isSubmitting}
        className={`p-1.5 rounded transition-colors ${
          rating === "negative"
            ? "bg-amber-500/20 text-amber-500"
            : "text-slate-500 hover:text-amber-500 hover:bg-amber-500/10"
        }`}
        title="Geliştirilebilir"
      >
        <ThumbsDown className="w-4 h-4" />
      </button>
      
      <button
        onClick={() => setShowFeedbackInput(!showFeedbackInput)}
        className={`p-1.5 rounded transition-colors text-slate-500 hover:text-blue-500 hover:bg-blue-500/10`}
        title="Detaylı geri bildirim"
      >
        <MessageSquare className="w-4 h-4" />
      </button>
      
      {showFeedbackInput && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-4 max-w-md w-full mx-4 border border-slate-700">
            <h3 className="text-sm font-semibold text-white mb-3">
              Geri Bildirim
            </h3>
            <p className="text-xs text-slate-400 mb-3">
              Bu yanıtı nasıl geliştirebiliriz?
            </p>
            <textarea
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              placeholder="Yanıt hakkında düşünceleriniz..."
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              rows={3}
            />
            <div className="flex justify-end gap-2 mt-3">
              <button
                onClick={() => setShowFeedbackInput(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
              >
                İptal
              </button>
              <button
                onClick={submitNegativeFeedback}
                disabled={isSubmitting}
                className="px-3 py-1.5 text-xs bg-amber-500 text-white rounded hover:bg-amber-600 disabled:opacity-50"
              >
                {isSubmitting ? "Gönderiliyor..." : "Gönder"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}