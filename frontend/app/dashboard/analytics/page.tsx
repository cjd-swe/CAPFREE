"use client"

import { useEffect, useState, useMemo } from "react"
import Link from "next/link"
import {
    AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ReferenceLine, Cell
} from "recharts"
import { TrendingUp, TrendingDown, Target, Trophy, Clock, ChevronDown } from "lucide-react"
import { API_URL, parseApiDate } from "@/lib/api"

// ─── Types ───────────────────────────────────────────────────────────────────

interface CapperStat {
    id: number
    name: string
    profit: number
    roi: number
    win_rate: number
    confirmed_win_rate: number
    total_win_rate: number
    total_picks: number
    wins: number
    losses: number
    pushes: number
    pending: number
}

interface ProfitHistoryEntry {
    date: string
    date_added: string
    pick_text: string
    result: string
    grade_source: string | null
    profit: number
    cumulative_profit: number
    sport: string
    units_risked: number
}

interface SportStat {
    name: string
    value: number
    win_rate: number
    roi: number
    profit: number
    total_picks: number
    record: string
}

interface SummaryStats {
    total_profit: number
    win_rate: number
    roi: number
    active_cappers: number
    total_picks: number
    pending_picks: number
}

interface CapperDetail {
    id: number
    name: string
    total_picks: number
    wins: number
    losses: number
    pushes: number
    pending: number
    win_rate: number
    roi: number
    total_profit: number
    total_units_risked: number
    sport_performance: Record<string, {
        wins: number
        losses: number
        pushes: number
        profit: number
        total: number
    }>
    recent_picks: Array<{
        id: number
        pick_text: string
        sport: string
        result: string
        profit: number
        units_risked: number
        odds: number | null
        grade_source: string | null
        date: string
        game_date: string | null
    }>
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const SPORT_COLORS = [
    "#16a34a", "#2563eb", "#d97706", "#dc2626",
    "#7c3aed", "#0891b2", "#be185d", "#65a30d"
]

function winRateColor(rate: number) {
    if (rate > 55) return "text-green-600"
    if (rate < 50) return "text-red-500"
    return "text-slate-700"
}

function profitColor(val: number) {
    if (val > 0) return "text-green-600"
    if (val < 0) return "text-red-500"
    return "text-slate-700"
}

function fmtProfit(val: number) {
    return (val > 0 ? "+" : "") + val.toFixed(2) + "u"
}

const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    return (
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-lg text-xs">
            <p className="font-medium text-slate-700 mb-1">{label}</p>
            {payload.map((p: any) => (
                <p key={p.dataKey} style={{ color: p.color }}>
                    {p.name}: {p.value > 0 ? "+" : ""}{p.value.toFixed(2)}u
                </p>
            ))}
        </div>
    )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
    const [cappers, setCappers] = useState<CapperStat[]>([])
    const [selectedId, setSelectedId] = useState<number | "all">("all")
    const [summary, setSummary] = useState<SummaryStats | null>(null)
    const [overallSportPerf, setOverallSportPerf] = useState<SportStat[]>([])
    const [capperDetail, setCapperDetail] = useState<CapperDetail | null>(null)
    const [profitHistory, setProfitHistory] = useState<ProfitHistoryEntry[]>([])
    const [dailyProfit, setDailyProfit] = useState<any[]>([])
    const [days, setDays] = useState(30)
    const [loading, setLoading] = useState(true)
    const [dropdownOpen, setDropdownOpen] = useState(false)

    // Load cappers + overall data once
    useEffect(() => {
        Promise.all([
            fetch(API_URL + "/api/analytics/cappers", { credentials: "include" }).then(r => r.json()),
            fetch(API_URL + "/api/analytics/summary", { credentials: "include" }).then(r => r.json()),
            fetch(API_URL + "/api/analytics/sport-performance", { credentials: "include" }).then(r => r.json()),
        ]).then(([c, s, sp]) => {
            setCappers(c)
            setSummary(s)
            setOverallSportPerf(sp)
            setLoading(false)
        }).catch(() => setLoading(false))
    }, [])

    // Load daily profit when days changes (overall view only)
    useEffect(() => {
        if (selectedId !== "all") return
        fetch(`${API_URL}/api/analytics/daily-profit?days=${days}`, { credentials: "include" })
            .then(r => r.json())
            .then(setDailyProfit)
            .catch(() => {})
    }, [days, selectedId])

