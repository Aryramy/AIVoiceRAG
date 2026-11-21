import {
  Conversation,
  Message,
  KnowledgeBase,
  Document,
  ProviderStatus,
  ModelInfo,
  VoiceInfo,
  ProviderTestResult,
  AISettings,
  AnalyticsSummary,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export async function fetchHealth(): Promise<any> {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

// Conversations
export async function fetchConversations(): Promise<Conversation[]> {
  const res = await fetch(`${API_BASE}/conversations`);
  if (!res.ok) throw new Error("Failed to load conversations");
  return res.json();
}

export async function createConversation(title: string = "New Conversation", language: string = "en", knowledgeBaseId?: string | null): Promise<Conversation> {
  const res = await fetch(`${API_BASE}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, language, knowledge_base_id: knowledgeBaseId || null }),
  });
  if (!res.ok) throw new Error("Failed to create conversation");
  return res.json();
}

export async function fetchConversationDetails(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/conversations/${id}`);
  if (!res.ok) throw new Error("Failed to load conversation details");
  return res.json();
}

export async function deleteConversation(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/conversations/${id}`, { method: "DELETE" });
  return res.json();
}

export async function updateConversation(
  id: string,
  data: { title?: string; language?: string; knowledge_base_id?: string | null }
): Promise<Conversation> {
  const res = await fetch(`${API_BASE}/conversations/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update conversation");
  return res.json();
}

export async function sendMessage(
  conversationId: string,
  content: string,
  knowledgeBaseId?: string | null,
  language?: string,
  useRag?: boolean
): Promise<any> {
  const url = new URL(`${API_BASE}/conversations/${conversationId}/messages`);
  if (knowledgeBaseId) {
    url.searchParams.append("knowledge_base_id", knowledgeBaseId);
  } else if (knowledgeBaseId === null || knowledgeBaseId === "" || useRag === false) {
    url.searchParams.append("knowledge_base_id", "null");
    url.searchParams.append("use_rag", "false");
  }

  const res = await fetch(url.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content,
      language,
      knowledge_base_id: knowledgeBaseId || null,
      use_rag: useRag !== undefined ? useRag : (knowledgeBaseId ? true : false)
    }),
  });
  if (!res.ok) throw new Error("Failed to send message");
  return res.json();
}

export async function streamMessage(
  conversationId: string,
  content: string,
  knowledgeBaseId?: string | null,
  language?: string,
  onToken?: (token: string) => void,
  onDone?: (data: any) => void,
  onError?: (err: any) => void,
  signal?: AbortSignal,
  useRag?: boolean,
  isVoice?: boolean
): Promise<void> {
  const url = new URL(`${API_BASE}/conversations/${conversationId}/messages/stream`);
  if (knowledgeBaseId) {
    url.searchParams.append("knowledge_base_id", knowledgeBaseId);
  } else if (knowledgeBaseId === null || knowledgeBaseId === "" || useRag === false) {
    url.searchParams.append("knowledge_base_id", "null");
    url.searchParams.append("use_rag", "false");
  }
  if (isVoice) {
    url.searchParams.append("is_voice", "true");
  }

  try {
    const res = await fetch(url.toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        language,
        knowledge_base_id: knowledgeBaseId || null,
        use_rag: useRag !== undefined ? useRag : (knowledgeBaseId ? true : false),
        is_voice: Boolean(isVoice)
      }),
      signal
    });

    if (!res.ok) {
      throw new Error(`Server returned ${res.status}: Failed to stream message`);
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error("ReadableStream not supported by browser");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const block of lines) {
        if (!block.trim()) continue;
        const blockLines = block.split("\n");
        let eventType = "";
        let eventData = "";

        for (const line of blockLines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            eventData = line.slice(6).trim();
          }
        }

        if (eventType === "token" && eventData) {
          try {
            const parsed = JSON.parse(eventData);
            if (parsed.token && onToken) onToken(parsed.token);
          } catch (e) {
            if (onToken) onToken(eventData);
          }
        } else if (eventType === "done" && eventData) {
          try {
            const parsed = JSON.parse(eventData);
            if (onDone) onDone(parsed);
          } catch (e) {
            if (onDone) onDone({});
          }
        }
      }
    }
  } catch (err: any) {
    if (signal?.aborted) return;
    if (onError) onError(err);
    else throw err;
  }
}

// Knowledge Bases
export async function fetchKnowledgeBases(): Promise<KnowledgeBase[]> {
  const res = await fetch(`${API_BASE}/knowledge-bases`);
  if (!res.ok) throw new Error("Failed to load knowledge bases");
  return res.json();
}

