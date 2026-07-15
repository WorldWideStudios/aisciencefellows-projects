import React, { useRef, useState } from 'react';
import { Upload, FileText, X, CheckCircle2, Loader2 } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import imageCompression from 'browser-image-compression';
import { PDFDocument } from 'pdf-lib';
import * as pdfjsLib from 'pdfjs-dist';
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface FileUploadProps {
  label: string;
  onFilesSelect: (files: { data: string; mimeType: string; name: string; sizeBytes: number }[]) => void;
  onProcessingChange?: (isProcessing: boolean) => void;
  accept?: string;
  id: string;
  multiple?: boolean;
}

type UploadFilePayload = { data: string; mimeType: string; name: string; sizeBytes: number };

const LARGE_PDF_THRESHOLD_BYTES = 12 * 1024 * 1024;
const TARGET_PDF_BYTES = 8 * 1024 * 1024;
const MIN_PAGE_EDGE_PX = 900;
const PDF_RASTER_PROFILES = [
  { longestSidePx: 1800, jpegQuality: 0.72 },
  { longestSidePx: 1400, jpegQuality: 0.58 },
  { longestSidePx: 1100, jpegQuality: 0.46 },
] as const;

export const FileUpload: React.FC<FileUploadProps> = ({ label, onFilesSelect, onProcessingChange, accept = ".pdf,image/*", id, multiple = false }) => {
  const [fileNames, setFileNames] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const setProcessing = (processing: boolean) => {
    setIsProcessing(processing);
    onProcessingChange?.(processing);
  };

  const fileToBase64 = (file: Blob): Promise<string> => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const base64Data = e.target?.result as string;
      resolve(base64Data.split(',')[1]);
    };
    reader.onerror = () => reject(reader.error ?? new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });

  const buildPayload = async (file: Blob, name: string, mimeType: string): Promise<UploadFilePayload> => ({
    data: await fileToBase64(file),
    mimeType,
    name,
    sizeBytes: file.size,
  });

  const canvasToBlob = (canvas: HTMLCanvasElement, type: string, quality?: number): Promise<Blob> =>
    new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (blob) {
          resolve(blob);
          return;
        }
        reject(new Error('Failed to encode canvas'));
      }, type, quality);
    });

  const compressImage = async (file: File): Promise<UploadFilePayload> => {
    const options = {
      maxSizeMB: 1.5, // Max size 1.5MB to stay safe for browser memory
      maxWidthOrHeight: 2048,
      useWebWorker: true,
      initialQuality: 0.85,
    };

    try {
      const compressedFile = await imageCompression(file, options);
      return buildPayload(compressedFile, file.name, compressedFile.type);
    } catch (error) {
      console.error('Compression error:', error);
      // Fallback to original if compression fails
      return buildPayload(file, file.name, file.type);
    }
  };

  const optimizePdf = async (file: File): Promise<UploadFilePayload> => {
    try {
      const inputBytes = await file.arrayBuffer();
      const pdf = await PDFDocument.load(inputBytes);

      // pdf-lib cannot aggressively recompress embedded page images,
      // but re-saving can still remove some structural overhead.
      const optimizedBytes = await pdf.save({
        useObjectStreams: true,
        addDefaultPage: false,
        updateFieldAppearances: false,
        objectsPerTick: 50,
      });

      const optimizedBlob = new Blob([optimizedBytes], { type: 'application/pdf' });
      let preferredFile: Blob = optimizedBlob.size < file.size ? optimizedBlob : file;

      if (preferredFile.size > LARGE_PDF_THRESHOLD_BYTES) {
        preferredFile = await rasterizePdf(preferredFile, file.name);
      }

      return buildPayload(preferredFile, file.name, 'application/pdf');
    } catch (error) {
      console.error('PDF optimization error:', error);
      return buildPayload(file, file.name, file.type || 'application/pdf');
    }
  };

  const rasterizePdf = async (candidateFile: Blob, fileName: string): Promise<Blob> => {
    let bestBlob = candidateFile;
    const sourceBytes = await candidateFile.arrayBuffer();

    for (const profile of PDF_RASTER_PROFILES) {
      try {
        const renderedBlob = await renderPdfProfile(sourceBytes, profile.longestSidePx, profile.jpegQuality);
        if (renderedBlob.size < bestBlob.size) {
          bestBlob = renderedBlob;
        }
        if (bestBlob.size <= TARGET_PDF_BYTES) {
          break;
        }
      } catch (error) {
        console.error(`Raster PDF compression failed for ${fileName} at profile`, profile, error);
      }
    }

    return bestBlob;
  };

  const renderPdfProfile = async (pdfBytes: ArrayBuffer, longestSidePx: number, jpegQuality: number): Promise<Blob> => {
    const loadingTask = pdfjsLib.getDocument({ data: pdfBytes });
    const pdf = await loadingTask.promise;
    const outputPdf = await PDFDocument.create();

    try {
      for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
        const page = await pdf.getPage(pageNumber);
        const baseViewport = page.getViewport({ scale: 1 });
        const dominantEdge = Math.max(baseViewport.width, baseViewport.height);
        const renderScale = Math.max(
          MIN_PAGE_EDGE_PX / dominantEdge,
          Math.min(longestSidePx / dominantEdge, 2)
        );
        const viewport = page.getViewport({ scale: renderScale });

        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(viewport.width));
        canvas.height = Math.max(1, Math.round(viewport.height));

        const context = canvas.getContext('2d', { alpha: false });
        if (!context) {
          throw new Error('2D canvas context unavailable');
        }

        context.fillStyle = '#ffffff';
        context.fillRect(0, 0, canvas.width, canvas.height);

        await page.render({ canvas, canvasContext: context, viewport }).promise;
        const pageBlob = await canvasToBlob(canvas, 'image/jpeg', jpegQuality);
        const pageBytes = await pageBlob.arrayBuffer();
        const pageImage = await outputPdf.embedJpg(pageBytes);
        const pdfPage = outputPdf.addPage([baseViewport.width, baseViewport.height]);
        pdfPage.drawImage(pageImage, {
          x: 0,
          y: 0,
          width: baseViewport.width,
          height: baseViewport.height,
        });

        canvas.width = 0;
        canvas.height = 0;
        page.cleanup();
      }
    } finally {
      await loadingTask.destroy();
    }

    const finalBytes = await outputPdf.save({
      useObjectStreams: true,
      addDefaultPage: false,
      objectsPerTick: 50,
    });
    return new Blob([finalBytes], { type: 'application/pdf' });
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    setProcessing(true);
    const newFiles: UploadFilePayload[] = [];
    const names: string[] = [];

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        let result;
        if (file.type.startsWith('image/')) {
          result = await compressImage(file);
        } else if (file.type === 'application/pdf') {
          result = await optimizePdf(file);
        } else {
          result = await buildPayload(file, file.name, file.type);
        }
        
        newFiles.push(result);
        names.push(file.name);
      }

      onFilesSelect(newFiles);
      setFileNames(names);
    } catch (error) {
      console.error('Error handling files:', error);
    } finally {
      setProcessing(false);
    }
  };

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const clearFiles = () => {
    setFileNames([]);
    onFilesSelect([]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-slate-700 dark:text-slate-200" id={`${id}-label`}>{label}</label>
      <div
        id={id}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        className={cn(
          "relative border-2 border-dashed rounded-xl p-6 transition-all duration-200 flex flex-col items-center justify-center gap-3 cursor-pointer min-h-[160px]",
          isDragging ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950/50" : "border-slate-200 hover:border-slate-300 bg-white dark:border-slate-600 dark:hover:border-slate-500 dark:bg-slate-900",
          fileNames.length > 0 ? "border-emerald-500 bg-emerald-50 dark:border-emerald-600 dark:bg-emerald-950/40" : ""
        )}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={onInputChange}
          accept={accept}
          multiple={multiple}
          className="hidden"
          id={`${id}-input`}
        />
        
        {isProcessing ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="animate-spin text-indigo-500 dark:text-indigo-400" size={32} />
            <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Processing files...</p>
          </div>
        ) : fileNames.length > 0 ? (
          <>
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 dark:bg-emerald-900/50 dark:text-emerald-400">
              <CheckCircle2 size={24} />
            </div>
            <div className="text-center w-full px-4">
              <div className="max-h-24 overflow-y-auto space-y-1 py-1">
                {fileNames.map((name, idx) => (
                  <p key={idx} className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">{name}</p>
                ))}
              </div>
              <button
                id={`${id}-remove`}
                onClick={(e) => { e.stopPropagation(); clearFiles(); }}
                className="text-xs text-slate-500 hover:text-red-500 mt-2 flex items-center gap-1 mx-auto dark:text-slate-400 dark:hover:text-red-400"
              >
                <X size={12} /> Remove all
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 dark:bg-slate-800 dark:text-slate-500">
              <Upload size={24} />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                {multiple ? "Click to upload multiple files or drag and drop" : "Click to upload or drag and drop"}
              </p>
              <p className="text-xs text-slate-500 mt-1 dark:text-slate-400">PDF</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
