"use client"

import { useEffect, useState } from "react"
import Link from "next/link"

interface SummaryStats {
    total_profit: number
    win_rate: number
    roi: number
    active_cappers: number
    total_picks: number
    pending_picks: number
}

interface Notification {
    id: number
    pick_id: number | null
    message: string
    read: boolean
    created_at: string
}

export default function DashboardPage() {
    const [stats, setStats] = useState<SummaryStats | null>(null)
    const [loading, setLoading] = useState(true)
    const [recentPicks, setRecentPicks] = useState<any[]>([])
    const [notifications, setNotifications] = useState<Notification[]>([])
    const [limit, setLimit] = useState<number>(10)

    useEffect(() => {
        fetchStats()
        fetchRecentPicks()
        fetchNotifications()
    }, [limit])

    const fetchStats = () => {
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
    }

    const fetchRecentPicks = () => {
        fetch(`http://localhost:8000/api/picks/?limit=${limit}`)
            .then((res) => res.json())
            .then((data) => setRecentPicks(data))
            .catch((err) => console.error("Failed to fetch recent picks:", err))
    }

    const fetchNotifications = () => {
        fetch("http://localhost:8000/api/notifications/")
            .then(res => res.json())
            .then(data => setNotifications(data.slice(0, 5)))
            .catch(() => {})
    }

    const handleDeletePick = async (pickId: number) => {
        if (!confirm("Are you sure you want to delete this pick?")) return
        try {
            const response = await fetch(`http://localhost:8000/api/picks/${pickId}`, { method: "DELETE" })
            if (response.ok) {
                fetchStats()
                fetchRecentPicks()
            }
        } catch (err) {
            console.error("Error deleting pick:", err)
        }
    }

    const handleMarkAllRead = async () => {
        await fetch("http://localhost:8000/api/notifications/read-all", { method: "POST" })
        fetchNotifications()
    }

    const timeAgo = (dateStr: string) => {
        const diff = Date.now() - new Date(dateStr).getTime()
        const mins = Math.floor(diff / 60000)
        if (mins < 60) return `${mins}m ago`
        const hrs = Math.floor(mins / 60)
        if (hrs < 24) return `${hrs}h ago`
        return `${Math.floor(hrs / 24)}d ago`
    }

    if (loading) {
        return <div className="text-gray-700">Loading...</div>
    }

    const unreadNotifs = notifications.filter(n => !n.read)

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-5">
                <div className="rounded-lg bg-white p-6 shadow">
                    <h3 className="text-sm font-medium text-gray-700">Total Profit</h3>
                    <p className={`mt-2 text-3xl font-bold ${(stats?.total_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {(stats?.total_profit || 0) >= 0 ? '+' : ''}{stats?.total_profit || 0}u
                    </p>
                </div>
                <div className="rounded-lg bg-white p-6 shadow">
                    <h3 className="text-sm font-medium text-gray-700">Win Rate</h3>
                    <p className="mt-2 text-3xl font-bold text-gray-900">{stats?.win_rate || 0}%</p>
                </div>
                <div className="rounded-lg bg-white p-6 shadow">
                    <h3 className="text-sm font-medium text-gray-700">ROI</h3>
                    <p className="mt-2 text-3xl font-bold text-blue-600">{stats?.roi || 0}%</p>
                </div>
                <div className="rounded-lg bg-white p-6 shadow">
                    <h3 className="text-sm font-medium text-gray-700">Active Cappers</h3>
                    <p className="mt-2 text-3xl font-bold text-gray-900">{stats?.active_cappers || 0}</p>
                </div>
                <Link href="/dashboard/picks" className="rounded-lg bg-white p-6 shadow hover:shadow-md transition-shadow">
                    <h3 className="text-sm font-medium text-gray-700">Pending Picks</h3>
                    <p className="mt-2 text-3xl font-bold text-yellow-500">{stats?.pending_picks || 0}</p>
                </Link>
            </div>

            {/* Recent Notifications */}
            {notifications.length > 0 && (
                <div className="rounded-lg bg-white shadow">
                    <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
                        <h2 className="text-lg font-medium text-gray-900">
                            Recent Activity
                            {unreadNotifs.length > 0 && (
                                <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                                    {unreadNotifs.length} new
                                </span>
                            )}
                        </h2>
                        {unreadNotifs.length > 0 && (
                            <button
                                onClick={handleMarkAllRead}
                                className="text-sm text-gray-500 hover:text-gray-700"
                            >
                                Mark all read
                            </button>
                        )}
                    </div>
                    <ul className="divide-y divide-gray-100">
                        {notifications.map(n => (
                            <li key={n.id} className={`px-6 py-3 flex items-start gap-3 ${!n.read ? 'bg-blue-50' : ''}`}>
                                <div className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${!n.read ? 'bg-blue-500' : 'bg-transparent'}`} />
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm text-gray-800">{n.message}</p>
                                    <p className="text-xs text-gray-400 mt-0.5">{timeAgo(n.created_at)}</p>
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Recent Picks Table */}
            <div className="rounded-lg bg-white shadow">
                <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
                    <h2 className="text-lg font-medium text-gray-900">Recent Picks</h2>
                    <div className="flex items-center gap-2">
                        <label htmlFor="limit" className="text-sm text-gray-700">Show:</label>
                        <select
                            id="limit"
                            value={limit}
                            onChange={(e) => setLimit(Number(e.target.value))}
                            className="rounded-md border-gray-300 text-sm shadow-sm focus:border-green-500 focus:ring-green-500"
                        >
                            <option value={10}>10</option>
                            <option value={25}>25</option>
                            <option value={50}>50</option>
                        </select>
                    </div>
                </div>
                <div className="overflow-x-auto">
                    {recentPicks.length === 0 ? (
                        <div className="p-6 text-center text-gray-700">
                            No picks yet. Upload a screenshot or add manually to get started.
                        </div>
                    ) : (
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Capper</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Sport</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Pick</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Result</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Profit</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-700">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 bg-white">
                                {recentPicks.map((pick) => (
                                    <tr key={pick.id}>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-700">
                                            {new Date(pick.date).toLocaleDateString()}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                                            {pick.capper?.name || "Unknown"}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-700">{pick.sport}</td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-700">{pick.pick_text}</td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm">
                                            <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${pick.result === 'WIN' ? 'bg-green-100 text-green-800' :
                                                pick.result === 'LOSS' ? 'bg-red-100 text-red-800' :
                                                    pick.result === 'PUSH' ? 'bg-yellow-100 text-yellow-800' :
                                                        'bg-gray-100 text-gray-800'
                                                }`}>
                                                {pick.result}
                                            </span>
                                        </td>
                                        <td className={`whitespace-nowrap px-6 py-4 text-sm font-medium ${pick.profit > 0 ? 'text-green-600' :
                                            pick.profit < 0 ? 'text-red-600' :
                                                'text-gray-700'
                                            }`}>
                                            {pick.profit > 0 ? '+' : ''}{pick.profit}u
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
                                            <button
                                                onClick={() => handleDeletePick(pick.id)}
                                                className="text-red-600 hover:text-red-900"
                                            >
                                                Delete
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </div>
    )
}
