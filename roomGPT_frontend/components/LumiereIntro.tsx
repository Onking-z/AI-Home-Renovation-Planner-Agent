"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

type LumiereIntroProps = {
  onComplete: () => void;
};

export default function LumiereIntro({ onComplete }: LumiereIntroProps) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    // 总动画时长约3秒
    const timer = setTimeout(() => {
      setIsVisible(false);
    }, 3000);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!isVisible) {
      const timer = setTimeout(onComplete, 800);
      return () => clearTimeout(timer);
    }
  }, [isVisible, onComplete]);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          key="lumiere-overlay"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8, ease: "easeInOut" }}
          className="fixed inset-0 z-[60] flex items-center justify-center bg-[#FAF8F5] text-[#2D2D2D]"
        >
          {/* 温暖背景光晕效果 */}
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(139,111,71,0.12)_0%,rgba(250,248,245,0)_60%)]" />

          <div className="relative z-10">
            <svg
              viewBox="0 0 600 160"
              className="w-[80vw] max-w-[600px] h-auto overflow-visible"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <linearGradient id="text-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#8B6F47" stopOpacity="0.9" />
                  <stop offset="50%" stopColor="#A68B5B" stopOpacity="1" />
                  <stop offset="100%" stopColor="#8B6F47" stopOpacity="0.9" />
                </linearGradient>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              <motion.text
                x="50%"
                y="50%"
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize="130"
                stroke="url(#text-gradient)"
                strokeWidth="1.5"
                fill="transparent"
                style={{ filter: "url(#glow)" }}
                initial={{
                  strokeDasharray: 1000,
                  strokeDashoffset: 1000,
                }}
                animate={{
                  strokeDashoffset: 0,
                }}
                transition={{
                  duration: 2,
                  ease: "easeInOut"
                }}
              >
                Lumière
              </motion.text>
            </svg>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 2, duration: 0.8 }}
              className="mt-2 text-center text-[#8A8A8A] font-sans text-sm tracking-[0.3em] uppercase"
            >
              AI Interior Designer
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}