    // Load capper-specific data
    useEffect(() => {
        if (selectedId === "all") {
            setCapperDetail(null)
            setProfitHistory([])
            return
        }
        Promise.all([
            fetch(`${API_URL}/api/analytics/capper/${selectedId}`, { credentials: "include" }).then(r => r.json()),
            fetch(`${API_URL}/api/analytics/capper/${selectedId}/profit-history`, { credentials: "include" }).then(r => r.json()),
        ]).then(([detail, history]) => {
            setCapperDetail(detail)
            setProfitHistory(history)
        }).catch(() => {})
    }, [selectedId])

    // Build cumulative profit from daily data for "all" view
    const overallCumulative = useMemo(() => {
        let running = 0
        return dailyProfit.map(d => {
            running += d.profit
            return { ...d, cumulative: parseFloat(running.toFixed(2)) }
        })
    }, [dailyProfit])

    // Filter profit history to selected time window
    const filteredHistory = useMemo(() => {
        if (!profitHistory.length) return []
        const cutoff = new Date()
        cutoff.setDate(cutoff.getDate() - days)
        return profitHistory.filter(p => parseApiDate(p.date) >= cutoff)
    }, [profitHistory, days])

    // Sport data for charts
    const sportChartData = useMemo(() => {
        if (selectedId === "all") {
            return overallSportPerf.map((s, i) => ({ name: s.name, profit: s.profit, win_rate: s.win_rate, roi: s.roi, total: s.total_picks, record: s.record, color: SPORT_COLORS[i % SPORT_COLORS.length] }))
        }
        if (!capperDetail) return []
        return Object.entries(capperDetail.sport_performance).map(([sport, s], i) => {
            const graded = s.wins + s.losses + s.pushes
            const wr = graded > 0 ? (s.wins / graded * 100) : 0
            const units = s.total > 0 ? s.total * 1 : 1 // approximate
            return {
                name: sport,
                profit: parseFloat(s.profit.toFixed(2)),
                win_rate: parseFloat(wr.toFixed(1)),
                record: `${s.wins}-${s.losses}-${s.pushes}`,
                total: s.total,
                color: SPORT_COLORS[i % SPORT_COLORS.length]
            }
        }).sort((a, b) => b.total - a.total)
    }, [selectedId, overallSportPerf, capperDetail])

    const selectedCapper = cappers.find(c => c.id === selectedId)

    // Stats to display in the strip
    const statsStrip = useMemo(() => {
        if (selectedId === "all" && summary) {
            return {
                profit: summary.total_profit,
                win_rate: summary.win_rate,
                roi: summary.roi,
                total_picks: summary.total_picks,
                wins: null as number | null,
                losses: null as number | null,
                pending: summary.pending_picks,
            }
        }
        if (selectedCapper) {
            return {
                profit: selectedCapper.profit,
                win_rate: selectedCapper.total_win_rate,
                roi: selectedCapper.roi,
                total_picks: selectedCapper.total_picks,
                wins: selectedCapper.wins,
                losses: selectedCapper.losses,
                pending: selectedCapper.pending,
            }
        }
        return null
    }, [selectedId, summary, selectedCapper])

