"use client"

import { useEffect, useState } from "react"
import { Trash2, Edit2, Plus, X } from "lucide-react"

interface Capper {
    id: number
    name: string
    telegram_chat_id: string | null
    created_at: string
}

export default function SettingsPage() {
    const [cappers, setCappers] = useState<Capper[]>([])
    const [loading, setLoading] = useState(true)
    const [showAddForm, setShowAddForm] = useState(false)
    const [editingCapper, setEditingCapper] = useState<Capper | null>(null)
    const [formData, setFormData] = useState({ name: "", telegram_chat_id: "" })

    useEffect(() => {
        fetchCappers()
    }, [])

    const fetchCappers = async () => {
        try {
            const res = await fetch("http://localhost:8000/api/settings/cappers")
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
            const res = await fetch("http://localhost:8000/api/settings/cappers", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: formData.name,
                    telegram_chat_id: formData.telegram_chat_id || null
                })
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
            const res = await fetch(`http://localhost:8000/api/settings/cappers/${editingCapper.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: formData.name,
                    telegram_chat_id: formData.telegram_chat_id || null
                })
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
            const res = await fetch(`http://localhost:8000/api/settings/cappers/${id}`, {
                method: "DELETE"
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

    if (loading) {
        return <div className="text-slate-700">Loading...</div>
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
                    {cappers.length === 0 ? (
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
        </div>
    )
}
