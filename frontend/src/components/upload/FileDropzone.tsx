import { useRef, useState, DragEvent, ChangeEvent } from 'react'
import { UploadCloud, CheckCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface FileDropzoneProps {
  onFile: (file: File) => void
  accept?: string
  disabled?: boolean
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export function FileDropzone({
  onFile,
  accept = 'image/*,application/pdf',
  disabled = false,
}: FileDropzoneProps) {
  const [dragging, setDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleFile(file: File) {
    setSelectedFile(file)
    onFile(file)
  }

  function onDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    if (!disabled) setDragging(true)
  }

  function onDragLeave(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(false)
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(false)
    if (disabled) return
    const file = e.dataTransfer.files?.[0]
    if (file) handleFile(file)
  }

  function onInputChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <div
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className={cn(
        'flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-10 text-center cursor-pointer transition-colors',
        dragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-gray-50 hover:border-gray-400',
        disabled && 'opacity-50 cursor-not-allowed',
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={onInputChange}
        disabled={disabled}
      />
      {selectedFile ? (
        <>
          <CheckCircle className="h-10 w-10 text-green-500" />
          <p className="text-sm font-medium text-gray-700">{selectedFile.name}</p>
          <p className="text-xs text-gray-500">{formatSize(selectedFile.size)}</p>
        </>
      ) : (
        <>
          <UploadCloud className="h-10 w-10 text-gray-400" />
          <p className="text-sm text-gray-600">
            Drag &amp; drop your invoice here, or{' '}
            <span className="text-blue-600 underline">click to browse</span>
          </p>
          <p className="text-xs text-gray-400">PDF or image files accepted</p>
        </>
      )}
    </div>
  )
}
