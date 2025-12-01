"use client"

import { useState } from "react"
import { Upload, FileText, Check, AlertCircle } from "lucide-react"

export default function UploadPage() {
    const [file, setFile] = useState<File | null>(null)
    const [uploading, setUploading] = useState(false)
    const [picks, setPicks] = useState<any[]>([])
    const [error, setError] = useState<string | null>(null)

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

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-gray-900">Upload Picks</h1>

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
        </div>
    )
}
