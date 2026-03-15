"use client";

import { motion } from "framer-motion";

interface SkeletonProps {
  className?: string;
  variant?: "text" | "circular" | "rectangular" | "rounded";
  width?: string | number;
  height?: string | number;
  animation?: boolean;
}

export default function Skeleton({
  className = "",
  variant = "text",
  width,
  height,
  animation = true,
}: SkeletonProps) {
  const getVariantStyles = () => {
    switch (variant) {
      case "circular":
        return "rounded-full";
      case "rectangular":
        return "rounded-none";
      case "rounded":
        return "rounded-xl";
      default:
        return "rounded-lg";
    }
  };

  const baseStyles = `
    bg-gradient-to-r from-[#E9E2D8] via-[#F5F1EB] to-[#E9E2D8]
    ${getVariantStyles()}
    ${animation ? "animate-shimmer" : ""}
    ${className}
  `;

  const style = {
    width: width,
    height: height || (variant === "text" ? "1rem" : undefined),
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={baseStyles}
      style={style}
    />
  );
}

// 预设骨架屏组件
export function SkeletonCard() {
  return (
    <div className="p-6 bg-white rounded-2xl border border-[#8B6F47]/15">
      <Skeleton variant="rounded" height={120} className="mb-4" />
      <Skeleton variant="text" width="60%" className="mb-2" />
      <Skeleton variant="text" width="80%" />
    </div>
  );
}

export function SkeletonMessage() {
  return (
    <div className="flex gap-3 p-4 bg-white/70 rounded-2xl border border-[#8B6F47]/20">
      <Skeleton variant="circular" width={40} height={40} />
      <div className="flex-1">
        <Skeleton variant="text" width="30%" className="mb-2" />
        <Skeleton variant="text" width="100%" className="mb-1" />
        <Skeleton variant="text" width="80%" />
      </div>
    </div>
  );
}