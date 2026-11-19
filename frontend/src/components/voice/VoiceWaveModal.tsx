"use client";

import React, { useState, useEffect, useRef } from "react";
import { useApp } from "@/context/AppContext";
import { sendMessage, synthesizeSpeech } from "@/lib/api";
import { Mic, MicOff, X, Radio, Volume2, Square, Sparkles } from "lucide-react";

type VoiceState = "idle" | "listening" | "processing" | "speaking" | "interrupted";

export function VoiceWaveModal() {
  const { voiceModalOpen, setVoiceModalOpen, language, activeConversationId, activeKbId, refreshConversations } = useApp();
  const [state, setState] = useState<VoiceState>("idle");
  const [isMuted, setIsMuted] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [assistantText, setAssistantText] = useState("");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<any>(null);

  // Initialize Speech Recognition (Web Speech API)
  useEffect(() => {
    if (!voiceModalOpen) {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setState("idle");
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = language === "ar" ? "ar-SA" : "en-US";

      recognition.onstart = () => {
        setState("listening");
      };

      recognition.onresult = (event: any) => {
        let currentText = "";
        for (let i = 0; i < event.results.length; i++) {
          currentText += event.results[i][0].transcript;
        }
        setTranscript(currentText);
      };

      recognition.onend = async () => {
        if (transcript.trim() && state === "listening") {
          await processUserSpeech(transcript);
        } else if (state === "listening") {
          setState("idle");
        }
      };

      recognition.onerror = () => {
        setState("idle");
      };

      recognitionRef.current = recognition;
      try {
        recognition.start();
      } catch (e) {
        console.error(e);
      }
    } else {
      // Fallback
      setState("listening");
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [voiceModalOpen, language]);

  // Handle Assistant Generation & Speech Playback
  const processUserSpeech = async (userText: string) => {
    if (!userText.trim()) return;
    setState("processing");
    try {
      if (!activeConversationId) return;
      const res = await sendMessage(activeConversationId, userText, activeKbId || undefined, language);
      const reply = res.content || "";
      setAssistantText(reply);
      setState("speaking");
      await refreshConversations();

      // Synthesize neural speech audio
      const audioBlob = await synthesizeSpeech(reply, language === "ar" ? "ar" : "en");
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onended = () => {
        setState("listening");
        setTranscript("");
        URL.revokeObjectURL(audioUrl);
        // Resume listening automatically
        if (recognitionRef.current) {
          try {
            recognitionRef.current.start();
          } catch (e) {}
        }
      };

      await audio.play();
    } catch (err) {
      console.error(err);
      setState("idle");
    }
  };

  // Canvas Waveform Animation
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

      // Color scheme based on state
      let strokeColor = "rgba(99, 102, 241, 0.8)"; // Indigo default
      let amplitude = 12;
      let freq = 0.02;

      if (state === "listening") {
        strokeColor = "rgba(59, 130, 246, 0.9)"; // Blue
        amplitude = 25;
        freq = 0.03;
      } else if (state === "processing") {
        strokeColor = "rgba(245, 158, 11, 0.9)"; // Orange
        amplitude = 8;
        freq = 0.05;
      } else if (state === "speaking") {
        strokeColor = "rgba(34, 197, 94, 0.9)"; // Emerald
        amplitude = 35;
        freq = 0.04;
      }

      // Draw multi-layered sine waves
      for (let wave = 0; wave < 3; wave++) {
        ctx.beginPath();
        ctx.lineWidth = 2.5 - wave * 0.5;
        ctx.strokeStyle = strokeColor;
        ctx.globalAlpha = 0.9 - wave * 0.25;

        for (let x = 0; x < width; x++) {
          const y = centerY + Math.sin(x * freq + phase + wave * 1.5) * amplitude * Math.sin(Math.PI * (x / width));
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

  const handleInterrupt = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setState("listening");
    if (recognitionRef.current) {
      try {
        recognitionRef.current.start();
      } catch (e) {}
    }
  };

  if (!voiceModalOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl p-6 text-center shadow-2xl flex flex-col items-center">
        {/* Close Button */}
        <button
          onClick={() => setVoiceModalOpen(false)}
          className="absolute top-4 end-4 p-2 text-slate-400 hover:text-white rounded-full hover:bg-slate-800 transition"
        >
          <X size={20} />
        </button>

        {/* Header Indicator */}
        <div className="flex items-center gap-2 mb-6 text-xs text-slate-400">
          <Radio size={14} className="text-indigo-400 animate-pulse" />
          <span className="font-medium tracking-wide uppercase">
            {language === "ar" ? "جلسة صوتية فورية متصلة" : "Live Real-Time Voice Assistant"}
          </span>
        </div>

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
        <div className="mt-4 mb-2">
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
            {state === "listening" && (language === "ar" ? "أستمع إليك الآن..." : "Listening...")}
            {state === "processing" && (language === "ar" ? "جاري المعالجة والتفكير..." : "Thinking...")}
            {state === "speaking" && (language === "ar" ? "يتحدث المساعد..." : "Voice Assistant speaking...")}
            {state === "idle" && (language === "ar" ? "اضغط على الميكروفون للتحدث" : "Tap microphone to speak")}
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
              className="flex items-center gap-1.5 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-amber-400 rounded-xl text-xs font-medium transition active:scale-95"
            >
              <Square size={14} fill="currentColor" />
              <span>{language === "ar" ? "مقاطعة الحديث" : "Interrupt"}</span>
            </button>
          )}

          {/* Mute/Unmute Mic Button */}
          <button
            onClick={() => {
              setIsMuted(!isMuted);
              if (recognitionRef.current) {
                if (!isMuted) recognitionRef.current.stop();
                else recognitionRef.current.start();
              }
            }}
            className={`p-3.5 rounded-2xl transition active:scale-95 ${
              isMuted
                ? "bg-red-500/20 text-red-400 border border-red-500/30"
                : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30"
            }`}
            title={isMuted ? "Unmute" : "Mute"}
          >
            {isMuted ? <MicOff size={20} /> : <Mic size={20} />}
          </button>

          {/* End Call Button */}
          <button
            onClick={() => setVoiceModalOpen(false)}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-red-600 hover:bg-red-500 text-white rounded-xl text-xs font-medium transition active:scale-95"
          >
            <X size={14} />
            <span>{language === "ar" ? "إنهاء المحادثة" : "End Call"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
