"use client";

import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";
import { useEffect, useState } from "react";

export type PairedSlide = {
  beforeSrc: string;
  afterSrc: string;
  beforeAlt: string;
  afterAlt: string;
};

type PairedCarouselProps = {
  pairs: PairedSlide[];
  interval?: number;
};

function SlidePanel({
  title,
  imageSrc,
  imageAlt,
}: {
  title: string;
  imageSrc: string;
  imageAlt: string;
}) {
  return (
    <div>
      <h3 className="mb-3 text-center text-xl font-semibold text-white sm:text-4xl">{title}</h3>
      <div className="group relative w-full overflow-hidden rounded-3xl border border-white/20 bg-black/35 shadow-[0_28px_90px_rgba(0,0,0,0.48)] transition duration-500 hover:border-blue-300/45 hover:shadow-[0_30px_110px_rgba(30,102,255,0.28)]">
        <div className="relative h-[240px] w-full sm:h-[360px] lg:h-[430px]">
          <AnimatePresence mode="wait">
            <motion.div
              key={imageSrc}
              initial={{ opacity: 0, x: 18, scale: 1.03 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: -18, scale: 0.99 }}
              transition={{ duration: 0.58, ease: "easeInOut" }}
              className="absolute inset-0"
            >
              <Image
                src={imageSrc}
                alt={imageAlt}
                fill
                sizes="(max-width: 768px) 100vw, 50vw"
                className="object-cover transition duration-700 group-hover:scale-110"
              />
            </motion.div>
          </AnimatePresence>
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/55 to-transparent" />
      </div>
    </div>
  );
}

export default function PairedCarousel({ pairs, interval = 3500 }: PairedCarouselProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % pairs.length);
    }, interval);

    return () => window.clearInterval(timer);
  }, [interval, pairs.length]);

  const activePair = pairs[activeIndex];

  return (
    <section className="w-full">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 lg:gap-10">
        <SlidePanel title="原始房间" imageSrc={activePair.beforeSrc} imageAlt={activePair.beforeAlt} />
        <SlidePanel title="生成后的房间" imageSrc={activePair.afterSrc} imageAlt={activePair.afterAlt} />
      </div>

      <div className="mt-6 flex justify-center gap-2">
        {pairs.map((pair, index) => (
          <button
            key={`${pair.beforeSrc}-${pair.afterSrc}-${index}`}
            type="button"
            aria-label={`切换到第 ${index + 1} 组对比图`}
            onClick={() => setActiveIndex(index)}
            className={`h-2.5 rounded-full transition-all duration-300 ${
              index === activeIndex ? "w-7 bg-blue-400" : "w-2.5 bg-white/45"
            }`}
          />
        ))}
      </div>
    </section>
  );
}
