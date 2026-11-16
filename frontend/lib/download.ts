/**
 * Utilities for downloading audio files and copying project paths/URLs.
 */

export function sanitizeFilename(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_|_$/g, "");
}

export function formatAudioFilename(options: {
  voiceName?: string;
  text?: string;
  id?: string;
}): string {
  const parts: string[] = ["voicerep"];

  if (options.voiceName) {
    const cleanVoice = sanitizeFilename(options.voiceName);
    if (cleanVoice) parts.push(cleanVoice);
  }

  if (options.text) {
    const cleanText = sanitizeFilename(options.text.slice(0, 30));
    if (cleanText) parts.push(cleanText);
  } else if (options.id) {
    parts.push(options.id.slice(0, 8));
  }

  return `${parts.join("_")}.mp3`;
}

import { getBackendUrl } from "@/lib/api";

/**
 * Initiates a seamless direct file download to the user's computer.
 * Uses client-side blob conversion to bypass cross-origin browser restrictions
 * that would otherwise open the audio in a new tab.
 */
export async function downloadAudioFile(
  url: string,
  filename: string
): Promise<void> {
  const resolvedUrl =
    url.startsWith("http://") || url.startsWith("https://") || url.startsWith("blob:")
      ? url
      : `${getBackendUrl()}${url.startsWith("/") ? "" : "/"}${url}`;

  try {
    const response = await fetch(resolvedUrl);
    if (!response.ok) {
      throw new Error(`Failed to fetch audio stream (${response.status})`);
    }

    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.style.display = "none";
    a.href = blobUrl;
    a.download = filename;

    document.body.appendChild(a);
    a.click();

    setTimeout(() => {
      document.body.removeChild(a);
      window.URL.revokeObjectURL(blobUrl);
    }, 200);
  } catch (err) {
    console.warn("Direct blob download failed, falling back to server attachment:", err);
    // Fallback: Append download=true & filename query params to trigger server Content-Disposition
    const separator = resolvedUrl.includes("?") ? "&" : "?";
    const fallbackUrl = `${resolvedUrl}${separator}download=true&filename=${encodeURIComponent(filename)}`;

    const a = document.createElement("a");
    a.style.display = "none";
    a.href = fallbackUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();

    setTimeout(() => {
      document.body.removeChild(a);
    }, 200);
  }
}

/**
 * Copies text (such as file paths or audio URLs) to the system clipboard.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    // Fallback for older browsers
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    document.body.appendChild(textArea);
    textArea.select();
    const successful = document.execCommand("copy");
    document.body.removeChild(textArea);
    return successful;
  } catch (err) {
    console.error("Clipboard copy error:", err);
    return false;
  }
}
