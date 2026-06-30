"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Sidebar } from "@/components/ui/sidebar"
import { apiUrl } from "@/lib/api"

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode
}) {
    const router = useRouter()
    const [checked, setChecked] = useState(false)

    useEffect(() => {
        fetch(apiUrl("/api/auth/me"), { credentials: "include" })
            .then((res) => {
                if (!res.ok) router.replace("/login")
                else setChecked(true)
            })
            .catch(() => {
                // Server may be waking up (Render free tier spindown).
                // Auth is disabled when APP_PASSWORD is unset, so don't redirect — just let through.
                setChecked(true)
            })
    }, [router])

    if (!checked) {
        return (
            <div className="flex h-screen items-center justify-center bg-slate-100">
                <p className="text-slate-400">Loading...</p>
            </div>
        )
    }

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
