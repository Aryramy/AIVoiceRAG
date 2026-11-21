"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "@/context/AppContext";
import { fetchKnowledgeBaseDetails, uploadDocument, deleteDocument, createKnowledgeBase } from "@/lib/api";
import {
  X,
  FileText,
  Upload,
  Trash2,
  Database,
  ExternalLink,
  Plus,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Bookmark
} from "lucide-react";

export function ContextualPanel() {
  const {
    contextualPanelOpen,
    setContextualPanelOpen,
    activeKbId,
    setActiveKbId,
    updateActiveConversationKb,
    knowledgeBases,
    refreshKnowledgeBases,
    selectedCitation,
    setSelectedCitation,
    language
  } = useApp();

  const [kbDetails, setKbDetails] = useState<any>(null);
  const [inspectingKbId, setInspectingKbId] = useState<string | null>(null);
  const [inspectingKbDetails, setInspectingKbDetails] = useState<any>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showNewKbModal, setShowNewKbModal] = useState(false);
  const [newKbName, setNewKbName] = useState("");
  const [newKbDesc, setNewKbDesc] = useState("");

  const activeKb = knowledgeBases.find((k) => k.id === activeKbId);

  const loadKbDetails = async (kbId: string | null) => {
    if (!kbId) {
      setKbDetails(null);
      return;
    }
    try {
      const data = await fetchKnowledgeBaseDetails(kbId);
      setKbDetails(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadKbDetails(activeKbId);
  }, [activeKbId]);

  const loadInspectingDetails = async (kbId: string | null) => {
    if (!kbId) {
      setInspectingKbDetails(null);
      return;
    }
    try {
      const data = await fetchKnowledgeBaseDetails(kbId);
      setInspectingKbDetails(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadInspectingDetails(inspectingKbId);
  }, [inspectingKbId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, targetKbId: string) => {
    const file = e.target.files?.[0];
    if (!file || !targetKbId) return;

    setUploading(true);
    setUploadError(null);
    try {
      await uploadDocument(targetKbId, file);
      if (targetKbId === activeKbId) await loadKbDetails(activeKbId);
      if (targetKbId === inspectingKbId) await loadInspectingDetails(inspectingKbId);
      await refreshKnowledgeBases();
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload and index document");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDeleteDoc = async (docId: string, targetKbId: string) => {
    if (!targetKbId) return;
    try {
      await deleteDocument(targetKbId, docId);
      if (targetKbId === activeKbId) await loadKbDetails(activeKbId);
      if (targetKbId === inspectingKbId) await loadInspectingDetails(inspectingKbId);
      await refreshKnowledgeBases();
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateKb = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKbName.trim()) return;
    try {
      const newKb = await createKnowledgeBase(newKbName.trim(), newKbDesc.trim());
      await refreshKnowledgeBases();
      await updateActiveConversationKb(newKb.id);
      setShowNewKbModal(false);
      setNewKbName("");
      setNewKbDesc("");
    } catch (err) {
      console.error(err);
    }
  };

  if (!contextualPanelOpen) return null;

  return (
    <aside className="w-80 md:w-96 h-screen flex flex-col border-s border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 select-none z-30 transition-all">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
          <Database size={16} className="text-indigo-500" />
          <span>{language === "ar" ? "لوحة المستندات والمعرفة" : "Knowledge & Citations"}</span>
        </div>
        <button
          onClick={() => setContextualPanelOpen(false)}
          className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 transition cursor-pointer"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Selected Citation Inspector */}
        {selectedCitation && (
          <div className="bg-indigo-50/60 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800/60 rounded-2xl p-3.5 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-indigo-900 dark:text-indigo-300">
              <span className="flex items-center gap-1.5">
                <Bookmark size={14} className="text-indigo-500" />
                {language === "ar" ? "تفاصيل المرجع المستشهد به:" : "Inspected Citation:"}
              </span>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
              >
                <X size={13} />
              </button>
            </div>
            <div className="text-xs font-medium text-slate-800 dark:text-slate-200">
              {selectedCitation.document_title || "Document"}
              {selectedCitation.page_number && (
                <span className="ms-2 px-1.5 py-0.5 bg-indigo-100 dark:bg-indigo-900/60 rounded text-[10px] text-indigo-700 dark:text-indigo-300">
                  {language === "ar" ? `صفحة ${selectedCitation.page_number}` : `Page ${selectedCitation.page_number}`}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed italic bg-white dark:bg-slate-900 p-2.5 rounded-xl border border-indigo-100 dark:border-indigo-950">
              "{selectedCitation.content_snippet || selectedCitation.content || selectedCitation.snippet || ""}"
            </p>
          </div>
        )}

        {/* Active Knowledge Base Info (if one is attached to current chat) */}
        {activeKb ? (
          <div className="space-y-4">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-2xs">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">{activeKb.name}</h3>
                  <p className="text-xs text-slate-500 mt-0.5">{activeKb.description || "Active Knowledge Base"}</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="px-2 py-0.5 text-[10px] bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 font-medium rounded-full">
                    {language === "ar" ? "نشط" : "Active"}
                  </span>
                  <button
                    onClick={() => updateActiveConversationKb(null)}
                    className="text-[10px] px-2 py-0.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-full transition cursor-pointer"
                    title={language === "ar" ? "التبديل إلى الوضع العام" : "Switch to General (No KB)"}
                  >
                    {language === "ar" ? "فصل" : "Detach"}
                  </button>
                </div>
              </div>

              {/* Upload Zone */}
              <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
                <label className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-indigo-500 dark:hover:border-indigo-500 rounded-xl cursor-pointer bg-slate-50 dark:bg-slate-800/40 hover:bg-indigo-50/20 transition group">
                  <Upload size={20} className="text-slate-400 group-hover:text-indigo-500 transition mb-1.5" />
                  <span className="text-xs font-medium text-slate-700 dark:text-slate-300 text-center">
                    {uploading
                      ? (language === "ar" ? "جاري الرفع والفهرسة..." : "Uploading & Indexing...")
                      : (language === "ar" ? "رفع مستند (PDF, Word, Excel, TXT)" : "Upload Source (PDF, Word, Excel, TXT)")}
                  </span>
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md"
                    onChange={(e) => handleFileUpload(e, activeKb.id)}
                    disabled={uploading}
                    className="hidden"
                  />
                </label>
                {uploadError && (
                  <p className="text-xs text-red-500 mt-2 flex items-center gap-1">
                    <AlertCircle size={12} />
                    {uploadError}
                  </p>
                )}
              </div>
            </div>

            {/* Document Sources List */}
            <div>
              <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-2.5">
                <span>{language === "ar" ? "المستندات المفهرسة" : "Indexed Documents"}</span>
                <span className="text-[11px] font-mono text-slate-400">
                  {kbDetails?.documents?.length || 0} {language === "ar" ? "ملفات" : "files"}
                </span>
              </div>

              <div className="space-y-2">
                {!kbDetails?.documents || kbDetails.documents.length === 0 ? (
                  <div className="text-center py-6 text-xs text-slate-400">
                    {language === "ar" ? "لا توجد مستندات بعد في هذه القاعدة" : "No documents added yet"}
                  </div>
                ) : (
                  kbDetails.documents.map((doc: any) => (
                    <div
                      key={doc.id}
                      className="p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl flex items-center justify-between text-xs hover:border-slate-300 dark:hover:border-slate-700 transition"
                    >
                      <div className="flex items-center gap-2.5 truncate pe-2">
                        <FileText size={16} className="text-indigo-500 shrink-0" />
                        <div className="truncate">
                          <p className="font-medium text-slate-800 dark:text-slate-200 truncate">{doc.title}</p>
                          <p className="text-[10px] text-slate-400 font-mono">
                            {doc.chunk_count} {language === "ar" ? "أجزاء مفهرسة" : "chunks"} • {doc.file_type.toUpperCase()}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteDoc(doc.id, activeKb.id)}
                        className="p-1 text-slate-400 hover:text-red-500 rounded transition cursor-pointer"
                        title={language === "ar" ? "حذف المستند" : "Delete Document"}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        ) : (
          /* General Mode Banner */
          <div className="p-3.5 bg-slate-100/80 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Database size={13} className="text-slate-400" />
                {language === "ar" ? "الوضع العام (بدون قاعدة معرفة)" : "General Mode (No KB)"}
              </span>
              <span className="text-[10px] px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-500 rounded">
                {language === "ar" ? "بدون استرجاع" : "RAG Off"}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
              {language === "ar"
                ? "هذه المحادثة تجيب من المعرفة العامة للذكاء الاصطناعي. يمكنك ربط أي قاعدة معرفة أدناه لتفعيل الاسترجاع الدقيق."
                : "This conversation answers using general AI knowledge. Attach any knowledge base below to enable grounded retrieval."}
            </p>
          </div>
        )}

        {/* All Knowledge Bases Section - Always Loaded & Visible */}
        <div className="pt-2 border-t border-slate-200 dark:border-slate-800/80 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <Database size={13} className="text-indigo-500" />
              {language === "ar" ? "قواعد المعرفة المتاحة" : "Available Knowledge Bases"}
              <span className="text-[10px] text-slate-400 font-mono">({knowledgeBases.length})</span>
            </span>
            <button
              onClick={() => setShowNewKbModal(true)}
              className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 rounded-lg transition cursor-pointer"
            >
              <Plus size={13} />
              <span>{language === "ar" ? "قاعدة جديدة" : "New KB"}</span>
            </button>
          </div>

          {knowledgeBases.length === 0 ? (
            <div className="text-center py-6 px-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-2">
              <Database size={24} className="mx-auto text-slate-400" />
              <p className="text-xs text-slate-500">
                {language === "ar" ? "لا توجد قواعد معرفة بعد" : "No knowledge bases created yet"}
              </p>
              <button
                onClick={() => setShowNewKbModal(true)}
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium cursor-pointer"
              >
                <Plus size={13} />
                <span>{language === "ar" ? "إنشاء أول قاعدة" : "Create First KB"}</span>
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {knowledgeBases.map((kb) => {
                const isCurrentActive = kb.id === activeKbId;
                const isInspecting = inspectingKbId === kb.id;

                return (
                  <div
                    key={kb.id}
                    className={`p-3 rounded-xl border text-xs transition ${isCurrentActive
                        ? "bg-indigo-50/50 dark:bg-indigo-950/20 border-indigo-200 dark:border-indigo-900/60"
                        : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                      }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="truncate flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-slate-800 dark:text-slate-100 truncate">{kb.name}</span>
                          {isCurrentActive && (
                            <span className="px-1.5 py-0.2 bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400 text-[9px] font-medium rounded">
                              {language === "ar" ? "نشط" : "Active"}
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate mt-0.5">
                          {kb.description || (language === "ar" ? "بدون وصف" : "No description")}
                        </p>
                        <span className="inline-block text-[10px] text-slate-400 font-mono mt-1">
                          {kb.document_count} {language === "ar" ? "مستندات" : "documents"}
                        </span>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {isCurrentActive ? (
                          <button
                            onClick={() => updateActiveConversationKb(null)}
                            className="px-2 py-1 text-[10px] bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-lg transition cursor-pointer"
                          >
                            {language === "ar" ? "فصل" : "Detach"}
                          </button>
                        ) : (
                          <button
                            onClick={() => updateActiveConversationKb(kb.id)}
                            className="px-2.5 py-1 text-[10px] bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg shadow-2xs transition cursor-pointer"
                          >
                            {language === "ar" ? "ربط بالدردشة" : "Attach"}
                          </button>
                        )}
                        <button
                          onClick={() => setInspectingKbId(isInspecting ? null : kb.id)}
                          className={`p-1 rounded-lg transition cursor-pointer ${isInspecting
                              ? "bg-slate-200 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400"
                              : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                            }`}
                          title={language === "ar" ? "عرض المستندات" : "Inspect documents"}
                        >
                          <FileText size={13} />
                        </button>
                      </div>
                    </div>

                    {/* Quick Document Inspector for this KB */}
                    {isInspecting && (
                      <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800 space-y-2">
                        <div className="flex items-center justify-between text-[11px] font-medium text-slate-500">
                          <span>{language === "ar" ? "مستندات هذه القاعدة:" : "Documents in this KB:"}</span>
                          <label className="text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer flex items-center gap-1">
                            <Upload size={11} />
                            <span>{language === "ar" ? "رفع" : "Upload"}</span>
                            <input
                              type="file"
                              accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md"
                              onChange={(e) => handleFileUpload(e, kb.id)}
                              disabled={uploading}
                              className="hidden"
                            />
                          </label>
                        </div>

                        {!inspectingKbDetails?.documents || inspectingKbDetails.documents.length === 0 ? (
                          <p className="text-[11px] text-slate-400 italic py-1">
                            {language === "ar" ? "لا توجد مستندات بعد" : "No documents indexed yet"}
                          </p>
                        ) : (
                          <div className="space-y-1 max-h-36 overflow-y-auto">
                            {inspectingKbDetails.documents.map((d: any) => (
                              <div
                                key={d.id}
                                className="flex items-center justify-between p-1.5 rounded bg-slate-50 dark:bg-slate-800/60 text-[11px]"
                              >
                                <span className="truncate pe-2 text-slate-700 dark:text-slate-300">{d.title}</span>
                                <button
                                  onClick={() => handleDeleteDoc(d.id, kb.id)}
                                  className="text-slate-400 hover:text-red-500 p-0.5 cursor-pointer"
                                  title="Delete"
                                >
                                  <Trash2 size={11} />
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* New KB Modal */}
      {showNewKbModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 w-full max-w-sm space-y-4 shadow-xl">
            <div className="flex items-center justify-between text-sm font-semibold text-slate-800 dark:text-slate-100">
              <span>{language === "ar" ? "قاعدة معرفة جديدة" : "New Knowledge Base"}</span>
              <button onClick={() => setShowNewKbModal(false)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleCreateKb} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                  {language === "ar" ? "اسم القاعدة" : "Name"}
                </label>
                <input
                  type="text"
                  required
                  value={newKbName}
                  onChange={(e) => setNewKbName(e.target.value)}
                  placeholder="e.g. HR Company Handbook"
                  className="w-full text-xs px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                  {language === "ar" ? "الوصف" : "Description"}
                </label>
                <textarea
                  value={newKbDesc}
                  onChange={(e) => setNewKbDesc(e.target.value)}
                  rows={2}
                  placeholder="Optional description"
                  className="w-full text-xs px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewKbModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg cursor-pointer"
                >
                  {language === "ar" ? "إلغاء" : "Cancel"}
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium cursor-pointer"
                >
                  {language === "ar" ? "إنشاء" : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </aside>
  );
}

