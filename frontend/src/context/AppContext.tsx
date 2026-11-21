"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { Conversation, KnowledgeBase, Citation } from "@/types";
import { fetchConversations, fetchKnowledgeBases, createConversation, updateConversation } from "@/lib/api";

type Theme = "light" | "dark" | "system";
type Language = "en" | "ar";

interface AppContextType {
  theme: Theme;
  setTheme: (t: Theme) => void;
  language: Language;
  setLanguage: (l: Language) => void;
  direction: "ltr" | "rtl";
  
  // Conversations
  conversations: Conversation[];
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
  refreshConversations: () => Promise<void>;
  createConversation: (title?: string, lang?: string, kbId?: string | null) => Promise<Conversation>;
  
  // Knowledge Bases
  knowledgeBases: KnowledgeBase[];
  activeKbId: string | null;
  setActiveKbId: (id: string | null) => void;
  updateActiveConversationKb: (id: string | null) => Promise<void>;
  refreshKnowledgeBases: () => Promise<void>;

  // Panels
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  contextualPanelOpen: boolean;
  setContextualPanelOpen: (open: boolean) => void;

  // Citation Preview
  selectedCitation: Citation | null;
  setSelectedCitation: (c: Citation | null) => void;

  // Voice Modal
  voiceModalOpen: boolean;
  setVoiceModalOpen: (open: boolean) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("dark");
  const [language, setLanguage] = useState<Language>("en");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [activeKbId, setActiveKbId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const [contextualPanelOpen, setContextualPanelOpen] = useState<boolean>(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [voiceModalOpen, setVoiceModalOpen] = useState<boolean>(false);

  const direction = language === "ar" ? "rtl" : "ltr";

  // Sync theme with document class
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else if (theme === "light") {
      root.classList.remove("dark");
    } else {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      if (prefersDark) root.classList.add("dark");
      else root.classList.remove("dark");
    }
  }, [theme]);

  // Sync direction and lang attributes
  useEffect(() => {
    document.documentElement.dir = direction;
    document.documentElement.lang = language;
  }, [direction, language]);

  const handleCreateConversation = async (
    title: string = language === "ar" ? "محادثة جديدة" : "New Conversation",
    lang: string = language,
    kbId?: string | null
  ) => {
    const targetKbId = kbId !== undefined ? kbId : activeKbId;
    const newConv = await createConversation(title, lang, targetKbId);
    setConversations((prev) => [newConv, ...prev.filter((c) => c.id !== newConv.id)]);
    setActiveConversationId(newConv.id);
    return newConv;
  };

  // Sync activeKbId when activeConversationId changes
  const handleSelectConversation = (id: string | null) => {
    setActiveConversationId(id);
    if (id) {
      const conv = conversations.find((c) => c.id === id);
      if (conv) {
        setActiveKbId(conv.knowledge_base_id || null);
      }
    } else {
      setActiveKbId(null);
    }
  };

  const updateActiveConversationKb = async (kbId: string | null) => {
    setActiveKbId(kbId);
    if (activeConversationId) {
      // Optimistically update conversation in local state
      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeConversationId
            ? { ...c, knowledge_base_id: kbId }
            : c
        )
      );
      try {
        await updateConversation(activeConversationId, {
          knowledge_base_id: kbId,
        });
        const list = await fetchConversations();
        setConversations(list);
      } catch (err) {
        console.error("Failed to persist conversation knowledge base update:", err);
      }
    }
  };

  const refreshConversations = async () => {
    try {
      const list = await fetchConversations();
      if (list.length === 0) {
        try {
          const initial = await createConversation(
            language === "ar" ? "محادثة جديدة" : "New Conversation",
            language
          );
          setConversations([initial]);
          setActiveConversationId(initial.id);
          setActiveKbId(initial.knowledge_base_id || null);
          return;
        } catch (createErr) {
          console.error("Failed to auto-create initial conversation:", createErr);
        }
      }
      setConversations(list);
      if (!activeConversationId && list.length > 0) {
        setActiveConversationId(list[0].id);
        setActiveKbId(list[0].knowledge_base_id || null);
      } else if (activeConversationId && !list.some((c) => c.id === activeConversationId) && list.length > 0) {
        setActiveConversationId(list[0].id);
        setActiveKbId(list[0].knowledge_base_id || null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const refreshKnowledgeBases = async () => {
    try {
      const list = await fetchKnowledgeBases();
      setKnowledgeBases(list);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    refreshConversations();
    refreshKnowledgeBases();
  }, []);

  return (
    <AppContext.Provider
      value={{
        theme,
        setTheme,
        language,
        setLanguage,
        direction,
        conversations,
        activeConversationId,
        setActiveConversationId: handleSelectConversation,
        refreshConversations,
        createConversation: handleCreateConversation,
        knowledgeBases,
        activeKbId,
        setActiveKbId,
        updateActiveConversationKb,
        refreshKnowledgeBases,
        sidebarOpen,
        setSidebarOpen,
        contextualPanelOpen,
        setContextualPanelOpen,
        selectedCitation,
        setSelectedCitation,
        voiceModalOpen,
        setVoiceModalOpen,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used within an AppProvider");
  return context;
}

