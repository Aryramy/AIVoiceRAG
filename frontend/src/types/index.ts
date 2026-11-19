export type Role = "user" | "assistant" | "system";

export interface Citation {
  id: string;
  chunk_id?: string;
  document_id?: string;
  document_title?: string;
  page_number?: number;
  content_snippet?: string;
  similarity_score?: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: Role;
  content: string;
  language?: string;
  provider?: string;
  model?: string;
  latency_ms?: number;
  cost_usd?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  created_at?: string;
  citations?: Citation[];
  is_streaming?: boolean;
}

export interface Conversation {
  id: string;
  user_id?: string;
  title: string;
  language: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Document {
  id: string;
  knowledge_base_id: string;
  title: string;
  file_name?: string;
  file_type: string;
  file_size_bytes: number;
  status: "pending" | "processing" | "indexed" | "failed";
  chunk_count: number;
  language?: string;
  created_at?: string;
  error_message?: string;
}

export interface KnowledgeBase {
  id: string;
  user_id?: string;
  name: string;
  description?: string;
  language?: string;
  document_count: number;
  chunk_count: number;
  created_at?: string;
  updated_at?: string;
  documents?: Document[];
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  capabilities: string[];
  context_window: number;
  input_cost_per_million: number;
  output_cost_per_million: number;
  supports_streaming: boolean;
  supports_vision: boolean;
  description?: string;
}

export interface VoiceInfo {
  id: string;
  name: string;
  provider: string;
  language: string;
  gender: string;
  description?: string;
}

export interface ProviderStatus {
  provider: string;
  name: string;
  is_configured: boolean;
  is_healthy: boolean;
  error?: string;
  supported_capabilities: string[];
  models: ModelInfo[];
  voices: VoiceInfo[];
}

export interface ProviderTestResult {
  provider: string;
  success: boolean;
  latency_ms: number;
  message: string;
  models_found: number;
  error?: string;
}

export interface AISettings {
  id?: string;
  llm_provider: string;
  llm_model: string;
  temperature: number;
  max_tokens: number;
  stt_provider: string;
  stt_model: string;
  tts_provider: string;
  tts_voice_en: string;
  tts_voice_ar: string;
  voice_provider: string;
  voice_model: string;
  routing_strategy: string;
  fallback_enabled: boolean;
  fallback_provider?: string;
  fallback_model?: string;
  similarity_threshold: number;
  top_k: number;
  hybrid_alpha: number;
  reranker_enabled: boolean;
  abstention_enabled: boolean;
  system_prompt_en: string;
  system_prompt_ar: string;
  monthly_budget_usd: number;
  rate_limit_per_minute: number;
}

export interface AnalyticsSummary {
  total_requests: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  error_rate_percentage: number;
  by_provider: Record<string, { calls: number; tokens: number; cost: number }>;
  by_capability: Record<string, { calls: number; tokens: number; cost: number }>;
  top_models: Array<{
    model: string;
    provider: string;
    calls_count: number;
    total_tokens: number;
    total_cost_usd: number;
    avg_latency_ms: number;
  }>;
  recent_logs: Array<{
    id: string;
    provider: string;
    model: string;
    capability: string;
    total_tokens: number;
    cost_usd: number;
    latency_ms: number;
    status: string;
    created_at: string;
  }>;
}
