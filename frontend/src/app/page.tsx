"use client";

import React, { useState, useEffect, useRef } from "react";
import { useApp } from "@/context/AppContext";
import { Sidebar } from "@/components/layout/Sidebar";
import { MessageItem } from "@/components/chat/MessageItem";
import { Composer } from "@/components/chat/Composer";
import { ContextualPanel } from "@/components/contextual/ContextualPanel";
import { VoiceWaveModal } from "@/components/voice/VoiceWaveModal";
import { fetchConversationDetails, sendMessage, streamMessage, createConversation } from "@/lib/api";
import { Message } from "@/types";
import {
  Radio,
  FileText,
  Sparkles,
  PanelRight,
  Mic,
  Database,
  ArrowRight,
  ArrowLeft,
  ChevronRight,
  ChevronLeft,
  Loader2
} from "lucide-react";

export default function ChatPage() {
  const {
    activeConversationId,
    setActiveConversationId,
    activeKbId,
    knowledgeBases,
    language,
    direction,
    contextualPanelOpen,
    setContextualPanelOpen,
    setVoiceModalOpen,
    refreshConversations
  } = useApp();

  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeKb = knowledgeBases.find((k) => k.id === activeKbId);

  // Load active conversation messages
  const loadMessages = async () => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }
    setLoading(true);
    try {
      const data = await fetchConversationDetails(activeConversationId);
      setMessages(data.messages || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMessages();
  }, [activeConversationId]);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, generating]);

  // Send Message Handler
  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return;

    let targetConvId = activeConversationId;
    if (!targetConvId) {
      try {
        const titleSnippet = content.trim().slice(0, 32);
        const title = titleSnippet || (language === "ar" ? "محادثة جديدة" : "New Conversation");
        const newConv = await createConversation(title, language, activeKbId || undefined);
        targetConvId = newConv.id;
        setActiveConversationId(newConv.id);
        await refreshConversations();
      } catch (err: any) {
        console.error("Failed to auto-create conversation:", err);
        return;
      }
    }

    // Optimistically append user message
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: targetConvId,
      role: "user",
      content,
      language: language === "ar" ? "ar" : "en",
      created_at: new Date().toISOString()
    };

    const assistantTempId = `asst-${Date.now()}`;
    const assistantPlaceholder: Message = {
      id: assistantTempId,
      conversation_id: targetConvId,
      role: "assistant",
      content: "",
      language: language === "ar" ? "ar" : "en",
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, tempUserMsg, assistantPlaceholder]);
    setGenerating(true);

    try {
      await streamMessage(
        targetConvId,
        content,
        activeKbId,
        language,
        // onToken
        (token: string) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantTempId ? { ...m, content: m.content + token } : m
            )
          );
        },
        // onDone
        (data: any) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantTempId
                ? {
                  ...m,
                  id: data.message_id || m.id,
                  content: data.content !== undefined ? data.content : m.content,
                  citations: data.citations || [],
                  provider: data.provider,
                  model: data.model,
                  latency_ms: data.latency_ms,
                  cost_usd: data.cost_usd,
                  prompt_tokens: data.prompt_tokens,
                  completion_tokens: data.completion_tokens,
                  total_tokens: data.total_tokens,
                  is_fallback: data.is_fallback,
                  fallback_info: data.fallback_info,
                }
                : m
            )
          );
          refreshConversations();
        },
        // onError
        (err: any) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantTempId
                ? {
                  ...m,
                  content: m.content
                    ? `${m.content}\n\n[Error: ${err.message}]`
                    : `Error: ${err.message || "Failed to generate response"}`,
                }
                : m
            )
          );
        }
      );
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantTempId
            ? {
              ...m,
              content: `Error: ${err.message || "Failed to generate response"}`,
            }
            : m
        )
      );
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white dark:bg-slate-950 font-sans">
      {/* 1. Left Sidebar */}
      <Sidebar />

      {/* 2. Main Chat Workspace */}
      <main className="flex-1 flex flex-col h-screen min-w-0 bg-white dark:bg-slate-950 relative">
        {/* Workspace Header */}
        <header className="h-14 border-b border-slate-200 dark:border-slate-800 px-6 flex items-center justify-between shrink-0 bg-white/70 dark:bg-slate-950/70 backdrop-blur-md z-10">
          <div className="flex items-center gap-3 truncate">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-xs shadow-emerald-500/50" />
            <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
              {activeKb ? activeKb.name : (language === "ar" ? "المساعد الذكي العام" : "Enterprise AI Assistant")}
            </h2>
            {activeKb && (
              <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-medium bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 rounded-full border border-indigo-200 dark:border-indigo-900/60">
                {activeKb.document_count} {language === "ar" ? "مستندات مفهرسة" : "Indexed Documents"}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Live Voice Mode Launch Button */}
            <button
              onClick={() => setVoiceModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white rounded-xl text-xs font-medium shadow-sm shadow-indigo-600/20 transition active:scale-95"
              title={language === "ar" ? "بدء المحادثة الصوتية الحية" : "Start Live Voice Chat"}
            >
              <Mic size={14} />
              <span className="hidden sm:inline">{language === "ar" ? "صوت حي" : "Live Voice"}</span>
            </button>

            {/* Contextual Panel Toggle Button */}
            <button
              onClick={() => setContextualPanelOpen(!contextualPanelOpen)}
              className={`p-2 rounded-xl transition ${contextualPanelOpen
                  ? "bg-slate-200 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400"
                  : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-900"
                }`}
              title={language === "ar" ? "تبديل لوحة المستندات" : "Toggle Knowledge Panel"}
            >
              <PanelRight size={17} />
            </button>
          </div>
        </header>

        {/* Message Feed */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 size={24} className="animate-spin text-indigo-500" />
            </div>
          ) : messages.length === 0 ? (
            /* Empty State & Quick Prompts */
            <div className="flex flex-col items-center justify-center h-full max-w-lg mx-auto text-center px-4 py-8 space-y-6">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center text-white shadow-lg shadow-indigo-500/30">
                <Radio size={28} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">
                  {language === "ar"
                    ? "مرحباً بك في VoiceRag"
                    : "Welcome to VoiceRag"}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 leading-relaxed">
                  {language === "ar"
                    ? "المساعد الصوتي والمعرفي المتقدم للشركات. اسأل صوتياً أو نصياً باللغة العربية والإنجليزية، مع استرجاع هجين موثق بالمصادر."
                    : "Enterprise Multilingual AI Voice & Knowledge Platform. Ask via voice or text in English and Arabic, grounded in private sources with source citations."}
                </p>
              </div>

              {/* Starter Quick Actions */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full text-start">
                <button
                  onClick={() => handleSendMessage(language === "ar" ? "مرحباً، كيف يمكنك مساعدتي اليوم؟" : "Hello! How can you help me today?")}
                  className="p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-indigo-400 dark:hover:border-indigo-500/50 rounded-xl text-xs text-slate-700 dark:text-slate-300 transition text-start shadow-2xs"
                >
                  <span className="font-semibold block text-indigo-600 dark:text-indigo-400 mb-0.5">
                    {language === "ar" ? "محادثة عامة" : "General Chat"}
                  </span>
                  <span>{language === "ar" ? "مرحباً، كيف يمكنك مساعدتي؟" : "Hello, how can you help me?"}</span>
                </button>

                <button
                  onClick={() => setContextualPanelOpen(true)}
                  className="p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-indigo-400 dark:hover:border-indigo-500/50 rounded-xl text-xs text-slate-700 dark:text-slate-300 transition text-start shadow-2xs"
                >
                  <span className="font-semibold block text-indigo-600 dark:text-indigo-400 mb-0.5">
                    {language === "ar" ? "ربط مستند" : "Attach Document"}
                  </span>
                  <span>{language === "ar" ? "رفع وفهرسة مستند جديد" : "Upload & index a new source"}</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto py-4 divide-y divide-transparent">
              {messages.map((m) => (
                <MessageItem key={m.id} message={m} />
              ))}
              {generating && (
                <div className="flex items-center gap-3 px-6 py-4 text-xs text-slate-400 animate-pulse">
                  <div className="w-2 h-2 rounded-full bg-indigo-500" />
                  <span>{language === "ar" ? "جاري التفكير وتوليد الإجابة الموثقة..." : "Thinking & generating grounded response..."}</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Message Composer */}
        <Composer
          onSendMessage={handleSendMessage}
          generating={generating}
        />
      </main>

      {/* 3. Right Contextual Panel */}
      <ContextualPanel />

      {/* 4. Realtime Voice Wave Modal */}
      <VoiceWaveModal />
    </div>
  );
}

