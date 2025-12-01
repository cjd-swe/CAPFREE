"use client"

import { useEffect, useState } from "react"

interface SummaryStats {
    total_profit: number
    win_rate: number
    roi: number
    active_cappers: number
    total_picks: number
}

export default function DashboardPage() {
    const [stats, setStats] = useState<SummaryStats | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetch("http://localhost:8000/api/analytics/summary")
            .then((res) => res.json())
            .then((data) => {
                setStats(data)
                setLoading(false)
            })
            .catch((err) => {
                console.error("Failed to fetch stats:", err)
                setLoading(false)
            })
    }, [])

    if (loading) {
        return <div className="text-gray-500">Loading...</div>
    }

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                {/* Stat Cards */}
                <div className="rounded-lg bg-white p-6 shadow">
                    <h3 className="text-sm font-medium text-gray-500">Total Profit</h3>
                    <p className={`mt-2 text-3xl font-bold ${(stats?.total_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        ${stats?.total_profit || 0}
                    </p>
                </div>
                <div className="rounded-lg bg-white p-6 shadow">
                    <h3 className="text-sm font-medium text-gray-500">Win Rate</h3>
                    <p className="mt-2 text-3xl font-bold text-gray-900">{stats?.win_rate || 0}%</p>
                </div>
                <div className="rounded-lg bg-white p-6 shadow">
                    <h3 className="text-sm font-medium text-gray-500">ROI</h3>
                    <p className="mt-2 text-3xl font-bold text-blue-600">{stats?.roi || 0}%</p>
                </div>
                <div className="rounded-lg bg-white p-6 shadow">
                    <h3 className="text-sm font-medium text-gray-500">Active Cappers</h3>
                    <p className="mt-2 text-3xl font-bold text-gray-900">{stats?.active_cappers || 0}</p>
                </div>
            </div>

            {/* Recent Picks Table Placeholder */}
            <div className="rounded-lg bg-white shadow">
                <div className="border-b border-gray-200 px-6 py-4">
                    <h2 className="text-lg font-medium text-gray-900">Recent Picks</h2>
                </div>
                <div className="p-6">
                    {stats?.total_picks === 0 ? (
                        <p className="text-gray-500">No picks yet. Upload a screenshot to get started.</p>
                    ) : (
                        <p className="text-gray-500">{stats?.total_picks} picks tracked. View all in the Picks page.</p>
                    )}
                </div>
            </div>
        </div>
    )
}
