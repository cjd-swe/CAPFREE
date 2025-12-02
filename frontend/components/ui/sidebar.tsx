import Link from "next/link"
import { LayoutDashboard, Upload, BarChart3, Users, Settings, ListChecks } from "lucide-react"

const navigation = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Picks", href: "/dashboard/picks", icon: ListChecks },
    { name: "Upload Picks", href: "/dashboard/upload", icon: Upload },
    { name: "Analytics", href: "/dashboard/analytics", icon: BarChart3 },
    { name: "Cappers", href: "/dashboard/cappers", icon: Users },
    { name: "Settings", href: "/dashboard/settings", icon: Settings },
]

export function Sidebar() {
    return (
        <div className="flex h-full w-64 flex-col bg-gray-900 text-white">
            <div className="flex h-16 items-center justify-center border-b border-gray-800">
                <h1 className="text-xl font-bold text-green-500">SharpWatch</h1>
            </div>
            <nav className="flex-1 space-y-1 px-2 py-4">
                {navigation.map((item) => (
                    <Link
                        key={item.name}
                        href={item.href}
                        className="group flex items-center rounded-md px-2 py-2 text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white"
                    >
                        <item.icon className="mr-3 h-6 w-6 flex-shrink-0 text-gray-400 group-hover:text-white" aria-hidden="true" />
                        {item.name}
                    </Link>
                ))}
            </nav>
        </div>
    )
}
