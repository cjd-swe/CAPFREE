"use client"

import { useEffect, useState } from "react"
import { CheckCircle, XCircle, MinusCircle, Clock, Trash2, Zap, Download, Pencil } from "lucide-react"
import { API_URL, parseApiDate } from "@/lib/api"

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
    const [selectedResult, setSelectedResult] = useState<string>("PENDING")
    const [dateRange, setDateRange] = useState<string>("all")
    const [autoGrading, setAutoGrading] = useState(false)
    const [gradeResult, setGradeResult] = useState<AutoGradeResult | null>(null)
    const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
    const [bulkGrading, setBulkGrading] = useState(false)
    const [bulkDeleting, setBulkDeleting] = useState(false)
    const [editingDateId, setEditingDateId] = useState<number | null>(null)
    const [backfilling, setBackfilling] = useState(false)
    const [backfillResult, setBackfillResult] = useState<{ filled: number; skipped: number } | null>(null)

    useEffect(() => {
        fetchCappers()
        fetchPicks()
    }, [])

    useEffect(() => {
        fetchPicks()
    }, [selectedCapper])

    const fetchCappers = async () => {
        try {
            const res = await fetch(API_URL + "/api/settings/cappers", { credentials: "include" })
            const data = await res.json()
            setCappers(data)
        } catch (err) {
            console.error("Failed to fetch cappers:", err)
        }
    }

    const fetchPicks = async () => {
        try {
            let url = API_URL + "/api/picks/?limit=500"
            if (selectedCapper !== "all") {
                url = `${API_URL}/api/picks/by-capper/${selectedCapper}`
            }
            const res = await fetch(url, { credentials: "include" })
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
            const res = await fetch(`${API_URL}/api/picks/${pickId}/grade`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ result }),
                credentials: "include",
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
            const res = await fetch(API_URL + "/api/picks/auto-grade", { method: "POST", credentials: "include" })
            if (res.ok) {
                const data: AutoGradeResult = await res.json()
                setGradeResult(data)
                fetchPicks()
                setTimeout(() => setGradeResult(null), data.errors.length > 0 ? 15000 : 6000)
            }
        } catch (err) {
            console.error("Auto-grade failed:", err)
        } finally {
            setAutoGrading(false)
        }
    }

    const handleBackfillOdds = async () => {
        setBackfilling(true)
        setBackfillResult(null)
        try {
            const res = await fetch(API_URL + "/api/picks/backfill-odds", { method: "POST", credentials: "include" })
            if (res.ok) {
                const data = await res.json()
                setBackfillResult(data)
                fetchPicks()
                setTimeout(() => setBackfillResult(null), 6000)
            }
        } catch (err) {
            console.error("Backfill odds failed:", err)
        } finally {
            setBackfilling(false)
        }
    }

    const toggleSelect = (id: number) => {
        setSelectedIds(prev => {
            const next = new Set(prev)
            next.has(id) ? next.delete(id) : next.add(id)
            return next
        })
    }

    const selectAllVisible = () => {
        setSelectedIds(new Set(filteredPicks.map(p => p.id)))
    }

    const clearSelection = () => setSelectedIds(new Set())

    const handleBulkDelete = async () => {
        if (selectedIds.size === 0) return
        if (!confirm(`Delete ${selectedIds.size} pick${selectedIds.size > 1 ? "s" : ""}? This cannot be undone.`)) return
        setBulkDeleting(true)
        try {
            const res = await fetch(API_URL + "/api/picks/bulk-delete", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pick_ids: Array.from(selectedIds) }),
                credentials: "include",
            })
            if (res.ok) {
                setSelectedIds(new Set())
                fetchPicks()
            }
        } catch (err) {
            console.error("Bulk delete failed:", err)
        } finally {
            setBulkDeleting(false)
        }
    }

    const handleBulkGrade = async (result: "WIN" | "LOSS" | "PUSH") => {
        if (selectedIds.size === 0) return
        setBulkGrading(true)
        try {
            const res = await fetch(API_URL + "/api/picks/bulk-grade", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pick_ids: Array.from(selectedIds), result }),
                credentials: "include",
            })
            if (res.ok) {
                setSelectedIds(new Set())
                fetchPicks()
            }
        } catch (err) {
            console.error("Bulk grade failed:", err)
        } finally {
            setBulkGrading(false)
        }
    }

    const handleDeletePick = async (pickId: number) => {
        if (!confirm("Are you sure you want to delete this pick?")) return
        try {
            const response = await fetch(`${API_URL}/api/picks/${pickId}`, { method: "DELETE", credentials: "include" })
            if (response.ok) fetchPicks()
        } catch (err) {
            console.error("Error deleting pick:", err)
        }
    }

    const updateGameDate = async (pickId: number, dateValue: string) => {
        if (!dateValue) return
        setEditingDateId(null)
        // optimistic update
        setPicks(prev => prev.map(p => p.id === pickId ? { ...p, game_date: `${dateValue}T12:00:00` } : p))
        try {
            const res = await fetch(`${API_URL}/api/picks/${pickId}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ game_date: `${dateValue}T12:00:00` }),
                credentials: "include",
            })
            if (res.ok) fetchPicks()
        } catch (err) {
            console.error("Failed to update game date:", err)
        }
    }

    const toDateInputValue = (isoStr: string) => {
        const d = parseApiDate(isoStr)
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
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
                return <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-800">
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
            <span className="ml-1 rounded bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-600">Manual</span>
        )
        return null
    }

    const exportCSV = () => {
        const headers = ["Date Added", "Game Date", "Capper", "Sport", "Pick", "Units", "Odds", "Result", "Profit", "Grade Source"]
        const rows = filteredPicks.map(p => [
            parseApiDate(p.date).toLocaleDateString(),
            p.game_date ? parseApiDate(p.game_date).toLocaleDateString() : "",
            p.capper.name,
            p.sport,
            `"${p.pick_text.replace(/"/g, '""')}"`,
            p.units_risked,
            p.odds ?? "",
            p.result,
            p.profit.toFixed(2),
            p.grade_source ?? "",
        ])
        const csv = [headers, ...rows].map(r => r.join(",")).join("\n")
        const blob = new Blob([csv], { type: "text/csv" })
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `picks-${new Date().toISOString().slice(0, 10)}.csv`
        a.click()
        URL.revokeObjectURL(url)
    }

    const pendingCount = picks.filter(p => p.result === "PENDING").length

    const filteredPicks = picks.filter(p => {
        if (selectedResult !== "all" && p.result !== selectedResult) return false
        if (dateRange !== "all") {
            const days = parseInt(dateRange)
            const cutoff = new Date()
            cutoff.setDate(cutoff.getDate() - days)
            const pickDate = parseApiDate(p.game_date ?? p.date)
            if (pickDate < cutoff) return false
        }
        return true
    })

    if (loading) return <div className="text-slate-700">Loading...</div>

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold text-slate-900">Picks</h1>
                <div className="flex items-center gap-2">
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
                    <button
                        onClick={handleBackfillOdds}
                        disabled={backfilling}
                        className="flex items-center gap-2 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                        title="Fill missing odds from ESPN for already-graded picks"
                    >
                        {backfilling ? "Fetching..." : "Backfill Odds"}
                    </button>
                    <button
                        onClick={exportCSV}
                        className="flex items-center gap-2 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                        <Download className="h-4 w-4" />
                        Export CSV
                    </button>
                </div>
            </div>

            {/* Auto-grade toast */}
            {gradeResult && (
                <div className="fixed bottom-6 right-6 z-50 rounded-lg bg-slate-900 p-4 text-white shadow-xl">
                    <p className="font-semibold">Auto-Grade Complete</p>
                    <p className="mt-1 text-sm text-slate-300">
                        ESPN graded: <span className="text-blue-400 font-medium">{gradeResult.graded_by_api}</span>
                        {" · "}Auto-win: <span className="text-orange-400 font-medium">{gradeResult.auto_win}</span>
                        {" · "}Skipped: <span className="text-slate-500">{gradeResult.skipped_not_final}</span>
                    </p>
                    {gradeResult.errors.length > 0 && (
                        <div className="mt-2 space-y-1">
                            {gradeResult.errors.map((e, i) => (
                                <p key={i} className="text-xs text-red-400">{e}</p>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Backfill odds toast */}
            {backfillResult && (
                <div className="fixed bottom-6 right-6 z-50 rounded-lg bg-slate-900 p-4 text-white shadow-xl">
                    <p className="font-semibold">Odds Backfill Complete</p>
                    <p className="mt-1 text-sm text-slate-300">
                        Filled: <span className="text-green-400 font-medium">{backfillResult.filled}</span>
                        {" · "}Skipped: <span className="text-slate-500">{backfillResult.skipped}</span>
                    </p>
                </div>
            )}

            {/* Bulk action bar */}
            {selectedIds.size > 0 && (
                <div className="flex items-center gap-3 rounded-lg bg-slate-900 px-4 py-3 text-white">
                    <span className="text-sm font-medium">{selectedIds.size} selected</span>
                    <div className="flex gap-2 ml-2">
                        <button onClick={() => handleBulkGrade("WIN")} disabled={bulkGrading || bulkDeleting} className="rounded bg-green-600 px-3 py-1.5 text-xs font-semibold hover:bg-green-700 disabled:opacity-50">Win</button>
                        <button onClick={() => handleBulkGrade("LOSS")} disabled={bulkGrading || bulkDeleting} className="rounded bg-red-600 px-3 py-1.5 text-xs font-semibold hover:bg-red-700 disabled:opacity-50">Loss</button>
                        <button onClick={() => handleBulkGrade("PUSH")} disabled={bulkGrading || bulkDeleting} className="rounded bg-gray-600 px-3 py-1.5 text-xs font-semibold hover:bg-slate-500 disabled:opacity-50">Push</button>
                    </div>
                    <div className="mx-2 h-4 w-px bg-slate-600" />
                    <button onClick={handleBulkDelete} disabled={bulkDeleting || bulkGrading} className="flex items-center gap-1.5 rounded bg-red-700 px-3 py-1.5 text-xs font-semibold hover:bg-red-800 disabled:opacity-50">
                        <Trash2 className="h-3.5 w-3.5" />
                        {bulkDeleting ? "Deleting..." : "Delete"}
                    </button>
                    <button onClick={clearSelection} className="ml-auto text-xs text-slate-500 hover:text-white">Clear</button>
                </div>
            )}

            {/* Filters */}
            <div className="flex gap-4 rounded-lg bg-white p-4 shadow">
                <div className="flex-1">
                    <label className="block text-sm font-medium text-slate-700">Filter by Capper</label>
                    <select
                        value={selectedCapper}
                        onChange={(e) => setSelectedCapper(e.target.value === "all" ? "all" : Number(e.target.value))}
                        className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
                    >
                        <option value="all">All Cappers</option>
                        {cappers.map((capper) => (
                            <option key={capper.id} value={capper.id}>{capper.name}</option>
                        ))}
                    </select>
                </div>
                <div className="flex-1">
                    <label className="block text-sm font-medium text-slate-700">Filter by Result</label>
                    <select
                        value={selectedResult}
                        onChange={(e) => setSelectedResult(e.target.value)}
                        className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
                    >
                        <option value="all">All Results</option>
                        <option value="PENDING">Pending</option>
                        <option value="WIN">Win</option>
                        <option value="LOSS">Loss</option>
                        <option value="PUSH">Push</option>
                    </select>
                </div>
                <div className="flex-1">
                    <label className="block text-sm font-medium text-slate-700">Date Range</label>
                    <select
                        value={dateRange}
                        onChange={(e) => setDateRange(e.target.value)}
                        className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
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
                    <table className="min-w-full divide-y divide-slate-200">
                        <thead className="bg-slate-50">
                            <tr>
                                <th className="px-3 py-3 text-left">
                                    <input
                                        type="checkbox"
                                        checked={filteredPicks.length > 0 && filteredPicks.every(p => selectedIds.has(p.id))}
                                        onChange={e => e.target.checked ? selectAllVisible() : clearSelection()}
                                        className="h-4 w-4 rounded border-slate-300 text-green-600 focus:ring-green-500"
                                        title="Select all visible"
                                    />
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Dates</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Capper</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Sport</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Pick</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Units</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Odds</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Result</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Profit</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200 bg-white">
                            {filteredPicks.length === 0 ? (
                                <tr>
                                    <td colSpan={10} className="px-6 py-4 text-center text-slate-700">No picks found</td>
                                </tr>
                            ) : (
                                filteredPicks.map((pick) => (
                                    <tr key={pick.id} className={`hover:bg-slate-50 ${selectedIds.has(pick.id) ? "bg-blue-50" : ""}`}>
                                        <td className="px-3 py-4">
                                            <input
                                                type="checkbox"
                                                checked={selectedIds.has(pick.id)}
                                                onChange={() => toggleSelect(pick.id)}
                                                className="h-4 w-4 rounded border-slate-300 text-green-600 focus:ring-green-500"
                                            />
                                        </td>
                                        <td className="px-6 py-4 text-sm text-slate-900">
                                            {editingDateId === pick.id ? (
                                                <input
                                                    type="date"
                                                    autoFocus
                                                    defaultValue={toDateInputValue(pick.game_date ?? pick.date)}
                                                    className="rounded border border-slate-300 px-2 py-1 text-sm focus:border-green-500 focus:outline-none"
                                                    onChange={e => updateGameDate(pick.id, e.target.value)}
                                                    onKeyDown={e => {
                                                        if (e.key === "Escape") setEditingDateId(null)
                                                    }}
                                                />
                                            ) : (
                                                <div className="group flex items-center gap-1">
                                                    <div>
                                                        {pick.game_date && (
                                                            <div className="font-medium">{parseApiDate(pick.game_date).toLocaleDateString()}</div>
                                                        )}
                                                        <div className={pick.game_date ? "text-xs text-slate-500" : ""}>
                                                            {pick.game_date ? "Added " : ""}{parseApiDate(pick.date).toLocaleDateString()}
                                                        </div>
                                                    </div>
                                                    <button
                                                        onClick={() => setEditingDateId(pick.id)}
                                                        className="invisible rounded p-0.5 text-slate-400 hover:text-slate-600 group-hover:visible"
                                                        title="Edit game date"
                                                    >
                                                        <Pencil className="h-3.5 w-3.5" />
                                                    </button>
                                                </div>
                                            )}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-slate-900">
                                            {pick.capper.name}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-900">{pick.sport}</td>
                                        <td className="px-6 py-4 text-sm text-slate-900">
                                            <div className="max-w-xs">
                                                {pick.match_key && <div className="font-medium">{pick.match_key}</div>}
                                                <div className="text-slate-600">{pick.pick_text}</div>
                                            </div>
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-900">{pick.units_risked}u</td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-900">
                                            {pick.odds ? (pick.odds > 0 ? `+${pick.odds}` : pick.odds) : "-"}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm">
                                            <div className="flex items-center gap-1">
                                                {getResultBadge(pick.result)}
                                                {pick.result !== "PENDING" && getGradeSourceBadge(pick.grade_source)}
                                            </div>
                                        </td>
                                        <td className={`whitespace-nowrap px-6 py-4 text-sm font-medium ${pick.profit > 0 ? 'text-green-600' : pick.profit < 0 ? 'text-red-600' : 'text-slate-900'}`}>
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
                                                        <button onClick={() => gradePick(pick.id, "PUSH")} className="rounded bg-slate-100 p-1 text-slate-600 hover:bg-slate-200" title="Push">
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
