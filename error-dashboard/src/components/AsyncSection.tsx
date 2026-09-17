import React from "react";

interface AsyncSectionProps {
  loading: boolean;
  error: string | null;
  isEmpty: boolean;
  emptyMessage: string;
  children: React.ReactNode;
}

export default function AsyncSection({
  loading,
  error,
  isEmpty,
  emptyMessage,
  children,
}: AsyncSectionProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-gray-400">
        Loading...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-red-500">
        ⚠ {error}
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-gray-400">
        {emptyMessage}
      </div>
    );
  }

  return <>{children}</>;
}