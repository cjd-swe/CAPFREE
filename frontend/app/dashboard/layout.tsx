"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Sidebar } from "@/components/ui/sidebar"
import { apiUrl } from "@/lib/api"

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode
}) {
    const router = useRouter()
    useEffect(() => {
        // Background check only — redirect to login if auth is enabled and session is invalid.
        // Don't block rendering; auth is disabled (APP_PASSWORD unset) in production.
        fetch(apiUrl("/api/auth/me"), { credentials: "include" })
            .then((res) => { if (!res.ok) router.replace("/login") })
            .catch(() => {})
    }, [router])

    return (
        <div className="flex h-screen bg-slate-100">
            <Sidebar />
            {/* pt-14 on mobile offsets the fixed top bar; pb-16 offsets the bottom nav */}
            <main className="flex-1 overflow-y-auto p-4 pt-[calc(3.5rem+1rem)] pb-[calc(4rem+1rem)] md:p-8 md:pt-8 md:pb-8">
                {children}
            </main>
        </div>
    )
}
