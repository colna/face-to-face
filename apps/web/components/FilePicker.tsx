"use client";

interface Props {
  label: string;
  accept: string;
  onSelect: (file: File | null) => void;
}

export function FilePicker({ label, accept, onSelect }: Props) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-gray-600">{label}</span>
      <input
        type="file"
        accept={accept}
        onChange={(e) => onSelect(e.target.files?.[0] ?? null)}
        className="rounded border border-gray-300 p-2"
      />
    </label>
  );
}
