import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds: number | undefined | null): string {
  if (seconds == null || isNaN(seconds)) {
    return '-:--';
  }
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function getFallbackCoverUrl(title: string | undefined | null, size: number = 64): string {
  const text = (title || 'M').substring(0, 2).toUpperCase();
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><rect width="${size}" height="${size}" fill="#6366F1"/><text x="${size / 2}" y="${size / 2 + size * 0.15}" font-family="Arial" font-size="${size * 0.3}" fill="white" text-anchor="middle" font-weight="bold">${text}</text></svg>`;
  return `data:image/svg+xml;base64,${btoa(svg)}`;
}
