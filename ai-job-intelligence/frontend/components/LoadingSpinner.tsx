"use client";

export default function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-6">
      <div className="animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 h-5 w-5"></div>
      <span className="text-sm text-gray-500 ml-2">Loading...</span>
    </div>
  );
}
