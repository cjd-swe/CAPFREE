"use client"

import { useEffect, useState } from "react"

interface Capper {
    id: number
    name: string
    profit: number
    roi: string
    win_rate: string
    total_picks: number
}

export default function CappersPage() {
    const [cappers, setCappers] = useState<Capper[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetch("http://localhost:8000/api/analytics/cappers")
            .then((res) => res.json())
            .then((data) => {
                setCappers(data)
                setLoading(false)
            })
            .catch((err) => {
                console.error("Failed to fetch cappers:", err)
                setLoading(false)
            })
    }, [])

    if (loading) {
        return <div className="text-gray-500">Loading...</div>
    }

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-gray-900">Cappers Leaderboard</h1>

            <div className="rounded-lg bg-white shadow">
                <div className="border-b border-gray-200 px-6 py-4">
                    <h2 className="text-lg font-medium text-gray-900">All Cappers</h2>
                </div>
                <div className="p-6">
                    {cappers.length === 0 ? (
                        <p className="text-gray-500">No cappers yet. Add some picks to get started.</p>
                    ) : (
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead>
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Name</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Profit</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">ROI</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Win Rate</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Picks</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 bg-white">
                                {cappers.map((capper) => (
                                    <tr key={capper.id}>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">{capper.name}</td>
                                        <td className={`whitespace-nowrap px-6 py-4 text-sm font-medium ${capper.profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                            ${capper.profit}
                                        </td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">{capper.roi}</td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">{capper.win_rate}</td>
                                        <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">{capper.total_picks}</td>
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
