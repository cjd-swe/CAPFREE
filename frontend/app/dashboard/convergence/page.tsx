"use client"

import { useRef, useState } from "react"
import { apiFetch } from "@/lib/api"

interface ConvergenceEntry {
    game: string
    market: string
    dominant_side: string
    dominant_count: number
    total_cappers: number
    share_pct: number
    sides: Record<string, string[]>
    note?: string
    conflict_side?: string
    conflict_count?: number
}

interface RecapRow {
    capper: string
    won: number
    lost: number
    pushed: number
    record: string
}

interface ConvergenceResult {
    date: string
    source: "db" | "telegram_export"
    total_picks: number
    live_messages?: number
    recap_messages?: number
    consensus: ConvergenceEntry[]
    conflicts: ConvergenceEntry[]
    unmatched_count: number
    recap_results?: RecapRow[]
}

function today() {
    return new Date().toISOString().slice(0, 10)
}

function MarketBadge({ market }: { market: string }) {
    const colors: Record<string, string> = {
        spread: "bg-blue-900/40 text-blue-300",
        moneyline: "bg-purple-900/40 text-purple-300",
        over: "bg-emerald-900/40 text-emerald-300",
        under: "bg-orange-900/40 text-orange-300",
        prop: "bg-gray-700 text-gray-300",
    }
    const cls = colors[market] ?? "bg-gray-700 text-gray-300"
    return (
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
            {market}
        </span>
    )
}

function SideList({ sides, highlight }: { sides: Record<string, string[]>; highlight: string }) {
    return (
        <div className="space-y-1">
            {Object.entries(sides).map(([side, cappers]) => (
                <div key={side} className={`text-xs ${side === highlight ? "text-white font-semibold" : "text-gray-400"}`}>
                    <span className="mr-1">{side === highlight ? "▶" : "·"}</span>
                    {side}: {cappers.join(", ")}
                </div>
            ))}
        </div>
    )
}

