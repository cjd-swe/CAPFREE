"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { ChevronUp, ChevronDown, GitCompare } from "lucide-react"

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
    current_streak: number
}

type SortKey = "name" | "total_picks" | "confirmed_win_rate" | "total_win_rate" | "roi" | "profit" | "pending" | "current_streak"

export default function CappersPage() {
    const [cappers, setCappers] = useState<CapperStat[]>([])
    const [loading, setLoading] = useState(true)
    const [sortKey, setSortKey] = useState<SortKey>("profit")
    const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")

    useEffect(() => {
        fetch("http://localhost:8000/api/analytics/cappers")
            .then((res) => res.json())
            .then((data) => {
                setCappers(data)
                setLoading(false)
            })
            .catch(() => setLoading(false))
    }, [])

    const handleSort = (key: SortKey) => {
        if (sortKey === key) {
            setSortDir(d => d === "asc" ? "desc" : "asc")
        } else {
            setSortKey(key)
            setSortDir("desc")
        }
    }

    const sorted = [...cappers].sort((a, b) => {
        const av = a[sortKey]
        const bv = b[sortKey]
        if (typeof av === "string" && typeof bv === "string") {
            return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av)
        }
        return sortDir === "asc" ? (av as number) - (bv as number) : (bv as number) - (av as number)
    })

    const SortIcon = ({ col }: { col: SortKey }) => {
        if (sortKey !== col) return <ChevronUp className="h-3 w-3 text-slate-500 opacity-0 group-hover:opacity-100" />
        return sortDir === "asc"
            ? <ChevronUp className="h-3 w-3 text-slate-700" />
            : <ChevronDown className="h-3 w-3 text-slate-700" />
    }

    const winRateColor = (rate: number) => {
        if (rate < 50) return "text-red-600"
        if (rate > 55) return "text-green-600"
        return "text-slate-900"
    }

    const Th = ({ col, label }: { col: SortKey, label: string }) => (
        <th
            className="group cursor-pointer px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700 hover:bg-slate-100"
            onClick={() => handleSort(col)}
        >
            <div className="flex items-center gap-1">
                {label}
                <SortIcon col={col} />
            </div>
        </th>
    )

    if (loading) return <div className="text-slate-700">Loading...</div>

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold text-slate-900">Cappers</h1>
                <Link href="/dashboard/cappers/compare" className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50">
                    <GitCompare className="h-4 w-4" /> Compare
                </Link>
            </div>

            <div className="rounded-lg bg-white shadow overflow-hidden">
                {cappers.length === 0 ? (
                    <div className="p-6 text-center text-slate-700">No cappers with picks yet</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-200">
                            <thead className="bg-slate-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">Rank</th>
                                    <Th col="name" label="Name" />
                                    <Th col="total_picks" label="Picks" />
                                    <Th col="confirmed_win_rate" label="Win Rate" />
                                    <Th col="total_win_rate" label="~Win Rate" />
                                    <Th col="roi" label="ROI" />
                                    <Th col="profit" label="Profit" />
                                    <Th col="pending" label="Pending" />
                                    <Th col="current_streak" label="Streak" />
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200 bg-white">
                                {sorted.map((capper, i) => (
                                    <tr key={capper.id} className="hover:bg-slate-50">
                                        <td className="whitespace-nowrap px-4 py-4 text-sm font-medium text-slate-500">
                                            #{i + 1}
                                        </td>
                                        <td className="whitespace-nowrap px-4 py-4">
                                            <Link
                                                href={`/dashboard/cappers/${capper.id}`}
                                                className="text-sm font-semibold text-slate-900 hover:text-green-600"
                                            >
                                                {capper.name}
                                            </Link>
                                            <div className="text-xs text-slate-500">{capper.wins}W-{capper.losses}L-{capper.pushes}P</div>
                                        </td>
                                        <td className="whitespace-nowrap px-4 py-4 text-sm text-slate-700">{capper.total_picks}</td>
                                        <td className={`whitespace-nowrap px-4 py-4 text-sm font-medium ${winRateColor(capper.confirmed_win_rate)}`}>
                                            {capper.confirmed_win_rate.toFixed(1)}%
                                        </td>
                                        <td className={`whitespace-nowrap px-4 py-4 text-sm ${winRateColor(capper.total_win_rate)}`}>
                                            ~{capper.total_win_rate.toFixed(1)}%
                                        </td>
                                        <td className={`whitespace-nowrap px-4 py-4 text-sm font-medium ${capper.roi > 0 ? 'text-green-600' : capper.roi < 0 ? 'text-red-600' : 'text-slate-700'}`}>
                                            {capper.roi > 0 ? '+' : ''}{capper.roi.toFixed(1)}%
                                        </td>
                                        <td className={`whitespace-nowrap px-4 py-4 text-sm font-medium ${capper.profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                            {capper.profit >= 0 ? '+' : ''}{capper.profit.toFixed(2)}u
                                        </td>
                                        <td className="whitespace-nowrap px-4 py-4 text-sm">
                                            {capper.pending > 0 ? (
                                                <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800">
                                                    {capper.pending}
                                                </span>
                                            ) : (
                                                <span className="text-slate-500">—</span>
                                            )}
                                        </td>
                                        <td className="whitespace-nowrap px-4 py-4 text-sm font-medium">
                                            {capper.current_streak === 0 ? (
                                                <span className="text-slate-500">—</span>
                                            ) : capper.current_streak > 0 ? (
                                                <span className="text-green-600">W{capper.current_streak}</span>
                                            ) : (
                                                <span className="text-red-500">L{Math.abs(capper.current_streak)}</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    )
}
