"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useApp } from "@/context/AppContext";
import { fetchAnalyticsSummary } from "@/lib/api";
import { AnalyticsSummary } from "@/types";
import {
  BarChart3,
  ArrowLeft,
  ArrowRight,
  TrendingUp,
  DollarSign,
  Clock,
  Layers,
  AlertTriangle,
  RotateCw,
  Loader2,
  CheckCircle2,
  XCircle
} from "lucide-react";

export default function AnalyticsPage() {
  const { language, direction } = useApp();
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const data = await fetchAnalyticsSummary();
      setSummary(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  if (loading || !summary) {
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
            <BarChart3 size={20} className="text-indigo-500" />
            <h1 className="text-lg font-semibold tracking-tight">
              {language === "ar" ? "لوحة القياس والتحليلات والتكاليف" : "Analytics & Cost Telemetry Dashboard"}
            </h1>
          </div>
        </div>

        <button
          onClick={loadAnalytics}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition"
        >
          <RotateCw size={13} />
          <span>{language === "ar" ? "تحديث" : "Refresh"}</span>
        </button>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {/* Requests */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">
              {language === "ar" ? "إجمالي الطلبات" : "Total Requests"}
            </span>
            <div className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              {summary.total_requests.toLocaleString()}
            </div>
          </div>

          {/* Tokens */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">
              {language === "ar" ? "الرموز المعالجة" : "Total Tokens"}
            </span>
            <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mt-1 font-mono">
              {summary.total_tokens.toLocaleString()}
            </div>
          </div>

          {/* Cost USD */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">
              {language === "ar" ? "إجمالي التكلفة" : "Total Cost"}
            </span>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1 font-mono">
              ${summary.total_cost_usd.toFixed(4)}
            </div>
          </div>

          {/* Latency */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-xs">
            <span className="text-xs text-slate-500 font-medium">
              {language === "ar" ? "متوسط الاستجابة" : "Avg Latency"}
            </span>
            <div className="text-2xl font-bold text-slate-900 dark:text-white mt-1 font-mono">
              {summary.avg_latency_ms}ms
            </div>
          </div>

          {/* Error Rate */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-xs col-span-2 md:col-span-1">
            <span className="text-xs text-slate-500 font-medium">
              {language === "ar" ? "معدل الأخطاء" : "Error Rate"}
            </span>
            <div className="text-2xl font-bold text-slate-900 dark:text-white mt-1 font-mono">
              {summary.error_rate_percentage}%
            </div>
          </div>
        </div>

        {/* Section 2: Breakdown by Provider & Capability */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* By Provider */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs">
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-4">
              {language === "ar" ? "الاستهلاك حسب المزود" : "Usage by AI Provider"}
            </h3>
            <div className="space-y-3">
              {Object.keys(summary.by_provider).length === 0 ? (
                <div className="text-xs text-slate-400 py-4 text-center">No data recorded yet</div>
              ) : (
                Object.entries(summary.by_provider).map(([pName, pStat]) => (
                  <div key={pName} className="flex items-center justify-between text-xs py-1.5 border-b border-slate-100 dark:border-slate-800/80">
                    <span className="font-semibold uppercase text-slate-700 dark:text-slate-300">{pName}</span>
                    <div className="flex items-center gap-4 font-mono text-slate-500">
                      <span>{pStat.calls} calls</span>
                      <span>{pStat.tokens.toLocaleString()} tok</span>
                      <span className="text-emerald-500 font-semibold">${pStat.cost.toFixed(4)}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* By Capability */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs">
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-4">
              {language === "ar" ? "الاستهلاك حسب نوع الخدمة" : "Usage by Capability"}
            </h3>
            <div className="space-y-3">
              {Object.keys(summary.by_capability).length === 0 ? (
                <div className="text-xs text-slate-400 py-4 text-center">No data recorded yet</div>
              ) : (
                Object.entries(summary.by_capability).map(([capName, capStat]) => (
                  <div key={capName} className="flex items-center justify-between text-xs py-1.5 border-b border-slate-100 dark:border-slate-800/80">
                    <span className="font-semibold uppercase text-slate-700 dark:text-slate-300">{capName}</span>
                    <div className="flex items-center gap-4 font-mono text-slate-500">
                      <span>{capStat.calls} calls</span>
                      <span>{capStat.tokens.toLocaleString()} tok</span>
                      <span className="text-emerald-500 font-semibold">${capStat.cost.toFixed(4)}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Section 3: Recent Activity Logs */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs">
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-4">
            {language === "ar" ? "سجل الاستدعاءات الأخير" : "Recent Invocation Logs"}
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-start">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 font-medium">
                  <th className="py-2.5 px-3 text-start">Provider</th>
                  <th className="py-2.5 px-3 text-start">Model</th>
                  <th className="py-2.5 px-3 text-start">Capability</th>
                  <th className="py-2.5 px-3 text-start">Tokens</th>
                  <th className="py-2.5 px-3 text-start">Latency</th>
                  <th className="py-2.5 px-3 text-start">Cost</th>
                  <th className="py-2.5 px-3 text-start">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
                {summary.recent_logs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-6 text-center text-slate-400 font-sans">
                      No logs available yet
                    </td>
                  </tr>
                ) : (
                  summary.recent_logs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                      <td className="py-2.5 px-3 uppercase text-slate-600 dark:text-slate-300">{log.provider}</td>
                      <td className="py-2.5 px-3 text-slate-800 dark:text-slate-200">{log.model}</td>
                      <td className="py-2.5 px-3 uppercase text-slate-500">{log.capability}</td>
                      <td className="py-2.5 px-3 text-indigo-500">{log.total_tokens}</td>
                      <td className="py-2.5 px-3 text-slate-500">{log.latency_ms}ms</td>
                      <td className="py-2.5 px-3 text-emerald-500">${log.cost_usd.toFixed(5)}</td>
                      <td className="py-2.5 px-3 font-sans">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${
                            log.status === "success"
                              ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400"
                              : "bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400"
                          }`}
                        >
                          {log.status === "success" ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
                          {log.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
