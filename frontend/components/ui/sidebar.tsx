"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { LayoutDashboard, Upload, BarChart3, Users, Settings, ListChecks, Bell } from "lucide-react"

const navigation = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Picks", href: "/dashboard/picks", icon: ListChecks },
    { name: "Upload Picks", href: "/dashboard/upload", icon: Upload },
    { name: "Analytics", href: "/dashboard/analytics", icon: BarChart3 },
    { name: "Cappers", href: "/dashboard/cappers", icon: Users },
    { name: "Settings", href: "/dashboard/settings", icon: Settings },
]

export function Sidebar() {
    const pathname = usePathname()
    const [unreadCount, setUnreadCount] = useState(0)
    const [pendingCount, setPendingCount] = useState(0)

    useEffect(() => {
        const fetchCounts = () => {
            fetch("http://localhost:8000/api/notifications/unread-count")
                .then(res => res.json())
                .then(data => setUnreadCount(data.count || 0))
                .catch(() => {})

            fetch("http://localhost:8000/api/analytics/summary")
                .then(res => res.json())
                .then(data => setPendingCount(data.pending_picks || 0))
                .catch(() => {})
        }

        fetchCounts()
        const interval = setInterval(fetchCounts, 30000)
        return () => clearInterval(interval)
    }, [])

    const isActive = (href: string) => {
        if (href === "/dashboard") return pathname === "/dashboard"
        return pathname.startsWith(href)
    }

    return (
        <div className="flex h-full w-64 flex-col bg-gray-900 text-white">
            <div className="flex h-16 items-center justify-between border-b border-gray-800 px-4">
                <h1 className="text-xl font-bold text-green-500">SharpWatch</h1>
                <div className="relative">
                    <Bell className="h-5 w-5 text-gray-400 cursor-pointer hover:text-white" />
                    {unreadCount > 0 && (
                        <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white">
                            {unreadCount > 9 ? "9+" : unreadCount}
                        </span>
                    )}
                </div>
            </div>
            <nav className="flex-1 space-y-1 px-2 py-4">
                {navigation.map((item) => {
                    const active = isActive(item.href)
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={`group flex items-center rounded-md px-2 py-2 text-sm font-medium ${
                                active
                                    ? "bg-gray-800 text-white"
                                    : "text-gray-300 hover:bg-gray-800 hover:text-white"
                            }`}
                        >
                            <item.icon
                                className={`mr-3 h-6 w-6 flex-shrink-0 ${
                                    active ? "text-green-400" : "text-gray-400 group-hover:text-white"
                                }`}
                                aria-hidden="true"
                            />
                            {item.name}
                            {item.name === "Picks" && pendingCount > 0 && (
                                <span className="ml-auto rounded-full bg-yellow-500 px-2 py-0.5 text-xs font-semibold text-white">
                                    {pendingCount}
                                </span>
                            )}
                        </Link>
                    )
                })}
            </nav>
        </div>
    )
}
