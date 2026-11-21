"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useApp } from "@/context/AppContext";
import {
  fetchProviders,
  fetchProviderModels,
  fetchProviderVoices,
  testProvider,
  fetchSettings,
  updateSettings,
  synthesizeSpeech,
  unlockBrowserAudio
} from "@/lib/api";
import { ProviderStatus, ModelInfo, VoiceInfo, AISettings, ProviderTestResult } from "@/types";
import {
  Sliders,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCw,
  Save,
  ArrowLeft,
  ArrowRight,
  Sparkles,
  Mic,
  Volume2,
  Radio,
  Cpu,
  Layers,
  Shield,
  Loader2,
  Check,
  Info
} from "lucide-react";

const AI_PROVIDERS = [
  {
    id: "openai",
    name: "OpenAI",
    tagline: "GPT-4o, Whisper STT, Neural HD TTS",
    icon: Sparkles,
  },
  {
    id: "gemini",
    name: "Google Gemini",
    tagline: "Gemini 2.0 Flash / Pro Multimodal",
    icon: Cpu,
  },
  {
    id: "openrouter",
    name: "OpenRouter",
    tagline: "Unified Multi-Model Gateway",
    icon: Layers,
  },
  {
    id: "cheaper_inference",
    name: "CheaperInference",
    tagline: "High-Throughput Low-Cost Inference",
    icon: Radio,
  },
];

