"use client";

import { useState, useRef } from "react";
import { FeatherIcon } from "@/components/xp/xp-feather-icon";

export default function OcrPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    text?: string;
    confidence?: number;
    pages?: number;
    error?: string;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setResult(null);
      
      // Create preview for images
      if (selectedFile.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (e) => setPreview(e.target?.result as string);
        reader.readAsDataURL(selectedFile);
      } else {
        setPreview(null);
      }
    }
  };

  const handleExtract = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/ocr/extract", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setResult({ error: "Metin çıkarma başarısız oldu" });
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (result?.text) {
      navigator.clipboard.writeText(result.text);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#ECE9D8] p-4 overflow-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4 pb-3 border-b border-[#d6d2c2]">
        <div className="w-10 h-10 rounded-lg bg-emerald-500 flex items-center justify-center">
          <FeatherIcon name="file-text" color="white" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-gray-800">OCR & Metin Çıkarma</h2>
          <p className="text-xs text-gray-600">Görseller ve PDF'lerden metin çıkarın</p>
        </div>
      </div>

      {/* File Upload */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Dosya Seçin
        </label>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,.pdf"
            onChange={handleFileChange}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex-1 px-3 py-2 border-2 border-dashed border-gray-400 rounded text-sm text-gray-600 hover:border-emerald-500 hover:text-emerald-600 transition-colors"
          >
            {file ? `📄 ${file.name}` : "Görsel veya PDF seçin..."}
          </button>
          <button
            onClick={handleExtract}
            disabled={loading || !file}
            className="px-4 py-2 bg-emerald-500 text-white rounded font-medium hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Çıkarılıyor..." : "Çıkar"}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Desteklenen formatlar: PNG, JPG, WEBP, PDF
        </p>
      </div>

      {/* Preview */}
      {preview && (
        <div className="mb-4">
          <img
            src={preview}
            alt="Preview"
            className="max-h-40 rounded border border-gray-300"
          />
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="flex-1 overflow-auto">
          {result.error ? (
            <div className="p-4 bg-red-100 border border-red-400 rounded text-red-700">
              {result.error}
            </div>
          ) : (
            <div className="space-y-3">
              {/* Stats */}
              <div className="flex gap-4 text-sm">
                {result.confidence && (
                  <span className="px-2 py-1 bg-emerald-100 text-emerald-700 rounded">
                    🎯 Güven: %{Math.round(result.confidence * 100)}
                  </span>
                )}
                {result.pages && (
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">
                    📄 {result.pages} sayfa
                  </span>
                )}
              </div>

              {/* Text */}
              {result.text && (
                <div className="p-3 bg-white border border-gray-300 rounded">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-bold text-gray-800">Çıkarılan Metin</h4>
                    <button
                      onClick={handleCopy}
                      className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded"
                    >
                      📋 Kopyala
                    </button>
                  </div>
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap max-h-80 overflow-auto">
                    {result.text}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!result && !loading && (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <div className="text-4xl mb-2">📄</div>
            <p>Bir görsel veya PDF yükleyin</p>
            <p className="text-xs mt-1">Tesseract OCR ile metin çıkarın</p>
          </div>
        </div>
      )}
    </div>
  );
}