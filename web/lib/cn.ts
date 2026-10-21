import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Join class names, letting the LAST Tailwind utility win (so a caller can override a component's default). */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