export default function SettingsPage() {
  const { language, direction } = useApp();
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [settings, setSettings] = useState<AISettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [cascadingLoading, setCascadingLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Dynamic Models and Voices for the active provider
  const [llmModels, setLlmModels] = useState<ModelInfo[]>([]);
  const [sttModels, setSttModels] = useState<ModelInfo[]>([]);
  const [ttsModels, setTtsModels] = useState<ModelInfo[]>([]);
  const [ttsVoices, setTtsVoices] = useState<VoiceInfo[]>([]);

  // Edge TTS fallback toggle and dedicated Edge voices cache
  const [useEdgeTtsFallback, setUseEdgeTtsFallback] = useState(false);
  const [edgeTtsVoices, setEdgeTtsVoices] = useState<VoiceInfo[]>([]);

  // Testing states
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, ProviderTestResult>>({});
  const [testingAudioVoice, setTestingAudioVoice] = useState<string | null>(null);

  // System Prompt active tab
  const [promptTab, setPromptTab] = useState<"en" | "ar">("en");

  const loadData = async () => {
    setLoading(true);
    try {
      const [provList, activeSettings] = await Promise.all([
        fetchProviders(),
        fetchSettings()
      ]);
      setProviders(provList);

      const activeProv = activeSettings.llm_provider || "openai";
      const isEdge = activeSettings.tts_provider === "edge_tts";
      setUseEdgeTtsFallback(isEdge);

      // Single-Provider Cascading Fetch for initial active provider
      const [llms, stts, ttss, voices] = await Promise.all([
        fetchProviderModels(activeProv, "llm"),
        fetchProviderModels(activeProv, "stt"),
        fetchProviderModels(activeProv, "tts"),
        fetchProviderVoices(activeProv)
      ]);

      const cleanStts = stts.filter((m) => !m.id.toLowerCase().includes("tts") && !m.id.toLowerCase().includes("speech"));

      setLlmModels(llms);
      setSttModels(cleanStts);
      setTtsModels(ttss);
      setTtsVoices(voices);

      if (isEdge) {
        const edgeV = await fetchProviderVoices("edge_tts");
        setEdgeTtsVoices(edgeV);
      }

      // Sanitize settings to ensure no stale or incompatible IDs exist
      const sanitized = { ...activeSettings };
      if (llms.length > 0 && !llms.some((m) => m.id === activeSettings.llm_model)) {
        sanitized.llm_model = llms[0].id;
      }
      if (stts.length > 0 && !stts.some((m) => m.id === activeSettings.stt_model)) {
        sanitized.stt_model = stts[0].id;
      }
      if (ttss.length > 0 && !ttss.some((m) => m.id === activeSettings.tts_model)) {
        sanitized.tts_model = ttss[0].id;
      }
      if (!isEdge && voices.length > 0) {
        const voiceIds = new Set(voices.map((v) => v.id.toLowerCase()));
        if (!voiceIds.has((activeSettings.tts_voice_en || "").toLowerCase())) {
          sanitized.tts_voice_en = voices[0].id;
        }
        if (!voiceIds.has((activeSettings.tts_voice_ar || "").toLowerCase())) {
          sanitized.tts_voice_ar = voices[0].id;
        }
      }

      setSettings(sanitized);
    } catch (err) {
      console.error("Failed to load settings data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Handle Switching the Unified Active AI Provider
  const handleActiveProviderChange = async (newProvider: string) => {
    if (!settings || newProvider === settings.llm_provider) return;
    setCascadingLoading(true);

    try {
      // 1. Single-Provider Cascading Fetch:
      // MUST immediately fetch and populate ONLY that provider's models & voices
      const [llmRes, sttRes, ttsRes, voiceRes] = await Promise.all([
        fetchProviderModels(newProvider, "llm"),
        fetchProviderModels(newProvider, "stt"),
        fetchProviderModels(newProvider, "tts"),
        fetchProviderVoices(newProvider)
      ]);

      const cleanSttRes = sttRes.filter((m) => !m.id.toLowerCase().includes("tts") && !m.id.toLowerCase().includes("speech"));

      setLlmModels(llmRes);
      setSttModels(cleanSttRes);
      setTtsModels(ttsRes);
      setTtsVoices(voiceRes);

      // 2. Auto-Reset on Provider Switch:
      // Reset selected LLM, STT model, TTS model, and Voice IDs to valid defaults
      // from the newly fetched provider list. Never persist incompatible IDs!
      const nextLlmModel = llmRes.length > 0 ? llmRes[0].id : "";
      const nextSttModel = cleanSttRes.length > 0 ? cleanSttRes[0].id : "";
      const nextTtsModel = ttsRes.length > 0 ? ttsRes[0].id : "";

      let nextVoiceEn = "";
      let nextVoiceAr = "";
      let nextTtsProvider = newProvider;

      if (useEdgeTtsFallback) {
        nextTtsProvider = "edge_tts";
        let evList = edgeTtsVoices;
        if (evList.length === 0) {
          evList = await fetchProviderVoices("edge_tts");
          setEdgeTtsVoices(evList);
        }
        const edgeEn = evList.filter((v) => v.language.toLowerCase().startsWith("en"));
        const edgeAr = evList.filter((v) => v.language.toLowerCase().startsWith("ar"));
        nextVoiceEn = edgeEn[0]?.id || "en-US-JennyNeural";
        nextVoiceAr = edgeAr[0]?.id || "ar-SA-HamedNeural";
      } else {
        const enV = voiceRes.filter(
          (v) =>
            v.language.toLowerCase().startsWith("en") ||
            v.language.toLowerCase() === "multilingual" ||
            v.language === "all"
        );
        const arV = voiceRes.filter(
          (v) =>
            v.language.toLowerCase().startsWith("ar") ||
            v.language.toLowerCase() === "multilingual" ||
            v.language === "all"
        );
        nextVoiceEn = enV[0]?.id || "";
        nextVoiceAr = arV[0]?.id || "";
      }

      setSettings((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          llm_provider: newProvider,
          llm_model: nextLlmModel,
          stt_provider: nextSttModel ? newProvider : "",
          stt_model: nextSttModel,
          tts_provider: nextTtsProvider,
          tts_model: nextTtsModel,
          tts_voice_en: nextVoiceEn,
          tts_voice_ar: nextVoiceAr,
          voice_provider: newProvider,
          voice_model: "",
        };
      });
    } catch (err) {
      console.error("Error cascading provider models and voices:", err);
    } finally {
      setCascadingLoading(false);
    }
  };

  // Handle explicit toggle for Microsoft Edge TTS fallback
  const handleToggleEdgeTtsFallback = async (checked: boolean) => {
    if (!settings) return;
    setUseEdgeTtsFallback(checked);

    if (checked) {
      let evList = edgeTtsVoices;
      if (evList.length === 0) {
        evList = await fetchProviderVoices("edge_tts");
        setEdgeTtsVoices(evList);
      }
      const edgeEn = evList.filter((v) => v.language.toLowerCase().startsWith("en"));
      const edgeAr = evList.filter((v) => v.language.toLowerCase().startsWith("ar"));
      setSettings((prev) =>
        prev
          ? {
            ...prev,
            tts_provider: "edge_tts",
            tts_voice_en: edgeEn[0]?.id || "en-US-JennyNeural",
            tts_voice_ar: edgeAr[0]?.id || "ar-SA-HamedNeural",
          }
          : null
      );
    } else {
      const activeProv = settings.llm_provider;
      const enV = ttsVoices.filter(
        (v) =>
          v.language.toLowerCase().startsWith("en") ||
          v.language.toLowerCase() === "multilingual" ||
          v.language === "all"
      );
      const arV = ttsVoices.filter(
        (v) =>
          v.language.toLowerCase().startsWith("ar") ||
          v.language.toLowerCase() === "multilingual" ||
          v.language === "all"
      );
      setSettings((prev) =>
        prev
          ? {
            ...prev,
            tts_provider: activeProv,
            tts_voice_en: enV[0]?.id || "",
            tts_voice_ar: arV[0]?.id || "",
          }
          : null
      );
    }
  };

  // Live Provider Connection Test
  const handleTestConnection = async (provider: string) => {
    setTestingProvider(provider);
    try {
      const res = await testProvider(provider);
      setTestResults((prev) => ({ ...prev, [provider]: res }));
    } catch (err: any) {
      setTestResults((prev) => ({
        ...prev,
        [provider]: {
          provider,
          success: false,
          latency_ms: 0,
          message: err.message || "Test connection failed",
          models_found: 0,
          error: String(err)
        }
      }));
    } finally {
      setTestingProvider(null);
    }
  };

  // Audio preview for voice
  const handlePreviewVoice = async (voiceId: string, lang: string) => {
    if (!voiceId) return;
    unlockBrowserAudio();
    setTestingAudioVoice(voiceId);
    try {
      const sampleText = lang === "ar"
        ? "مرحباً بكم في منصة فويس راج، المساعد الصوتي والمعرفي الذكي للمؤسسات."
        : "Hello, welcome to VoiceRag, your enterprise multilingual AI assistant.";
      const ttsProv = useEdgeTtsFallback ? "edge_tts" : settings?.tts_provider;
      const blob = await synthesizeSpeech(sampleText, lang, voiceId, ttsProv);
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      audio.onended = () => {
        setTestingAudioVoice(null);
        URL.revokeObjectURL(audioUrl);
      };
      audio.onerror = (err) => {
        console.error("Audio preview error:", err);
        setTestingAudioVoice(null);
        URL.revokeObjectURL(audioUrl);
      };
      await audio.play().catch((playErr) => {
        console.warn("Audio preview playback was prevented by browser:", playErr);
        setTestingAudioVoice(null);
      });
    } catch (err) {
      console.error(err);
      setTestingAudioVoice(null);
    }
  };

  // Save Settings
  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    setSaveSuccess(false);
    try {
      await updateSettings(settings);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading || !settings) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-950">
        <Loader2 className="animate-spin text-indigo-500" size={32} />
      </div>
    );
  }

  const activeProvider = settings.llm_provider || "openai";
  const activeProviderObj = AI_PROVIDERS.find((p) => p.id === activeProvider);

  // Active voice options (Edge voices when fallback toggle is on, or active provider voices)
  const availableVoices = useEdgeTtsFallback ? edgeTtsVoices : ttsVoices;
  const enVoices = availableVoices.filter(
    (v) =>
      v.language.toLowerCase().startsWith("en") ||
      v.language.toLowerCase() === "multilingual" ||
      v.language === "all"
  );
  const arVoices = availableVoices.filter(
    (v) =>
      v.language.toLowerCase().startsWith("ar") ||
      v.language.toLowerCase() === "multilingual" ||
      v.language === "all"
  );

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100">
      {/* Top Navbar */}
      <div className="sticky top-0 z-30 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="p-2 rounded-xl text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            {direction === "rtl" ? <ArrowRight size={18} /> : <ArrowLeft size={18} />}
          </Link>
          <div className="flex items-center gap-2">
            <Sliders size={20} className="text-indigo-500" />
            <h1 className="text-lg font-semibold tracking-tight">
              {language === "ar" ? "إعدادات المزودين والنماذج الذكية" : "AI Provider & Model Configuration"}
            </h1>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-medium shadow-sm shadow-indigo-600/30 transition active:scale-95 cursor-pointer"
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          <span>{saveSuccess ? (language === "ar" ? "تم الحفظ بنجاح!" : "Saved!") : (language === "ar" ? "حفظ التغييرات" : "Save Changes")}</span>
        </button>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        {/* Section 1: Connected Providers Status & Dynamic Discovery */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Cpu size={16} className="text-indigo-500" />
              <span>{language === "ar" ? "المزودون المعتمدون والاكتشاف الحي" : "Registered Providers & Dynamic Discovery"}</span>
            </h2>
            <button
              onClick={loadData}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-indigo-500 transition cursor-pointer"
            >
              <RotateCw size={12} />
              <span>{language === "ar" ? "تحديث الاكتشاف" : "Refresh Discovery"}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {providers.map((p) => {
              const test = testResults[p.provider];
              const isTesting = testingProvider === p.provider;

              return (
                <div
                  key={p.provider}
                  className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 space-y-3 shadow-xs"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">{p.name}</h3>
                      <div className="flex gap-1.5 mt-1">
                        {p.supported_capabilities.map((cap) => (
                          <span
                            key={cap}
                            className="px-2 py-0.5 text-[10px] font-mono uppercase bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded-md"
                          >
                            {cap}
                          </span>
                        ))}
                      </div>
                    </div>
                    <span
                      className={`px-2.5 py-1 text-xs font-medium rounded-full flex items-center gap-1.5 ${p.is_configured
                          ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-400"
                        }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${p.is_configured ? "bg-emerald-500" : "bg-slate-400"}`} />
                      {p.is_configured ? (language === "ar" ? "جاهز" : "Configured") : (language === "ar" ? "غير مهيأ" : "No Key")}
                    </span>
                  </div>

                  {/* Test Connection Button & Result */}
                  <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between">
                    <button
                      onClick={() => handleTestConnection(p.provider)}
                      disabled={isTesting || !p.is_configured}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-slate-750 disabled:opacity-40 text-slate-700 dark:text-slate-300 rounded-xl text-xs font-medium transition cursor-pointer"
                    >
                      {isTesting ? <Loader2 size={12} className="animate-spin text-indigo-500" /> : <Play size={12} />}
                      <span>{language === "ar" ? "اختبار الاتصال الحي" : "Test Live Connection"}</span>
                    </button>

                    {test && (
                      <span
                        className={`text-xs font-medium flex items-center gap-1 ${test.success ? "text-emerald-500" : "text-red-500"
                          }`}
                      >
                        {test.success ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
                        <span>{test.latency_ms}ms ({test.models_found} {language === "ar" ? "نماذج" : "models"})</span>
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Section 2: Unified Strict Provider-Dependent Configuration Flow */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-6 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Layers size={16} className="text-indigo-500" />
                <span>{language === "ar" ? "المزود النشط والتهيئة المعتمدة عليه" : "Unified Active AI Provider & Model Suite"}</span>
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {language === "ar"
                  ? "اختيار المزود النشط يستدعي حصرياً نماذج المحادثة والنطق والأصوات الخاصة بهذا المزود مع إعادة تعيين تلقائية متوافقة."
                  : "Selecting an Active Provider cascades strictly to its LLM, STT, and TTS models with zero cross-provider leakage."}
              </p>
            </div>

            {cascadingLoading && (
              <span className="flex items-center gap-1.5 text-xs text-indigo-600 dark:text-indigo-400 font-medium bg-indigo-50 dark:bg-indigo-950/50 px-2.5 py-1 rounded-lg">
                <Loader2 size={13} className="animate-spin" />
                <span>{language === "ar" ? "جاري تحديث النماذج..." : "Fetching models..."}</span>
              </span>
            )}
          </div>

          {/* Unified Active AI Provider Selector */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
              {language === "ar" ? "اختر المزود النشط للنظام:" : "Select Active AI Provider:"}
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {AI_PROVIDERS.map((p) => {
                const isSelected = activeProvider === p.id;
                const provInfo = providers.find((pr) => pr.provider === p.id);
                const isConfigured = provInfo?.is_configured ?? false;
                const Icon = p.icon;

                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => handleActiveProviderChange(p.id)}
                    className={`relative text-start p-3.5 rounded-2xl border transition-all cursor-pointer ${isSelected
                        ? "bg-indigo-50/70 dark:bg-indigo-950/40 border-indigo-500 shadow-xs ring-2 ring-indigo-500/20"
                        : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                      }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className={`p-2 rounded-xl ${isSelected ? "bg-indigo-600 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"}`}>
                        <Icon size={16} />
                      </div>
                      <span
                        className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${isConfigured
                            ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/60"
                            : "bg-slate-100 dark:bg-slate-800 text-slate-400"
                          }`}
                      >
                        {isConfigured ? (language === "ar" ? "مهيأ" : "Ready") : (language === "ar" ? "بدون مفتاح" : "No Key")}
                      </span>
                    </div>
                    <div className="font-semibold text-xs text-slate-900 dark:text-slate-100">{p.name}</div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1">{p.tagline}</div>
                    {isSelected && (
                      <div className="absolute top-2.5 end-2.5">
                        <span className="flex h-2 w-2 relative">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-600"></span>
                        </span>
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Cascaded Dependent Models Grid */}
          <div className="pt-4 border-t border-slate-100 dark:border-slate-800/80 grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 1. LLM Chat Model */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Sparkles size={14} className="text-indigo-500" />
                  <span>{language === "ar" ? "نموذج المحادثة الرئيسي (LLM)" : "Primary LLM Chat Model"}</span>
                </span>
                <span className="text-[10px] uppercase font-mono text-indigo-500">{activeProvider}</span>
              </label>

              <select
                value={settings.llm_model}
                onChange={(e) => setSettings({ ...settings, llm_model: e.target.value })}
                className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 truncate"
              >
                {llmModels.length === 0 ? (
                  <option value={settings.llm_model}>{settings.llm_model || "No LLM models found"}</option>
                ) : (
                  llmModels.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name || m.id} {m.context_window ? `(${Math.round(m.context_window / 1000)}k ctx)` : ""}
                    </option>
                  ))
                )}
              </select>
            </div>

            {/* 2. STT Transcription Model */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Mic size={14} className="text-blue-500" />
                  <span>{language === "ar" ? "نموذج تحويل الصوت إلى نص (STT)" : "Speech-to-Text (STT) Model"}</span>
                </span>
                <span className="text-[10px] uppercase font-mono text-blue-500">{activeProvider}</span>
              </label>

              {sttModels.length > 0 ? (
                <select
                  value={settings.stt_model}
                  onChange={(e) => setSettings({ ...settings, stt_model: e.target.value })}
                  className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  {sttModels.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name || m.id}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="w-full text-xs bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/80 rounded-xl px-3 py-2 text-slate-400 italic flex items-center gap-1.5">
                  <Info size={13} className="text-slate-400 shrink-0" />
                  <span>
                    {language === "ar"
                      ? `المزود ${activeProviderObj?.name || activeProvider} لا يقدم نماذج STT مباشرة.`
                      : `No native STT models available for ${activeProviderObj?.name || activeProvider}.`}
                  </span>
                </div>
              )}
            </div>

            {/* 3. TTS Model (if provider offers dedicated TTS models) */}
            {ttsModels.length > 0 && !useEdgeTtsFallback && (
              <div className="space-y-2 md:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <Volume2 size={14} className="text-emerald-500" />
                  <span>{language === "ar" ? "نموذج توليد الصوت (TTS Audio Model)" : "Text-to-Speech (TTS) Engine Model"}</span>
                </label>
                <select
                  value={settings.tts_model || ttsModels[0]?.id}
                  onChange={(e) => setSettings({ ...settings, tts_model: e.target.value })}
                  className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  {ttsModels.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name || m.id}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Edge TTS Fast Mode Toggle */}
          <div className="p-4 bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-2xl space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useEdgeTtsFallback}
                  onChange={(e) => handleToggleEdgeTtsFallback(e.target.checked)}
                  className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                />
                <span>{language === "ar" ? "استخدام Edge TTS للصوت فائق السرعة (الوضع الأساسي/السريع)" : "Use Edge TTS for Low-Latency Voice (Primary/Fast Mode)"}</span>
              </label>

              <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                {useEdgeTtsFallback ? (language === "ar" ? "فائق السرعة · ~300ms" : "Fast Mode · ~300ms") : (language === "ar" ? "معطل" : "Provider Default")}
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 ps-6">
              {language === "ar"
                ? "يستخدم تدفق Microsoft Edge TTS فائق السرعة مباشرة (~300 مللي ثانية، بدون تكلفة إضافية) للجلسات الصوتية الحية، متجاوزاً نماذج المعاينة الأبطأ."
                : "Directly uses ultra-fast Microsoft Edge TTS streaming (~300ms latency, zero API cost) for live voice output, bypassing slower provider preview TTS."}
            </p>
          </div>

          {/* Voice Selection Section (English & Arabic) */}
          <div className="space-y-4 pt-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Volume2 size={14} className="text-emerald-500" />
                <span>
                  {useEdgeTtsFallback
                    ? (language === "ar" ? "أصوات Microsoft Edge TTS النشطة:" : "Microsoft Edge TTS Neural Voices:")
                    : (language === "ar"
                      ? `أصوات ${activeProviderObj?.name || activeProvider} الأصلية:`
                      : `${activeProviderObj?.name || activeProvider} Native Voices:`)}
                </span>
              </h3>
            </div>

            {/* Zero voices notice when provider has no native voices and fallback is off */}
            {!useEdgeTtsFallback && availableVoices.length === 0 && (
              <div className="p-3 bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-300 rounded-xl text-xs flex items-center gap-2">
                <AlertCircle size={15} className="shrink-0 text-amber-600" />
                <span>
                  {language === "ar"
                    ? `المزود ${activeProviderObj?.name || activeProvider} لا يوفر أصوات توليد كلام مدمجة. يرجى تفعيل خيار "استخدام Microsoft Edge TTS كبديل للصوت" أعلاه للاستماع للإجابات.`
                    : `${activeProviderObj?.name || activeProvider} does not provide native speech synthesis models. Turn ON "Use Microsoft Edge TTS as Fallback" above for voice output.`}
                </span>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* English Voice Selector */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  {language === "ar" ? "الصوت الإنجليزي (English Voice)" : "English Neural Voice (TTS)"}
                </label>
                <div className="flex gap-2">
                  <select
                    value={settings.tts_voice_en}
                    onChange={(e) => setSettings({ ...settings, tts_voice_en: e.target.value })}
                    disabled={enVoices.length === 0}
                    className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
                  >
                    {enVoices.length > 0 ? (
                      enVoices.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.name} {v.gender ? `(${v.gender})` : ""}
                        </option>
                      ))
                    ) : (
                      <option value="" disabled>
                        {language === "ar" ? "لا توجد أصوات إنجليزية متاحة لهذا المزود" : "No English voices available for this provider"}
                      </option>
                    )}
                  </select>
                  <button
                    type="button"
                    onClick={() => handlePreviewVoice(settings.tts_voice_en, "en")}
                    disabled={!settings.tts_voice_en || testingAudioVoice === settings.tts_voice_en}
                    className="p-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl text-xs disabled:opacity-40 transition cursor-pointer"
                    title="Listen preview"
                  >
                    {testingAudioVoice === settings.tts_voice_en ? <Loader2 size={14} className="animate-spin text-emerald-500" /> : <Play size={14} />}
                  </button>
                </div>
              </div>

              {/* Arabic Voice Selector */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  {language === "ar" ? "الصوت العربي العصبي (Arabic Voice)" : "Arabic Neural Voice (TTS)"}
                </label>
                <div className="flex gap-2">
                  <select
                    value={settings.tts_voice_ar}
                    onChange={(e) => setSettings({ ...settings, tts_voice_ar: e.target.value })}
                    disabled={arVoices.length === 0}
                    className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
                  >
                    {arVoices.length > 0 ? (
                      arVoices.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.name} {v.gender ? `(${v.gender})` : ""}
                        </option>
                      ))
                    ) : (
                      <option value="" disabled>
                        {language === "ar" ? "لا توجد أصوات عربية متاحة لهذا المزود" : "No Arabic voices available for this provider"}
                      </option>
                    )}
                  </select>
                  <button
                    type="button"
                    onClick={() => handlePreviewVoice(settings.tts_voice_ar, "ar")}
                    disabled={!settings.tts_voice_ar || testingAudioVoice === settings.tts_voice_ar}
                    className="p-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl text-xs disabled:opacity-40 transition cursor-pointer"
                    title="استماع للعينة"
                  >
                    {testingAudioVoice === settings.tts_voice_ar ? <Loader2 size={14} className="animate-spin text-emerald-500" /> : <Play size={14} />}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Smart Routing & Fallback */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-5 shadow-xs">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Radio size={16} className="text-indigo-500" />
            <span>{language === "ar" ? "التوجيه الذكي التلقائي واستراتيجية التراجع" : "Smart Auto Router & Fallback Strategy"}</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                {language === "ar" ? "استراتيجية التوجيه (Routing Strategy)" : "Routing Strategy"}
              </label>
              <select
                value={settings.routing_strategy}
                onChange={(e) => setSettings({ ...settings, routing_strategy: e.target.value })}
                className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="smart_auto">Smart Auto Router (Dynamic Intent & Workload)</option>
                <option value="balanced">Balanced (Optimal Cost & Intelligence)</option>
                <option value="low_cost">Low Cost (Cheapest Adequate Model)</option>
                <option value="high_quality">High Quality (Flagship Reasoning Models)</option>
                <option value="manual">Manual (Strictly Selected Model)</option>
              </select>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 cursor-pointer">
                  {language === "ar" ? "التراجع التلقائي عند انقطاع المزود" : "Automatic Circuit-Breaker Fallback"}
                </label>
                <input
                  type="checkbox"
                  checked={settings.fallback_enabled}
                  onChange={(e) => setSettings({ ...settings, fallback_enabled: e.target.checked })}
                  className="rounded text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                />
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                {language === "ar"
                  ? "عند حدوث خطأ أو تجاوز حد الاستهلاك لدى المزود الرئيسي، يتم التراجع تلقائياً للمزود الاحتياطي."
                  : "If primary provider fails or rate-limits, requests seamlessly route to secondary fallback."}
              </p>
            </div>
          </div>
        </div>

        {/* Section 4: Hybrid RAG Parameters */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-5 shadow-xs">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Shield size={16} className="text-indigo-500" />
            <span>{language === "ar" ? "معايير استرجاع المعرفة الهجين (Hybrid RAG)" : "Hybrid RAG & Grounding Parameters"}</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>{language === "ar" ? "حد الامتناع عند نقص المعلومات" : "Similarity Threshold"}</span>
                <span className="font-mono text-indigo-500">{settings.similarity_threshold}</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="0.9"
                step="0.05"
                value={settings.similarity_threshold}
                onChange={(e) => setSettings({ ...settings, similarity_threshold: parseFloat(e.target.value) })}
                className="w-full"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>{language === "ar" ? "عدد المقاطع المسترجعة (Top K)" : "Top K Retrieved Chunks"}</span>
                <span className="font-mono text-indigo-500">{settings.top_k}</span>
              </div>
              <input
                type="range"
                min="1"
                max="15"
                step="1"
                value={settings.top_k}
                onChange={(e) => setSettings({ ...settings, top_k: parseInt(e.target.value) })}
                className="w-full"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>{language === "ar" ? "وزن البحث الشعاعي مقابل الكلمات (Alpha)" : "Dense vs Sparse Weight (Alpha)"}</span>
                <span className="font-mono text-indigo-500">{settings.hybrid_alpha}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={settings.hybrid_alpha}
                onChange={(e) => setSettings({ ...settings, hybrid_alpha: parseFloat(e.target.value) })}
                className="w-full"
              />
            </div>
          </div>
        </div>

        {/* Section 5: System Prompts */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-4 shadow-xs">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {language === "ar" ? "توجيهات النظام (System Prompts)" : "System Prompts"}
            </h2>
            <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl text-xs">
              <button
                type="button"
                onClick={() => setPromptTab("en")}
                className={`px-3 py-1 rounded-lg font-medium transition cursor-pointer ${promptTab === "en" ? "bg-white dark:bg-slate-900 text-indigo-600 shadow-xs" : "text-slate-500"
                  }`}
              >
                English
              </button>
              <button
                type="button"
                onClick={() => setPromptTab("ar")}
                className={`px-3 py-1 rounded-lg font-medium transition cursor-pointer ${promptTab === "ar" ? "bg-white dark:bg-slate-900 text-indigo-600 shadow-xs" : "text-slate-500"
                  }`}
              >
                العربية
              </button>
            </div>
          </div>

          {promptTab === "en" ? (
            <textarea
              rows={4}
              value={settings.system_prompt_en}
              onChange={(e) => setSettings({ ...settings, system_prompt_en: e.target.value })}
              className="w-full text-xs font-mono p-3.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          ) : (
            <textarea
              dir="rtl"
              rows={4}
              value={settings.system_prompt_ar}
              onChange={(e) => setSettings({ ...settings, system_prompt_ar: e.target.value })}
              className="w-full text-xs font-mono p-3.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          )}
        </div>
      </div>
    </div>
  );
}
