"use client";

import React, { useState, useEffect, useRef } from "react";
import { useApp } from "@/context/AppContext";
import { streamMessage, synthesizeSpeech, synthesizeSpeechStream, transcribeAudio, createConversation, unlockBrowserAudio } from "@/lib/api";
import { Mic, MicOff, X, Radio, Square, AlertCircle, RefreshCw } from "lucide-react";

type VoiceState = "idle" | "listening" | "processing" | "speaking" | "interrupted";

interface AudioResult {
  audio: HTMLAudioElement;
  url: string;
  cleanup?: () => void;
}

interface QueuedAudio {
  id: number;
  text: string;
  lang: string;
  fetchStarted: boolean;
  promise?: Promise<AudioResult | null>;
}

/**
 * Cleans spoken sentence text before TTS synthesis:
 * Strips citation brackets like [1], [2], [1][2], [1, 2], [1-3],
 * markdown links [text](url) -> text, and residual formatting (*, #, _, `, ~, >)
 * so citation numbers and symbols are never spoken aloud.
 */
export function cleanVoiceText(text: string): string {
  if (!text) return "";
  // 1. Strip markdown links [label](url) -> label
  let cleaned = text.replace(/\[([^\]]+)\]\([^\)]+\)/g, "$1");
  // 2. Strip citation markers like [1], [2], [1, 2], [1][2], [1-3]
  cleaned = cleaned.replace(/\[\s*\d+(?:\s*[,-]\s*\d+)*\s*\]/g, "");
  // 3. Strip any residual citation brackets like [source 1] or [1.1]
  cleaned = cleaned.replace(/\[\s*(?:source\s*)?\d+(?:\.\d+)?\s*\]/gi, "");
  // 4. Strip residual markdown formatting symbols: *, #, _, `, ~, >
  cleaned = cleaned.replace(/[*#_`~>]/g, "");
  // 5. Fix spaces before punctuation after citation removal
  cleaned = cleaned.replace(/\s+([,.;:!?،۔])/g, "$1");
  // 6. Normalize whitespace
  return cleaned.replace(/\s+/g, " ").trim();
}

/**
 * Extracts the next complete sentence or early clause from the text buffer.
 * If isFirstClause is true: dispatches immediately on the first punctuation mark
 * (. ? ! ؟ , ; ، :) once >= 5 words are received to achieve sub-second TTFA!
 */
function extractNextSentence(
  buffer: string,
  isFirstClause: boolean = false
): { sentence: string; remainder: string } | null {
  const trimmed = buffer.replace(/^\s+/, "");
  if (!trimmed) return null;

  // Clause 1 Early Dispatch: dispatch on first punctuation mark once >= 5 words are received
  if (isFirstClause) {
    const earlyClauseRegex = /([.!?؟۔,;،:]+|\n\n+|\n)/g;
    let match: RegExpExecArray | null;
    while ((match = earlyClauseRegex.exec(trimmed)) !== null) {
      const matchIndex = match.index;
      const matchEnd = matchIndex + match[1].length;
      const candidate = trimmed.slice(0, matchEnd).trim();
      const words = candidate.split(/\s+/).filter(Boolean);
      if (words.length >= 5 && /[\p{L}\p{N}]/u.test(candidate)) {
        const remainder = trimmed.slice(matchEnd);
        return { sentence: candidate, remainder };
      }
    }
  }

  // Standard sentence boundary: [.!?؟۔] or \n\n or \n
  const boundaryRegex = /([.!?؟۔]+|\n\n+|\n)/g;
  let match: RegExpExecArray | null;

  while ((match = boundaryRegex.exec(trimmed)) !== null) {
    const delim = match[1];
    const matchIndex = match.index;
    const matchEnd = matchIndex + delim.length;

    // Check if period is a decimal point (e.g. 3.14 or 2024.1)
    if (delim === ".") {
      const prevChar = matchIndex > 0 ? trimmed[matchIndex - 1] : "";
      const nextChar = matchEnd < trimmed.length ? trimmed[matchEnd] : "";
      if (/\d/.test(prevChar) && (/\d/.test(nextChar) || nextChar === "")) {
        // Decimal number or trailing dot on number
        continue;
      }
      // Common abbreviations
      const prefix = trimmed.slice(0, matchIndex);
      if (/(?:^|\s)(?:Dr|Mr|Mrs|Ms|Prof|Sr|Jr|vs|eg|ie|etc)\b$/i.test(prefix)) {
        continue;
      }
      // Numbered list items at the start (e.g. "1.")
      if (/^\d+$/.test(prefix.trim())) {
        continue;
      }
    }

    const candidate = trimmed.slice(0, matchEnd).trim();
    // Must contain letters or numbers
    if (/[\p{L}\p{N}]/u.test(candidate)) {
      const remainder = trimmed.slice(matchEnd);
      return { sentence: candidate, remainder };
    }
  }

  // Clause boundary fallback for long run-on sentences (> 80 chars without punctuation)
  if (trimmed.length > 80) {
    const clauseRegex = /([,;،:])\s+/g;
    const clauseMatch = clauseRegex.exec(trimmed);
    if (clauseMatch && clauseMatch.index > 20) {
      const cut = clauseMatch.index + 1;
      const candidate = trimmed.slice(0, cut).trim();
      const remainder = trimmed.slice(cut);
      return { sentence: candidate, remainder };
    }
  }

  return null;
}

/**
 * Low-latency streaming TTS fetcher:
 * Connects to /api/v1/voice/synthesize/stream and plays audio/mpeg chunks
 * via MediaSource (MSE) as soon as the first chunk arrives (~300-500ms).
 * Falls back to Blob playback for audio/wav or if MSE is unavailable.
 */
async function fetchAudioStream(
  text: string,
  lang: string,
  signal?: AbortSignal
): Promise<AudioResult | null> {
  try {
    const res = await synthesizeSpeechStream(text, lang, undefined, undefined, signal);
    const contentType = res.headers.get("content-type") || "audio/mpeg";
    const isMpeg = contentType.includes("mpeg") || contentType.includes("mp3");

    // Attempt MSE streaming playback if audio/mpeg is supported
    if (
      isMpeg &&
      typeof window !== "undefined" &&
      window.MediaSource &&
      MediaSource.isTypeSupported("audio/mpeg")
    ) {
      try {
        const mediaSource = new MediaSource();
        const audio = new Audio();
        const msUrl = URL.createObjectURL(mediaSource);
        audio.src = msUrl;
        audio.preload = "auto";

        const msePromise = new Promise<AudioResult>((resolve, reject) => {
          let hasResolved = false;
          const reader = res.body?.getReader();
          if (!reader) {
            reject(new Error("ReadableStream not available"));
            return;
          }

          const onSourceOpen = async () => {
            mediaSource.removeEventListener("sourceopen", onSourceOpen);
            let sourceBuffer: SourceBuffer;
            try {
              sourceBuffer = mediaSource.addSourceBuffer("audio/mpeg");
            } catch (sbErr) {
              reject(sbErr);
              return;
            }

            const chunkQueue: Uint8Array[] = [];
            let isStreamDone = false;

            const pumpBuffer = () => {
              if (mediaSource.readyState !== "open" || sourceBuffer.updating) return;
              if (chunkQueue.length > 0) {
                const nextChunk = chunkQueue.shift()!;
                try {
                  sourceBuffer.appendBuffer(nextChunk as any);
                } catch (appendErr) {
                  console.warn("SourceBuffer append error:", appendErr);
                }
              } else if (isStreamDone && mediaSource.readyState === "open") {
                try {
                  mediaSource.endOfStream();
                } catch (eosErr) { }
              }
            };

            sourceBuffer.addEventListener("updateend", () => {
              if (!hasResolved) {
                hasResolved = true;
                resolve({
                  audio,
                  url: msUrl,
                  cleanup: () => {
                    try { URL.revokeObjectURL(msUrl); } catch { }
                  }
                });
              }
              pumpBuffer();
            });

            sourceBuffer.addEventListener("error", (e) => {
              console.warn("SourceBuffer error:", e);
            });

            try {
              while (true) {
                const { done, value } = await reader.read();
                if (done) {
                  isStreamDone = true;
                  pumpBuffer();
                  break;
                }
                if (value) {
                  chunkQueue.push(value);
                  pumpBuffer();
                }
              }
            } catch (readErr) {
              if (!hasResolved) reject(readErr);
            }
          };

          mediaSource.addEventListener("sourceopen", onSourceOpen);
        });

        const result = await Promise.race([
          msePromise,
          new Promise<null>((_, reject) =>
            setTimeout(() => reject(new Error("MSE timeout")), 1500)
          )
        ]);
        if (result) return result;
      } catch (mseErr) {
        console.warn("MSE streaming fallback to Blob:", mseErr);
      }
    }

    // Direct Blob Fallback for WAV, non-MSE, or MSE fallback
    const arrayBuf = await res.arrayBuffer();
    if (!arrayBuf || arrayBuf.byteLength === 0) return null;
    const blob = new Blob([arrayBuf], { type: contentType.split(";")[0].trim() });
    const blobUrl = URL.createObjectURL(blob);
    const audio = new Audio(blobUrl);
    audio.preload = "auto";
    return {
      audio,
      url: blobUrl,
      cleanup: () => {
        try { URL.revokeObjectURL(blobUrl); } catch { }
      }
    };
  } catch (err) {
    if (signal?.aborted) return null;
    console.warn("fetchAudioStream failed:", err);
    return null;
  }
}

/**
 * Safely closes an AudioContext instance or ref, ensuring:
 * 1. The ref is detached immediately to avoid double-close rejections
 * 2. Checks ctx.state !== "closed"
 * 3. Handles Promise rejection via .catch()
 */
function safeCloseAudioContext(
  ctxRef: React.MutableRefObject<AudioContext | null> | { current: AudioContext | null }
) {
  const ctx = ctxRef.current;
  ctxRef.current = null;
  if (ctx && ctx.state !== "closed") {
    try {
      ctx.close().catch(() => { });
    } catch { }
  }
}

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
  const [infoMessage, setInfoMessage] = useState<string | null>(null);
  const [useDirectMode, setUseDirectMode] = useState(false);
  const [isDirectRecording, setIsDirectRecording] = useState(false);
  const [speechLang, setSpeechLang] = useState<"en" | "ar" | "auto">(
    language === "ar" ? "ar" : "en"
  );

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);
  const vadContextRef = useRef<AudioContext | null>(null);
  const vadAnimRef = useRef<number | null>(null);
  const cooldownTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Synchronized refs to avoid stale closures in event callbacks
  const latestTranscriptRef = useRef("");
  const stateRef = useRef<VoiceState>("idle");
  const isMutedRef = useRef(false);
  const speechLangRef = useRef<"en" | "ar" | "auto">(
    language === "ar" ? "ar" : "en"
  );

  // Keep speechLangRef strictly in sync with speechLang state
  useEffect(() => {
    speechLangRef.current = speechLang;
  }, [speechLang]);

  // Sync default speech language if the app UI is toggled
  useEffect(() => {
    if (voiceModalOpen) {
      const initLang = language === "ar" ? "ar" : "en";
      setSpeechLang(initLang);
      speechLangRef.current = initLang;
    }
  }, [voiceModalOpen, language]);

  // Pipelined TTS Audio Queue & Streaming Refs
  const audioQueueRef = useRef<QueuedAudio[]>([]);
  const sentenceBufferRef = useRef<string>("");
  const generationRef = useRef<number>(0);
  const isPlayingRef = useRef<boolean>(false);
  const isStreamingRef = useRef<boolean>(false);
  const activeObjectUrlsRef = useRef<string[]>([]);
  const sentenceCounterRef = useRef<number>(0);

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

  // Cleanly cancels active direct recording / VAD without triggering leftover onstop callbacks
  const cancelDirectRecording = () => {
    if (vadAnimRef.current) {
      cancelAnimationFrame(vadAnimRef.current);
      vadAnimRef.current = null;
    }
    safeCloseAudioContext(vadContextRef);
    if (mediaRecorderRef.current) {
      try {
        mediaRecorderRef.current.onstop = null;
        mediaRecorderRef.current.ondataavailable = null;
        if (mediaRecorderRef.current.state !== "inactive") {
          mediaRecorderRef.current.stop();
        }
      } catch (e) { }
      mediaRecorderRef.current = null;
    }
    if (mediaStreamRef.current) {
      try {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      } catch (e) { }
      mediaStreamRef.current = null;
    }
    audioChunksRef.current = [];
    setIsDirectRecording(false);
  };

  // Bullet-Proof Interrupt Handling
  const handleInterrupt = () => {
    // Invalidate generation counter immediately so in-flight promises are discarded
    generationRef.current += 1;

    // Clear cooldown timer if active
    if (cooldownTimerRef.current) {
      clearTimeout(cooldownTimerRef.current);
      cooldownTimerRef.current = null;
    }

    // 1. Abort active LLM stream and pending TTS synthesis fetch calls
    if (abortControllerRef.current) {
      try {
        abortControllerRef.current.abort();
      } catch (e) { }
      abortControllerRef.current = null;
    }

    // 2. Stop currently playing audio
    if (audioRef.current) {
      try {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      } catch (e) { }
      audioRef.current = null;
    }

    // 3. Clear audio queue & sentence buffer
    audioQueueRef.current = [];
    sentenceBufferRef.current = "";
    isPlayingRef.current = false;
    isStreamingRef.current = false;

    // 4. Revoke all active object URLs to prevent memory leaks
    activeObjectUrlsRef.current.forEach((u) => {
      try {
        URL.revokeObjectURL(u);
      } catch (e) { }
    });
    activeObjectUrlsRef.current = [];

    // 5. Cleanly cancel direct recording if active & clear VAD
    cancelDirectRecording();

    // 6. Reset state to idle
    setState("idle");
  };

  // Start prefetching up to 2 items (1 active playing + 1 next prefetching)
  const pumpAudioQueue = (gen: number) => {
    if (generationRef.current !== gen) return;

    // Count how many items in the queue have started fetching
    const inFlight = audioQueueRef.current.filter((item) => item.fetchStarted).length;

    // We allow at most 2 items in-flight (1 active + 1 next prefetching) to stop 3x concurrent bursts
    if (inFlight < 2) {
      const nextPending = audioQueueRef.current.find((item) => !item.fetchStarted);
      if (nextPending) {
        nextPending.fetchStarted = true;
        nextPending.promise = fetchAudioStream(
          nextPending.text,
          nextPending.lang,
          abortControllerRef.current?.signal
        );
      }
    }

    playNextInQueue(gen);
  };

  // Zero-gap playback queue consumer
  const playNextInQueue = async (gen: number) => {
    // If an audio is currently playing or generation changed, do not start concurrent playback
    if (isPlayingRef.current || generationRef.current !== gen) {
      return;
    }

    // If audio queue is empty:
    if (audioQueueRef.current.length === 0) {
      // If the LLM is still streaming tokens, remain in current state and wait for next sentence
      if (isStreamingRef.current) {
        return;
      }
      // Both streaming and audio playback are finished: session complete!
      finishVoiceSession(gen);
      return;
    }

    // Ensure the head item is fetching
    const head = audioQueueRef.current[0];
    if (!head.fetchStarted) {
      head.fetchStarted = true;
      head.promise = fetchAudioStream(
        head.text,
        head.lang,
        abortControllerRef.current?.signal
      );
    }

    // Dequeue next synthesized sentence
    const nextItem = audioQueueRef.current.shift()!;
    isPlayingRef.current = true;

    // Immediately pump queue so the NEXT sentence starts prefetching in the background!
    pumpAudioQueue(gen);

    try {
      const result = await (nextItem.promise || Promise.resolve(null));

      // Invalidation check after async fetch
      if (generationRef.current !== gen) {
        if (result?.cleanup) {
          result.cleanup();
        }
        isPlayingRef.current = false;
        return;
      }

      // If synthesis failed (null), skip cleanly and play next queued sentence without crashing!
      if (!result) {
        isPlayingRef.current = false;
        playNextInQueue(gen);
        return;
      }

      const { audio, url, cleanup } = result;
      activeObjectUrlsRef.current.push(url);
      audioRef.current = audio;

      // Mark state as "speaking" as soon as Sentence starts playing!
      setState("speaking");
      setErrorMessage(null);

      // Immediately abort / stop recognition to prevent microphone echo / self-hearing
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) { }
      }
      latestTranscriptRef.current = "";

      audio.onended = () => {
        if (cleanup) {
          cleanup();
        }
        activeObjectUrlsRef.current = activeObjectUrlsRef.current.filter((u) => u !== url);

        if (generationRef.current !== gen) return;

        audioRef.current = null;
        isPlayingRef.current = false;

        // Zero-gap playback: immediately dequeue and play next sentence!
        playNextInQueue(gen);
      };

      audio.onerror = (e) => {
        console.error("Audio playback error on sentence:", e);
        if (cleanup) {
          cleanup();
        }
        activeObjectUrlsRef.current = activeObjectUrlsRef.current.filter((u) => u !== url);

        if (generationRef.current !== gen) return;

        setErrorMessage(
          language === "ar"
            ? "تعذر تشغيل الصوت في المتصفح. تأكد من تفعيل الصوت أو انقر على الشاشة لتمكين التشغيل."
            : "Audio decoding or playback failed. Please click anywhere to allow audio playback."
        );

        audioRef.current = null;
        isPlayingRef.current = false;

        // Skip and continue playing next sentence without crashing
        playNextInQueue(gen);
      };

      await audio.play();
    } catch (playErr: any) {
      console.error("Failed to play audio sentence:", playErr);
      if (generationRef.current !== gen) return;

      if (playErr?.name === "NotAllowedError") {
        setErrorMessage(
          language === "ar"
            ? "تم حظر التشغيل التلقائي للصوت بواسطة المتصفح. انقر على الشاشة لتمكين الصوت."
            : "Autoplay blocked by browser. Click anywhere on the screen to enable audio."
        );
      } else {
        setErrorMessage(
          language === "ar"
            ? `تعذر تشغيل الصوت: ${playErr?.message || "خطأ غير معروف"}`
            : `Could not play audio: ${playErr?.message || "playback error"}`
        );
      }

      audioRef.current = null;
      isPlayingRef.current = false;
      playNextInQueue(gen);
    }
  };

  // Complete voice turn and return to idle/listening
  const finishVoiceSession = (gen: number) => {
    if (generationRef.current !== gen) return;

    setState("idle");
    setTranscript("");
    latestTranscriptRef.current = "";

    // Revoke any leftover URLs
    activeObjectUrlsRef.current.forEach((u) => {
      try {
        URL.revokeObjectURL(u);
      } catch (e) { }
    });
    activeObjectUrlsRef.current = [];

    // 400ms post-playback cooldown after last audio sentence finishes before restarting listening
    if (cooldownTimerRef.current) {
      clearTimeout(cooldownTimerRef.current);
    }
    cooldownTimerRef.current = setTimeout(() => {
      if (generationRef.current !== gen) return;
      latestTranscriptRef.current = "";
      // Restart speech recognition automatically if unmuted and in Web Speech mode
      if (!useDirectMode && recognitionRef.current && !isMutedRef.current) {
        try {
          recognitionRef.current.start();
        } catch (e) {
          console.warn("Speech recognition restart warning:", e);
        }
      }
    }, 400);
  };

  // Dispatch a sentence to low-latency streaming TTS queue
  const enqueueSentence = (sentenceText: string, gen: number) => {
    const clean = cleanVoiceText(sentenceText);
    if (!clean || !/[\p{L}\p{N}]/u.test(clean)) return;

    const sentenceId = ++sentenceCounterRef.current;
    const isArabicSentence = /[\u0600-\u06FF]/.test(clean);
    const sentenceLang = isArabicSentence ? "ar" : "en";

    audioQueueRef.current.push({
      id: sentenceId,
      text: clean,
      lang: sentenceLang,
      fetchStarted: false,
    });

    pumpAudioQueue(gen);
  };

  // Initialize Speech Recognition when modal opens (if in Web Speech mode)
  useEffect(() => {
    if (!voiceModalOpen) {
      handleInterrupt();
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) { }
        recognitionRef.current = null;
      }
      cancelDirectRecording();
      setTranscript("");
      setAssistantText("");
      setErrorMessage(null);
      setInfoMessage(null);
      return;
    }

    // Pre-unlock audio subsystem on user open gesture so async playback is never blocked
    unlockBrowserAudio();

    // If Web Speech API is not supported, automatically activate Direct Recording mode
    if (!hasWebSpeech) {
      setUseDirectMode(true);
      return;
    }

    if (useDirectMode) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) { }
      }
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = speechLang === "ar" ? "ar-SA" : "en-US";

      recognition.onstart = () => {
        setState("listening");
        setErrorMessage(null);
        setInfoMessage(null);
      };

      recognition.onresult = (event: any) => {
        // Prevent mic echo / self-hearing loop: ignore input if processing or speaking
        if (stateRef.current === "processing" || stateRef.current === "speaking") {
          return;
        }

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
        console.warn("Speech recognition notice/error:", event.error);
        if (event.error === "not-allowed") {
          setErrorMessage(
            language === "ar"
              ? "تم رفض إذن الوصول إلى الميكروفون. يرجى تفعيل الصلاحية في المتصفح."
              : "Microphone access was denied. Please allow microphone access in browser settings."
          );
        } else if (event.error === "service-not-allowed" || event.error === "network") {
          // Gracefully fallback to Direct Recording without showing a red error alert
          setErrorMessage(null);
          setInfoMessage(
            language === "ar"
              ? "خدمة التعرف المباشر غير متوفرة في المتصفح. تم التبديل تلقائياً إلى التسجيل المباشر."
              : "Browser speech service is unavailable. Switched to direct mic recording mode."
          );
          setUseDirectMode(true);
        }
        setState("idle");
      };

      recognitionRef.current = recognition;
      try {
        recognition.start();
      } catch (e) {
        console.warn("Failed to start speech recognition:", e);
      }
    }

    return () => {
      handleInterrupt();
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) { }
      }
    };
  }, [voiceModalOpen, language, useDirectMode, hasWebSpeech, speechLang]);

  // Handle switching speech language between EN, عربي, and Auto (EN/AR)
  const handleSpeechLangChange = (mode: "en" | "ar" | "auto") => {
    speechLangRef.current = mode;
    setSpeechLang(mode);
    setErrorMessage(null);
    setInfoMessage(null);

    // Cancel active direct recording / VAD session cleanly so no leftover Auto callback fires
    cancelDirectRecording();
    handleInterrupt();

    if (mode === "auto") {
      setUseDirectMode(true);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) { }
      }
    } else {
      if (hasWebSpeech) {
        setUseDirectMode(false);
        if (recognitionRef.current) {
          recognitionRef.current.lang = mode === "ar" ? "ar-SA" : "en-US";
          try {
            recognitionRef.current.start();
          } catch (e) { }
        }
      } else {
        setUseDirectMode(true);
      }
    }
  };

  // Toggle between Web Speech Real-Time and Direct Mic Recording with strict synchronization
  const handleToggleMode = () => {
    setErrorMessage(null);
    setInfoMessage(null);
    cancelDirectRecording();
    handleInterrupt();

    if (speechLang === "auto") {
      // If Auto (EN/AR) was active, clicking the mode toggle means the user wants Web Speech Real-Time!
      // But Web Speech cannot run in Auto mode, so switch the language pill to Arabic or English
      const isArabicContext =
        language === "ar" ||
        /[\u0600-\u06FF]/.test(transcript) ||
        /[\u0600-\u06FF]/.test(latestTranscriptRef.current);
      const targetLang = isArabicContext ? "ar" : "en";

      setSpeechLang(targetLang);
      setUseDirectMode(false);

      if (recognitionRef.current) {
        recognitionRef.current.lang = targetLang === "ar" ? "ar-SA" : "en-US";
        try {
          recognitionRef.current.start();
        } catch (e) { }
      }
    } else {
      // In EN or عربي mode: toggle between Direct Mic Recording and Web Speech Real-Time
      const nextDirect = !useDirectMode;
      setUseDirectMode(nextDirect);

      if (nextDirect) {
        if (recognitionRef.current) {
          try {
            recognitionRef.current.stop();
          } catch (e) { }
        }
      } else {
        if (recognitionRef.current) {
          recognitionRef.current.lang = speechLang === "ar" ? "ar-SA" : "en-US";
          try {
            recognitionRef.current.start();
          } catch (e) { }
        }
      }
    }
  };

  // Compute clean, localized Mode Badge text
  const getModeBadgeText = () => {
    if (speechLang === "auto") {
      return language === "ar"
        ? "الوضع: استماع ثنائي تلقائي (Native STT + VAD)"
        : "Mode: Auto Bilingual (Native STT + VAD)";
    }
    if (useDirectMode) {
      return language === "ar"
        ? `الوضع: تسجيل ميكروفون مباشر (${speechLang === "ar" ? "عربي" : "إنجليزي"})`
        : `Mode: Direct Mic Recording (${speechLang === "ar" ? "Arabic" : "English"})`;
    }
    return language === "ar"
      ? `الوضع: تعرف صوتي مباشر (${speechLang === "ar" ? "عربي" : "English"})`
      : `Mode: Web Speech Real-Time (${speechLang === "ar" ? "Arabic" : "English"})`;
  };

  // Direct Audio Recording Fallback using MediaRecorder & /api/v1/voice/transcribe
  const startDirectRecording = async () => {
    try {
      unlockBrowserAudio();
      setErrorMessage(null);
      setInfoMessage(null);
      if (!navigator.mediaDevices?.getUserMedia) {
        setErrorMessage(
          language === "ar"
            ? "المتصفح لا يدعم التسجيل الصوتي."
            : "MediaDevices recording is not supported in this browser."
        );
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      mediaStreamRef.current = stream;
      audioChunksRef.current = [];

      const mimeType =
        typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported("audio/webm")
            ? "audio/webm"
            : "";

      const options: MediaRecorderOptions = {
        audioBitsPerSecond: 16000
      };
      if (mimeType) {
        options.mimeType = mimeType;
      }
      const recorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        if (vadAnimRef.current) {
          cancelAnimationFrame(vadAnimRef.current);
          vadAnimRef.current = null;
        }
        safeCloseAudioContext(vadContextRef);
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
            const currentLangSetting = speechLangRef.current;
            const reqLang = currentLangSetting === "auto" ? "auto" : currentLangSetting;
            const res = await transcribeAudio(audioBlob, reqLang);
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

      // Voice Activity Detection (VAD) using Web Audio Analyser
      try {
        const AudioCtxClass = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioCtxClass) {
          const audioCtx = new AudioCtxClass();
          vadContextRef.current = audioCtx;
          const source = audioCtx.createMediaStreamSource(stream);
          const analyser = audioCtx.createAnalyser();
          analyser.fftSize = 512;
          source.connect(analyser);

          const dataArray = new Uint8Array(analyser.frequencyBinCount);
          let speechDetected = false;
          let silenceStart = 0;

          const checkVAD = () => {
            if (!mediaRecorderRef.current || mediaRecorderRef.current.state !== "recording") {
              safeCloseAudioContext(vadContextRef);
              return;
            }
            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
            }
            const avg = sum / dataArray.length;
            const now = Date.now();

            if (avg > 14) {
              speechDetected = true;
              silenceStart = 0;
            } else if (speechDetected) {
              if (silenceStart === 0) {
                silenceStart = now;
              } else if (now - silenceStart > 750) {
                // 750ms of silence after speech detected: automatically stop recording
                stopDirectRecording();
                safeCloseAudioContext(vadContextRef);
                return;
              }
            }

            vadAnimRef.current = requestAnimationFrame(checkVAD);
          };
          vadAnimRef.current = requestAnimationFrame(checkVAD);
        }
      } catch (vadErr) {
        console.warn("VAD analyser setup skipped:", vadErr);
      }

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
    if (vadAnimRef.current) {
      cancelAnimationFrame(vadAnimRef.current);
      vadAnimRef.current = null;
    }
    safeCloseAudioContext(vadContextRef);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) { }
    }
  };

  // Process User Speech: Auto-create conversation if none exists, stream response, and pipeline TTS sentences
  const processUserSpeech = async (userText: string) => {
    if (!userText.trim()) return;

    // Immediately stop / abort recognition & recording to prevent mic echo / self-hearing loop
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (e) { }
    }
    cancelDirectRecording();
    latestTranscriptRef.current = "";
    setErrorMessage(null);
    setInfoMessage(null);

    // Clean up any previous playback session first
    handleInterrupt();

    const myGen = ++generationRef.current;
    setState("processing");
    setAssistantText("");
    sentenceBufferRef.current = "";
    audioQueueRef.current = [];
    sentenceCounterRef.current = 0;
    isPlayingRef.current = false;
    isStreamingRef.current = true;

    // Modal explicit voice language resolution:
    // If EN pill is selected -> strictly "en"
    // If عربي pill is selected -> strictly "ar"
    // If Auto (EN/AR) is selected -> script-first detection:
    //   Arabic characters -> "ar"
    //   Latin characters -> "en"
    //   Fallback -> "en"
    let activeVoiceLang: "en" | "ar" = "en";
    if (speechLangRef.current === "ar") {
      activeVoiceLang = "ar";
    } else if (speechLangRef.current === "en") {
      activeVoiceLang = "en";
    } else {
      const hasArabic = /[\u0600-\u06FF]/.test(userText);
      const hasLatin = /[A-Za-z]/.test(userText);
      if (hasArabic) {
        activeVoiceLang = "ar";
      } else if (hasLatin) {
        activeVoiceLang = "en";
      } else {
        activeVoiceLang = language === "ar" ? "ar" : "en";
      }
    }

    try {
      let targetConvId = activeConversationId;
      if (!targetConvId) {
        try {
          const titleSnippet = userText.trim().slice(0, 32);
          const title = titleSnippet || (activeVoiceLang === "ar" ? "محادثة صوتية" : "Voice Conversation");
          const newConv = await createConversation(title, activeVoiceLang, activeKbId || undefined);
          targetConvId = newConv.id;
          setActiveConversationId(newConv.id);
          // Defer conversations list refresh to background without blocking playback
          refreshConversations().catch(() => { });
        } catch (convErr: any) {
          console.error("Failed to auto-create conversation in voice mode:", convErr);
          setErrorMessage(
            language === "ar" ? "فشل إنشاء محادثة جديدة" : "Failed to create conversation"
          );
          setState("idle");
          isStreamingRef.current = false;
          return;
        }
      }

      if (generationRef.current !== myGen) return;

      abortControllerRef.current = new AbortController();
      let fullReply = "";

      await streamMessage(
        targetConvId,
        userText,
        activeKbId || undefined,
        activeVoiceLang,
        // onToken: accumulate text in sentence buffer and extract sentences as tokens arrive
        (token: string) => {
          if (generationRef.current !== myGen) return;
          fullReply += token;
          setAssistantText(fullReply);

          sentenceBufferRef.current += token;

          // Split on sentence boundaries (or early Clause 1 after >= 5 words) and enqueue immediately
          while (true) {
            const isFirst = sentenceCounterRef.current === 0;
            const result = extractNextSentence(sentenceBufferRef.current, isFirst);
            if (!result) break;
            sentenceBufferRef.current = result.remainder;
            enqueueSentence(result.sentence, myGen);
          }
        },
        // onDone
        async (data: any) => {
          if (generationRef.current !== myGen) return;
          const reply = data.content || fullReply;
          setAssistantText(reply);
          // Defer conversation refresh non-blocking so audio starts without delay
          refreshConversations().catch(() => { });

          // Drain any remaining complete sentences
          while (true) {
            const isFirst = sentenceCounterRef.current === 0;
            const result = extractNextSentence(sentenceBufferRef.current, isFirst);
            if (!result) break;
            sentenceBufferRef.current = result.remainder;
            enqueueSentence(result.sentence, myGen);
          }

          // At onDone, if there is any remaining text in sentenceBufferRef, synthesize and push it
          const leftover = cleanVoiceText(sentenceBufferRef.current);
          if (leftover && /[\p{L}\p{N}]/u.test(leftover)) {
            sentenceBufferRef.current = "";
            enqueueSentence(leftover, myGen);
          }

          isStreamingRef.current = false;

          // If nothing was enqueued and queue is empty, finish session immediately
          if (!isPlayingRef.current && audioQueueRef.current.length === 0) {
            finishVoiceSession(myGen);
          }
        },
        // onError
        (err: any) => {
          if (generationRef.current !== myGen) return;
          console.error("Streaming error in voice:", err);
          setErrorMessage(err.message || "Streaming failed");
          isStreamingRef.current = false;
          if (!isPlayingRef.current && audioQueueRef.current.length === 0) {
            setState("idle");
          }
        },
        abortControllerRef.current.signal,
        undefined,
        true // isVoice = true parameter passed to backend
      );
    } catch (err: any) {
      if (abortControllerRef.current?.signal.aborted || generationRef.current !== myGen) return;
      console.error(err);
      setErrorMessage(
        err.message || (language === "ar" ? "فشل توليد الإجابة" : "Failed to generate response")
      );
      isStreamingRef.current = false;
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
        } catch (e) { }
      }
      setState("idle");
    } else {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.start();
        } catch (e) {
          console.warn("Speech recognition start warning:", e);
        }
      }
    }
  };

  if (!voiceModalOpen) return null;

  return (
    <div
      onClick={() => unlockBrowserAudio()}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl p-6 text-center shadow-2xl flex flex-col items-center">
        {/* Row 1: Header Bar with Title and Close Button */}
        <div className="flex items-center justify-between w-full mb-3 px-1">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Radio size={14} className="text-indigo-400 animate-pulse shrink-0" />
            <span className="font-medium tracking-wide uppercase">
              {language === "ar" ? "جلسة صوتية فورية متصلة" : "Live Real-Time Voice Assistant"}
            </span>
          </div>
          <button
            onClick={() => {
              handleInterrupt();
              setVoiceModalOpen(false);
            }}
            className="p-1.5 text-slate-400 hover:text-white rounded-full hover:bg-slate-800 transition cursor-pointer shrink-0"
            title={language === "ar" ? "إغلاق" : "Close"}
          >
            <X size={20} />
          </button>
        </div>

        {/* Row 2: Centered Speech Language Selector (EN | عربي | Auto) */}
        <div className="flex items-center justify-center w-full mb-2.5">
          <div className="inline-flex items-center p-1 rounded-full bg-slate-800/90 border border-slate-700/80 shadow-inner gap-1">
            <button
              onClick={() => handleSpeechLangChange("en")}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition cursor-pointer ${speechLang === "en"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
                }`}
            >
              EN
            </button>
            <button
              onClick={() => handleSpeechLangChange("ar")}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition cursor-pointer ${speechLang === "ar"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
                }`}
            >
              عربي
            </button>
            <button
              onClick={() => handleSpeechLangChange("auto")}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition cursor-pointer ${speechLang === "auto"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
                }`}
            >
              Auto (EN/AR)
            </button>
          </div>
        </div>

        {/* Row 3: Centered Mode Toggle Badge */}
        <div className="flex items-center justify-center w-full mb-3">
          <button
            onClick={handleToggleMode}
            className="flex items-center gap-1.5 px-3.5 py-1 rounded-full text-[11px] font-medium border transition cursor-pointer bg-slate-800/80 border-slate-700 text-slate-300 hover:text-white hover:border-slate-600"
            title={language === "ar" ? "تبديل وضع التسجيل الصوتي" : "Toggle voice recording mode"}
          >
            <span>{getModeBadgeText()}</span>
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

        {/* Subtle Info Alert Banner for Graceful Fallback */}
        {infoMessage && !errorMessage && (
          <div className="w-full mb-3 px-3.5 py-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs flex items-center justify-between gap-2 text-start animate-in fade-in">
            <div className="flex items-center gap-2">
              <Radio size={14} className="shrink-0 text-indigo-400" />
              <span>{infoMessage}</span>
            </div>
            <button
              onClick={() => setInfoMessage(null)}
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
            className={`absolute w-36 h-36 rounded-full blur-3xl transition-all duration-700 opacity-30 ${state === "listening"
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
            className={`text-sm font-semibold tracking-wide ${state === "listening"
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
        <div dir="auto" className="h-14 flex items-center justify-center px-4 text-xs text-slate-300 max-w-sm line-clamp-2 text-center">
          {transcript ? (
            <span dir="auto" className="italic text-slate-200">"{transcript}"</span>
          ) : assistantText ? (
            <span dir="auto" className="text-slate-300">{assistantText.slice(0, 100)}...</span>
          ) : (
            <span dir="auto" className="text-slate-500">
              {speechLang === "ar" || language === "ar"
                ? "يمكنك التحدث باللغة العربية بحرية"
                : speechLang === "auto"
                  ? "Speak freely in English or Arabic (Auto-detect)"
                  : "Speak freely in English"}
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
            className={`p-3.5 rounded-2xl transition active:scale-95 cursor-pointer ${state === "listening" || isDirectRecording
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
            onClick={() => {
              handleInterrupt();
              setVoiceModalOpen(false);
            }}
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
