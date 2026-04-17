"use client"

import { useEffect, useState, useMemo } from "react"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import {
    RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
    Tooltip
} from "recharts"
import { API_URL, parseApiDate } from "@/lib/api"

interface CapperStat {
    id: number
    name: string
    profit: number
    roi: number
    confirmed_win_rate: number
    total_win_rate: number
    total_picks: number
    wins: number
    losses: number
    pushes: number
    pending: number
    current_streak: number
}

interface ProfitEntry {
    date: string
    profit: number
    cumulative_profit: number
    result: string
    sport: string
    units_risked: number
}

function periodStats(history: ProfitEntry[], days: number) {
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - days)
    const slice = history.filter(p => parseApiDate(p.date) >= cutoff)
    if (!slice.length) return null
    const wins = slice.filter(p => p.result === "WIN").length
    const losses = slice.filter(p => p.result === "LOSS").length
    const graded = wins + losses + slice.filter(p => p.result === "PUSH").length
    const profit = slice.reduce((s, p) => s + p.profit, 0)
    const units = slice.reduce((s, p) => s + p.units_risked, 0)
    return {
        wins, losses,
        profit: parseFloat(profit.toFixed(2)),
        win_rate: graded > 0 ? parseFloat((wins / graded * 100).toFixed(1)) : 0,
        roi: units > 0 ? parseFloat((profit / units * 100).toFixed(1)) : 0,
    }
}

function StatRow({ label, a, b, format = (v: number) => String(v), higherIsBetter = true }: {
    label: string
    a: number | null
    b: number | null
    format?: (v: number) => string
    higherIsBetter?: boolean
}) {
    const aWins = a !== null && b !== null && (higherIsBetter ? a > b : a < b)
    const bWins = a !== null && b !== null && (higherIsBetter ? b > a : b < a)
    return (
        <tr className="border-b border-slate-200">
            <td className={`py-3 pl-4 pr-2 text-right text-sm font-semibold ${aWins ? "text-green-600" : "text-slate-900"}`}>
                {a !== null ? format(a) : "—"}
                {aWins && <span className="ml-1 text-green-500">◀</span>}
            </td>
            <td className="py-3 px-4 text-center text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</td>
            <td className={`py-3 pr-4 pl-2 text-left text-sm font-semibold ${bWins ? "text-green-600" : "text-slate-900"}`}>
                {bWins && <span className="mr-1 text-green-500">▶</span>}
                {b !== null ? format(b) : "—"}
            </td>
        </tr>
    )
}

