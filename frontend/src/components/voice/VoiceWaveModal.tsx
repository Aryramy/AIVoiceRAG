"use client";

import React, { useState, useEffect, useRef } from "react";
import { useApp } from "@/context/AppContext";
import { sendMessage, synthesizeSpeech, transcribeAudio, createConversation } from "@/lib/api";
import { Mic, MicOff, X, Radio, Volume2, Square, Sparkles, AlertCircle, RefreshCw } from "lucide-react";

type VoiceState = "idle" | "listening" | "processing" | "speaking" | "interrupted";

export function VoiceWaveModal() {
  const {
    voiceModalOpen,
    setVoiceModalOpen,
    language,
    activeConversationId,
    setActiveConversationId,
    activeKbId,
    refreshConversations
  } = useApp();

  const [state, setState] = useState<VoiceState>("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [assistantText, setAssistantText] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [useDirectMode, setUseDirectMode] = useState(false);
  const [isDirectRecording, setIsDirectRecording] = useState(false);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Synchronized refs to avoid stale closures in event callbacks
  const latestTranscriptRef = useRef("");
  const stateRef = useRef<VoiceState>("idle");
  const isMutedRef = useRef(false);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    isMutedRef.current = isMuted;
  }, [isMuted]);

  // Check browser speech recognition support
  const hasWebSpeech =
    typeof window !== "undefined" &&
    Boolean((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);

  // Initialize Speech Recognition when modal opens (if in Web Speech mode)
  useEffect(() => {
    if (!voiceModalOpen) {
      // Cleanup when closed
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
        recognitionRef.current = null;
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
      }
      setState("idle");
      setTranscript("");
      setAssistantText("");
      setErrorMessage(null);
      setIsDirectRecording(false);
      return;
    }

    // If Web Speech API is not supported, automatically activate Direct Recording mode
    if (!hasWebSpeech) {
      setUseDirectMode(true);
      return;
    }

    if (useDirectMode) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = language === "ar" ? "ar-SA" : "en-US";

      recognition.onstart = () => {
        setState("listening");
        setErrorMessage(null);
      };

      recognition.onresult = (event: any) => {
        let currentText = "";
        for (let i = 0; i < event.results.length; i++) {
          currentText += event.results[i][0].transcript;
        }
        latestTranscriptRef.current = currentText;
        setTranscript(currentText);
      };

      recognition.onend = async () => {
        const speechText = latestTranscriptRef.current.trim();
        if (speechText && (stateRef.current === "listening" || stateRef.current === "idle")) {
          latestTranscriptRef.current = "";
          await processUserSpeech(speechText);
        } else if (stateRef.current === "listening") {
          setState("idle");
        }
      };

      recognition.onerror = (event: any) => {
        console.error("Speech recognition error:", event.error);
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          setErrorMessage(
            language === "ar"
              ? "تم رفض إذن الوصول إلى الميكروفون. يرجى تفعيل الصلاحية في المتصفح."
              : "Microphone access was denied. Please allow microphone access in browser settings."
          );
        } else if (event.error === "network") {
          setErrorMessage(
            language === "ar"
              ? "تعذر الاتصال بخدمة التعرف على الصوت. تم تفعيل خيار التسجيل المباشر."
              : "Network error with speech recognition. Direct recording mode is available below."
          );
          setUseDirectMode(true);
        }
        setState("idle");
      };

      recognitionRef.current = recognition;
      try {
        recognition.start();
      } catch (e) {
        console.error("Failed to start speech recognition:", e);
      }
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
    };
  }, [voiceModalOpen, language, useDirectMode, hasWebSpeech]);

  // Direct Audio Recording Fallback using MediaRecorder & /api/v1/voice/transcribe
  const startDirectRecording = async () => {
    try {
      setErrorMessage(null);
      if (!navigator.mediaDevices?.getUserMedia) {
        setErrorMessage(
          language === "ar"
            ? "المتصفح لا يدعم التسجيل الصوتي."
            : "MediaDevices recording is not supported in this browser."
        );
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioChunksRef.current = [];

      const mimeType =
        typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";

      const options = mimeType ? { mimeType } : undefined;
      const recorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }
        setIsDirectRecording(false);

        const audioBlob = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || "audio/webm"
        });

        if (audioBlob.size > 500) {
          setState("processing");
          try {
            const res = await transcribeAudio(audioBlob, language);
            if (res.text && res.text.trim()) {
              setTranscript(res.text);
              await processUserSpeech(res.text);
            } else {
              setErrorMessage(
                language === "ar"
                  ? "لم يتم التعرف على أي صوت، يرجى المحاولة مرة أخرى."
                  : "No speech recognized, please try speaking again."
              );
              setState("idle");
            }
          } catch (tErr: any) {
            console.error("Transcribe failed:", tErr);
            setErrorMessage(
              language === "ar"
                ? "فشل تحويل الصوت إلى نص عبر الخادم."
                : "Speech transcription service failed."
            );
            setState("idle");
          }
        } else {
          setState("idle");
        }
      };

      recorder.start(250);
      setIsDirectRecording(true);
      setState("listening");
    } catch (err: any) {
      console.error("getUserMedia error:", err);
      setErrorMessage(
        language === "ar"
          ? "تعذر الوصول للميكروفون. يرجى التأكد من توصيله ومنح الإذن في المتصفح."
          : "Could not access microphone. Please ensure permissions are granted in browser."
      );
      setState("idle");
    }
  };

  const stopDirectRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  };

  // Process User Speech: Auto-create conversation if none exists, send message, synthesize speech
  const processUserSpeech = async (userText: string) => {
    if (!userText.trim()) return;
    setState("processing");

    try {
      let targetConvId = activeConversationId;
      if (!targetConvId) {
        try {
          const titleSnippet = userText.trim().slice(0, 32);
          const title = titleSnippet || (language === "ar" ? "محادثة صوتية" : "Voice Conversation");
          const newConv = await createConversation(title, language);
          targetConvId = newConv.id;
          setActiveConversationId(newConv.id);
          await refreshConversations();
        } catch (convErr: any) {
          console.error("Failed to auto-create conversation in voice mode:", convErr);
          setErrorMessage(
            language === "ar" ? "فشل إنشاء محادثة جديدة" : "Failed to create conversation"
          );
          setState("idle");
          return;
        }
      }

      const res = await sendMessage(targetConvId, userText, activeKbId || undefined, language);
      const reply = res.content || "";
      setAssistantText(reply);
      setState("speaking");
      await refreshConversations();

      // Neural Speech Synthesis
      try {
        const audioBlob = await synthesizeSpeech(reply, language === "ar" ? "ar" : "en");
        if (audioBlob && audioBlob.size > 0) {
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          audioRef.current = audio;

          audio.onended = () => {
            URL.revokeObjectURL(audioUrl);
            audioRef.current = null;
            setState("idle");
            setTranscript("");
            // Restart speech recognition automatically if in Web Speech mode and unmuted
            if (!useDirectMode && recognitionRef.current && !isMutedRef.current) {
              try {
                recognitionRef.current.start();
              } catch (e) {}
            }
          };

          audio.onerror = (e) => {
            console.error("Audio playback error:", e);
            URL.revokeObjectURL(audioUrl);
            audioRef.current = null;
            setState("idle");
          };

          await audio.play();
        } else {
          setState("idle");
        }
      } catch (synthErr) {
        console.error("Speech synthesis failed, text reply preserved:", synthErr);
        setState("idle");
      }
    } catch (err: any) {
      console.error(err);
      setErrorMessage(
        err.message || (language === "ar" ? "فشل توليد الإجابة" : "Failed to generate response")
      );
      setState("idle");
    }
  };

  // Waveform Visualizer
  useEffect(() => {
    if (!voiceModalOpen) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      let strokeColor = "rgba(99, 102, 241, 0.8)";
      let amplitude = 12;
      let freq = 0.02;

      if (state === "listening") {
        strokeColor = "rgba(59, 130, 246, 0.9)";
        amplitude = 26;
        freq = 0.03;
      } else if (state === "processing") {
        strokeColor = "rgba(245, 158, 11, 0.9)";
        amplitude = 9;
        freq = 0.05;
      } else if (state === "speaking") {
        strokeColor = "rgba(34, 197, 94, 0.9)";
        amplitude = 36;
        freq = 0.04;
      }

      for (let wave = 0; wave < 3; wave++) {
        ctx.beginPath();
        ctx.lineWidth = 2.5 - wave * 0.5;
        ctx.strokeStyle = strokeColor;
        ctx.globalAlpha = 0.9 - wave * 0.25;

        for (let x = 0; x < width; x++) {
          const y =
            centerY +
            Math.sin(x * freq + phase + wave * 1.5) *
              amplitude *
              Math.sin(Math.PI * (x / width));
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      phase += 0.05;
      animationId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationId);
  }, [voiceModalOpen, state]);

  // Interrupt Speech
  const handleInterrupt = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    if (isDirectRecording) {
      stopDirectRecording();
    }
    setState("idle");
  };

  // Toggle or retry microphone trigger
  const handleMicToggle = () => {
    if (state === "speaking") {
      handleInterrupt();
      return;
    }

    if (useDirectMode) {
      if (isDirectRecording) {
        stopDirectRecording();
      } else {
        startDirectRecording();
      }
      return;
    }

    // Web Speech API toggle
    if (state === "listening") {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
      setState("idle");
    } else {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.start();
        } catch (e) {
          console.error(e);
        }
      }
    }
  };

  if (!voiceModalOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl p-6 text-center shadow-2xl flex flex-col items-center">
        {/* Close Button */}
        <button
          onClick={() => setVoiceModalOpen(false)}
          className="absolute top-4 end-4 p-2 text-slate-400 hover:text-white rounded-full hover:bg-slate-800 transition cursor-pointer"
        >
          <X size={20} />
        </button>

        {/* Header Indicator */}
        <div className="flex items-center gap-2 mb-4 text-xs text-slate-400">
          <Radio size={14} className="text-indigo-400 animate-pulse" />
          <span className="font-medium tracking-wide uppercase">
            {language === "ar" ? "جلسة صوتية فورية متصلة" : "Live Real-Time Voice Assistant"}
          </span>
        </div>

        {/* Mode Switch Pill */}
        <div className="flex items-center gap-2 mb-2">
          <button
            onClick={() => {
              setErrorMessage(null);
              setUseDirectMode(!useDirectMode);
            }}
            className="flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-medium border transition cursor-pointer bg-slate-800 border-slate-700 text-slate-300 hover:text-white hover:border-slate-600"
          >
            <span>
              {useDirectMode
                ? language === "ar"
                  ? "الوضع: تسجيل ميكروفون مباشر (Whisper)"
                  : "Mode: Direct Mic Recording (Whisper)"
                : language === "ar"
                ? "الوضع: تعرف صوتي مباشر (Web Speech)"
                : "Mode: Web Speech Real-Time"}
            </span>
            <RefreshCw size={11} className="text-indigo-400" />
          </button>
        </div>

        {/* Error / Permission Alert Banner */}
        {errorMessage && (
          <div className="w-full mb-3 px-3.5 py-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center justify-between gap-2 text-start animate-in fade-in">
            <div className="flex items-center gap-2">
              <AlertCircle size={15} className="shrink-0 text-red-400" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="p-1 hover:text-white rounded-md transition cursor-pointer"
            >
              <X size={13} />
            </button>
          </div>
        )}

        {/* Waveform Canvas */}
        <div className="relative w-full h-44 flex items-center justify-center my-2">
          {/* Ambient Glow */}
          <div
            className={`absolute w-36 h-36 rounded-full blur-3xl transition-all duration-700 opacity-30 ${
              state === "listening"
                ? "bg-blue-500 scale-125"
                : state === "speaking"
                ? "bg-emerald-500 scale-150"
                : state === "processing"
                ? "bg-amber-500 scale-90"
                : "bg-indigo-500"
            }`}
          />
          <canvas ref={canvasRef} width={420} height={160} className="relative z-10 w-full h-full" />
        </div>

        {/* Status Caption */}
        <div className="mt-2 mb-2">
          <span
            className={`text-sm font-semibold tracking-wide ${
              state === "listening"
                ? "text-blue-400"
                : state === "processing"
                ? "text-amber-400"
                : state === "speaking"
                ? "text-emerald-400"
                : "text-slate-400"
            }`}
          >
            {state === "listening" &&
              (isDirectRecording
                ? language === "ar"
                  ? "جاري التسجيل الصوتي... اضغط عند الانتهاء"
                  : "Recording audio... Tap mic when finished"
                : language === "ar"
                ? "أستمع إليك الآن..."
                : "Listening...")}
            {state === "processing" &&
              (language === "ar" ? "جاري المعالجة والتفكير..." : "Thinking & generating response...")}
            {state === "speaking" &&
              (language === "ar" ? "يتحدث المساعد..." : "Voice Assistant speaking...")}
            {state === "idle" &&
              (useDirectMode
                ? language === "ar"
                  ? "اضغط على الميكروفون لبدء التسجيل"
                  : "Tap microphone to record voice"
                : language === "ar"
                ? "اضغط على الميكروفون للتحدث"
                : "Tap microphone to speak")}
          </span>
        </div>

        {/* Live Transcript / Response preview */}
        <div className="h-14 flex items-center justify-center px-4 text-xs text-slate-300 max-w-sm line-clamp-2">
          {transcript ? (
            <span className="italic text-slate-200">"{transcript}"</span>
          ) : assistantText ? (
            <span className="text-slate-300">{assistantText.slice(0, 100)}...</span>
          ) : (
            <span className="text-slate-500">
              {language === "ar"
                ? "يمكنك التحدث باللغة العربية أو الإنجليزية بحرية"
                : "Speak freely in English or Arabic"}
            </span>
          )}
        </div>

        {/* Voice Control Buttons */}
        <div className="flex items-center gap-4 mt-6">
          {/* Interrupt Button */}
          {state === "speaking" && (
            <button
              onClick={handleInterrupt}
              className="flex items-center gap-1.5 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-amber-400 rounded-xl text-xs font-medium transition active:scale-95 cursor-pointer"
            >
              <Square size={14} fill="currentColor" />
              <span>{language === "ar" ? "مقاطعة الحديث" : "Interrupt"}</span>
            </button>
          )}

          {/* Main Mic Button */}
          <button
            onClick={handleMicToggle}
            className={`p-3.5 rounded-2xl transition active:scale-95 cursor-pointer ${
              state === "listening" || isDirectRecording
                ? "bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30 animate-pulse"
                : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30"
            }`}
            title={
              useDirectMode
                ? isDirectRecording
                  ? "Stop Recording"
                  : "Record Voice"
                : state === "listening"
                ? "Pause Mic"
                : "Start Mic"
            }
          >
            {state === "listening" || isDirectRecording ? <MicOff size={20} /> : <Mic size={20} />}
          </button>

          {/* End Call Button */}
          <button
            onClick={() => setVoiceModalOpen(false)}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-slate-800 hover:bg-red-600 text-slate-300 hover:text-white rounded-xl text-xs font-medium transition active:scale-95 cursor-pointer"
          >
            <X size={14} />
            <span>{language === "ar" ? "إغلاق" : "Close"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
