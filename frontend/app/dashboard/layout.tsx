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
            .catch(() => router.replace("/login"))
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
            <main className="flex-1 overflow-y-auto p-8">
                {children}
            </main>
        </div>
    )
}
