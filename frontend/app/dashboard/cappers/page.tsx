"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { ArrowRight } from "lucide-react"

interface CapperStat {
    id: number
    name: string
    profit: number
    roi: string
    win_rate: string
    total_picks: number
}

export default function CappersPage() {
    const [cappers, setCappers] = useState<CapperStat[]>([])
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
        return <div className="text-gray-700">Loading...</div>
    }

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-gray-900">Cappers</h1>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {cappers.length === 0 ? (
                    <div className="col-span-full rounded-lg bg-white p-6 text-center text-gray-700 shadow">
                        No cappers with picks yet
                    </div>
                ) : (
                    cappers.map((capper) => (
                        <Link
                            key={capper.id}
                            href={`/dashboard/cappers/${capper.id}`}
                            className="group rounded-lg bg-white p-6 shadow transition-all hover:shadow-lg"
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex-1">
                                    <h3 className="text-xl font-semibold text-gray-900 group-hover:text-green-600">
                                        {capper.name}
                                    </h3>
                                    <p className="mt-1 text-sm text-gray-700">{capper.total_picks} picks</p>
                                </div>
                                <ArrowRight className="h-5 w-5 text-gray-400 transition-transform group-hover:translate-x-1 group-hover:text-green-600" />
                            </div>

                            <div className="mt-4 grid grid-cols-3 gap-4">
                                <div>
                                    <p className="text-xs text-gray-700">Profit</p>
                                    <p className={`text-lg font-bold ${capper.profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                        {capper.profit >= 0 ? '+' : ''}{capper.profit}u
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-gray-700">Win Rate</p>
                                    <p className="text-lg font-bold text-gray-900">{capper.win_rate}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-gray-700">ROI</p>
                                    <p className="text-lg font-bold text-blue-600">{capper.roi}</p>
                                </div>
                            </div>
                        </Link>
                    ))
                )}
            </div>
        </div>
    )
}
