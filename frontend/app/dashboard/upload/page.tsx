"use client"

import { useState, useEffect, useRef } from "react"
import { Upload, FileText, Check, AlertCircle, Plus, X, ImageIcon } from "lucide-react"

type TabType = "upload" | "manual"

interface Capper {
    id: number
    name: string
}

export default function UploadPage() {
    const [activeTab, setActiveTab] = useState<TabType>("upload")

    // Upload state
    const [files, setFiles] = useState<File[]>([])
    const [isDragging, setIsDragging] = useState(false)
    const [uploading, setUploading] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)
    const dragCounter = useRef(0)
    const [picks, setPicks] = useState<any[]>([])
    const [error, setError] = useState<string | null>(null)
    const [errorModal, setErrorModal] = useState<{ title: string; message: string; rawText?: string } | null>(null)
    const [selectedCapper, setSelectedCapper] = useState<string>("")
    const [capperAutoDetected, setCapperAutoDetected] = useState<boolean>(false)
    const [saving, setSaving] = useState(false)
    const [saveSuccess, setSaveSuccess] = useState(false)
    const [saveMessage, setSaveMessage] = useState("")
    const [gameDate, setGameDate] = useState<string>("")

    // Manual entry state
    const [cappers, setCappers] = useState<Capper[]>([])
    const [submitting, setSubmitting] = useState(false)
    const [success, setSuccess] = useState(false)
    const [formData, setFormData] = useState({
        capper_name: "",
        sport: "",
        league: "",
        match_key: "",
        pick_text: "",
        units_risked: "",
        odds: "",
        game_date: "",
    })

    // Fetch cappers for dropdown
    useEffect(() => {
        fetchCappers()
    }, [])

    const fetchCappers = async () => {
        try {
            const response = await fetch("http://localhost:8000/api/settings/cappers")
            if (response.ok) {
                const data = await response.json()
                setCappers(data)
            }
        } catch (err) {
            console.error("Failed to fetch cappers:", err)
        }
    }

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            addFiles(Array.from(e.target.files))
            e.target.value = ""  // reset so same file can be re-added
        }
    }

    const addFiles = (incoming: File[]) => {
        const images = incoming.filter(f => f.type.startsWith("image/"))
        if (images.length === 0) { setError("Please drop image files only"); return }
        setFiles(prev => {
            const existing = new Set(prev.map(f => f.name + f.size))
            return [...prev, ...images.filter(f => !existing.has(f.name + f.size))]
        })
        setError(null)
    }

    const handleDragEnter = (e: React.DragEvent) => {
        e.preventDefault()
        dragCounter.current++
        setIsDragging(true)
    }

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault()
    }

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault()
        dragCounter.current--
        if (dragCounter.current === 0) setIsDragging(false)
    }

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault()
        dragCounter.current = 0
        setIsDragging(false)
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            addFiles(Array.from(e.dataTransfer.files))
        }
    }

    const removeFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index))
    }

    const handleUpload = async () => {
        if (files.length === 0) return

        setUploading(true)
        setError(null)

        const formData = new FormData()
        files.forEach(file => {
            formData.append("files", file)
        })

        try {
            const response = await fetch("http://localhost:8000/api/upload/", {
                method: "POST",
                body: formData,
            })

            if (!response.ok) {
                throw new Error("Upload failed")
            }

            const data = await response.json()
            const parsedPicks = data.picks ?? data

            if (parsedPicks.length === 0) {
                setErrorModal({
                    title: "No picks found",
                    message: "OCR processed the image but couldn't identify any picks. Make sure the screenshot shows clearly formatted picks (e.g. 'Lakers -5.5 2u'). Higher resolution screenshots work best.",
                    rawText: data.raw_text || undefined,
                })
                return
            }

            setPicks(parsedPicks)

            if (data.detected_capper) {
                setSelectedCapper(data.detected_capper)
                setCapperAutoDetected(true)
            } else {
                setSelectedCapper("")
                setCapperAutoDetected(false)
            }
        } catch (err) {
            setErrorModal({
                title: "Upload failed",
                message: "Could not reach the server or process the image. Make sure the backend is running and try again.",
            })
            console.error(err)
        } finally {
            setUploading(false)
        }
    }

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        const { name, value } = e.target
        setFormData(prev => ({ ...prev, [name]: value }))
        setError(null)
    }

    const handleManualSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        // Validation
        if (!formData.capper_name || !formData.sport || !formData.pick_text || !formData.units_risked) {
            setError("Please fill in all required fields")
            return
        }

        setSubmitting(true)
        setError(null)
        setSuccess(false)

        try {
            const payload = {
                capper_name: formData.capper_name,
                sport: formData.sport,
                league: formData.league || null,
                match_key: formData.match_key || null,
                pick_text: formData.pick_text,
                units_risked: parseFloat(formData.units_risked),
                odds: formData.odds ? parseInt(formData.odds) : null,
                result: "PENDING",
                profit: 0.0,
                game_date: formData.game_date ? new Date(formData.game_date).toISOString() : null,
            }

            const response = await fetch("http://localhost:8000/api/picks/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            })

            if (!response.ok) {
                throw new Error("Failed to create pick")
            }

            setSuccess(true)
            // Reset form
            setFormData({
                capper_name: "",
                sport: "",
                league: "",
                match_key: "",
                pick_text: "",
                units_risked: "",
                odds: "",
                game_date: "",
            })

            // Refresh cappers list in case a new one was added
            fetchCappers()

            // Clear success message after 3 seconds
            setTimeout(() => setSuccess(false), 3000)
        } catch (err) {
            setError("Failed to create pick. Please try again.")
            console.error(err)
        } finally {
            setSubmitting(false)
        }
    }

    const handleRemovePick = (index: number) => {
        setPicks(prev => prev.filter((_, i) => i !== index))
    }

    const handleSavePicks = async () => {
        if (!selectedCapper) {
            setError("Please select a capper")
            return
        }

        if (picks.length === 0) {
            setError("No picks to save")
            return
        }

        setSaving(true)
        setError(null)
        setSaveSuccess(false)

        try {
            // Save each pick
            const savePromises = picks.map(pick => {
                const payload = {
                    capper_name: selectedCapper,
                    sport: pick.sport || "Unknown",
                    league: pick.league || null,
                    match_key: pick.match_key || null,
                    pick_text: pick.pick_text,
                    units_risked: pick.units_risked,
                    odds: pick.odds || null,
                    result: "PENDING",
                    profit: 0.0,
                    raw_text: pick.raw_text || null,
                    game_date: gameDate ? new Date(gameDate).toISOString() : null,
                }

                return fetch("http://localhost:8000/api/picks/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(payload),
                })
            })

            const responses = await Promise.all(savePromises)

            if (responses.some(r => !r.ok)) {
                throw new Error("Some picks failed to save")
            }

            const duplicates = responses.filter(r => r.headers.get("X-Duplicate") === "true").length
            const saved = responses.length - duplicates
            setSaveSuccess(true)
            setSaveMessage(
                duplicates > 0
                    ? `${saved} pick${saved !== 1 ? "s" : ""} saved · ${duplicates} already existed`
                    : `${saved} pick${saved !== 1 ? "s" : ""} saved`
            )

            // Clear the picks and files after successful save
            setPicks([])
            setFiles([])
            setSelectedCapper("")
            setCapperAutoDetected(false)
            setGameDate("")

            // Refresh cappers list in case a new one was added
            fetchCappers()

            // Clear success message after 3 seconds
            setTimeout(() => setSaveSuccess(false), 3000)
        } catch (err) {
            setError("Failed to save picks. Please try again.")
            console.error(err)
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="space-y-6">
            {/* Error Modal */}
            {errorModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl">
                        <div className="flex items-start gap-4 border-b border-gray-100 p-6">
                            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-red-100">
                                <AlertCircle className="h-6 w-6 text-red-600" />
                            </div>
                            <div className="flex-1">
                                <h3 className="text-lg font-semibold text-gray-900">{errorModal.title}</h3>
                                <p className="mt-1 text-sm text-gray-600">{errorModal.message}</p>
                            </div>
                            <button onClick={() => setErrorModal(null)} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
                                <X className="h-5 w-5" />
                            </button>
                        </div>
                        {errorModal.rawText && (
                            <div className="p-6">
                                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
                                    What OCR extracted from your image
                                </p>
                                <pre className="max-h-48 overflow-y-auto rounded-lg bg-gray-50 p-3 text-xs text-gray-700 whitespace-pre-wrap break-words border border-gray-200">
                                    {errorModal.rawText.trim() || "(nothing — image may be unreadable or blank)"}
                                </pre>
                                <p className="mt-2 text-xs text-gray-400">
                                    If the text above looks correct but picks weren&apos;t detected, the format may not be recognised. Try a clearer screenshot.
                                </p>
                            </div>
                        )}
                        <div className="flex justify-end gap-3 border-t border-gray-100 px-6 py-4">
                            <button
                                onClick={() => setErrorModal(null)}
                                className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
                            >
                                Got it
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <h1 className="text-3xl font-bold text-gray-900">Add Picks</h1>

            {/* Tab Navigation */}
            <div className="border-b border-gray-200">
                <nav className="-mb-px flex space-x-8">
                    <button
                        onClick={() => setActiveTab("upload")}
                        className={`${activeTab === "upload"
                            ? "border-green-500 text-green-600"
                            : "border-transparent text-gray-600 hover:border-gray-300 hover:text-gray-800"
                            } flex items-center whitespace-nowrap border-b-2 px-1 py-4 text-sm font-medium`}
                    >
                        <Upload className="mr-2 h-5 w-5" />
                        Upload Screenshot
                    </button>
                    <button
                        onClick={() => setActiveTab("manual")}
                        className={`${activeTab === "manual"
                            ? "border-green-500 text-green-600"
                            : "border-transparent text-gray-600 hover:border-gray-300 hover:text-gray-800"
                            } flex items-center whitespace-nowrap border-b-2 px-1 py-4 text-sm font-medium`}
                    >
                        <Plus className="mr-2 h-5 w-5" />
                        Manual Entry
                    </button>
                </nav>
            </div>

            {/* Upload Tab Content */}
            {activeTab === "upload" && (
                <>
                    <div className="rounded-lg bg-white p-6 shadow">
                        {/* Hidden file input */}
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            multiple
                            onChange={handleFileChange}
                            className="hidden"
                        />

                        {/* Drop zone */}
                        <div
                            className={`relative rounded-xl border-2 border-dashed transition-all duration-150 ${
                                isDragging
                                    ? "border-green-500 bg-green-50 scale-[1.01]"
                                    : "border-gray-300 hover:border-green-400 hover:bg-gray-50"
                            }`}
                            onDragEnter={handleDragEnter}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                        >
                            {isDragging && (
                                <div className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-xl bg-green-50/80 z-10">
                                    <div className="flex flex-col items-center gap-2">
                                        <Upload className="h-12 w-12 text-green-500" />
                                        <p className="text-lg font-semibold text-green-700">Drop to upload</p>
                                    </div>
                                </div>
                            )}

                            {files.length === 0 ? (
                                /* Empty state — click to browse */
                                <button
                                    type="button"
                                    onClick={() => fileInputRef.current?.click()}
                                    className="flex w-full flex-col items-center justify-center gap-3 p-16 text-center focus:outline-none"
                                >
                                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gray-100">
                                        <Upload className="h-8 w-8 text-gray-400" />
                                    </div>
                                    <div>
                                        <p className="text-sm font-medium text-gray-700">
                                            Drop screenshots here, or{" "}
                                            <span className="text-green-600 underline underline-offset-2">browse</span>
                                        </p>
                                        <p className="mt-1 text-xs text-gray-400">PNG, JPG, WEBP — multiple files supported</p>
                                    </div>
                                </button>
                            ) : (
                                /* Thumbnail grid */
                                <div className="p-4">
                                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                                        {files.map((file, index) => (
                                            <div key={index} className="group relative aspect-square overflow-hidden rounded-lg border border-gray-200 bg-gray-50">
                                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                                <img
                                                    src={URL.createObjectURL(file)}
                                                    alt={file.name}
                                                    className="h-full w-full object-cover"
                                                />
                                                <div className="absolute inset-0 flex flex-col justify-between bg-gradient-to-t from-black/60 to-transparent p-2 opacity-0 transition-opacity group-hover:opacity-100">
                                                    <button
                                                        onClick={() => removeFile(index)}
                                                        className="ml-auto flex h-6 w-6 items-center justify-center rounded-full bg-black/50 text-white hover:bg-red-600"
                                                    >
                                                        <X className="h-3.5 w-3.5" />
                                                    </button>
                                                    <p className="truncate text-xs text-white">{file.name}</p>
                                                </div>
                                            </div>
                                        ))}

                                        {/* Add more tile */}
                                        <button
                                            type="button"
                                            onClick={() => fileInputRef.current?.click()}
                                            className="flex aspect-square items-center justify-center rounded-lg border-2 border-dashed border-gray-200 text-gray-400 hover:border-green-400 hover:text-green-500 transition-colors"
                                        >
                                            <Plus className="h-6 w-6" />
                                        </button>
                                    </div>

                                    <div className="mt-4 flex items-center justify-between">
                                        <p className="text-sm text-gray-500">{files.length} image{files.length !== 1 ? "s" : ""} selected</p>
                                        <button
                                            onClick={handleUpload}
                                            disabled={uploading}
                                            className="rounded-lg bg-green-600 px-5 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
                                        >
                                            {uploading ? "Processing…" : `Extract Picks`}
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>

                    </div>

                    {picks.length > 0 && (
                        <div className="rounded-lg bg-white shadow">
                            <div className="border-b border-gray-200 px-6 py-4">
                                <h2 className="text-lg font-medium text-gray-900">Extracted Picks</h2>
                            </div>
                            <div className="p-6">
                                {/* Capper Selection */}
                                <div className="mb-6">
                                    <label htmlFor="upload-capper" className="block text-sm font-medium text-gray-700 mb-2">
                                        Capper <span className="text-red-500">*</span>
                                    </label>

                                    {/* New capper notice */}
                                    {selectedCapper && !cappers.some(c => c.name.toLowerCase() === selectedCapper.toLowerCase()) && (
                                        <div className="mb-2 flex items-start gap-2 rounded-md border border-blue-300 bg-blue-50 px-3 py-2 text-sm text-blue-800">
                                            <span>New capper will be created: <strong>{selectedCapper}</strong></span>
                                        </div>
                                    )}

                                    {/* Warning banner when capper could not be detected */}
                                    {!capperAutoDetected && (
                                        <div className="mb-2 flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                                            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                                            <span>
                                                Could not detect the capper name from the image.
                                                Please enter it below.
                                            </span>
                                        </div>
                                    )}

                                    <div className="relative max-w-md">
                                        <input
                                            type="text"
                                            id="upload-capper"
                                            list="upload-cappers-list"
                                            value={selectedCapper}
                                            onChange={(e) => {
                                                setSelectedCapper(e.target.value)
                                                setCapperAutoDetected(false)
                                            }}
                                            className={`block w-full rounded-md px-3 py-2 shadow-sm placeholder-gray-400 focus:outline-none focus:ring-1 ${
                                                capperAutoDetected
                                                    ? "border border-green-400 bg-green-50 focus:border-green-500 focus:ring-green-500"
                                                    : "border-2 border-amber-400 focus:border-amber-500 focus:ring-amber-400"
                                            }`}
                                            placeholder="Select or type capper name"
                                        />
                                        {capperAutoDetected && (
                                            <span className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                                                <Check className="h-3 w-3" />
                                                Auto-detected
                                            </span>
                                        )}
                                    </div>
                                    <datalist id="upload-cappers-list">
                                        {cappers.map(capper => (
                                            <option key={capper.id} value={capper.name} />
                                        ))}
                                    </datalist>
                                </div>

                                {/* Game Date */}
                                <div className="mb-6">
                                    <label htmlFor="upload-game-date" className="block text-sm font-medium text-gray-700 mb-1">
                                        Game Date
                                        <span className="ml-1.5 text-xs font-normal text-gray-400">(used for ESPN auto-grading)</span>
                                    </label>
                                    <input
                                        type="date"
                                        id="upload-game-date"
                                        value={gameDate}
                                        onChange={e => setGameDate(e.target.value)}
                                        className="block w-48 rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
                                    />
                                </div>

                                {/* Success Message */}
                                {saveSuccess && (
                                    <div className="mb-4 flex items-center rounded-md bg-green-50 p-4 text-green-800">
                                        <Check className="mr-2 h-5 w-5 shrink-0" />
                                        {saveMessage || "Picks saved successfully!"}
                                    </div>
                                )}

                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead>
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Pick</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Sport</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Units</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700">Odds</th>
                                            <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-700">Remove</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-200 bg-white">
                                        {picks.map((pick, index) => (
                                            <tr key={index}>
                                                <td className="px-6 py-4 text-sm font-medium text-gray-900">{pick.pick_text}</td>
                                                <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-700">{pick.sport || "—"}</td>
                                                <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-700">{pick.units_risked}u</td>
                                                <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-700">
                                                    {pick.odds ? (pick.odds > 0 ? `+${pick.odds}` : pick.odds) : "—"}
                                                </td>
                                                <td className="whitespace-nowrap px-6 py-4 text-right">
                                                    <button
                                                        onClick={() => handleRemovePick(index)}
                                                        className="text-red-500 hover:text-red-700"
                                                        title="Remove pick"
                                                    >
                                                        <X className="h-4 w-4" />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>

                                <div className="mt-6 flex justify-end">
                                    <button
                                        onClick={handleSavePicks}
                                        disabled={!selectedCapper || saving}
                                        className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {saving ? "Saving..." : "Save Picks"}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* Manual Entry Tab Content */}
            {activeTab === "manual" && (
                <div className="rounded-lg bg-white p-6 shadow">
                    <form onSubmit={handleManualSubmit} className="space-y-6">
                        {/* Capper Selection */}
                        <div>
                            <label htmlFor="capper_name" className="block text-sm font-medium text-gray-700">
                                Capper <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="text"
                                id="capper_name"
                                name="capper_name"
                                list="cappers-list"
                                value={formData.capper_name}
                                onChange={handleInputChange}
                                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm placeholder-gray-500 focus:border-green-500 focus:outline-none focus:ring-green-500"
                                placeholder="Select or type capper name"
                                required
                            />
                            <datalist id="cappers-list">
                                {cappers.map(capper => (
                                    <option key={capper.id} value={capper.name} />
                                ))}
                            </datalist>
                        </div>

                        {/* Sport */}
                        <div>
                            <label htmlFor="sport" className="block text-sm font-medium text-gray-700">
                                Sport <span className="text-red-500">*</span>
                            </label>
                            <select
                                id="sport"
                                name="sport"
                                value={formData.sport}
                                onChange={handleInputChange}
                                className="mt-1 block w-full rounded-md border border-gray-900 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
                                required
                            >
                                <option value="">Select a sport</option>
                                <option value="NFL">NFL</option>
                                <option value="NBA">NBA</option>
                                <option value="MLB">MLB</option>
                                <option value="NHL">NHL</option>
                                <option value="NCAAF">NCAAF</option>
                                <option value="NCAAB">NCAAB</option>
                                <option value="Soccer">Soccer</option>
                                <option value="UFC">UFC</option>
                                <option value="Boxing">Boxing</option>
                                <option value="Other">Other</option>
                            </select>
                        </div>

                        {/* League */}
                        <div>
                            <label htmlFor="league" className="block text-sm font-medium text-gray-700">
                                League
                            </label>
                            <input
                                type="text"
                                id="league"
                                name="league"
                                value={formData.league}
                                onChange={handleInputChange}
                                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm placeholder-gray-500 focus:border-green-500 focus:outline-none focus:ring-green-500"
                                placeholder="e.g., NFL, Premier League"
                            />
                        </div>

                        {/* Match/Game */}
                        <div>
                            <label htmlFor="match_key" className="block text-sm font-medium text-gray-700">
                                Match/Game
                            </label>
                            <input
                                type="text"
                                id="match_key"
                                name="match_key"
                                value={formData.match_key}
                                onChange={handleInputChange}
                                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm placeholder-gray-500 focus:border-green-500 focus:outline-none focus:ring-green-500"
                                placeholder="e.g., LAL vs BOS"
                            />
                        </div>

                        {/* Pick Description */}
                        <div>
                            <label htmlFor="pick_text" className="block text-sm font-medium text-gray-700">
                                Pick Description <span className="text-red-500">*</span>
                            </label>
                            <textarea
                                id="pick_text"
                                name="pick_text"
                                value={formData.pick_text}
                                onChange={handleInputChange}
                                rows={3}
                                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm placeholder-gray-500 focus:border-green-500 focus:outline-none focus:ring-green-500"
                                placeholder="e.g., Lakers -5.5, Over 220.5"
                                required
                            />
                        </div>

                        {/* Units and Odds Row */}
                        <div className="grid grid-cols-2 gap-4">
                            {/* Units Risked */}
                            <div>
                                <label htmlFor="units_risked" className="block text-sm font-medium text-gray-700">
                                    Units Risked <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="number"
                                    id="units_risked"
                                    name="units_risked"
                                    value={formData.units_risked}
                                    onChange={handleInputChange}
                                    step="0.5"
                                    min="0.5"
                                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm placeholder-gray-500 focus:border-green-500 focus:outline-none focus:ring-green-500"
                                    placeholder="1.0"
                                    required
                                />
                            </div>

                            {/* Odds */}
                            <div>
                                <label htmlFor="odds" className="block text-sm font-medium text-gray-700">
                                    Odds (American)
                                </label>
                                <input
                                    type="number"
                                    id="odds"
                                    name="odds"
                                    value={formData.odds}
                                    onChange={handleInputChange}
                                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm placeholder-gray-500 focus:border-green-500 focus:outline-none focus:ring-green-500"
                                    placeholder="-110"
                                />
                            </div>
                        </div>

                        {/* Game Date */}
                        <div>
                            <label htmlFor="manual_game_date" className="block text-sm font-medium text-gray-700">
                                Game Date <span className="text-gray-400 font-normal">(optional)</span>
                            </label>
                            <input
                                type="date"
                                id="manual_game_date"
                                name="game_date"
                                value={formData.game_date}
                                onChange={handleInputChange}
                                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
                            />
                            <p className="mt-1 text-xs text-gray-400">When the game is played — used for auto-grading</p>
                        </div>

                        {/* Success Message */}
                        {success && (
                            <div className="flex items-center rounded-md bg-green-50 p-4 text-green-800">
                                <Check className="mr-2 h-5 w-5" />
                                Pick created successfully!
                            </div>
                        )}

                        {/* Error Message */}
                        {error && (
                            <div className="flex items-center rounded-md bg-red-50 p-4 text-red-800">
                                <AlertCircle className="mr-2 h-5 w-5" />
                                {error}
                            </div>
                        )}

                        {/* Submit Button */}
                        <div className="flex justify-end">
                            <button
                                type="submit"
                                disabled={submitting}
                                className="rounded-md bg-green-600 px-6 py-2 text-white hover:bg-green-700 disabled:opacity-50"
                            >
                                {submitting ? "Creating..." : "Create Pick"}
                            </button>
                        </div>
                    </form>
                </div>
            )}
        </div>
    )
}
