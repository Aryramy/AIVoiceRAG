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
    knowledgeBases,
    refreshKnowledgeBases,
    selectedCitation,
    setSelectedCitation,
    language
  } = useApp();

  const [kbDetails, setKbDetails] = useState<any>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showNewKbModal, setShowNewKbModal] = useState(false);
  const [newKbName, setNewKbName] = useState("");
  const [newKbDesc, setNewKbDesc] = useState("");

  const activeKb = knowledgeBases.find((k) => k.id === activeKbId);

  const loadKbDetails = async () => {
    if (!activeKbId) {
      setKbDetails(null);
      return;
    }
    try {
      const data = await fetchKnowledgeBaseDetails(activeKbId);
      setKbDetails(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadKbDetails();
  }, [activeKbId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeKbId) return;

    setUploading(true);
    setUploadError(null);
    try {
      await uploadDocument(activeKbId, file);
      await loadKbDetails();
      await refreshKnowledgeBases();
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload and index document");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDeleteDoc = async (docId: string) => {
    if (!activeKbId) return;
    try {
      await deleteDocument(activeKbId, docId);
      await loadKbDetails();
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
      setActiveKbId(newKb.id);
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
          className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 transition"
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
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
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
              "{selectedCitation.content_snippet}"
            </p>
          </div>
        )}

        {/* Knowledge Base Info */}
        {activeKb ? (
          <div className="space-y-4">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-2xs">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">{activeKb.name}</h3>
                  <p className="text-xs text-slate-500 mt-0.5">{activeKb.description || "General Knowledge Base"}</p>
                </div>
                <span className="px-2 py-0.5 text-[10px] bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 font-medium rounded-full">
                  {language === "ar" ? "نشط" : "Active"}
                </span>
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
                    onChange={handleFileUpload}
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
                        onClick={() => handleDeleteDoc(doc.id)}
                        className="p-1 text-slate-400 hover:text-red-500 rounded transition"
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
          <div className="text-center py-10 space-y-3">
            <Database size={32} className="mx-auto text-slate-400" />
            <p className="text-xs text-slate-500 max-w-xs mx-auto">
              {language === "ar"
                ? "حدد قاعدة معرفة من القائمة الجانبية أو قم بإنشاء قاعدة جديدة لرفع المستندات والبحث فيها"
                : "Select a knowledge base or create a new one to upload documents and query them"}
            </p>
            <button
              onClick={() => setShowNewKbModal(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-medium transition active:scale-95"
            >
              <Plus size={14} />
              <span>{language === "ar" ? "إنشاء قاعدة معرفة" : "Create Knowledge Base"}</span>
            </button>
          </div>
        )}
      </div>

      {/* New KB Modal */}
      {showNewKbModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 w-full max-w-sm space-y-4">
            <div className="flex items-center justify-between text-sm font-semibold text-slate-800 dark:text-slate-100">
              <span>{language === "ar" ? "قاعدة معرفة جديدة" : "New Knowledge Base"}</span>
              <button onClick={() => setShowNewKbModal(false)} className="text-slate-400 hover:text-slate-600">
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
                  className="px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
                >
                  {language === "ar" ? "إلغاء" : "Cancel"}
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium"
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
