"use client"

import { useEffect, useState } from "react"
import { Trash2, Edit2, Plus, X, RefreshCw, AlertTriangle } from "lucide-react"
import { API_URL, parseApiDate } from "@/lib/api"

interface Capper {
    id: number
    name: string
    telegram_chat_id: string | null
    created_at: string
}

interface TelegramStatus {
    configured: boolean
    connected: boolean
    bot_username: string | null
    can_read_all_group_messages: boolean | null
    polling_running: boolean
    polling_started_at: string | null
    last_error: string | null
    last_update_at: string | null
    messages_recorded: number
}

interface TelegramMessage {
    id: number
    message_id: string
    chat_id: string
    chat_title: string | null
    sender_name: string | null
    message_type: string
    text: string | null
    status: string
    detail: string | null
    picks_saved: number
    created_at: string
}

const MESSAGE_STATUS_STYLES: Record<string, { label: string; className: string }> = {
    saved_picks: { label: "Picks saved", className: "bg-green-100 text-green-700" },
    no_picks: { label: "No picks found", className: "bg-amber-100 text-amber-700" },
    not_parsed: { label: "Not parsed", className: "bg-slate-100 text-slate-600" },
    error: { label: "Error", className: "bg-red-100 text-red-700" },
    received: { label: "Received", className: "bg-blue-100 text-blue-700" },
}

