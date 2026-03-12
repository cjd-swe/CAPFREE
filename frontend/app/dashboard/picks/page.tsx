"use client"

import { useEffect, useState } from "react"
import { CheckCircle, XCircle, MinusCircle, Clock, Trash2, Zap } from "lucide-react"

interface Capper {
    id: number
    name: string
}

interface Pick {
    id: number
    capper_id: number
    capper: Capper
    date: string
    game_date: string | null
    sport: string
    league: string | null
    match_key: string | null
    pick_text: string
    units_risked: number
    odds: number | null
    result: "WIN" | "LOSS" | "PUSH" | "PENDING"
    profit: number
    original_image_path: string | null
    grade_source: string | null
}

interface AutoGradeResult {
    total_pending: number
    graded_by_api: number
    auto_win: number
    skipped_not_final: number
    errors: string[]
}

export default function PicksPage() {
    const [picks, setPicks] = useState<Pick[]>([])
    const [cappers, setCappers] = useState<Capper[]>([])
    const [loading, setLoading] = useState(true)
    const [selectedCapper, setSelectedCapper] = useState<number | "all">("all")
    const [selectedResult, setSelectedResult] = useState<string>("all")
    const [dateRange, setDateRange] = useState<string>("all")
    const [autoGrading, setAutoGrading] = useState(false)
    const [gradeResult, setGradeResult] = useState<AutoGradeResult | null>(null)

    useEffect(() => {
        fetchCappers()
        fetchPicks()
    }, [])

    useEffect(() => {
        fetchPicks()
    }, [selectedCapper])

    const fetchCappers = async () => {
        try {
            const res = await fetch("http://localhost:8000/api/settings/cappers")
            const data = await res.json()
            setCappers(data)
        } catch (err) {
            console.error("Failed to fetch cappers:", err)
        }
    }

    const fetchPicks = async () => {
        try {
            let url = "http://localhost:8000/api/picks/?limit=500"
            if (selectedCapper !== "all") {
                url = `http://localhost:8000/api/picks/by-capper/${selectedCapper}`
            }
            const res = await fetch(url)
            const data = await res.json()
            setPicks(data)
        } catch (err) {
            console.error("Failed to fetch picks:", err)
        } finally {
            setLoading(false)
        }
    }

    const gradePick = async (pickId: number, result: "WIN" | "LOSS" | "PUSH") => {
        try {
            const res = await fetch(`http://localhost:8000/api/picks/${pickId}/grade`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ result })
            })
            if (res.ok) fetchPicks()
        } catch (err) {
            console.error("Failed to grade pick:", err)
        }
    }

    const handleAutoGrade = async () => {
        setAutoGrading(true)
        setGradeResult(null)
        try {
            const res = await fetch("http://localhost:8000/api/picks/auto-grade", { method: "POST" })
            if (res.ok) {
                const data: AutoGradeResult = await res.json()
                setGradeResult(data)
                fetchPicks()
                setTimeout(() => setGradeResult(null), 6000)
            }
        } catch (err) {
            console.error("Auto-grade failed:", err)
        } finally {
            setAutoGrading(false)
        }
    }

    const handleDeletePick = async (pickId: number) => {
        if (!confirm("Are you sure you want to delete this pick?")) return
        try {
            const response = await fetch(`http://localhost:8000/api/picks/${pickId}`, { method: "DELETE" })
            if (response.ok) fetchPicks()
        } catch (err) {
            console.error("Error deleting pick:", err)
        }
    }

    const getResultBadge = (result: string) => {
        switch (result) {
            case "WIN":
                return <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800">
                    <CheckCircle className="h-4 w-4" /> Win
                </span>
            case "LOSS":
                return <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-800">
                    <XCircle className="h-4 w-4" /> Loss
                </span>
            case "PUSH":
                return <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-800">
                    <MinusCircle className="h-4 w-4" /> Push
                </span>
            default:
                return <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-3 py-1 text-sm font-medium text-yellow-800">
                    <Clock className="h-4 w-4" /> Pending
                </span>
        }
    }

    const getGradeSourceBadge = (gradeSource: string | null) => {
        if (!gradeSource) return null
        if (gradeSource === "espn_api") return (
            <span className="ml-1 rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700">ESPN ✓</span>
        )
        if (gradeSource === "auto_win") return (
            <span className="ml-1 rounded bg-orange-100 px-1.5 py-0.5 text-xs font-medium text-orange-700">Auto</span>
        )
        if (gradeSource === "manual") return (
            <span className="ml-1 rounded bg-gray-100 px-1.5 py-0.5 text-xs font-medium text-gray-600">Manual</span>
        )
        return null
    }

    const pendingCount = picks.filter(p => p.result === "PENDING").length

    const filteredPicks = picks.filter(p => {
        if (selectedResult !== "all" && p.result !== selectedResult) return false
        if (dateRange !== "all") {
            const days = parseInt(dateRange)
            const cutoff = new Date()
            cutoff.setDate(cutoff.getDate() - days)
            const pickDate = new Date(p.game_date ?? p.date)
            if (pickDate < cutoff) return false
        }
        return true
    })

    if (loading) return <div className="text-gray-700">Loading...</div>

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold text-gray-900">Picks</h1>
                {pendingCount > 0 && (
                    <button
                        onClick={handleAutoGrade}
                        disabled={autoGrading}
                        className="flex items-center gap-2 rounded-md bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
                    >
                        <Zap className="h-4 w-4" />
                        {autoGrading ? "Grading..." : `Auto-Grade Pending (${pendingCount})`}
                    </button>
                )}
            </div>

            {/* Auto-grade toast */}
            {gradeResult && (
                <div className="fixed bottom-6 right-6 z-50 rounded-lg bg-gray-900 p-4 text-white shadow-xl">
                    <p className="font-semibold">Auto-Grade Complete</p>
                    <p className="mt-1 text-sm text-gray-300">
                        ESPN graded: <span className="text-blue-400 font-medium">{gradeResult.graded_by_api}</span>
                        {" · "}Auto-win: <span className="text-orange-400 font-medium">{gradeResult.auto_win}</span>
                        {" · "}Skipped: <span className="text-gray-400">{gradeResult.skipped_not_final}</span>
                    </p>
                    {gradeResult.errors.length > 0 && (
                        <p className="mt-1 text-xs text-red-400">{gradeResult.errors.length} error(s)</p>
                    )}
                </div>
            )}

            {/* Filters */}
            <div className="flex gap-4 rounded-lg bg-white p-4 shadow">
                <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700">Filter by Capper</label>
                    <select
                        value={selectedCapper}
                        onChange={(e) => setSelectedCapper(e.target.value === "all" ? "all" : Number(e.target.value))}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
                    >
                        <option value="all">All Cappers</option>
                        {cappers.map((capper) => (
                            <option key={capper.id} value={capper.id}>{capper.name}</option>
                        ))}
                    </select>
                </div>
                <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700">Filter by Result</label>
                    <select
                        value={selectedResult}
                        onChange={(e) => setSelectedResult(e.target.value)}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
                    >
                        <option value="all">All Results</option>
                        <option value="PENDING">Pending</option>
                        <option value="WIN">Win</option>
                        <option value="LOSS">Loss</option>
                        <option value="PUSH">Push</option>
                    </select>
                </div>
                <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700">Date Range</label>
                    <select
                        value={dateRange}
                        onChange={(e) => setDateRange(e.target.value)}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
                    >
                        <option value="all">All Time</option>
                        <option value="1">Today</option>
                        <option value="7">Last 7 Days</option>
                        <option value="30">Last 30 Days</option>
                        <option value="90">Last 90 Days</option>
                    </select>
                </div>
            </div>

            {/* Picks Table */}
            <div className="rounded-lg bg-white shadow overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Dates</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Capper</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Sport</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Pick</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Units</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Odds</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Result</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Profit</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 bg-white">
                            {filteredPicks.length === 0 ? (
                                <tr>
                                    <td colSpan={9} className="px-6 py-4 text-center text-gray-700">No picks found</td>
                                </tr>
                            ) : (
                                filteredPicks.map((pick) => (
                                    <tr key={pick.id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 text-sm text-gray-900">
                                            {pick.game_date && (
                                                <div className="font-medium">{new Date(pick.game_date).toLocaleDateString()}</div>
                                            )}
                                            <div className={pick.game_date ? "text-xs text-gray-400" : ""}>
                                                {pick.game_date ? "Added " : ""}{new Date(pick.date).toLocaleDateString()}
                                            </div>
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                                            {pick.capper.name}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">{pick.sport}</td>
                                        <td className="px-6 py-4 text-sm text-gray-900">
                                            <div className="max-w-xs">
                                                {pick.match_key && <div className="font-medium">{pick.match_key}</div>}
                                                <div className="text-gray-600">{pick.pick_text}</div>
                                            </div>
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">{pick.units_risked}u</td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                                            {pick.odds ? (pick.odds > 0 ? `+${pick.odds}` : pick.odds) : "-"}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm">
                                            <div className="flex items-center gap-1">
                                                {getResultBadge(pick.result)}
                                                {pick.result !== "PENDING" && getGradeSourceBadge(pick.grade_source)}
                                            </div>
                                        </td>
                                        <td className={`whitespace-nowrap px-6 py-4 text-sm font-medium ${pick.profit > 0 ? 'text-green-600' : pick.profit < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                                            {pick.profit > 0 ? '+' : ''}{pick.profit.toFixed(2)}u
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm">
                                            <div className="flex gap-1">
                                                {pick.result === "PENDING" && (
                                                    <>
                                                        <button onClick={() => gradePick(pick.id, "WIN")} className="rounded bg-green-100 p-1 text-green-600 hover:bg-green-200" title="Win">
                                                            <CheckCircle className="h-5 w-5" />
                                                        </button>
                                                        <button onClick={() => gradePick(pick.id, "LOSS")} className="rounded bg-red-100 p-1 text-red-600 hover:bg-red-200" title="Loss">
                                                            <XCircle className="h-5 w-5" />
                                                        </button>
                                                        <button onClick={() => gradePick(pick.id, "PUSH")} className="rounded bg-gray-100 p-1 text-gray-600 hover:bg-gray-200" title="Push">
                                                            <MinusCircle className="h-5 w-5" />
                                                        </button>
                                                    </>
                                                )}
                                                <button onClick={() => handleDeletePick(pick.id)} className="rounded bg-red-50 p-1 text-red-600 hover:bg-red-100" title="Delete">
                                                    <Trash2 className="h-5 w-5" />
                                                </button>
                                            </div>
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