export async function createKnowledgeBase(name: string, description?: string, language: string = "multilingual"): Promise<KnowledgeBase> {
  const res = await fetch(`${API_BASE}/knowledge-bases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description, language }),
  });
  if (!res.ok) throw new Error("Failed to create knowledge base");
  return res.json();
}

export async function fetchKnowledgeBaseDetails(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/knowledge-bases/${id}`);
  if (!res.ok) throw new Error("Failed to load knowledge base details");
  return res.json();
}

export async function deleteKnowledgeBase(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/knowledge-bases/${id}`, { method: "DELETE" });
  return res.json();
}

export async function uploadDocument(kbId: string, file: File): Promise<any> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/knowledge-bases/${kbId}/documents/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function deleteDocument(kbId: string, docId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/knowledge-bases/${kbId}/documents/${docId}`, { method: "DELETE" });
  return res.json();
}

// Providers & Settings
export async function fetchProviders(): Promise<ProviderStatus[]> {
  const res = await fetch(`${API_BASE}/providers`);
  if (!res.ok) throw new Error("Failed to load providers");
  return res.json();
}

export async function fetchProviderModels(provider: string, capability?: string): Promise<ModelInfo[]> {
  const url = new URL(`${API_BASE}/providers/${provider}/models`);
  if (capability) url.searchParams.append("capability", capability);
  const res = await fetch(url.toString());
  if (!res.ok) return [];
  return res.json();
}

export async function fetchProviderVoices(provider: string, language?: string): Promise<VoiceInfo[]> {
  const url = new URL(`${API_BASE}/providers/${provider}/voices`);
  if (language) url.searchParams.append("language", language);
  const res = await fetch(url.toString());
  if (!res.ok) return [];
  return res.json();
}

export async function testProvider(provider: string, apiKey?: string, baseUrl?: string): Promise<ProviderTestResult> {
  const res = await fetch(`${API_BASE}/providers/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, api_key: apiKey, base_url: baseUrl }),
  });
  return res.json();
}

export async function fetchSettings(): Promise<AISettings> {
  const res = await fetch(`${API_BASE}/settings`);
  if (!res.ok) throw new Error("Failed to load settings");
  return res.json();
}

export async function updateSettings(settings: Partial<AISettings>): Promise<AISettings> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error("Failed to update settings");
  return res.json();
}

// Voice APIs
export async function transcribeAudio(audioBlob: Blob, language?: string): Promise<any> {
  const formData = new FormData();
  formData.append("file", audioBlob, "speech.wav");
  if (language) formData.append("language", language);

  const res = await fetch(`${API_BASE}/voice/transcribe`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Transcription failed");
  return res.json();
}

export async function synthesizeSpeech(
  text: string,
  language: string = "en",
  voice?: string,
  provider?: string,
  signal?: AbortSignal
): Promise<Blob> {
  const res = await fetch(`${API_BASE}/voice/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language, voice, provider }),
    signal,
  });
  if (!res.ok) throw new Error("Speech synthesis failed");
  const contentType = res.headers.get("content-type") || "audio/mpeg";
  const arrayBuffer = await res.arrayBuffer();
  return new Blob([arrayBuffer], { type: contentType.split(";")[0].trim() });
}

export async function synthesizeSpeechStream(
  text: string,
  language: string = "en",
  voice?: string,
  provider?: string,
  signal?: AbortSignal
): Promise<Response> {
  const res = await fetch(`${API_BASE}/voice/synthesize/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language, voice, provider }),
    signal,
  });
  if (!res.ok) throw new Error("Speech synthesis stream failed");
  return res;
}

/**
 * Pre-unlocks browser audio subsystem on user gesture (click/touch)
 * so that async playback is never blocked by browser autoplay policy.
 */
let unlockedAudioContext: AudioContext | null = null;
export function unlockBrowserAudio(): void {
  try {
    if (typeof window === "undefined") return;
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (AudioContextClass) {
      if (!unlockedAudioContext || unlockedAudioContext.state === "closed") {
        unlockedAudioContext = new AudioContextClass();
      }
      if (unlockedAudioContext.state === "suspended") {
        unlockedAudioContext.resume().catch(() => {});
      }
      // Play 1-frame silent oscillator/buffer to satisfy Chrome/Safari autoplay policy
      const buffer = unlockedAudioContext.createBuffer(1, 1, 22050);
      const src = unlockedAudioContext.createBufferSource();
      src.buffer = buffer;
      src.connect(unlockedAudioContext.destination);
      src.start(0);
    }
  } catch (e) {
    console.warn("Audio unlock notice:", e);
  }
}

export async function getLiveKitToken(roomName: string, participantName: string): Promise<any> {
  const res = await fetch(`${API_BASE}/voice/livekit-token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ room_name: roomName, participant_name: participantName }),
  });
  return res.json();
}

// Analytics
export async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  const res = await fetch(`${API_BASE}/analytics/summary`);
  if (!res.ok) throw new Error("Failed to load analytics");
  return res.json();
}