function ConsensusTable({ rows }: { rows: ConvergenceEntry[] }) {
    if (!rows.length) return <p className="text-gray-500 text-sm">No games with ≥2 cappers on the same side.</p>
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="text-left text-gray-400 border-b border-gray-700">
                        <th className="pb-2 pr-4 font-medium">Game</th>
                        <th className="pb-2 pr-4 font-medium">Market</th>
                        <th className="pb-2 pr-4 font-medium">Side</th>
                        <th className="pb-2 pr-4 font-medium text-right">Cappers</th>
                        <th className="pb-2 font-medium">Who</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((e, i) => (
                        <tr key={i} className="border-b border-gray-800/50">
                            <td className="py-2 pr-4 text-white font-medium">{e.game}</td>
                            <td className="py-2 pr-4"><MarketBadge market={e.market} /></td>
                            <td className="py-2 pr-4 text-emerald-300 font-semibold">
                                {e.dominant_side}
                                {e.note && <span className="ml-2 text-yellow-500 text-xs">⚠ {e.note}</span>}
                            </td>
                            <td className="py-2 pr-4 text-right">
                                <span className="text-white font-bold">{e.dominant_count}</span>
                                <span className="text-gray-500">/{e.total_cappers}</span>
                                <span className="ml-1 text-gray-400 text-xs">({e.share_pct}%)</span>
                            </td>
                            <td className="py-2 text-gray-400 text-xs">{(e.sides[e.dominant_side] ?? []).join(", ")}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

function ConflictTable({ rows }: { rows: ConvergenceEntry[] }) {
    if (!rows.length) return <p className="text-gray-500 text-sm">No games with meaningful capper disagreement.</p>
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="text-left text-gray-400 border-b border-gray-700">
                        <th className="pb-2 pr-4 font-medium">Game</th>
                        <th className="pb-2 pr-4 font-medium">Market</th>
                        <th className="pb-2 pr-4 font-medium">Side A</th>
                        <th className="pb-2 pr-4 font-medium">Side B</th>
                        <th className="pb-2 font-medium">Detail</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((e, i) => (
                        <tr key={i} className="border-b border-gray-800/50">
                            <td className="py-2 pr-4 text-white font-medium">{e.game}</td>
                            <td className="py-2 pr-4"><MarketBadge market={e.market} /></td>
                            <td className="py-2 pr-4">
                                <span className="text-blue-300 font-semibold">{e.dominant_side}</span>
                                <span className="text-gray-500 text-xs ml-1">×{e.dominant_count}</span>
                            </td>
                            <td className="py-2 pr-4">
                                <span className="text-red-300 font-semibold">{e.conflict_side}</span>
                                <span className="text-gray-500 text-xs ml-1">×{e.conflict_count}</span>
                            </td>
                            <td className="py-2">
                                <SideList sides={e.sides} highlight={e.dominant_side} />
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

function RecapTable({ rows }: { rows: RecapRow[] }) {
    if (!rows.length) return null
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="text-left text-gray-400 border-b border-gray-700">
                        <th className="pb-2 pr-4 font-medium">Capper</th>
                        <th className="pb-2 pr-4 font-medium text-right">W</th>
                        <th className="pb-2 pr-4 font-medium text-right">L</th>
                        <th className="pb-2 font-medium text-right">Record</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((r, i) => (
                        <tr key={i} className="border-b border-gray-800/50">
                            <td className="py-1.5 pr-4 text-white">{r.capper}</td>
                            <td className="py-1.5 pr-4 text-right text-emerald-400">{r.won}</td>
                            <td className="py-1.5 pr-4 text-right text-red-400">{r.lost}</td>
                            <td className="py-1.5 text-right text-gray-300 font-mono">{r.record}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

function ResultsPanel({ result }: { result: ConvergenceResult }) {
    return (
        <div className="space-y-6 mt-6">
            <div className="flex flex-wrap gap-4 text-sm text-gray-400">
                <span>Date: <strong className="text-white">{result.date}</strong></span>
                <span>Picks analyzed: <strong className="text-white">{result.total_picks}</strong></span>
                <span>Unmatched: <strong className="text-white">{result.unmatched_count}</strong></span>
                {result.source === "telegram_export" && (
                    <>
                        <span>Live msgs: <strong className="text-white">{result.live_messages}</strong></span>
                        <span>Recaps decoded: <strong className="text-white">{result.recap_messages}</strong></span>
                    </>
                )}
            </div>

            <section>
                <h2 className="text-base font-semibold text-emerald-400 mb-3 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
                    Consensus plays ({result.consensus.length})
                </h2>
                <ConsensusTable rows={result.consensus} />
            </section>

            <section>
                <h2 className="text-base font-semibold text-red-400 mb-3 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
                    Conflict games ({result.conflicts.length})
                </h2>
                <ConflictTable rows={result.conflicts} />
            </section>

            {result.recap_results && result.recap_results.length > 0 && (
                <section>
                    <h2 className="text-base font-semibold text-gray-300 mb-3">
                        Recap results ({result.recap_results.length} cappers)
                    </h2>
                    <RecapTable rows={result.recap_results} />
                </section>
            )}

            <p className="text-xs text-gray-600 border-t border-gray-800 pt-4">
                ⚠ These picks may come from free Telegram repost accounts — not independent
                Vegas sharps. Consensus likely tracks public money. Validate with a backtest
                before acting on any convergence signal.
            </p>
        </div>
    )
}

export default function ConvergencePage() {
    const [tab, setTab] = useState<"daily" | "upload">("daily")
    const [date, setDate] = useState(today())
    const [uploadDate, setUploadDate] = useState(today())
    const [file, setFile] = useState<File | null>(null)
    const [dragOver, setDragOver] = useState(false)
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<ConvergenceResult | null>(null)
    const [error, setError] = useState<string | null>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)

    function reset() {
        setResult(null)
        setError(null)
    }

    async function analyzeDaily() {
        reset()
        setLoading(true)
        try {
            const res = await apiFetch(`/api/convergence/daily?date=${date}`)
            if (!res.ok) throw new Error((await res.json()).detail ?? await res.text())
            setResult(await res.json())
        } catch (e: any) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }

    async function analyzeUpload() {
        if (!file) return
        reset()
        setLoading(true)
        try {
            const fd = new FormData()
            fd.append("file", file)
            const res = await apiFetch(`/api/convergence/upload?date=${uploadDate}`, {
                method: "POST",
                body: fd,
            })
            if (!res.ok) throw new Error((await res.json()).detail ?? await res.text())
            setResult(await res.json())
        } catch (e: any) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }

    function handleDrop(e: React.DragEvent) {
        e.preventDefault()
        setDragOver(false)
        const dropped = e.dataTransfer.files[0]
        if (dropped?.name.endsWith(".zip")) setFile(dropped)
    }

    return (
        <div className="p-6 max-w-5xl mx-auto">
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-white">Convergence</h1>
                <p className="text-gray-400 text-sm mt-1">
                    Find games where multiple cappers agree (consensus) or disagree (conflict).
                </p>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-6 bg-gray-800/50 p-1 rounded-lg w-fit">
                {(["daily", "upload"] as const).map(t => (
                    <button
                        key={t}
                        onClick={() => { setTab(t); reset() }}
                        className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                            tab === t
                                ? "bg-gray-700 text-white"
                                : "text-gray-400 hover:text-white"
                        }`}
                    >
                        {t === "daily" ? "Daily (DB)" : "Telegram Export"}
                    </button>
                ))}
            </div>

            {/* Daily tab */}
            {tab === "daily" && (
                <div className="flex items-end gap-3">
                    <div>
                        <label className="block text-xs text-gray-400 mb-1">Game date</label>
                        <input
                            type="date"
                            value={date}
                            onChange={e => { setDate(e.target.value); reset() }}
                            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm"
                        />
                    </div>
                    <button
                        onClick={analyzeDaily}
                        disabled={loading}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded text-sm font-medium transition-colors"
                    >
                        {loading ? "Analyzing…" : "Analyze"}
                    </button>
                </div>
            )}

            {/* Upload tab */}
            {tab === "upload" && (
                <div className="space-y-4">
                    <p className="text-gray-400 text-sm">
                        Export a Telegram group via <strong className="text-white">Telegram Desktop → ⋮ → Export chat history</strong>,
                        choose HTML format with photos. Then zip the exported folder and upload it here.
                    </p>

                    {/* Drop zone */}
                    <div
                        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                        onDragLeave={() => setDragOver(false)}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
                        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                            dragOver
                                ? "border-blue-500 bg-blue-900/10"
                                : file
                                ? "border-emerald-600 bg-emerald-900/10"
                                : "border-gray-700 hover:border-gray-500"
                        }`}
                    >
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".zip"
                            className="hidden"
                            onChange={e => { const f = e.target.files?.[0]; if (f) setFile(f) }}
                        />
                        {file ? (
                            <p className="text-emerald-400 text-sm">
                                {file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)
                            </p>
                        ) : (
                            <p className="text-gray-500 text-sm">Drop ZIP here or click to browse</p>
                        )}
                    </div>

                    <div className="flex items-end gap-3">
                        <div>
                            <label className="block text-xs text-gray-400 mb-1">Game date</label>
                            <input
                                type="date"
                                value={uploadDate}
                                onChange={e => setUploadDate(e.target.value)}
                                className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm"
                            />
                        </div>
                        <button
                            onClick={analyzeUpload}
                            disabled={!file || loading}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded text-sm font-medium transition-colors"
                        >
                            {loading ? "Processing… (may take a few minutes)" : "Analyze Export"}
                        </button>
                        {file && (
                            <button
                                onClick={() => { setFile(null); reset() }}
                                className="px-3 py-2 text-gray-400 hover:text-white text-sm"
                            >
                                Clear
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Loading spinner */}
            {loading && (
                <div className="mt-8 flex items-center gap-3 text-gray-400">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    {tab === "upload"
                        ? "Running vision extraction on photos — this may take 1-3 minutes…"
                        : "Fetching picks and resolving games…"}
                </div>
            )}

            {/* Error */}
            {error && (
                <div className="mt-6 p-4 bg-red-900/20 border border-red-700 rounded text-red-300 text-sm">
                    {error}
                </div>
            )}

            {/* Results */}
            {result && !loading && <ResultsPanel result={result} />}
        </div>
    )
}
