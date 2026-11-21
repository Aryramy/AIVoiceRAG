"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Message, Citation } from "@/types";
import { useApp } from "@/context/AppContext";
import { synthesizeSpeech } from "@/lib/api";
import { Copy, Check, Volume2, Sparkles, User, FileText, Loader2, AlertTriangle } from "lucide-react";

interface MessageItemProps {
  message: Message;
}

export function MessageItem({ message }: MessageItemProps) {
  const { language, setSelectedCitation, setContextualPanelOpen } = useApp();
  const [copied, setCopied] = useState(false);
  const [playingAudio, setPlayingAudio] = useState(false);
  const [audioError, setAudioError] = useState<string | null>(null);

  const isUser = message.role === "user";

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePlayAudio = async () => {
    if (playingAudio) return;
    setPlayingAudio(true);
    setAudioError(null);
    try {
      const audioBlob = await synthesizeSpeech(
        message.content,
        message.language || (language === "ar" ? "ar" : "en")
      );
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.onended = () => {
        setPlayingAudio(false);
        URL.revokeObjectURL(audioUrl);
      };
      audio.onerror = () => {
        setPlayingAudio(false);
        setAudioError("Audio playback error");
      };
      await audio.play().catch((playErr) => {
        console.warn("Audio playback was prevented by browser:", playErr);
        setAudioError("Playback prevented");
        setPlayingAudio(false);
      });
    } catch (err: any) {
      setAudioError("Synthesis failed");
      setPlayingAudio(false);
    }
  };

  const handleCitationClick = (citation: Citation) => {
    setSelectedCitation(citation);
    setContextualPanelOpen(true);
  };

  return (
    <div className={`py-4 px-4 flex gap-3.5 transition ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar Icon */}
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-sm font-semibold shadow-sm ${isUser
            ? "bg-slate-700 text-white"
            : "bg-gradient-to-tr from-indigo-600 to-indigo-400 text-white shadow-indigo-500/20"
          }`}
      >
        {isUser ? <User size={15} /> : <Sparkles size={15} />}
      </div>

      {/* Message Content & Metadata */}
      <div className={`max-w-[85%] md:max-w-[75%] space-y-2 ${isUser ? "items-end" : "items-start"}`}>
        {/* Content Box */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${isUser
              ? "bg-indigo-600 text-white rounded-se-none"
              : "bg-slate-100 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 text-slate-800 dark:text-slate-200 rounded-ss-none"
            }`}
        >
          {isUser ? (
            <div className="whitespace-pre-wrap" dir="auto">{message.content}</div>
          ) : (
            <div
              dir="auto"
              className="prose dark:prose-invert max-w-none text-sm break-words leading-relaxed text-slate-800 dark:text-slate-200"
            >
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => <p className="mb-2.5 last:mb-0 leading-relaxed">{children}</p>,
                  strong: ({ children }) => <strong className="font-semibold text-slate-900 dark:text-slate-100">{children}</strong>,
                  ul: ({ children }) => <ul className="list-disc list-inside mb-2.5 space-y-1">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal list-inside mb-2.5 space-y-1">{children}</ol>,
                  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                  code: ({ className, children, ...props }) => {
                    const isInline = !className && typeof children === "string" && !children.includes("\n");
                    if (isInline) {
                      return (
                        <code className="px-1.5 py-0.5 rounded-md text-xs font-mono bg-slate-200 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400" {...props}>
                          {children}
                        </code>
                      );
                    }
                    return (
                      <div className="my-2 rounded-xl overflow-x-auto bg-slate-800 text-slate-100 p-3 text-xs font-mono" dir="ltr">
                        <code className={className} {...props}>
                          {children}
                        </code>
                      </div>
                    );
                  },
                  pre: ({ children }) => <pre className="my-2 overflow-x-auto bg-transparent p-0 m-0">{children}</pre>,
                  blockquote: ({ children }) => (
                    <blockquote className="border-s-4 border-indigo-400 ps-3 my-2 text-slate-600 dark:text-slate-400 italic">
                      {children}
                    </blockquote>
                  ),
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-3">
                      <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800 text-xs text-start border border-slate-200 dark:border-slate-800 rounded-lg">
                        {children}
                      </table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className="px-3 py-2 bg-slate-200/50 dark:bg-slate-800/50 font-semibold text-start">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="px-3 py-1.5 border-t border-slate-200 dark:border-slate-800 text-start">
                      {children}
                    </td>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {/* Fallback Warning Badge */}
          {!isUser && message.is_fallback && (
            <div className="mt-2.5 flex items-center gap-1.5 px-2.5 py-1 text-xs bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400 rounded-lg">
              <AlertTriangle size={13} className="shrink-0" />
              <span>
                {language === "ar"
                  ? `تنبيه: تم التحويل إلى المزود الاحتياطي (${message.fallback_info || "Circuit Breaker Fallback"})`
                  : `Notice: Fallback Provider Invoked (${message.fallback_info || "Circuit Breaker Fallback"})`}
              </span>
            </div>
          )}

          {/* Citations list for assistant message */}
          {!isUser && message.citations && message.citations.length > 0 && (
            <div className="mt-3 pt-2.5 border-t border-slate-200 dark:border-slate-800/80">
              <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1.5 flex items-center gap-1">
                <FileText size={12} />
                <span>{language === "ar" ? "المصادر المرجعية الموثقة:" : "Verified Source Citations:"}</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {message.citations.map((c, i) => (
                  <button
                    key={c.id || i}
                    onClick={() => handleCitationClick(c)}
                    className="flex items-center gap-1 px-2.5 py-1 text-xs bg-white dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-slate-750 border border-slate-300 dark:border-slate-700 hover:border-indigo-400 rounded-lg text-slate-700 dark:text-slate-300 transition shadow-xs"
                  >
                    <span className="font-semibold text-indigo-600 dark:text-indigo-400">[{c.citation_index || i + 1}]</span>
                    <span className="truncate max-w-[140px]">{c.document_title || "Document"}</span>
                    {c.page_number && <span className="text-[10px] text-slate-400">p.{c.page_number}</span>}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Action Controls & Telemetry Footnote */}
        {!isUser && (
          <div className="flex items-center gap-3 text-xs text-slate-400 px-1 select-none">
            {/* Copy button */}
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 hover:text-slate-600 dark:hover:text-slate-300 transition"
              title={language === "ar" ? "نسخ الإجابة" : "Copy answer"}
            >
              {copied ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
              <span>{copied ? (language === "ar" ? "تم النسخ" : "Copied") : (language === "ar" ? "نسخ" : "Copy")}</span>
            </button>

            {/* Read out loud via Neural TTS */}
            <button
              onClick={handlePlayAudio}
              disabled={playingAudio}
              className="flex items-center gap-1 hover:text-indigo-500 transition"
              title={language === "ar" ? "استماع صوتي للإجابة" : "Listen to answer"}
            >
              {playingAudio ? <Loader2 size={13} className="animate-spin text-indigo-500" /> : <Volume2 size={13} />}
              <span>
                {playingAudio
                  ? (language === "ar" ? "جاري القراءة..." : "Speaking...")
                  : (language === "ar" ? "استماع" : "Listen")}
              </span>
            </button>

            {/* Model & Cost Telemetry */}
            {(message.model || message.cost_usd !== undefined) && (
              <span className="text-[11px] text-slate-500 dark:text-slate-400 font-mono ms-auto flex items-center gap-2">
                {message.model && <span>{message.model}</span>}
                {message.latency_ms !== undefined && <span>{message.latency_ms}ms</span>}
                {message.cost_usd !== undefined && (
                  <span className="text-emerald-600 dark:text-emerald-400">
                    ${message.cost_usd.toFixed(5)}
                  </span>
                )}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

