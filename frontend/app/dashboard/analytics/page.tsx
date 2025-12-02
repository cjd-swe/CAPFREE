"use client"

import { useEffect, useState } from "react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

export default function AnalyticsPage() {
    const [dailyProfit, setDailyProfit] = useState<any[]>([])
    const [sportPerformance, setSportPerformance] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        Promise.all([
            fetch("http://localhost:8000/api/analytics/daily-profit").then(res => res.json()),
            fetch("http://localhost:8000/api/analytics/sport-performance").then(res => res.json())
        ]).then(([profitData, sportData]) => {
            setDailyProfit(profitData)
            setSportPerformance(sportData)
            setLoading(false)
        }).catch(err => {
            console.error("Failed to fetch analytics:", err)
            setLoading(false)
        })
    }, [])

    if (loading) {
        return <div className="text-gray-500">Loading analytics...</div>
    }

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* Profit Chart */}
                <div className="rounded-lg bg-white p-6 shadow">
                    <h2 className="mb-4 text-lg font-medium text-gray-900">Daily Profit (Last 30 Days)</h2>
                    <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={dailyProfit}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="name" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="profit" stroke="#16a34a" activeDot={{ r: 8 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Win Rate by Sport */}
                <div className="rounded-lg bg-white p-6 shadow">
                    <h2 className="mb-4 text-lg font-medium text-gray-900">Win Rate by Sport</h2>
                    <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={sportPerformance}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                                    outerRadius={80}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {sportPerformance.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Detailed Sport Stats Table */}
            <div className="rounded-lg bg-white shadow">
                <div className="border-b border-gray-200 px-6 py-4">
                    <h2 className="text-lg font-medium text-gray-900">Performance by Sport</h2>
                </div>
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Sport</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Record (W-L-P)</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Win Rate</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">ROI</th>
                                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Profit</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 bg-white">
                            {sportPerformance.map((sport, index) => (
                                <tr key={index}>
                                    <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">{sport.name}</td>
                                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">{sport.record}</td>
                                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">{sport.win_rate}%</td>
                                    <td className={`whitespace-nowrap px-6 py-4 text-sm font-medium ${sport.roi > 0 ? 'text-green-600' : sport.roi < 0 ? 'text-red-600' : 'text-gray-500'
                                        }`}>
                                        {sport.roi}%
                                    </td>
                                    <td className={`whitespace-nowrap px-6 py-4 text-sm font-medium ${sport.profit > 0 ? 'text-green-600' : sport.profit < 0 ? 'text-red-600' : 'text-gray-500'
                                        }`}>
                                        {sport.profit > 0 ? '+' : ''}{sport.profit}u
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}
