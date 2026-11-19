"use client";

import React, { useState, useRef, useEffect } from "react";
import { useApp } from "@/context/AppContext";
import { Send, Mic, Radio, Square, Database } from "lucide-react";

interface ComposerProps {
  onSendMessage: (content: string) => Promise<void>;
  disabled?: boolean;
  generating?: boolean;
  onStop?: () => void;
}

export function Composer({ onSendMessage, disabled, generating, onStop }: ComposerProps) {
  const { language, activeKbId, knowledgeBases, setVoiceModalOpen } = useApp();
  const [content, setContent] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const activeKb = knowledgeBases.find((k) => k.id === activeKbId);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [content]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!content.trim() || disabled || generating) return;
    const textToSend = content.trim();
    setContent("");
    onSendMessage(textToSend);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 pb-4">
      {/* Active Context Indicator */}
      <div className="flex items-center justify-between text-[11px] text-slate-500 mb-2 px-1">
        <div className="flex items-center gap-1.5">
          <Database size={12} className={activeKb ? "text-indigo-500" : "text-slate-400"} />
          <span>
            {activeKb
              ? `${language === "ar" ? "قاعدة المعرفة:" : "Knowledge Base:"} ${activeKb.name}`
              : (language === "ar" ? "الوضع العام (بدون مستندات)" : "General Assistant Mode")}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-emerald-500 font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] uppercase tracking-wider">{language === "ar" ? "متصل" : "Live"}</span>
        </div>
      </div>

      {/* Input Container */}
      <div className="relative rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm focus-within:border-indigo-500/80 focus-within:ring-2 focus-within:ring-indigo-500/10 transition-all">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || generating}
          rows={1}
          placeholder={
            language === "ar"
              ? "اسأل أي سؤال حول مستنداتك، أو تحدث صوتياً، أو قل مرحباً..."
              : "Ask anything about your documents, talk via voice, or say hello..."
          }
          className="w-full py-3.5 ps-4 pe-24 text-sm bg-transparent text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none resize-none leading-relaxed"
        />

        {/* Action Controls */}
        <div className="absolute bottom-2 end-2 flex items-center gap-1.5">
          {/* Voice Mode Button */}
          <button
            type="button"
            onClick={() => setVoiceModalOpen(true)}
            className="p-2 text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition"
            title={language === "ar" ? "فتح المحادثة الصوتية الحية" : "Start Live Voice Chat"}
          >
            <Mic size={17} />
          </button>

          {/* Send or Stop Button */}
          {generating ? (
            <button
              type="button"
              onClick={onStop}
              className="p-2 bg-red-600 hover:bg-red-500 text-white rounded-xl shadow-xs transition"
              title={language === "ar" ? "إيقاف التوليد" : "Stop generation"}
            >
              <Square size={16} fill="currentColor" />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => handleSubmit()}
              disabled={!content.trim() || disabled}
              className="p-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 disabled:hover:bg-indigo-600 text-white rounded-xl shadow-xs transition active:scale-95"
              title={language === "ar" ? "إرسال" : "Send message"}
            >
              <Send size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
