"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useEffect, useRef, useState } from "react"
import { LayoutDashboard, Upload, BarChart3, Users, Settings, ListChecks, Bell, X, LogOut } from "lucide-react"
import { API_URL, apiUrl } from "@/lib/api"

const navigation = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Picks", href: "/dashboard/picks", icon: ListChecks },
    { name: "Upload Picks", href: "/dashboard/upload", icon: Upload },
    { name: "Analytics", href: "/dashboard/analytics", icon: BarChart3 },
    { name: "Cappers", href: "/dashboard/cappers", icon: Users },
    { name: "Settings", href: "/dashboard/settings", icon: Settings },
]

interface Notification {
    id: number
    message: string
    read: boolean
    created_at: string
}

export function Sidebar() {
    const pathname = usePathname()
    const router = useRouter()
    const [unreadCount, setUnreadCount] = useState(0)
    const [pendingCount, setPendingCount] = useState(0)
    const [bellOpen, setBellOpen] = useState(false)
    const [notifications, setNotifications] = useState<Notification[]>([])
    const [popupNotifs, setPopupNotifs] = useState<Notification[]>([])
    const bellRef = useRef<HTMLDivElement>(null)
    const prevUnreadRef = useRef<number | null>(null)

    const fetchCounts = async () => {
        try {
            const res = await fetch(API_URL + "/api/notifications/unread-count", { credentials: "include" })
            if (res.status === 401) return
            const data = await res.json()
            const newCount: number = data.count || 0

            // If count went up since last poll, fetch the new unread notifications for popup
            if (prevUnreadRef.current !== null && newCount > prevUnreadRef.current) {
                const notifRes = await fetch(API_URL + "/api/notifications/", { credentials: "include" })
                const allNotifs: Notification[] = await notifRes.json()
                const fresh = allNotifs.filter(n => !n.read)
                if (fresh.length > 0) setPopupNotifs(fresh)
            }
            prevUnreadRef.current = newCount
            setUnreadCount(newCount)
        } catch {}

        fetch(API_URL + "/api/analytics/summary", { credentials: "include" })
            .then(res => res.json())
            .then(data => setPendingCount(data.pending_picks || 0))
            .catch(() => {})
    }

    const fetchNotifications = () => {
        fetch(API_URL + "/api/notifications/", { credentials: "include" })
            .then(res => res.json())
            .then(data => setNotifications(data))
            .catch(() => {})
    }

    const dismissPopup = async () => {
        await fetch(API_URL + "/api/notifications/read-all", { method: "POST", credentials: "include" })
        setPopupNotifs([])
        setUnreadCount(0)
        prevUnreadRef.current = 0
    }

    const handleLogout = async () => {
        await fetch(apiUrl("/api/auth/logout"), { method: "POST", credentials: "include" })
        router.push("/login")
    }

    useEffect(() => {
        fetchCounts()
        const interval = setInterval(fetchCounts, 15000)
        return () => clearInterval(interval)
    }, [])

    // Close dropdown when clicking outside
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (bellRef.current && !bellRef.current.contains(e.target as Node)) {
                setBellOpen(false)
            }
        }
        document.addEventListener("mousedown", handler)
        return () => document.removeEventListener("mousedown", handler)
    }, [])

    const handleBellClick = () => {
        if (!bellOpen) fetchNotifications()
        setBellOpen(prev => !prev)
    }

    const handleMarkAllRead = async () => {
        await fetch(API_URL + "/api/notifications/read-all", { method: "POST", credentials: "include" })
        setUnreadCount(0)
        setNotifications(prev => prev.map(n => ({ ...n, read: true })))
    }

    const timeAgo = (dateStr: string) => {
        const diff = Date.now() - new Date(dateStr).getTime()
        const mins = Math.floor(diff / 60000)
        if (mins < 1) return "just now"
        if (mins < 60) return `${mins}m ago`
        const hrs = Math.floor(mins / 60)
        if (hrs < 24) return `${hrs}h ago`
        return `${Math.floor(hrs / 24)}d ago`
    }

    const isActive = (href: string) => {
        if (href === "/dashboard") return pathname === "/dashboard"
        return pathname.startsWith(href)
    }

    return (
        <div className="flex h-full w-64 flex-col bg-slate-900 text-white">
            <div className="flex h-16 items-center justify-between border-b border-slate-700 px-4">
                <h1 className="text-xl font-bold text-green-500">SharpWatch</h1>

                {/* Bell with dropdown */}
                <div className="relative" ref={bellRef}>
                    <button
                        onClick={handleBellClick}
                        className="relative rounded-md p-1.5 text-slate-500 hover:bg-slate-800 hover:text-white transition-colors"
                        aria-label="Notifications"
                    >
                        <Bell className="h-5 w-5" />
                        {unreadCount > 0 && (
                            <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white">
                                {unreadCount > 9 ? "9+" : unreadCount}
                            </span>
                        )}
                    </button>

                    {bellOpen && (
                        // Fixed to viewport: appears below the header at the right edge of the sidebar
                        // so it's never clipped by the sidebar's layout
                        <div className="fixed top-16 left-64 z-50 w-96 rounded-xl bg-white shadow-2xl ring-1 ring-black/10 overflow-hidden">
                            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
                                <span className="text-sm font-semibold text-slate-900">
                                    Notifications
                                    {unreadCount > 0 && (
                                        <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-600">
                                            {unreadCount} new
                                        </span>
                                    )}
                                </span>
                                <div className="flex items-center gap-2">
                                    {unreadCount > 0 && (
                                        <button
                                            onClick={handleMarkAllRead}
                                            className="text-xs text-slate-500 hover:text-slate-700"
                                        >
                                            Mark all read
                                        </button>
                                    )}
                                    <button onClick={() => setBellOpen(false)} className="text-slate-500 hover:text-slate-600">
                                        <X className="h-4 w-4" />
                                    </button>
                                </div>
                            </div>

                            <ul className="max-h-[calc(100vh-5rem)] overflow-y-auto divide-y divide-slate-100">
                                {notifications.length === 0 ? (
                                    <li className="px-4 py-6 text-center text-sm text-slate-500">
                                        No notifications yet
                                    </li>
                                ) : (
                                    notifications.map(n => (
                                        <li
                                            key={n.id}
                                            className={`flex items-start gap-3 px-4 py-3 ${!n.read ? 'bg-blue-50' : ''}`}
                                        >
                                            <div className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${!n.read ? 'bg-blue-500' : 'bg-slate-200'}`} />
                                            <div className="flex-1">
                                                <p className="text-sm text-slate-800 leading-snug break-words">{n.message}</p>
                                                <p className="mt-0.5 text-xs text-slate-500">{timeAgo(n.created_at)}</p>
                                            </div>
                                        </li>
                                    ))
                                )}
                            </ul>
                        </div>
                    )}
                </div>
            </div>

            {/* Telegram notification popup — must be manually dismissed */}
            {popupNotifs.length > 0 && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40">
                    <div className="w-full max-w-sm rounded-2xl bg-white shadow-2xl ring-1 ring-black/10 overflow-hidden mx-4">
                        <div className="flex items-center gap-3 px-5 py-4 bg-green-50 border-b border-green-100">
                            <Bell className="h-5 w-5 text-green-600 flex-shrink-0" />
                            <span className="font-semibold text-green-900">
                                {popupNotifs.length === 1 ? "New pick received" : `${popupNotifs.length} new picks received`}
                            </span>
                        </div>
                        <ul className="divide-y divide-slate-100 max-h-72 overflow-y-auto">
                            {popupNotifs.map(n => (
                                <li key={n.id} className="px-5 py-3">
                                    <p className="text-sm text-slate-800 leading-snug">{n.message}</p>
                                    <p className="mt-0.5 text-xs text-slate-500">{timeAgo(n.created_at)}</p>
                                </li>
                            ))}
                        </ul>
                        <div className="px-5 py-4 bg-slate-50 border-t border-slate-200 flex justify-end">
                            <button
                                onClick={dismissPopup}
                                className="rounded-lg bg-green-600 px-5 py-2 text-sm font-semibold text-white hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
                            >
                                Dismiss
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <nav className="flex-1 space-y-1 px-2 py-4">
                {navigation.map((item) => {
                    const active = isActive(item.href)
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={`group flex items-center rounded-md px-2 py-2 text-sm font-medium ${
                                active
                                    ? "bg-slate-800 text-white"
                                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                            }`}
                        >
                            <item.icon
                                className={`mr-3 h-6 w-6 flex-shrink-0 ${
                                    active ? "text-green-400" : "text-slate-500 group-hover:text-white"
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
            <div className="border-t border-slate-700 px-2 py-4">
                <button
                    onClick={handleLogout}
                    className="group flex w-full items-center rounded-md px-2 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
                >
                    <LogOut className="mr-3 h-6 w-6 flex-shrink-0 text-slate-500 group-hover:text-white" aria-hidden="true" />
                    Sign out
                </button>
            </div>
        </div>
    )
}
