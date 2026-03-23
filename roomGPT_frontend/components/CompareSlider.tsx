import {
  ReactCompareSlider,
  ReactCompareSliderImage,
} from "react-compare-slider";

export const CompareSlider = ({
  original,
  restored,
  className,
}: {
  original: string;
  restored: string;
  className?: string;
}) => {
  return (
    <ReactCompareSlider
      itemOne={<ReactCompareSliderImage src={original} alt="原始房间照片" />}
      itemTwo={<ReactCompareSliderImage src={restored} alt="生成后的房间照片" />}
      portrait
      className={className || "w-full h-full"}
    />
  );
};