    if (loading) {
        return (
            <div className="flex h-64 items-center justify-center text-slate-500 text-sm">
                Loading analytics...
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Header + Capper Selector */}
            <div className="flex flex-wrap items-center justify-between gap-4">
                <h1 className="text-2xl font-bold text-slate-900">Analytics</h1>

                <div className="flex items-center gap-3">
                    {/* Capper Selector */}
                    <div className="relative">
                        <button
                            onClick={() => setDropdownOpen(v => !v)}
                            className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
                        >
                            {selectedId === "all" ? "All Cappers" : selectedCapper?.name ?? "Select Capper"}
                            <ChevronDown className="h-4 w-4 text-slate-500" />
                        </button>
                        {dropdownOpen && (
                            <div className="absolute right-0 z-20 mt-1 w-52 rounded-lg border border-slate-200 bg-white shadow-xl">
                                <button
                                    onClick={() => { setSelectedId("all"); setDropdownOpen(false) }}
                                    className={`block w-full px-4 py-2.5 text-left text-sm hover:bg-slate-50 ${selectedId === "all" ? "font-semibold text-green-600" : "text-slate-700"}`}
                                >
                                    All Cappers
                                </button>
                                <div className="border-t border-slate-200" />
                                {cappers.map(c => (
                                    <button
                                        key={c.id}
                                        onClick={() => { setSelectedId(c.id); setDropdownOpen(false) }}
                                        className={`block w-full px-4 py-2.5 text-left text-sm hover:bg-slate-50 ${selectedId === c.id ? "font-semibold text-green-600" : "text-slate-700"}`}
                                    >
                                        <span>{c.name}</span>
                                        <span className="ml-2 text-xs text-slate-500">{c.total_picks} picks</span>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Time Range */}
                    <div className="flex rounded-lg border border-slate-200 bg-white overflow-hidden">
                        {[7, 30, 90].map(d => (
                            <button
                                key={d}
                                onClick={() => setDays(d)}
                                className={`px-3 py-2 text-sm font-medium transition-colors ${days === d ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-50"}`}
                            >
                                {d}d
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Stats Strip */}
            {statsStrip && (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
                    <div className="rounded-xl bg-white p-4 shadow-sm border border-slate-200">
                        <p className="text-xs text-slate-500 uppercase tracking-wide">Profit</p>
                        <p className={`mt-1 text-2xl font-bold ${profitColor(statsStrip.profit)}`}>
                            {fmtProfit(statsStrip.profit)}
                        </p>
                    </div>
                    <div className="rounded-xl bg-white p-4 shadow-sm border border-slate-200">
                        <p className="text-xs text-slate-500 uppercase tracking-wide">Win Rate</p>
                        <p className={`mt-1 text-2xl font-bold ${winRateColor(statsStrip.win_rate)}`}>
                            {statsStrip.win_rate.toFixed(1)}%
                        </p>
                    </div>
                    <div className="rounded-xl bg-white p-4 shadow-sm border border-slate-200">
                        <p className="text-xs text-slate-500 uppercase tracking-wide">ROI</p>
                        <p className={`mt-1 text-2xl font-bold ${profitColor(statsStrip.roi)}`}>
                            {statsStrip.roi > 0 ? "+" : ""}{statsStrip.roi.toFixed(1)}%
                        </p>
                    </div>
                    <div className="rounded-xl bg-white p-4 shadow-sm border border-slate-200">
                        <p className="text-xs text-slate-500 uppercase tracking-wide">Picks</p>
                        <p className="mt-1 text-2xl font-bold text-slate-900">{statsStrip.total_picks}</p>
                        {statsStrip.wins !== null && (
                            <p className="text-xs text-slate-500 mt-0.5">{statsStrip.wins}W · {statsStrip.losses}L</p>
                        )}
                    </div>
                    <div className="rounded-xl bg-white p-4 shadow-sm border border-slate-200">
                        <p className="text-xs text-slate-500 uppercase tracking-wide">Pending</p>
                        <p className="mt-1 text-2xl font-bold text-amber-500">{statsStrip.pending}</p>
                        {statsStrip.pending > 0 && (
                            <Link href="/dashboard/picks" className="text-xs text-slate-500 hover:text-green-600 mt-0.5 block">
                                Grade now →
                            </Link>
                        )}
                    </div>
                </div>
            )}

            {/* Main Chart: Cumulative Profit */}
            <div className="rounded-xl bg-white p-6 shadow-sm border border-slate-200">
                <div className="mb-4 flex items-center justify-between">
                    <h2 className="font-semibold text-slate-900">
                        Cumulative Profit
                        <span className="ml-2 text-sm font-normal text-slate-500">
                            {selectedId === "all" ? `Last ${days} days` : `Last ${days} days · ${selectedCapper?.name}`}
                        </span>
                    </h2>
                    {selectedId !== "all" && filteredHistory.length === 0 && (
                        <span className="text-sm text-slate-500">No graded picks in window</span>
                    )}
                </div>
                <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart
                            data={selectedId === "all" ? overallCumulative : filteredHistory.map(p => ({ name: p.date, cumulative: p.cumulative_profit, profit: p.profit }))}
                            margin={{ top: 5, right: 10, left: 0, bottom: 0 }}
                        >
                            <defs>
                                <linearGradient id="profitGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#16a34a" stopOpacity={0.15} />
                                    <stop offset="95%" stopColor="#16a34a" stopOpacity={0} />
                                </linearGradient>
                                <linearGradient id="profitGradRed" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#dc2626" stopOpacity={0.1} />
                                    <stop offset="95%" stopColor="#dc2626" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} />
                            <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} tickFormatter={v => `${v}u`} />
                            <Tooltip content={<CustomTooltip />} />
                            <ReferenceLine y={0} stroke="#e5e7eb" strokeWidth={1.5} />
                            <Area
                                type="monotone"
                                dataKey="cumulative"
                                name="Cumulative"
                                stroke="#16a34a"
                                strokeWidth={2}
                                fill="url(#profitGrad)"
                                dot={false}
                                activeDot={{ r: 4, strokeWidth: 0 }}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Sport Breakdown + Per-Pick Chart */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* Sport Performance Bar */}
                <div className="rounded-xl bg-white p-6 shadow-sm border border-slate-200">
                    <h2 className="mb-4 font-semibold text-slate-900">
                        Profit by Sport
                        {selectedId !== "all" && <span className="ml-2 text-sm font-normal text-slate-500">{selectedCapper?.name}</span>}
                    </h2>
                    {sportChartData.length === 0 ? (
                        <div className="flex h-48 items-center justify-center text-sm text-slate-500">No data</div>
                    ) : (
                        <div className="h-48">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={sportChartData} layout="vertical" margin={{ left: 0, right: 16, top: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                                    <XAxis type="number" tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} tickFormatter={v => `${v}u`} />
                                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "#6b7280" }} tickLine={false} width={72} />
                                    <Tooltip content={<CustomTooltip />} />
                                    <ReferenceLine x={0} stroke="#e5e7eb" strokeWidth={1.5} />
                                    <Bar dataKey="profit" name="Profit" radius={[0, 4, 4, 0]}>
                                        {sportChartData.map((entry, i) => (
                                            <Cell key={i} fill={entry.profit >= 0 ? "#16a34a" : "#dc2626"} fillOpacity={0.8} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </div>

                {/* Daily picks profit (per-pick for capper, daily bars for all) */}
                <div className="rounded-xl bg-white p-6 shadow-sm border border-slate-200">
                    <h2 className="mb-4 font-semibold text-slate-900">
                        {selectedId === "all" ? `Daily Profit · Last ${days} days` : `Pick Results · ${selectedCapper?.name}`}
                    </h2>
                    {selectedId === "all" ? (
                        <div className="h-48">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={dailyProfit} margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#9ca3af" }} tickLine={false} interval="preserveStartEnd" />
                                    <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} tickFormatter={v => `${v}u`} />
                                    <Tooltip content={<CustomTooltip />} />
                                    <ReferenceLine y={0} stroke="#e5e7eb" />
                                    <Bar dataKey="profit" name="Daily Profit" radius={[3, 3, 0, 0]}>
                                        {dailyProfit.map((entry, i) => (
                                            <Cell key={i} fill={entry.profit >= 0 ? "#16a34a" : "#dc2626"} fillOpacity={0.75} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <div className="h-48">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={filteredHistory} margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#9ca3af" }} tickLine={false} interval="preserveStartEnd" />
                                    <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} tickFormatter={v => `${v}u`} />
                                    <Tooltip content={<CustomTooltip />} />
                                    <ReferenceLine y={0} stroke="#e5e7eb" />
                                    <Bar dataKey="profit" name="Pick Profit" radius={[3, 3, 0, 0]}>
                                        {filteredHistory.map((entry, i) => (
                                            <Cell key={i} fill={entry.profit >= 0 ? "#16a34a" : "#dc2626"} fillOpacity={0.75} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </div>
            </div>

            {/* Sport Stats Table */}
            {sportChartData.length > 0 && (
                <div className="rounded-xl bg-white shadow-sm border border-slate-200 overflow-hidden">
                    <div className="px-6 py-4 border-b border-slate-200">
                        <h2 className="font-semibold text-slate-900">
                            Performance by Sport
                            {selectedId !== "all" && <span className="ml-2 text-sm font-normal text-slate-500">{selectedCapper?.name}</span>}
                        </h2>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-100">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Sport</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Record</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Win Rate</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Profit</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 bg-white">
                                {sportChartData.map((s, i) => (
                                    <tr key={i} className="hover:bg-slate-50">
                                        <td className="whitespace-nowrap px-6 py-3 text-sm font-medium text-slate-900">
                                            <span className="inline-block w-2 h-2 rounded-full mr-2" style={{ backgroundColor: s.color }} />
                                            {s.name}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-3 text-sm text-slate-600">{s.record}</td>
                                        <td className="px-6 py-3">
                                            <div className="flex items-center gap-2">
                                                <div className="flex-1 h-1.5 rounded-full bg-slate-100 min-w-[60px] max-w-[100px]">
                                                    <div
                                                        className="h-1.5 rounded-full"
                                                        style={{
                                                            width: `${Math.min(s.win_rate, 100)}%`,
                                                            backgroundColor: s.win_rate > 55 ? "#16a34a" : s.win_rate < 50 ? "#dc2626" : "#6b7280"
                                                        }}
                                                    />
                                                </div>
                                                <span className={`text-sm font-medium ${winRateColor(s.win_rate)}`}>
                                                    {s.win_rate.toFixed(1)}%
                                                </span>
                                            </div>
                                        </td>
                                        <td className={`whitespace-nowrap px-6 py-3 text-sm font-semibold ${profitColor(s.profit)}`}>
                                            {fmtProfit(s.profit)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Capper-specific: Recent Picks */}
            {selectedId !== "all" && capperDetail && capperDetail.recent_picks.length > 0 && (
                <div className="rounded-xl bg-white shadow-sm border border-slate-200 overflow-hidden">
                    <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
                        <h2 className="font-semibold text-slate-900">Recent Picks · {capperDetail.name}</h2>
                        <Link href={`/dashboard/cappers/${capperDetail.id}`} className="text-sm text-green-600 hover:underline">
                            Full profile →
                        </Link>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-100">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Pick</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Sport</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Units</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Odds</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Result</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-500">Profit</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 bg-white">
                                {capperDetail.recent_picks.map((pick, i) => (
                                    <tr key={i} className="hover:bg-slate-50">
                                        <td className="whitespace-nowrap px-6 py-3 text-xs text-slate-500">
                                            {pick.game_date
                                                ? parseApiDate(pick.game_date).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                                                : parseApiDate(pick.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                                            }
                                        </td>
                                        <td className="px-6 py-3 text-sm text-slate-800 max-w-xs">{pick.pick_text}</td>
                                        <td className="whitespace-nowrap px-6 py-3 text-xs text-slate-500">{pick.sport}</td>
                                        <td className="whitespace-nowrap px-6 py-3 text-xs text-slate-500">{pick.units_risked}u</td>
                                        <td className="whitespace-nowrap px-6 py-3 text-xs text-slate-500">
                                            {pick.odds ? (pick.odds > 0 ? `+${pick.odds}` : pick.odds) : "—"}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-3">
                                            {pick.result === "WIN" && (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                                                    Win
                                                    {pick.grade_source === "espn_api" && <span className="opacity-60">·ESPN</span>}
                                                    {pick.grade_source === "auto_win" && <span className="opacity-60">·Auto</span>}
                                                </span>
                                            )}
                                            {pick.result === "LOSS" && (
                                                <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">Loss</span>
                                            )}
                                            {pick.result === "PUSH" && (
                                                <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">Push</span>
                                            )}
                                            {pick.result === "PENDING" && (
                                                <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">Pending</span>
                                            )}
                                        </td>
                                        <td className={`whitespace-nowrap px-6 py-3 text-sm font-semibold text-right ${profitColor(pick.profit)}`}>
                                            {pick.result === "PENDING" ? "—" : fmtProfit(pick.profit)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* All Cappers overview table */}
            {selectedId === "all" && cappers.length > 0 && (
                <div className="rounded-xl bg-white shadow-sm border border-slate-200 overflow-hidden">
                    <div className="px-6 py-4 border-b border-slate-200">
                        <h2 className="font-semibold text-slate-900">All Cappers Overview</h2>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-100">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Capper</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Picks</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Record</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Win Rate</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">ROI</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Pending</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-500">Profit</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 bg-white">
                                {cappers.map((c) => (
                                    <tr key={c.id} className="hover:bg-slate-50 cursor-pointer" onClick={() => setSelectedId(c.id)}>
                                        <td className="whitespace-nowrap px-6 py-3 text-sm font-medium text-slate-900 hover:text-green-600">
                                            {c.name}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-3 text-sm text-slate-600">{c.total_picks}</td>
                                        <td className="whitespace-nowrap px-6 py-3 text-sm text-slate-600">{c.wins}-{c.losses}-{c.pushes}</td>
                                        <td className="px-6 py-3">
                                            <div className="flex items-center gap-2">
                                                <div className="flex-1 h-1.5 rounded-full bg-slate-100 min-w-[60px] max-w-[100px]">
                                                    <div
                                                        className="h-1.5 rounded-full"
                                                        style={{
                                                            width: `${Math.min(c.total_win_rate, 100)}%`,
                                                            backgroundColor: c.total_win_rate > 55 ? "#16a34a" : c.total_win_rate < 50 ? "#dc2626" : "#6b7280"
                                                        }}
                                                    />
                                                </div>
                                                <span className={`text-sm font-medium ${winRateColor(c.total_win_rate)}`}>
                                                    {c.total_win_rate.toFixed(1)}%
                                                </span>
                                            </div>
                                        </td>
                                        <td className={`whitespace-nowrap px-6 py-3 text-sm font-medium ${profitColor(c.roi)}`}>
                                            {c.roi > 0 ? "+" : ""}{c.roi.toFixed(1)}%
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-3 text-sm text-amber-500">
                                            {c.pending > 0 ? c.pending : "—"}
                                        </td>
                                        <td className={`whitespace-nowrap px-6 py-3 text-sm font-semibold text-right ${profitColor(c.profit)}`}>
                                            {fmtProfit(c.profit)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    )
}
