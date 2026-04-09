"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, TrendingUp, TrendingDown, Trophy, Target } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"
import { API_URL } from "@/lib/api"

interface Pick {
    id: number
    date: string
    sport: string
    pick_text: string
    units_risked: number
    odds: number | null
    result: string
    profit: number
}

interface SportPerformance {
    wins: number
    losses: number
    pushes: number
    profit: number
    total: number
}

interface CapperAnalytics {
    id: number
    name: string
    notes: string | null
    total_picks: number
    wins: number
    losses: number
    pushes: number
    pending: number
    win_rate: number
    roi: number
    total_profit: number
    total_units_risked: number
    recent_picks: Pick[]
    sport_performance: Record<string, SportPerformance>
}

interface ProfitHistoryEntry {
    date: string
    pick_text: string
    result: string
    grade_source: string | null
    profit: number
    cumulative_profit: number
    sport: string
    units_risked: number
}

function periodStats(history: ProfitHistoryEntry[], days: number) {
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - days)
    const slice = history.filter(p => new Date(p.date) >= cutoff)
    if (!slice.length) return null
    const wins = slice.filter(p => p.result === "WIN").length
    const losses = slice.filter(p => p.result === "LOSS").length
    const graded = wins + losses + slice.filter(p => p.result === "PUSH").length
    const profit = slice.reduce((s, p) => s + p.profit, 0)
    const units = slice.reduce((s, p) => s + p.units_risked, 0)
    return {
        picks: slice.length,
        wins,
        losses,
        profit: parseFloat(profit.toFixed(2)),
        win_rate: graded > 0 ? parseFloat((wins / graded * 100).toFixed(1)) : 0,
        roi: units > 0 ? parseFloat((profit / units * 100).toFixed(1)) : 0,
    }
}