export default function SettingsPage() {
    const [cappers, setCappers] = useState<Capper[]>([])
    const [loading, setLoading] = useState(true)
    const [showAddForm, setShowAddForm] = useState(false)
    const [editingCapper, setEditingCapper] = useState<Capper | null>(null)
    const [formData, setFormData] = useState({ name: "", telegram_chat_id: "" })
    const [tgStatus, setTgStatus] = useState<TelegramStatus | null>(null)
    const [tgMessages, setTgMessages] = useState<TelegramMessage[]>([])
    const [tgLoading, setTgLoading] = useState(true)

    useEffect(() => {
        fetchCappers()
        fetchTelegram()
    }, [])

    const fetchTelegram = async () => {
        setTgLoading(true)
        try {
            const [statusRes, messagesRes] = await Promise.all([
                fetch(API_URL + "/api/telegram/status", { credentials: "include" }),
                fetch(API_URL + "/api/telegram/messages?limit=25", { credentials: "include" }),
            ])
            if (statusRes.ok) setTgStatus(await statusRes.json())
            if (messagesRes.ok) setTgMessages(await messagesRes.json())
        } catch (err) {
            console.error("Failed to fetch telegram status:", err)
        } finally {
            setTgLoading(false)
        }
    }

    const fetchCappers = async () => {
        try {
            const res = await fetch(API_URL + "/api/settings/cappers", { credentials: "include" })
            const data = await res.json()
            setCappers(data)
        } catch (err) {
            console.error("Failed to fetch cappers:", err)
        } finally {
            setLoading(false)
        }
    }

    const handleAddCapper = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            const res = await fetch(API_URL + "/api/settings/cappers", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: formData.name,
                    telegram_chat_id: formData.telegram_chat_id || null
                }),
                credentials: "include",
            })
            if (res.ok) {
                setFormData({ name: "", telegram_chat_id: "" })
                setShowAddForm(false)
                fetchCappers()
            } else {
                const error = await res.json()
                alert(error.detail || "Failed to add capper")
            }
        } catch (err) {
            console.error("Failed to add capper:", err)
            alert("Failed to add capper")
        }
    }

    const handleUpdateCapper = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!editingCapper) return

        try {
            const res = await fetch(`${API_URL}/api/settings/cappers/${editingCapper.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: formData.name,
                    telegram_chat_id: formData.telegram_chat_id || null
                }),
                credentials: "include",
            })
            if (res.ok) {
                setFormData({ name: "", telegram_chat_id: "" })
                setEditingCapper(null)
                fetchCappers()
            } else {
                const error = await res.json()
                alert(error.detail || "Failed to update capper")
            }
        } catch (err) {
            console.error("Failed to update capper:", err)
            alert("Failed to update capper")
        }
    }

    const handleDeleteCapper = async (id: number) => {
        if (!confirm("Are you sure you want to delete this capper? All associated picks will also be deleted.")) {
            return
        }

        try {
            const res = await fetch(`${API_URL}/api/settings/cappers/${id}`, {
                method: "DELETE",
                credentials: "include",
            })
            if (res.ok) {
                fetchCappers()
            } else {
                alert("Failed to delete capper")
            }
        } catch (err) {
            console.error("Failed to delete capper:", err)
            alert("Failed to delete capper")
        }
    }

    const startEdit = (capper: Capper) => {
        setEditingCapper(capper)
        setFormData({
            name: capper.name,
            telegram_chat_id: capper.telegram_chat_id || ""
        })
        setShowAddForm(false)
    }

    const cancelEdit = () => {
        setEditingCapper(null)
        setFormData({ name: "", telegram_chat_id: "" })
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold text-slate-900">Settings</h1>
                <button
                    onClick={() => {
                        setShowAddForm(true)
                        setEditingCapper(null)
                        setFormData({ name: "", telegram_chat_id: "" })
                    }}
                    className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-white hover:bg-green-700"
                >
                    <Plus className="h-5 w-5" />
                    Add Capper
                </button>
            </div>

            {/* Add/Edit Form */}
            {(showAddForm || editingCapper) && (
                <div className="rounded-lg bg-white p-6 shadow">
                    <div className="mb-4 flex items-center justify-between">
                        <h2 className="text-xl font-semibold text-slate-900">
                            {editingCapper ? "Edit Capper" : "Add New Capper"}
                        </h2>
                        <button
                            onClick={() => {
                                setShowAddForm(false)
                                cancelEdit()
                            }}
                            className="text-slate-500 hover:text-slate-600"
                        >
                            <X className="h-6 w-6" />
                        </button>
                    </div>
                    <form onSubmit={editingCapper ? handleUpdateCapper : handleAddCapper} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-700">Name</label>
                            <input
                                type="text"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                required
                                className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700">
                                Telegram Chat ID (Optional)
                            </label>
                            <input
                                type="text"
                                value={formData.telegram_chat_id}
                                onChange={(e) => setFormData({ ...formData, telegram_chat_id: e.target.value })}
                                className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
                            />
                        </div>
                        <div className="flex gap-2">
                            <button
                                type="submit"
                                className="rounded-lg bg-green-600 px-4 py-2 text-white hover:bg-green-700"
                            >
                                {editingCapper ? "Update" : "Add"}
                            </button>
                            {editingCapper && (
                                <button
                                    type="button"
                                    onClick={cancelEdit}
                                    className="rounded-lg bg-slate-200 px-4 py-2 text-slate-700 hover:bg-gray-300"
                                >
                                    Cancel
                                </button>
                            )}
                        </div>
                    </form>
                </div>
            )}

            {/* Cappers List */}
            <div className="rounded-lg bg-white shadow">
                <div className="border-b border-slate-200 px-6 py-4">
                    <h2 className="text-lg font-medium text-slate-900">Cappers</h2>
                </div>
                <div className="divide-y divide-slate-200">
                    {loading ? (
                        <div className="p-6 text-center text-slate-500">
                            Loading cappers...
                        </div>
                    ) : cappers.length === 0 ? (
                        <div className="p-6 text-center text-slate-700">
                            No cappers yet. Add one to get started.
                        </div>
                    ) : (
                        cappers.map((capper) => (
                            <div key={capper.id} className="flex items-center justify-between p-6">
                                <div>
                                    <h3 className="font-medium text-slate-900">{capper.name}</h3>
                                    {capper.telegram_chat_id && (
                                        <p className="text-sm text-slate-700">
                                            Telegram: {capper.telegram_chat_id}
                                        </p>
                                    )}
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => startEdit(capper)}
                                        className="rounded-lg bg-blue-100 p-2 text-blue-600 hover:bg-blue-200"
                                    >
                                        <Edit2 className="h-5 w-5" />
                                    </button>
                                    <button
                                        onClick={() => handleDeleteCapper(capper.id)}
                                        className="rounded-lg bg-red-100 p-2 text-red-600 hover:bg-red-200"
                                    >
                                        <Trash2 className="h-5 w-5" />
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Telegram Bot */}
            <div className="rounded-lg bg-white shadow">
                <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
                    <h2 className="text-lg font-medium text-slate-900">Telegram Bot</h2>
                    <button
                        onClick={fetchTelegram}
                        className="flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-200"
                    >
                        <RefreshCw className={`h-4 w-4 ${tgLoading ? "animate-spin" : ""}`} />
                        Refresh
                    </button>
                </div>

                {tgLoading && !tgStatus ? (
                    <div className="p-6 text-center text-slate-500">Checking bot status...</div>
                ) : !tgStatus || !tgStatus.configured ? (
                    <div className="p-6 text-slate-700">
                        No Telegram bot token configured. Set <code className="rounded bg-slate-100 px-1">TELEGRAM_BOT_TOKEN</code> in the backend environment to enable auto-ingestion.
                    </div>
                ) : (
                    <div className="space-y-4 p-6">
                        {/* Status pills */}
                        <div className="flex flex-wrap gap-2 text-sm">
                            <span className={`rounded-full px-3 py-1 ${tgStatus.connected ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                                {tgStatus.connected
                                    ? `Bot @${tgStatus.bot_username} connected`
                                    : "Bot unreachable"}
                            </span>
                            <span className={`rounded-full px-3 py-1 ${tgStatus.polling_running ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                                {tgStatus.polling_running ? "Listening for messages" : "Not listening"}
                            </span>
                            <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">
                                {tgStatus.messages_recorded} message{tgStatus.messages_recorded === 1 ? "" : "s"} received all-time
                            </span>
                            {tgStatus.last_update_at && (
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">
                                    Last message: {parseApiDate(tgStatus.last_update_at).toLocaleString()}
                                </span>
                            )}
                        </div>

                        {/* Privacy mode warning — the usual reason group messages never arrive */}
                        {tgStatus.can_read_all_group_messages === false && (
                            <div className="flex gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
                                <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" />
                                <div>
                                    <p className="font-semibold">Privacy mode is ON — the bot cannot see messages sent in groups.</p>
                                    <p className="mt-1">
                                        This is why messages you send to the group never show up here. To fix:
                                        message <span className="font-medium">@BotFather</span>, send <code className="rounded bg-amber-100 px-1">/setprivacy</code>,
                                        pick <span className="font-medium">@{tgStatus.bot_username}</span>, choose <span className="font-medium">Disable</span>,
                                        then <span className="font-medium">remove and re-add the bot to the group</span> (required for the change to take effect).
                                    </p>
                                </div>
                            </div>
                        )}

                        {tgStatus.last_error && (
                            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                                {tgStatus.last_error}
                            </div>
                        )}

                        {/* Recent messages */}
                        <div>
                            <h3 className="mb-2 text-sm font-medium text-slate-700">Recent messages received by the bot</h3>
                            {tgMessages.length === 0 ? (
                                <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">
                                    Nothing received yet. If you&apos;ve sent messages to the group and they don&apos;t
                                    appear here, Telegram isn&apos;t delivering them to the bot — check the privacy-mode
                                    warning above, make sure the bot is a member of the group, and that the backend was
                                    running (or has since restarted — queued messages are processed on startup).
                                </p>
                            ) : (
                                <div className="divide-y divide-slate-200 rounded-lg border border-slate-200">
                                    {tgMessages.map((msg) => {
                                        const badge = MESSAGE_STATUS_STYLES[msg.status] || MESSAGE_STATUS_STYLES.received
                                        return (
                                            <div key={msg.id} className="flex items-start justify-between gap-4 p-3">
                                                <div className="min-w-0">
                                                    <p className="text-sm text-slate-900">
                                                        <span className="font-medium">{msg.sender_name || "Unknown sender"}</span>
                                                        <span className="text-slate-500"> · {msg.message_type}</span>
                                                        {msg.chat_title && <span className="text-slate-500"> · {msg.chat_title}</span>}
                                                    </p>
                                                    {msg.text && (
                                                        <p className="mt-0.5 truncate text-sm text-slate-600">{msg.text}</p>
                                                    )}
                                                    {msg.detail && (
                                                        <p className="mt-0.5 text-xs text-slate-500">{msg.detail}</p>
                                                    )}
                                                </div>
                                                <div className="shrink-0 text-right">
                                                    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${badge.className}`}>
                                                        {badge.label}
                                                    </span>
                                                    <p className="mt-1 text-xs text-slate-500">
                                                        {parseApiDate(msg.created_at).toLocaleString()}
                                                    </p>
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
