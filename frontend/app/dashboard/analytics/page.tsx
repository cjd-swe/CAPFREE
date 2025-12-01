"use client"

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const data = [
    { name: 'Mon', profit: 400 },
    { name: 'Tue', profit: 300 },
    { name: 'Wed', profit: -200 },
    { name: 'Thu', profit: 500 },
    { name: 'Fri', profit: 100 },
    { name: 'Sat', profit: 800 },
    { name: 'Sun', profit: 600 },
]

export default function AnalyticsPage() {
    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* Profit Chart */}
                <div className="rounded-lg bg-white p-6 shadow">
                    <h2 className="mb-4 text-lg font-medium text-gray-900">Daily Profit</h2>
                    <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={data}>
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

                {/* Win Rate by Sport (Placeholder) */}
                <div className="rounded-lg bg-white p-6 shadow">
                    <h2 className="mb-4 text-lg font-medium text-gray-900">Win Rate by Sport</h2>
                    <div className="flex h-80 items-center justify-center text-gray-500">
                        Pie Chart Placeholder
                    </div>
                </div>
            </div>
        </div>
    )
}
