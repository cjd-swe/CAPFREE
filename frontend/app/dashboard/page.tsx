"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Zap, TrendingUp, TrendingDown, CheckCircle, XCircle, MinusCircle, Clock, ArrowRight, Bell, Users } from "lucide-react"
import { API_URL, parseApiDate } from "@/lib/api"

interface SummaryStats {
    total_profit: number
    win_rate: number
    roi: number
    active_cappers: number
    total_picks: number
    pending_picks: number
}

interface CapperStat {
    id: number
    name: string
    profit: number
    roi: number
    confirmed_win_rate: number
    total_picks: number
    wins: number
    losses: number
    pushes: number
    pending: number
}

interface Notification {
    id: number
    pick_id: number | null
    message: string
    read: boolean
    created_at: string
}

interface AutoGradeResult {
    total_pending: number
    graded_by_api: number
    auto_win: number
    skipped_not_final: number
    errors: string[]
}

export default function DashboardPage() {
    const [stats, setStats] = useState<SummaryStats | null>(null)
    const [cappers, setCappers] = useState<CapperStat[]>([])
    const [recentPicks, setRecentPicks] = useState<any[]>([])
    const [notifications, setNotifications] = useState<Notification[]>([])
    const [loading, setLoading] = useState(true)
    const [autoGrading, setAutoGrading] = useState(false)
    const [gradeResult, setGradeResult] = useState<AutoGradeResult | null>(null)

    useEffect(() => {
        Promise.all([
            fetch(API_URL + "/api/analytics/summary", { credentials: "include" }).then(r => r.json()),
            fetch(API_URL + "/api/analytics/cappers", { credentials: "include" }).then(r => r.json()),
            fetch(API_URL + "/api/picks/?limit=10", { credentials: "include" }).then(r => r.json()),
            fetch(API_URL + "/api/notifications/", { credentials: "include" }).then(r => r.json()),
        ]).then(([summaryData, cappersData, picksData, notifsData]) => {
            setStats(summaryData)
            setCappers(cappersData.slice(0, 5))
            setRecentPicks(picksData)
            setNotifications(notifsData)
            setLoading(false)
        }).catch(() => setLoading(false))
    }, [])

    const refreshAll = () => {
        Promise.all([
            fetch(API_URL + "/api/analytics/summary", { credentials: "include" }).then(r => r.json()),
            fetch(API_URL + "/api/analytics/cappers", { credentials: "include" }).then(r => r.json()),
            fetch(API_URL + "/api/picks/?limit=10", { credentials: "include" }).then(r => r.json()),
            fetch(API_URL + "/api/notifications/", { credentials: "include" }).then(r => r.json()),
        ]).then(([summaryData, cappersData, picksData, notifsData]) => {
            setStats(summaryData)
            setCappers(cappersData.slice(0, 5))
            setRecentPicks(picksData)
            setNotifications(notifsData)
        })
    }

    const handleAutoGrade = async () => {
        setAutoGrading(true)
        setGradeResult(null)
        try {
            const res = await fetch(API_URL + "/api/picks/auto-grade", { method: "POST", credentials: "include" })
            if (res.ok) {
                const data: AutoGradeResult = await res.json()
                setGradeResult(data)
                refreshAll()
                setTimeout(() => setGradeResult(null), 8000)
            }
        } catch (err) {
            console.error("Auto-grade failed:", err)
        } finally {
            setAutoGrading(false)
        }
    }

    const handleMarkAllRead = async () => {
        await fetch(API_URL + "/api/notifications/read-all", { method: "POST", credentials: "include" })
        fetch(API_URL + "/api/notifications/", { credentials: "include" }).then(r => r.json()).then(setNotifications)
    }

    const timeAgo = (dateStr: string) => {
        const diff = Date.now() - parseApiDate(dateStr).getTime()
        const mins = Math.floor(diff / 60000)
        if (mins < 1) return "just now"
        if (mins < 60) return `${mins}m ago`
        const hrs = Math.floor(mins / 60)
        if (hrs < 24) return `${hrs}h ago`
        return `${Math.floor(hrs / 24)}d ago`
    }

    const winRateColor = (rate: number) => {
        if (rate >= 55) return "text-green-600"
        if (rate < 50) return "text-red-500"
        return "text-slate-900"
    }

    if (loading) {
        return (
            <div className="flex h-64 items-center justify-center">
                <div className="text-slate-500">Loading...</div>
            </div>
        )
    }

    const profit = stats?.total_profit ?? 0
    const pending = stats?.pending_picks ?? 0
    const totalPicks = stats?.total_picks ?? 0
    const graded = totalPicks - pending
    const wins = Math.round((stats?.win_rate ?? 0) * graded / 100)
    const unreadCount = notifications.filter(n => !n.read).length
    const unreadNotifs = notifications.filter(n => !n.read).slice(0, 4)
    const hasActivity = notifications.length > 0

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
                {pending > 0 && !gradeResult && (
                    <button
                        onClick={handleAutoGrade}
                        disabled={autoGrading}
                        className="flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-purple-700 disabled:opacity-60 transition-colors"
                    >
                        <Zap className="h-4 w-4" />
                        {autoGrading ? "Grading…" : `Auto-Grade ${pending} Pending`}
                    </button>
                )}
                {gradeResult && (
                    <div className="flex items-center gap-3 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white shadow-lg">
                        <Zap className="h-4 w-4 text-purple-400" />
                        <span>
                            <span className="text-blue-400 font-semibold">{gradeResult.graded_by_api}</span> ESPN
                            {" · "}
                            <span className="text-orange-400 font-semibold">{gradeResult.auto_win}</span> auto-win
                            {" · "}
                            <span className="text-slate-500">{gradeResult.skipped_not_final}</span> skipped
                        </span>
                    </div>
                )}
            </div>

            {/* Stat Cards */}
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                {/* Profit — dominant card */}
                <div className="col-span-2 lg:col-span-1 rounded-xl bg-white p-6 shadow-sm border border-slate-200">
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Total Profit</p>
                    <p className={`mt-2 text-4xl font-bold tabular-nums ${profit >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                        {profit >= 0 ? '+' : ''}{profit.toFixed(2)}
                        <span className="ml-1 text-lg font-normal text-slate-500">u</span>
                    </p>
                    <div className="mt-2 flex items-center gap-1 text-xs text-slate-500">
                        {profit >= 0
                            ? <TrendingUp className="h-3 w-3 text-green-500" />
                            : <TrendingDown className="h-3 w-3 text-red-500" />
                        }
                        {totalPicks} total picks
                    </div>
                </div>

                {/* Win Rate */}
                <div className="rounded-xl bg-white p-6 shadow-sm border border-slate-200">
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Win Rate</p>
                    <p className={`mt-2 text-4xl font-bold tabular-nums ${winRateColor(stats?.win_rate ?? 0)}`}>
                        {(stats?.win_rate ?? 0).toFixed(1)}
                        <span className="ml-0.5 text-lg font-normal text-slate-500">%</span>
                    </p>
                    <p className="mt-2 text-xs text-slate-500">confirmed results only</p>
                </div>

                {/* ROI */}
                <div className="rounded-xl bg-white p-6 shadow-sm border border-slate-200">
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">ROI</p>
                    <p className={`mt-2 text-4xl font-bold tabular-nums ${(stats?.roi ?? 0) >= 0 ? 'text-blue-600' : 'text-red-500'}`}>
                        {(stats?.roi ?? 0) >= 0 ? '+' : ''}{(stats?.roi ?? 0).toFixed(1)}
                        <span className="ml-0.5 text-lg font-normal text-slate-500">%</span>
                    </p>
                    <p className="mt-2 text-xs text-slate-500">{stats?.active_cappers ?? 0} active cappers</p>
                </div>

                {/* Record */}
                <div className="rounded-xl bg-white p-6 shadow-sm border border-slate-200">
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Record</p>
                    <p className="mt-2 text-2xl font-bold text-slate-900 tabular-nums">
                        {wins}
                        <span className="text-slate-300 font-normal"> / </span>
                        {graded - wins}
                    </p>
                    <div className="mt-2 flex items-center gap-1.5 text-xs text-slate-500">
                        <Clock className="h-3 w-3 text-yellow-500" />
                        {pending > 0
                            ? <Link href="/dashboard/picks" className="text-yellow-600 hover:underline font-medium">{pending} pending</Link>
                            : "no pending picks"
                        }
                    </div>
                </div>
            </div>

            {/* Middle row: Top Cappers + Action Center */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

                {/* Top Cappers — takes 2/3 width */}
                <div className="lg:col-span-2 rounded-xl bg-white shadow-sm border border-slate-200 overflow-hidden">
                    <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
                        <div className="flex items-center gap-2">
                            <Users className="h-4 w-4 text-slate-500" />
                            <h2 className="text-sm font-semibold text-slate-900">Top Cappers</h2>
                        </div>
                        <Link href="/dashboard/cappers" className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700">
                            View all <ArrowRight className="h-3 w-3" />
                        </Link>
                    </div>
                    {cappers.length === 0 ? (
                        <div className="px-6 py-8 text-center text-sm text-slate-500">
                            No cappers yet — upload a screenshot to get started.
                        </div>
                    ) : (
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-slate-100">
                                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500">#</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500">Capper</th>
                                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-500">Win%</th>
                                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-500">ROI</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-slate-500">Profit</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {cappers.map((c, i) => (
                                    <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                                        <td className="px-6 py-3.5 text-sm text-slate-500 font-medium">#{i + 1}</td>
                                        <td className="px-6 py-3.5">
                                            <Link href={`/dashboard/cappers/${c.id}`} className="text-sm font-semibold text-slate-900 hover:text-green-600">
                                                {c.name}
                                            </Link>
                                            <div className="text-xs text-slate-500">{c.wins}W–{c.losses}L{c.pending > 0 ? ` · ${c.pending} pending` : ''}</div>
                                        </td>
                                        <td className={`px-4 py-3.5 text-right text-sm font-semibold tabular-nums ${winRateColor(c.confirmed_win_rate)}`}>
                                            {c.confirmed_win_rate.toFixed(1)}%
                                        </td>
                                        <td className={`px-4 py-3.5 text-right text-sm tabular-nums ${c.roi >= 0 ? 'text-blue-600' : 'text-red-500'}`}>
                                            {c.roi >= 0 ? '+' : ''}{c.roi.toFixed(1)}%
                                        </td>
                                        <td className={`px-6 py-3.5 text-right text-sm font-semibold tabular-nums ${c.profit >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                                            {c.profit >= 0 ? '+' : ''}{c.profit.toFixed(2)}u
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* Action Center — takes 1/3 width */}
                <div className="rounded-xl bg-white shadow-sm border border-slate-200 overflow-hidden">
                    <div className="flex items-center gap-2 px-6 py-4 border-b border-slate-200">
                        <Bell className="h-4 w-4 text-slate-500" />
                        <h2 className="text-sm font-semibold text-slate-900">Activity</h2>
                        {unreadCount > 0 && (
                            <span className="ml-auto rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                                {unreadCount} new
                            </span>
                        )}
                    </div>

                    <div className="divide-y divide-slate-100">
                        {/* Auto-grade prompt */}
                        {pending > 0 && (
                            <div className="px-6 py-4">
                                <div className="flex items-start gap-3">
                                    <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-yellow-100">
                                        <Clock className="h-4 w-4 text-yellow-600" />
                                    </div>
                                    <div>
                                        <p className="text-sm font-medium text-slate-900">{pending} picks awaiting result</p>
                                        <p className="mt-0.5 text-xs text-slate-500">Run ESPN grading to resolve them automatically</p>
                                        <button
                                            onClick={handleAutoGrade}
                                            disabled={autoGrading}
                                            className="mt-2 flex items-center gap-1.5 rounded-md bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-700 disabled:opacity-60"
                                        >
                                            <Zap className="h-3 w-3" />
                                            {autoGrading ? "Grading…" : "Auto-Grade Now"}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Notification items */}
                        {hasActivity ? (
                            <>
                                {unreadNotifs.length > 0 ? unreadNotifs.map(n => (
                                    <div key={n.id} className="flex items-start gap-3 px-6 py-3 bg-blue-50/50">
                                        <div className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-blue-500" />
                                        <div className="min-w-0">
                                            <p className="text-xs text-slate-800 leading-snug">{n.message}</p>
                                            <p className="mt-0.5 text-xs text-slate-500">{timeAgo(n.created_at)}</p>
                                        </div>
                                    </div>
                                )) : notifications.slice(0, 3).map(n => (
                                    <div key={n.id} className="flex items-start gap-3 px-6 py-3">
                                        <div className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-slate-200" />
                                        <div className="min-w-0">
                                            <p className="text-xs text-slate-600 leading-snug">{n.message}</p>
                                            <p className="mt-0.5 text-xs text-slate-500">{timeAgo(n.created_at)}</p>
                                        </div>
                                    </div>
                                ))}
                                {unreadCount > 0 && (
                                    <div className="px-6 py-3">
                                        <button onClick={handleMarkAllRead} className="text-xs text-slate-500 hover:text-slate-700">
                                            Mark all read
                                        </button>
                                    </div>
                                )}
                            </>
                        ) : pending === 0 ? (
                            <div className="px-6 py-8 text-center">
                                <p className="text-sm font-medium text-slate-500">All caught up</p>
                                <p className="mt-1 text-xs text-slate-500">No pending picks or new activity</p>
                            </div>
                        ) : null}
                    </div>
                </div>
            </div>

            {/* Recent Picks */}
            <div className="rounded-xl bg-white shadow-sm border border-slate-200 overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
                    <h2 className="text-sm font-semibold text-slate-900">Recent Picks</h2>
                    <Link href="/dashboard/picks" className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700">
                        View all <ArrowRight className="h-3 w-3" />
                    </Link>
                </div>
                {recentPicks.length === 0 ? (
                    <div className="px-6 py-10 text-center">
                        <p className="text-sm text-slate-500">No picks yet.</p>
                        <Link href="/dashboard/upload" className="mt-2 inline-block text-sm font-medium text-green-600 hover:underline">
                            Upload a screenshot →
                        </Link>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-slate-100">
                                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500">Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-500">Capper</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">Sport</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">Pick</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">Units</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">Result</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-slate-500">Profit</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {recentPicks.map((pick) => (
                                    <tr key={pick.id} className="hover:bg-slate-50 transition-colors">
                                        <td className="px-6 py-3 text-xs text-slate-500">
                                            {pick.game_date
                                                ? parseApiDate(pick.game_date).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                                                : parseApiDate(pick.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                                            }
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-3">
                                            <Link href={`/dashboard/cappers/${pick.capper?.id}`} className="text-sm font-medium text-slate-900 hover:text-green-600">
                                                {pick.capper?.name ?? "Unknown"}
                                            </Link>
                                        </td>
                                        <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">{pick.sport}</td>
                                        <td className="px-4 py-3 text-sm text-slate-700 max-w-xs truncate">{pick.pick_text}</td>
                                        <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">{pick.units_risked}u</td>
                                        <td className="whitespace-nowrap px-4 py-3">
                                            {pick.result === "WIN" && (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                                                    <CheckCircle className="h-3 w-3" /> Win
                                                    {pick.grade_source === "espn_api" && <span className="text-green-500 opacity-70">·ESPN</span>}
                                                    {pick.grade_source === "auto_win" && <span className="text-green-500 opacity-70">·Auto</span>}
                                                </span>
                                            )}
                                            {pick.result === "LOSS" && (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                                                    <XCircle className="h-3 w-3" /> Loss
                                                </span>
                                            )}
                                            {pick.result === "PUSH" && (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                                                    <MinusCircle className="h-3 w-3" /> Push
                                                </span>
                                            )}
                                            {pick.result === "PENDING" && (
                                                <span className="inline-flex items-center gap-1 rounded-full bg-yellow-50 px-2 py-0.5 text-xs font-medium text-yellow-700">
                                                    <Clock className="h-3 w-3" /> Pending
                                                </span>
                                            )}
                                        </td>
                                        <td className={`whitespace-nowrap px-6 py-3 text-right text-sm font-semibold tabular-nums ${pick.profit > 0 ? 'text-green-600' : pick.profit < 0 ? 'text-red-500' : 'text-slate-500'}`}>
                                            {pick.profit !== 0 ? (pick.profit > 0 ? '+' : '') + pick.profit.toFixed(2) + 'u' : '—'}
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
