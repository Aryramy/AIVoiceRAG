"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useApp } from "@/context/AppContext";
import { createConversation, deleteConversation } from "@/lib/api";
import {
  MessageSquare,
  Plus,
  Database,
  Sliders,
  BarChart3,
  Trash2,
  Search,
  Sun,
  Moon,
  Globe,
  Radio,
  ChevronRight,
  ChevronLeft
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const {
    theme,
    setTheme,
    language,
    setLanguage,
    direction,
    conversations,
    activeConversationId,
    setActiveConversationId,
    refreshConversations,
    knowledgeBases,
    activeKbId,
    setActiveKbId,
    updateActiveConversationKb,
    sidebarOpen,
    setSidebarOpen,
    setVoiceModalOpen
  } = useApp();

  const [searchQuery, setSearchQuery] = useState("");

  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleNewChat = async () => {
    try {
      const newConv = await createConversation(
        language === "ar" ? "محادثة جديدة" : "New Conversation",
        language,
        activeKbId || undefined
      );
      await refreshConversations();
      setActiveConversationId(newConv.id);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteConversation = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await deleteConversation(id);
      await refreshConversations();
      if (activeConversationId === id) {
        setActiveConversationId(null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (!sidebarOpen) {
    return (
      <button
        onClick={() => setSidebarOpen(true)}
        className="fixed top-4 start-4 z-40 p-2.5 bg-slate-900 border border-slate-700 rounded-xl text-slate-300 hover:text-white shadow-lg transition-all"
        title={language === "ar" ? "فتح القائمة" : "Open Sidebar"}
      >
        {direction === "rtl" ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
      </button>
    );
  }

  return (
    <aside className="w-72 h-screen flex flex-col border-e border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 select-none z-30 transition-all">
      {/* Brand & New Chat */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800/80">
        <div className="flex items-center justify-between mb-4">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center text-white shadow-sm shadow-indigo-500/30">
              <Radio size={18} />
            </div>
            <div>
              <span className="font-semibold text-base text-slate-900 dark:text-white tracking-tight">VoiceRag</span>
              <span className="block text-[10px] text-slate-500 uppercase tracking-wider font-medium">Enterprise AI</span>
            </div>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 transition"
          >
            {direction === "rtl" ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        <button
          onClick={handleNewChat}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-3.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium shadow-sm shadow-indigo-600/20 transition active:scale-[0.98]"
        >
          <Plus size={16} />
          <span>{language === "ar" ? "محادثة جديدة" : "New Conversation"}</span>
        </button>
      </div>

      {/* Active Knowledge Base Selector */}
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-800/60">
        <div className="flex items-center justify-between text-xs text-slate-500 font-medium mb-1.5">
          <span className="flex items-center gap-1.5">
            <Database size={13} />
            {language === "ar" ? "قاعدة المعرفة النشطة" : "Active Knowledge Base"}
          </span>
        </div>
        <select
          value={activeKbId || ""}
          onChange={(e) => updateActiveConversationKb(e.target.value || null)}
          className="w-full text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer"
        >
          <option value="">{language === "ar" ? "عام (بدون قاعدة معرفة)" : "General (No Knowledge Base)"}</option>
          {knowledgeBases.map((kb) => (
            <option key={kb.id} value={kb.id}>
              {kb.name} ({kb.document_count} {language === "ar" ? "مستندات" : "docs"})
            </option>
          ))}
        </select>
      </div>

      {/* Search Input */}
      <div className="px-4 pt-3 pb-2">
        <div className="relative">
          <Search size={14} className="absolute top-2.5 start-2.5 text-slate-400" />
          <input
            type="text"
            placeholder={language === "ar" ? "بحث في المحادثات..." : "Search conversations..."}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full ps-8 pe-3 py-1.5 text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-0.5">
        <div className="px-2 py-1 text-[11px] font-medium text-slate-400 uppercase tracking-wider">
          {language === "ar" ? "المحادثات الأخيرة" : "Recent Chats"}
        </div>
        {filteredConversations.length === 0 ? (
          <div className="px-3 py-6 text-center text-xs text-slate-400">
            {language === "ar" ? "لا توجد محادثات سابقة" : "No conversations found"}
          </div>
        ) : (
          filteredConversations.map((conv) => {
            const isActive = activeConversationId === conv.id;
            return (
              <div
                key={conv.id}
                onClick={() => setActiveConversationId(conv.id)}
                className={`group flex items-center justify-between px-3 py-2 rounded-lg text-xs cursor-pointer transition ${
                  isActive
                    ? "bg-slate-200/70 dark:bg-slate-800 text-slate-900 dark:text-white font-medium"
                    : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900/60 hover:text-slate-900 dark:hover:text-slate-200"
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <MessageSquare size={14} className={isActive ? "text-indigo-500" : "text-slate-400"} />
                  <span className="truncate">{conv.title}</span>
                </div>
                <button
                  onClick={(e) => handleDeleteConversation(e, conv.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-500 transition rounded"
                  title={language === "ar" ? "حذف" : "Delete"}
                >
                  <Trash2 size={12} />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Navigation & Preferences Footer */}
      <div className="p-3 border-t border-slate-200 dark:border-slate-800 space-y-1">
        <Link
          href="/settings"
          className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition ${
            pathname === "/settings"
              ? "bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400"
              : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900"
          }`}
        >
          <Sliders size={15} />
          <span>{language === "ar" ? "إعدادات النماذج والمزودين" : "AI Provider & Model Settings"}</span>
        </Link>

        <Link
          href="/analytics"
          className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition ${
            pathname === "/analytics"
              ? "bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400"
              : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900"
          }`}
        >
          <BarChart3 size={15} />
          <span>{language === "ar" ? "التحليلات والتكاليف" : "Analytics & Cost Telemetry"}</span>
        </Link>

        <div className="pt-2 mt-1 border-t border-slate-200 dark:border-slate-800/60 flex items-center justify-between px-1">
          {/* Language Toggle */}
          <button
            onClick={() => setLanguage(language === "en" ? "ar" : "en")}
            className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 rounded-md hover:bg-slate-100 dark:hover:bg-slate-900 transition"
          >
            <Globe size={13} />
            <span>{language === "en" ? "العربية (RTL)" : "English (LTR)"}</span>
          </button>

          {/* Theme Toggle */}
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="p-1.5 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 rounded-md hover:bg-slate-100 dark:hover:bg-slate-900 transition"
            title={language === "ar" ? "تغيير المظهر" : "Toggle Theme"}
          >
            {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
          </button>
        </div>
      </div>
    </aside>
  );
}

