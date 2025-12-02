"use client"

import { useState, useEffect } from "react"
import { Upload, FileText, Check, AlertCircle, Plus } from "lucide-react"

type TabType = "upload" | "manual"

interface Capper {
    id: number
    name: string
}

export default function UploadPage() {
    const [activeTab, setActiveTab] = useState<TabType>("upload")

    // Upload state
    const [file, setFile] = useState<File | null>(null)
    const [uploading, setUploading] = useState(false)
    const [picks, setPicks] = useState<any[]>([])
    const [error, setError] = useState<string | null>(null)

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
        odds: ""
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
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0])
            setError(null)
        }
    }

    const handleUpload = async () => {
        if (!file) return

        setUploading(true)
        setError(null)

        const formData = new FormData()
        formData.append("file", file)

        try {
            const response = await fetch("http://localhost:8000/api/upload/", {
                method: "POST",
                body: formData,
            })

            if (!response.ok) {
                throw new Error("Upload failed")
            }

            const data = await response.json()
            setPicks(data)
        } catch (err) {
            setError("Failed to upload and parse image. Please try again.")
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
                profit: 0.0
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
                odds: ""
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

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-gray-900">Add Picks</h1>

            {/* Tab Navigation */}
            <div className="border-b border-gray-200">
                <nav className="-mb-px flex space-x-8">
                    <button
                        onClick={() => setActiveTab("upload")}
                        className={`${activeTab === "upload"
                                ? "border-green-500 text-green-600"
                                : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                            } flex items-center whitespace-nowrap border-b-2 px-1 py-4 text-sm font-medium`}
                    >
                        <Upload className="mr-2 h-5 w-5" />
                        Upload Screenshot
                    </button>
                    <button
                        onClick={() => setActiveTab("manual")}
                        className={`${activeTab === "manual"
                                ? "border-green-500 text-green-600"
                                : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
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
                        <div className="flex flex-col items-center justify-center rounded-md border-2 border-dashed border-gray-300 p-12">
                            <Upload className="h-12 w-12 text-gray-400" />
                            <p className="mt-2 text-sm text-gray-500">Upload a screenshot of your picks</p>
                            <input
                                type="file"
                                accept="image/*"
                                onChange={handleFileChange}
                                className="mt-4"
                            />
                            {file && (
                                <button
                                    onClick={handleUpload}
                                    disabled={uploading}
                                    className="mt-4 rounded-md bg-green-600 px-4 py-2 text-white hover:bg-green-700 disabled:opacity-50"
                                >
                                    {uploading ? "Processing..." : "Extract Picks"}
                                </button>
                            )}
                        </div>

                        {error && (
                            <div className="mt-4 flex items-center text-red-600">
                                <AlertCircle className="mr-2 h-5 w-5" />
                                {error}
                            </div>
                        )}
                    </div>

                    {picks.length > 0 && (
                        <div className="rounded-lg bg-white shadow">
                            <div className="border-b border-gray-200 px-6 py-4">
                                <h2 className="text-lg font-medium text-gray-900">Extracted Picks</h2>
                            </div>
                            <div className="p-6">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead>
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Pick</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Units</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Raw Text</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-200 bg-white">
                                        {picks.map((pick, index) => (
                                            <tr key={index}>
                                                <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">{pick.pick_text}</td>
                                                <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">{pick.units_risked}u</td>
                                                <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">{pick.raw_text}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>

                                <div className="mt-6 flex justify-end">
                                    <button className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">
                                        Save Picks
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
                                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
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
                                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
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
                                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
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
                                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
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
                                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
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
                                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
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
                                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-green-500 focus:outline-none focus:ring-green-500"
                                    placeholder="-110"
                                />
                            </div>
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