export default function ComparePage() {
    const [cappers, setCappers] = useState<CapperStat[]>([])
    const [selectedA, setSelectedA] = useState<number | "">("")
    const [selectedB, setSelectedB] = useState<number | "">("")
    const [historyA, setHistoryA] = useState<ProfitEntry[]>([])
    const [historyB, setHistoryB] = useState<ProfitEntry[]>([])
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        fetch(API_URL + "/api/analytics/cappers", { credentials: "include" })
            .then(r => r.json())
            .then(setCappers)
    }, [])

    useEffect(() => {
        if (!selectedA) { setHistoryA([]); return }
        fetch(`${API_URL}/api/analytics/capper/${selectedA}/profit-history`, { credentials: "include" })
            .then(r => r.json()).then(setHistoryA).catch(() => setHistoryA([]))
    }, [selectedA])

    useEffect(() => {
        if (!selectedB) { setHistoryB([]); return }
        fetch(`${API_URL}/api/analytics/capper/${selectedB}/profit-history`, { credentials: "include" })
            .then(r => r.json()).then(setHistoryB).catch(() => setHistoryB([]))
    }, [selectedB])

    const capperA = cappers.find(c => c.id === Number(selectedA))
    const capperB = cappers.find(c => c.id === Number(selectedB))

    const p7A = useMemo(() => selectedA && historyA.length ? periodStats(historyA, 7) : null, [historyA, selectedA])
    const p30A = useMemo(() => selectedA && historyA.length ? periodStats(historyA, 30) : null, [historyA, selectedA])
    const p7B = useMemo(() => selectedB && historyB.length ? periodStats(historyB, 7) : null, [historyB, selectedB])
    const p30B = useMemo(() => selectedB && historyB.length ? periodStats(historyB, 30) : null, [historyB, selectedB])

    // Radar chart data — normalize each metric 0-100
    const radarData = useMemo(() => {
        if (!capperA || !capperB) return []
        const maxProfit = Math.max(Math.abs(capperA.profit), Math.abs(capperB.profit), 1)
        const maxROI = Math.max(Math.abs(capperA.roi), Math.abs(capperB.roi), 1)
        return [
            { metric: "Win Rate", A: capperA.confirmed_win_rate, B: capperB.confirmed_win_rate },
            { metric: "ROI", A: Math.max(0, capperA.roi / maxROI * 100), B: Math.max(0, capperB.roi / maxROI * 100) },
            { metric: "Profit", A: Math.max(0, capperA.profit / maxProfit * 100), B: Math.max(0, capperB.profit / maxProfit * 100) },
            { metric: "Volume", A: Math.min(capperA.total_picks, 100), B: Math.min(capperB.total_picks, 100) },
        ]
    }, [capperA, capperB])

    const fmtPct = (v: number) => `${v > 0 ? "+" : ""}${v}%`
    const fmtU = (v: number) => `${v > 0 ? "+" : ""}${v.toFixed(2)}u`

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <Link href="/dashboard/cappers" className="rounded-lg p-2 hover:bg-slate-200">
                    <ArrowLeft className="h-6 w-6 text-slate-600" />
                </Link>
                <h1 className="text-2xl font-bold text-slate-900">Compare Cappers</h1>
            </div>

            {/* Capper Selectors */}
            <div className="grid grid-cols-2 gap-4">
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Capper A</label>
                    <select
                        value={selectedA}
                        onChange={e => setSelectedA(e.target.value ? Number(e.target.value) : "")}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
                    >
                        <option value="">Select capper...</option>
                        {cappers.filter(c => c.id !== Number(selectedB)).map(c => (
                            <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                    </select>
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Capper B</label>
                    <select
                        value={selectedB}
                        onChange={e => setSelectedB(e.target.value ? Number(e.target.value) : "")}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
                    >
                        <option value="">Select capper...</option>
                        {cappers.filter(c => c.id !== Number(selectedA)).map(c => (
                            <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                    </select>
                </div>
            </div>

            {(!selectedA || !selectedB) && (
                <div className="rounded-xl bg-slate-50 border border-slate-200 p-12 text-center text-slate-500 text-sm">
                    Select two cappers above to compare them
                </div>
            )}

            {capperA && capperB && (
                <>
                    {/* Header names */}
                    <div className="grid grid-cols-[1fr_120px_1fr] items-center">
                        <Link href={`/dashboard/cappers/${capperA.id}`} className="text-xl font-bold text-slate-900 hover:text-green-600 text-right pr-4">
                            {capperA.name}
                        </Link>
                        <div className="text-center text-xs font-semibold text-slate-500 uppercase tracking-widest">vs</div>
                        <Link href={`/dashboard/cappers/${capperB.id}`} className="text-xl font-bold text-slate-900 hover:text-green-600 pl-4">
                            {capperB.name}
                        </Link>
                    </div>

                    {/* Stats comparison table */}
                    <div className="rounded-xl bg-white shadow-sm border border-slate-200 overflow-hidden">
                        <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">All-Time</p>
                        </div>
                        <table className="w-full">
                            <tbody>
                                <StatRow label="Picks" a={capperA.total_picks} b={capperB.total_picks} format={v => String(v)} />
                                <StatRow label="Record" a={capperA.wins} b={capperB.wins}
                                    format={(v) => {
                                        const c = v === capperA.wins ? capperA : capperB
                                        return `${c.wins}W-${c.losses}L-${c.pushes}P`
                                    }} />
                                <StatRow label="Win Rate" a={capperA.confirmed_win_rate} b={capperB.confirmed_win_rate} format={v => `${v.toFixed(1)}%`} />
                                <StatRow label="~Win Rate" a={capperA.total_win_rate} b={capperB.total_win_rate} format={v => `~${v.toFixed(1)}%`} />
                                <StatRow label="ROI" a={capperA.roi} b={capperB.roi} format={v => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`} />
                                <StatRow label="Profit" a={capperA.profit} b={capperB.profit} format={fmtU} />
                                <StatRow label="Streak" a={capperA.current_streak} b={capperB.current_streak}
                                    format={v => v > 0 ? `W${v}` : v < 0 ? `L${Math.abs(v)}` : "—"} />
                            </tbody>
                        </table>
                    </div>

                    {/* Recent period stats */}
                    {(p7A || p7B || p30A || p30B) && (
                        <div className="rounded-xl bg-white shadow-sm border border-slate-200 overflow-hidden">
                            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Recent Form</p>
                            </div>
                            <table className="w-full">
                                <thead>
                                    <tr className="border-b border-slate-200">
                                        <th className="py-2 px-4 text-right text-xs text-slate-500">{capperA.name}</th>
                                        <th className="py-2 px-4 text-center text-xs text-slate-500"></th>
                                        <th className="py-2 px-4 text-left text-xs text-slate-500">{capperB.name}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr className="bg-slate-50"><td colSpan={3} className="px-4 py-1 text-xs font-semibold text-slate-500">Last 7 days</td></tr>
                                    <StatRow label="Win Rate" a={p7A?.win_rate ?? null} b={p7B?.win_rate ?? null} format={v => `${v}%`} />
                                    <StatRow label="ROI" a={p7A?.roi ?? null} b={p7B?.roi ?? null} format={fmtPct} />
                                    <StatRow label="Profit" a={p7A?.profit ?? null} b={p7B?.profit ?? null} format={fmtU} />
                                    <tr className="bg-slate-50"><td colSpan={3} className="px-4 py-1 text-xs font-semibold text-slate-500">Last 30 days</td></tr>
                                    <StatRow label="Win Rate" a={p30A?.win_rate ?? null} b={p30B?.win_rate ?? null} format={v => `${v}%`} />
                                    <StatRow label="ROI" a={p30A?.roi ?? null} b={p30B?.roi ?? null} format={fmtPct} />
                                    <StatRow label="Profit" a={p30A?.profit ?? null} b={p30B?.profit ?? null} format={fmtU} />
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Radar chart */}
                    {radarData.length > 0 && (
                        <div className="rounded-xl bg-white shadow-sm border border-slate-200 p-6">
                            <h2 className="mb-2 text-sm font-semibold text-slate-700">Overall Profile</h2>
                            <div className="h-64">
                                <ResponsiveContainer width="100%" height="100%">
                                    <RadarChart data={radarData}>
                                        <PolarGrid stroke="#e5e7eb" />
                                        <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12, fill: "#6b7280" }} />
                                        <Radar name={capperA.name} dataKey="A" stroke="#16a34a" fill="#16a34a" fillOpacity={0.15} strokeWidth={2} />
                                        <Radar name={capperB.name} dataKey="B" stroke="#2563eb" fill="#2563eb" fillOpacity={0.15} strokeWidth={2} />
                                        <Tooltip />
                                    </RadarChart>
                                </ResponsiveContainer>
                            </div>
                            <div className="mt-2 flex justify-center gap-6 text-xs text-slate-500">
                                <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 bg-green-600" />{capperA.name}</span>
                                <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 bg-blue-600" />{capperB.name}</span>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}
