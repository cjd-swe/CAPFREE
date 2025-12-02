"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, TrendingUp, TrendingDown, Trophy, Target } from "lucide-react"

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

export default function CapperAnalyticsPage() {
    const params = useParams()
    const capperId = params.id as string
    const [analytics, setAnalytics] = useState<CapperAnalytics | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetch(`http://localhost:8000/api/analytics/capper/${capperId}`)
            .then((res) => res.json())
            .then((data) => {
                setAnalytics(data)
                setLoading(false)
            })
            .catch((err) => {
                console.error("Failed to fetch analytics:", err)
                setLoading(false)
            })
    }, [capperId])

    if (loading) {
        return <div className="text-gray-700">Loading...</div>
    }

    if (!analytics) {
        return <div className="text-gray-700">Capper not found</div>
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link
                    href="/dashboard/cappers"
                    className="rounded-lg p-2 hover:bg-gray-200"
                >
                    <ArrowLeft className="h-6 w-6 text-gray-600" />
                </Link>
                <h1 className="text-3xl font-bold text-gray-900">{analytics.name}</h1>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-lg bg-white p-6 shadow">
                    <div className="flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-green-600" />
                        <h3 className="text-sm font-medium text-gray-700">Total Profit</h3>
                    </div>
                    <p className={`mt-2 text-3xl font-bold ${analytics.total_profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {analytics.total_profit >= 0 ? '+' : ''}{analytics.total_profit}u
                    </p>
                </div>

                <div className="rounded-lg bg-white p-6 shadow">
                    <div className="flex items-center gap-2">
                        <Trophy className="h-5 w-5 text-yellow-600" />
                        <h3 className="text-sm font-medium text-gray-700">Win Rate</h3>
                    </div>
                    <p className="mt-2 text-3xl font-bold text-gray-900">{analytics.win_rate}%</p>
                    <p className="mt-1 text-sm text-gray-700">
                        {analytics.wins}W - {analytics.losses}L - {analytics.pushes}P
                    </p>
                </div>

                <div className="rounded-lg bg-white p-6 shadow">
                    <div className="flex items-center gap-2">
                        <Target className="h-5 w-5 text-blue-600" />
                        <h3 className="text-sm font-medium text-gray-700">ROI</h3>
                    </div>
                    <p className="mt-2 text-3xl font-bold text-blue-600">{analytics.roi}%</p>
                </div>

                <div className="rounded-lg bg-white p-6 shadow">
                    <h3 className="text-sm font-medium text-gray-700">Total Picks</h3>
                    <p className="mt-2 text-3xl font-bold text-gray-900">{analytics.total_picks}</p>
                    {analytics.pending > 0 && (
                        <p className="mt-1 text-sm text-yellow-600">{analytics.pending} pending</p>
                    )}
                </div>
            </div>

            {/* Performance by Sport */}
            <div className="rounded-lg bg-white shadow">
                <div className="border-b border-gray-200 px-6 py-4">
                    <h2 className="text-lg font-medium text-gray-900">Performance by Sport</h2>
                </div>
                <div className="p-6">
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {Object.entries(analytics.sport_performance).map(([sport, perf]) => {
                            const winRate = perf.total > 0 ? ((perf.wins / perf.total) * 100).toFixed(1) : '0.0'
                            return (
                                <div key={sport} className="rounded-lg border border-gray-200 p-4">
                                    <h3 className="font-semibold text-gray-900">{sport}</h3>
                                    <div className="mt-2 space-y-1 text-sm">
                                        <div className="flex justify-between">
                                            <span className="text-gray-600">Record:</span>
                                            <span className="font-medium">
                                                {perf.wins}-{perf.losses}-{perf.pushes}
                                            </span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-gray-600">Win Rate:</span>
                                            <span className="font-medium">{winRate}%</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-gray-600">Profit:</span>
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
                <div className="border-b border-gray-200 px-6 py-4">
                    <h2 className="text-lg font-medium text-gray-900">Recent Picks</h2>
                </div>
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">
                                    Date
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">
                                    Sport
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">
                                    Pick
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">
                                    Units
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">
                                    Result
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">
                                    Profit
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 bg-white">
                            {analytics.recent_picks.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-4 text-center text-gray-700">
                                        No picks yet
                                    </td>
                                </tr>
                            ) : (
                                analytics.recent_picks.map((pick) => (
                                    <tr key={pick.id}>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                                            {new Date(pick.date).toLocaleDateString()}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                                            {pick.sport}
                                        </td>
                                        <td className="px-6 py-4 text-sm text-gray-900">
                                            {pick.pick_text}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                                            {pick.units_risked}u
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm">
                                            <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${pick.result === 'WIN' ? 'bg-green-100 text-green-800' :
                                                pick.result === 'LOSS' ? 'bg-red-100 text-red-800' :
                                                    pick.result === 'PUSH' ? 'bg-gray-100 text-gray-800' :
                                                        'bg-yellow-100 text-yellow-800'
                                                }`}>
                                                {pick.result}
                                            </span>
                                        </td>
                                        <td className={`whitespace-nowrap px-6 py-4 text-sm font-medium ${pick.profit > 0 ? 'text-green-600' :
                                            pick.profit < 0 ? 'text-red-600' :
                                                'text-gray-900'
                                            }`}>
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
