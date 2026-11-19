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
  synthesizeSpeech
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
  Loader2
} from "lucide-react";

export default function SettingsPage() {
  const { language, direction } = useApp();
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [settings, setSettings] = useState<AISettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Dynamic Models and Voices for dropdowns
  const [llmModels, setLlmModels] = useState<ModelInfo[]>([]);
  const [sttModels, setSttModels] = useState<ModelInfo[]>([]);
  const [ttsVoices, setTtsVoices] = useState<VoiceInfo[]>([]);
  const [voiceModels, setVoiceModels] = useState<ModelInfo[]>([]);

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
      setSettings(activeSettings);

      // Load models for current active providers
      if (activeSettings.llm_provider) {
        const models = await fetchProviderModels(activeSettings.llm_provider, "llm");
        setLlmModels(models);
      }
      if (activeSettings.stt_provider) {
        const models = await fetchProviderModels(activeSettings.stt_provider, "stt");
        setSttModels(models);
      }
      if (activeSettings.tts_provider) {
        const voices = await fetchProviderVoices(activeSettings.tts_provider);
        setTtsVoices(voices);
      }
      if (activeSettings.voice_provider) {
        const models = await fetchProviderModels(activeSettings.voice_provider, "voice");
        setVoiceModels(models);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Update LLM Models when provider changes
  const handleLlmProviderChange = async (newProvider: string) => {
    if (!settings) return;
    setSettings({ ...settings, llm_provider: newProvider });
    const models = await fetchProviderModels(newProvider, "llm");
    setLlmModels(models);
    if (models.length > 0) {
      setSettings((prev) => prev ? { ...prev, llm_provider: newProvider, llm_model: models[0].id } : null);
    }
  };

  // Update TTS Voices when provider changes
  const handleTtsProviderChange = async (newProvider: string) => {
    if (!settings) return;
    setSettings({ ...settings, tts_provider: newProvider });
    const voices = await fetchProviderVoices(newProvider);
    setTtsVoices(voices);
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
    setTestingAudioVoice(voiceId);
    try {
      const sampleText = lang === "ar"
        ? "مرحباً بكم في منصة فويس راج، المساعد الصوتي والمعرفي الذكي للمؤسسات."
        : "Hello, welcome to VoiceRag, your enterprise multilingual AI assistant.";
      const blob = await synthesizeSpeech(sampleText, lang, voiceId, settings?.tts_provider);
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      audio.onended = () => setTestingAudioVoice(null);
      audio.onerror = () => setTestingAudioVoice(null);
      await audio.play();
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
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-medium shadow-sm shadow-indigo-600/30 transition active:scale-95"
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
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-indigo-500 transition"
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
                      className={`px-2.5 py-1 text-xs font-medium rounded-full flex items-center gap-1.5 ${
                        p.is_configured
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
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-slate-750 disabled:opacity-40 text-slate-700 dark:text-slate-300 rounded-xl text-xs font-medium transition"
                    >
                      {isTesting ? <Loader2 size={12} className="animate-spin text-indigo-500" /> : <Play size={12} />}
                      <span>{language === "ar" ? "اختبار الاتصال الحي" : "Test Live Connection"}</span>
                    </button>

                    {test && (
                      <span
                        className={`text-xs font-medium flex items-center gap-1 ${
                          test.success ? "text-emerald-500" : "text-red-500"
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

        {/* Section 2: Capability Model Mapping */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-6 shadow-xs">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Layers size={16} className="text-indigo-500" />
            <span>{language === "ar" ? "تحديد النماذج لكل قدرة بشكل مستقل" : "Independent Capability Assignment"}</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* LLM Chat Model */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Sparkles size={14} className="text-indigo-500" />
                <span>{language === "ar" ? "نموذج المحادثة الرئيسي (LLM)" : "Primary LLM Chat Model"}</span>
              </label>
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={settings.llm_provider}
                  onChange={(e) => handleLlmProviderChange(e.target.value)}
                  className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="openai">OpenAI</option>
                  <option value="gemini">Google Gemini</option>
                  <option value="openrouter">OpenRouter</option>
                  <option value="cheaper_inference">CheaperInference</option>
                </select>
                <select
                  value={settings.llm_model}
                  onChange={(e) => setSettings({ ...settings, llm_model: e.target.value })}
                  className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 truncate"
                >
                  {llmModels.length === 0 ? (
                    <option value={settings.llm_model}>{settings.llm_model}</option>
                  ) : (
                    llmModels.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))
                  )}
                </select>
              </div>
            </div>

            {/* STT Transcription Model */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Mic size={14} className="text-blue-500" />
                <span>{language === "ar" ? "نموذج تحويل الصوت إلى نص (STT)" : "Speech-to-Text (STT) Model"}</span>
              </label>
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={settings.stt_provider}
                  onChange={(e) => setSettings({ ...settings, stt_provider: e.target.value })}
                  className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="openai">OpenAI (Whisper)</option>
                </select>
                <select
                  value={settings.stt_model}
                  onChange={(e) => setSettings({ ...settings, stt_model: e.target.value })}
                  className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="whisper-1">whisper-1</option>
                </select>
              </div>
            </div>

            {/* TTS Speech Synthesis (English Voice) */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Volume2 size={14} className="text-emerald-500" />
                <span>{language === "ar" ? "الصوت الإنجليزي (English Voice)" : "English Neural Voice (TTS)"}</span>
              </label>
              <div className="flex gap-2">
                <select
                  value={settings.tts_voice_en}
                  onChange={(e) => setSettings({ ...settings, tts_voice_en: e.target.value })}
                  className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="en-US-JennyNeural">Jenny (US - Female)</option>
                  <option value="en-US-GuyNeural">Guy (US - Male)</option>
                  <option value="en-US-AriaNeural">Aria (US - Expressive)</option>
                  <option value="en-GB-SoniaNeural">Sonia (UK - Refined)</option>
                </select>
                <button
                  type="button"
                  onClick={() => handlePreviewVoice(settings.tts_voice_en, "en")}
                  disabled={testingAudioVoice === settings.tts_voice_en}
                  className="p-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-300 rounded-xl text-xs"
                  title="Listen preview"
                >
                  {testingAudioVoice === settings.tts_voice_en ? <Loader2 size={14} className="animate-spin text-emerald-500" /> : <Play size={14} />}
                </button>
              </div>
            </div>

            {/* TTS Speech Synthesis (Arabic Voice) */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Volume2 size={14} className="text-emerald-500" />
                <span>{language === "ar" ? "الصوت العربي العصبي (Arabic Voice)" : "Arabic Neural Voice (TTS)"}</span>
              </label>
              <div className="flex gap-2">
                <select
                  value={settings.tts_voice_ar}
                  onChange={(e) => setSettings({ ...settings, tts_voice_ar: e.target.value })}
                  className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="ar-SA-HamedNeural">حامد (السعودية - فصحى طبيعية)</option>
                  <option value="ar-SA-ZariyahNeural">زارية (السعودية - دافئة واضحة)</option>
                  <option value="ar-EG-SalmaNeural">سلمى (مصر - واضحة وممتازة)</option>
                  <option value="ar-EG-ShakirNeural">شاكر (مصر - وقور واحترافي)</option>
                  <option value="ar-AE-FatimaNeural">فاطمة (الإمارات - راقية)</option>
                </select>
                <button
                  type="button"
                  onClick={() => handlePreviewVoice(settings.tts_voice_ar, "ar")}
                  disabled={testingAudioVoice === settings.tts_voice_ar}
                  className="p-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-300 rounded-xl text-xs"
                  title="استماع للعينة"
                >
                  {testingAudioVoice === settings.tts_voice_ar ? <Loader2 size={14} className="animate-spin text-emerald-500" /> : <Play size={14} />}
                </button>
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
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  {language === "ar" ? "التراجع التلقائي عند انقطاع المزود" : "Automatic Circuit-Breaker Fallback"}
                </label>
                <input
                  type="checkbox"
                  checked={settings.fallback_enabled}
                  onChange={(e) => setSettings({ ...settings, fallback_enabled: e.target.checked })}
                  className="rounded text-indigo-600 focus:ring-indigo-500"
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
                className={`px-3 py-1 rounded-lg font-medium transition ${
                  promptTab === "en" ? "bg-white dark:bg-slate-900 text-indigo-600 shadow-xs" : "text-slate-500"
                }`}
              >
                English
              </button>
              <button
                type="button"
                onClick={() => setPromptTab("ar")}
                className={`px-3 py-1 rounded-lg font-medium transition ${
                  promptTab === "ar" ? "bg-white dark:bg-slate-900 text-indigo-600 shadow-xs" : "text-slate-500"
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