export default function CapperAnalyticsPage() {
    const params = useParams()
    const capperId = params.id as string
    const [analytics, setAnalytics] = useState<CapperAnalytics | null>(null)
    const [profitHistory, setProfitHistory] = useState<ProfitHistoryEntry[]>([])
    const [loading, setLoading] = useState(true)
    const [notes, setNotes] = useState("")
    const [editingNotes, setEditingNotes] = useState(false)
    const [savingNotes, setSavingNotes] = useState(false)

    useEffect(() => {
        Promise.all([
            fetch(`${API_URL}/api/analytics/capper/${capperId}`).then(r => r.json()),
            fetch(`${API_URL}/api/analytics/capper/${capperId}/profit-history`).then(r => r.json()),
        ]).then(([analyticsData, historyData]) => {
            setAnalytics(analyticsData)
            setNotes(analyticsData.notes ?? "")
            setProfitHistory(historyData)
            setLoading(false)
        }).catch(() => setLoading(false))
    }, [capperId])

    const saveNotes = async () => {
        setSavingNotes(true)
        try {
            await fetch(`${API_URL}/api/settings/cappers/${capperId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ notes }),
            })
            setEditingNotes(false)
        } finally {
            setSavingNotes(false)
        }
    }

    if (loading) return <div className="text-slate-700">Loading...</div>
    if (!analytics) return <div className="text-slate-700">Capper not found</div>

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link href="/dashboard/cappers" className="rounded-lg p-2 hover:bg-slate-200">
                    <ArrowLeft className="h-6 w-6 text-slate-600" />
                </Link>
                <h1 className="text-3xl font-bold text-slate-900">{analytics.name}</h1>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-lg bg-white p-6 shadow">
                    <div className="flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-green-600" />
                        <h3 className="text-sm font-medium text-slate-700">Total Profit</h3>
                    </div>
                    <p className={`mt-2 text-3xl font-bold ${analytics.total_profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {analytics.total_profit >= 0 ? '+' : ''}{analytics.total_profit}u
                    </p>
                </div>

                <div className="rounded-lg bg-white p-6 shadow">
                    <div className="flex items-center gap-2">
                        <Trophy className="h-5 w-5 text-yellow-600" />
                        <h3 className="text-sm font-medium text-slate-700">Win Rate</h3>
                    </div>
                    <p className="mt-2 text-3xl font-bold text-slate-900">{analytics.win_rate}%</p>
                    <p className="mt-1 text-sm text-slate-700">
                        {analytics.wins}W - {analytics.losses}L - {analytics.pushes}P
                    </p>
                </div>

                <div className="rounded-lg bg-white p-6 shadow">
                    <div className="flex items-center gap-2">
                        <Target className="h-5 w-5 text-blue-600" />
                        <h3 className="text-sm font-medium text-slate-700">ROI</h3>
                    </div>
                    <p className="mt-2 text-3xl font-bold text-blue-600">{analytics.roi}%</p>
                </div>

                <div className="rounded-lg bg-white p-6 shadow">
                    <h3 className="text-sm font-medium text-slate-700">Total Picks</h3>
                    <p className="mt-2 text-3xl font-bold text-slate-900">{analytics.total_picks}</p>
                    {analytics.pending > 0 && (
                        <p className="mt-1 text-sm text-yellow-600">{analytics.pending} pending</p>
                    )}
                </div>
            </div>

            {/* Notes */}
            <div className="rounded-lg bg-white shadow p-6">
                <div className="flex items-center justify-between mb-3">
                    <h2 className="text-lg font-medium text-slate-900">Notes</h2>
                    {!editingNotes ? (
                        <button onClick={() => setEditingNotes(true)} className="text-xs text-slate-500 hover:text-slate-800 border border-slate-200 rounded px-2 py-1">Edit</button>
                    ) : (
                        <div className="flex gap-2">
                            <button onClick={saveNotes} disabled={savingNotes} className="text-xs bg-green-600 text-white rounded px-3 py-1 hover:bg-green-700 disabled:opacity-50">Save</button>
                            <button onClick={() => { setNotes(analytics.notes ?? ""); setEditingNotes(false) }} className="text-xs text-slate-500 hover:text-slate-800 border border-slate-200 rounded px-2 py-1">Cancel</button>
                        </div>
                    )}
                </div>
                {editingNotes ? (
                    <textarea
                        value={notes}
                        onChange={e => setNotes(e.target.value)}
                        rows={4}
                        placeholder="Add notes about this capper's style, track record, specialties..."
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-green-500 focus:outline-none focus:ring-green-500 resize-none"
                    />
                ) : (
                    <p className={`text-sm ${notes ? "text-slate-700 whitespace-pre-wrap" : "text-slate-500 italic"}`}>
                        {notes || "No notes yet. Click Edit to add some."}
                    </p>
                )}
            </div>

            {/* Period Breakdown */}
            {profitHistory.length > 0 && (() => {
                const periods = [
                    { label: "Last 7 days", days: 7 },
                    { label: "Last 30 days", days: 30 },
                    { label: "Last 90 days", days: 90 },
                ]
                const rows = periods.map(p => ({ ...p, stats: periodStats(profitHistory, p.days) })).filter(p => p.stats)
                if (!rows.length) return null
                return (
                    <div className="rounded-lg bg-white shadow overflow-hidden">
                        <div className="border-b border-slate-200 px-6 py-4">
                            <h2 className="text-lg font-medium text-slate-900">Performance by Period</h2>
                        </div>
                        <table className="min-w-full divide-y divide-slate-200">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Period</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Record</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Win Rate</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">ROI</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-500">Profit</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200 bg-white">
                                {rows.map(({ label, stats }) => (
                                    <tr key={label} className="hover:bg-slate-50">
                                        <td className="whitespace-nowrap px-6 py-3 text-sm font-medium text-slate-900">{label}</td>
                                        <td className="whitespace-nowrap px-6 py-3 text-sm text-slate-600">{stats!.wins}W-{stats!.losses}L</td>
                                        <td className={`whitespace-nowrap px-6 py-3 text-sm font-medium ${stats!.win_rate > 55 ? "text-green-600" : stats!.win_rate < 50 ? "text-red-500" : "text-slate-900"}`}>
                                            {stats!.win_rate}%
                                        </td>
                                        <td className={`whitespace-nowrap px-6 py-3 text-sm font-medium ${stats!.roi > 0 ? "text-green-600" : stats!.roi < 0 ? "text-red-500" : "text-slate-900"}`}>
                                            {stats!.roi > 0 ? "+" : ""}{stats!.roi}%
                                        </td>
                                        <td className={`whitespace-nowrap px-6 py-3 text-sm font-semibold text-right ${stats!.profit > 0 ? "text-green-600" : stats!.profit < 0 ? "text-red-500" : "text-slate-900"}`}>
                                            {stats!.profit > 0 ? "+" : ""}{stats!.profit}u
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )
            })()}

            {/* Profit Over Time Chart */}
            {profitHistory.length > 1 && (
                <div className="rounded-lg bg-white p-6 shadow">
                    <h2 className="mb-4 text-lg font-medium text-slate-900">Profit Over Time</h2>
                    <div className="h-72 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={profitHistory}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                                <YAxis />
                                <Tooltip
                                    formatter={(value: number) => [`${value > 0 ? '+' : ''}${value.toFixed(2)}u`, "Cumulative Profit"]}
                                />
                                <ReferenceLine y={0} stroke="#6b7280" strokeDasharray="4 4" />
                                <Line
                                    type="monotone"
                                    dataKey="cumulative_profit"
                                    stroke="#16a34a"
                                    strokeWidth={2}
                                    dot={false}
                                    activeDot={{ r: 5 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}

            {/* Performance by Sport */}
            <div className="rounded-lg bg-white shadow">
                <div className="border-b border-slate-200 px-6 py-4">
                    <h2 className="text-lg font-medium text-slate-900">Performance by Sport</h2>
                </div>
                <div className="p-6">
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {Object.entries(analytics.sport_performance).map(([sport, perf]) => {
                            const winRate = perf.total > 0 ? ((perf.wins / perf.total) * 100).toFixed(1) : '0.0'
                            return (
                                <div key={sport} className="rounded-lg border border-slate-200 p-4">
                                    <h3 className="font-semibold text-slate-900">{sport}</h3>
                                    <div className="mt-2 space-y-1 text-sm">
                                        <div className="flex justify-between">
                                            <span className="text-slate-600">Record:</span>
                                            <span className="font-medium">{perf.wins}-{perf.losses}-{perf.pushes}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-slate-600">Win Rate:</span>
                                            <span className="font-medium">{winRate}%</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-slate-600">Profit:</span>
                                            <span className={`font-medium ${perf.profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                                {perf.profit >= 0 ? '+' : ''}{perf.profit.toFixed(2)}u
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            </div>

            {/* Recent Picks */}
            <div className="rounded-lg bg-white shadow">
                <div className="border-b border-slate-200 px-6 py-4">
                    <h2 className="text-lg font-medium text-slate-900">Recent Picks</h2>
                </div>
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-200">
                        <thead className="bg-slate-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Date</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Sport</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Pick</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Units</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Result</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Profit</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200 bg-white">
                            {analytics.recent_picks.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-4 text-center text-slate-700">No picks yet</td>
                                </tr>
                            ) : (
                                analytics.recent_picks.map((pick) => (
                                    <tr key={pick.id}>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-900">
                                            {new Date(pick.date).toLocaleDateString()}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-900">{pick.sport}</td>
                                        <td className="px-6 py-4 text-sm text-slate-900">{pick.pick_text}</td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-900">{pick.units_risked}u</td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm">
                                            <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${pick.result === 'WIN' ? 'bg-green-100 text-green-800' :
                                                pick.result === 'LOSS' ? 'bg-red-100 text-red-800' :
                                                    pick.result === 'PUSH' ? 'bg-slate-100 text-slate-800' :
                                                        'bg-yellow-100 text-yellow-800'
                                                }`}>
                                                {pick.result}
                                            </span>
                                        </td>
                                        <td className={`whitespace-nowrap px-6 py-4 text-sm font-medium ${pick.profit > 0 ? 'text-green-600' : pick.profit < 0 ? 'text-red-600' : 'text-slate-900'}`}>
                                            {pick.profit > 0 ? '+' : ''}{pick.profit.toFixed(2)}u
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}
