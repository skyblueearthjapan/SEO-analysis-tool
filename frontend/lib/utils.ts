import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind classes with clsx
 * Handles conflicts and conditional classes
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format date to locale string
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Get score badge class
 */
export function getScoreBadgeClass(grade: string): string {
  switch (grade) {
    case "A":
      return "score-badge-a";
    case "B":
      return "score-badge-b";
    case "C":
      return "score-badge-c";
    case "D":
      return "score-badge-d";
    default:
      return "score-badge-d";
  }
}

/**
 * Get priority class
 */
export function getPriorityClass(priority: string): string {
  switch (priority) {
    case "P0":
      return "priority-p0";
    case "P1":
      return "priority-p1";
    case "P2":
      return "priority-p2";
    default:
      return "priority-p2";
  }
}

/**
 * Get cause badge class
 */
export function getCauseBadgeClass(cause: string): string {
  switch (cause) {
    case "content_quality":
      return "cause-content";
    case "technical":
      return "cause-technical";
    case "ctr":
      return "cause-ctr";
    case "mixed":
    default:
      return "cause-mixed";
  }
}

/**
 * Translate cause to Japanese
 */
export function translateCause(cause: string): string {
  switch (cause) {
    case "content_quality":
      return "コンテンツ品質";
    case "technical":
      return "テクニカル";
    case "ctr":
      return "CTR";
    case "mixed":
      return "複合要因";
    default:
      return "不明";
  }
}
