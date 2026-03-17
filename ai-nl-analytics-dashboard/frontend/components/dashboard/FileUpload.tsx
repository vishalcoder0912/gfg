'use client';

import React, { useState } from 'react';
import { Upload, X, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

import { uploadCsv } from '../../lib/api';
import type { DatasetProfile } from '../../lib/types';

interface FileUploadProps {
  onUploadComplete?: (profile: DatasetProfile) => Promise<void> | void;
}

const DEFAULT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024;

function getMaxUploadBytes(): number {
  const raw = process.env.NEXT_PUBLIC_MAX_UPLOAD_BYTES;
  const parsed = raw ? Number(raw) : NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_MAX_UPLOAD_BYTES;
}

function formatBytes(n: number) {
  const units = ['B', 'KB', 'MB', 'GB'];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

const FileUpload = ({ onUploadComplete }: FileUploadProps) => {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      const maxUploadBytes = getMaxUploadBytes();
      if (selectedFile.name.endsWith('.csv')) {
        if (selectedFile.size > maxUploadBytes) {
          setError(`File too large. Max ${formatBytes(maxUploadBytes)}.`);
          setFile(null);
          setStatus('idle');
          return;
        }
        setFile(selectedFile);
        setError(null);
        setStatus('idle');
      } else {
        setError('Please select a valid CSV file');
        setFile(null);
      }
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setStatus('uploading');
    setError(null);

    try {
      const data = await uploadCsv(file);
      console.log('Upload success:', data);
      setStatus('success');
      if (onUploadComplete) {
         await onUploadComplete(data);
      }
    } catch (err) {
      setStatus('error');
      setError(err instanceof Error ? err.message : 'Something went wrong');
    }
  };



  return (
    <div className="bg-white rounded-2xl border-2 border-dashed border-gray-200 p-8 transition-all hover:border-indigo-300">
      <div className="flex flex-col items-center text-center">
        {!file ? (
          <>
            <div className="w-16 h-16 bg-indigo-50 rounded-full flex items-center justify-center mb-4">
              <Upload className="w-8 h-8 text-indigo-600" />
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Upload your dataset</h3>
            <p className="text-sm text-gray-500 mb-6 max-w-xs">
              Drag and drop your CSV file here or click to browse from your computer.
            </p>
            <label className="bg-indigo-600 text-white px-6 py-2.5 rounded-xl font-bold text-sm cursor-pointer hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-100">
              Browse Files
              <input type="file" className="hidden" accept=".csv" onChange={handleFileChange} />
            </label>
          </>
        ) : (
          <div className="w-full">
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center text-indigo-600">
                  <FileText className="w-6 h-6" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-bold text-gray-900 truncate max-w-[200px]">{file.name}</p>
                  <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(2)} KB</p>
                </div>
              </div>
              <button 
                onClick={() => setFile(null)}
                className="p-1 hover:bg-gray-200 rounded-full transition-colors"
                disabled={status === 'uploading'}
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            {status === 'idle' && (
              <button 
                onClick={handleUpload}
                className="w-full bg-indigo-600 text-white py-3 rounded-xl font-bold hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-100"
              >
                Analyze Dataset
              </button>
            )}

            {status === 'uploading' && (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
                <p className="text-sm font-medium text-gray-600">Processing with Gemini AI...</p>
              </div>
            )}

            {status === 'success' && (
              <div className="flex flex-col items-center gap-2">
                <CheckCircle2 className="w-8 h-8 text-green-500" />
                <p className="text-sm font-bold text-gray-900">Analysis Complete!</p>
                <p className="text-xs text-gray-500 mb-4">Your dashboard is ready.</p>
                <button 
                  onClick={() => setFile(null)}
                  className="text-indigo-600 text-sm font-bold hover:underline"
                >
                  Upload another file
                </button>
              </div>
            )}

            {status === 'error' && (
              <div className="flex flex-col items-center gap-2">
                <AlertCircle className="w-8 h-8 text-red-500" />
                <p className="text-sm font-bold text-gray-900">{error || 'Upload failed'}</p>
                <button 
                  onClick={handleUpload}
                  className="mt-2 bg-red-50 text-red-600 px-4 py-2 rounded-lg text-sm font-bold hover:bg-red-100 transition-colors"
                >
                  Try Again
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default FileUpload;
