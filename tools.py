import os
import json
import uuid
import logging
import base64
import math
import mimetypes
import requests
from typing import Optional, Dict, Any, List

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from db import save_asset, latest_asset, session_state_snapshot
from llm_provider import generate_image, get_chat_llm, get_vision_llm
from baidu_search import baidu_web_search_sync

logger = logging.getLogger(__name__)

ARTIFACT_ROOT = os.path.join(os.getcwd(), ".adk", "artifacts")
os.makedirs(ARTIFACT_ROOT, exist_ok=True)


def _build_structure_locked_prompt(prompt: str) -> str:
    lock_rules = (
        "结构约束（必须遵守）："
        "严格保留原始户型结构与拍摄机位，墙体/门窗/梁柱/地面边界与主要家具相对位置保持不变；"
        "只允许优化软装、配色、材质、灯光与装饰细节；"
        "不得重构户型，不得改变镜头朝向，不得凭空新增或删除主要硬装体块；"
        "不得将空间改造成与原图明显不同的房型或家具布局。"
    )
    fidelity_rules = (
        "高保真要求："
        "优先保持地面铺装走向、窗户比例、电视墙位置、主要通道宽度与透视关系；"
        "优先做轻改造方案，不做大拆大改。"
    )
    return f"{lock_rules}\n{fidelity_rules}\n\n设计目标：{prompt}"


def _read_image_size(path: str) -> Optional[tuple[int, int]]:
    try:
        from PIL import Image  # type: ignore

        with Image.open(path) as img:
            return int(img.width), int(img.height)
    except Exception:
        return None


def _round_to_multiple(value: float, multiple: int = 64) -> int:
    return max(multiple, int(round(value / multiple) * multiple))


def _derive_size_from_ratio(width: int, height: int) -> str:
    ratio = max(0.125, min(8.0, width / max(height, 1)))
    target_area = 1536 * 1536
    out_w = math.sqrt(target_area * ratio)
    out_h = math.sqrt(target_area / ratio)

    out_w = max(768, min(2048, _round_to_multiple(out_w)))
    out_h = max(768, min(2048, _round_to_multiple(out_h)))

    ratio_now = out_w / max(out_h, 1)
    if ratio_now > 8.0:
        out_h = max(768, _round_to_multiple(out_w / 8.0))
    elif ratio_now < 0.125:
        out_w = max(768, _round_to_multiple(out_h * 0.125))

    return f"{out_w}*{out_h}"


def _derive_size_from_aspect(aspect_ratio: str) -> str:
    try:
        left, right = (aspect_ratio or "16:9").split(":", 1)
        w = float(left)
        h = float(right)
        if w <= 0 or h <= 0:
            raise ValueError("Invalid ratio")
        return _derive_size_from_ratio(int(w * 100), int(h * 100))
    except Exception:
        return "1536*1024"


def _load_latest_current_room_reference(session_id: str, user_id: str) -> tuple[Optional[str], Optional[str]]:
    latest_room = latest_asset(session_id, user_id, "current_room")
    if not latest_room:
        return None, None

    filename = (latest_room.get("filename") or "").strip()
    if not filename:
        return None, None

    path = os.path.join(ARTIFACT_ROOT, filename)
    if not os.path.exists(path):
        return None, None

    with open(path, "rb") as f:
        image_bytes = f.read()
    if not image_bytes:
        return None, None

    mime_type = mimetypes.guess_type(path)[0] or "image/png"
    data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"

    size = None
    size_hint = _read_image_size(path)
    if size_hint:
        size = _derive_size_from_ratio(size_hint[0], size_hint[1])
    return data_url, size


# ============================================================================
# Search Tool
# ============================================================================

@tool
def baidu_search_tool(query: str) -> str:
    """搜索引擎工具：搜索装修成本、材料、寻找同款家具或了解流行趋势。当你需要查找真实世界的最新信息时，请调用此工具。"""
    api_key = os.getenv("BAIDU_SEARCH_API_KEY", "")
    if not api_key:
        logger.warning("BAIDU_SEARCH_API_KEY 未配置，搜索功能不可用。")
        return f"搜索失败：BAIDU_SEARCH_API_KEY 未配置，无法联网搜索关于 '{query}' 的信息。"

    try:
        results = baidu_web_search_sync(query, max_results=5)
        if not results:
            return f"百度搜索 '{query}' 未找到相关结果。"

        # 格式化为 LLM 易读的文本
        lines = [f"百度搜索结果（关键词：{query}）：\n"]
        for i, item in enumerate(results, 1):
            lines.append(f"{i}. **{item['title']}**")
            lines.append(f"   链接：{item['url']}")
            if item.get("snippet"):
                lines.append(f"   摘要：{item['snippet']}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        logger.error("百度搜索调用失败: %s", e)
        return f"搜索出错：{e}"


# ============================================================================
# Utility Tools
# ============================================================================

class CostEstimateInput(BaseModel):
    room_type: str = Field(description="Type of room (kitchen, bathroom, bedroom, living_room, etc.)")
    scope: str = Field(description="Renovation scope (cosmetic, moderate, full, luxury)")
    square_footage: int = Field(description="Room size in square feet")

@tool(args_schema=CostEstimateInput)
def estimate_renovation_cost_tool(room_type: str, scope: str, square_footage: int) -> str:
    """估算不同房间在不同装修规模下的预算范围。返回人民币预算区间。"""
    rates = {
        "kitchen": {"cosmetic": (50, 100), "moderate": (150, 250), "full": (300, 500), "luxury": (600, 1200)},
        "bathroom": {"cosmetic": (75, 125), "moderate": (200, 350), "full": (400, 600), "luxury": (800, 1500)},
        "bedroom": {"cosmetic": (30, 60), "moderate": (75, 150), "full": (150, 300), "luxury": (400, 800)},
        "living_room": {"cosmetic": (40, 80), "moderate": (100, 200), "full": (200, 400), "luxury": (500, 1000)},
    }
    
    room = room_type.lower().replace(" ", "_")
    scope_level = scope.lower()
    
    if room not in rates:
        room = "living_room"
    if scope_level not in rates[room]:
        scope_level = "moderate"
    
    low, high = rates[room][scope_level]
    
    total_low_usd = low * square_footage
    total_high_usd = high * square_footage

    usd_to_cny = 7.2
    total_low_cny = int(total_low_usd * usd_to_cny)
    total_high_cny = int(total_high_usd * usd_to_cny)
    square_meters = max(1, round(square_footage * 0.0929, 1))

    scope_labels = {"cosmetic": "软装优化/轻改造", "moderate": "中度翻新", "full": "整体翻新", "luxury": "高配精装"}
    room_labels = {"kitchen": "厨房", "bathroom": "卫生间", "bedroom": "卧室", "living_room": "客厅"}

    return (
        f"预算参考：约人民币 {total_low_cny:,} - {total_high_cny:,} 元"
        f"（{room_labels.get(room, room_type)}，{scope_labels.get(scope_level, scope_level)}，"
        f"约 {square_meters} 平方米 / {square_footage} 平方英尺）。"
    )


class TimelineInput(BaseModel):
    scope: str = Field(description="Renovation scope (cosmetic, moderate, full, luxury)")
    room_type: str = Field(description="Type of room being renovated")

@tool(args_schema=TimelineInput)
def calculate_timeline_tool(scope: str, room_type: str) -> str:
    """输入装修规模，返回施工周期估算。"""
    timelines = {
        "cosmetic": "1-2 周（软装优化或轻改造）",
        "moderate": "3-6 周（含部分定制与施工）",
        "full": "2-4 个月（整体翻新）",
        "luxury": "4-6 个月（高配定制与精细施工）"
    }
    scope_level = scope.lower()
    return f"施工周期参考：{timelines.get(scope_level, timelines['moderate'])}"


# ============================================================================
# Core Generation Tools
# ============================================================================

class GenerateInput(BaseModel):
    prompt: str = Field(description="A detailed description of the renovated space. Needs SLC formula for prompt.")
    aspect_ratio: str = Field(default="16:9")
    asset_name: str = Field(default="renovation_rendering")

@tool(args_schema=GenerateInput)
async def generate_renovation_rendering_tool(prompt: str, aspect_ratio: str, asset_name: str, config: RunnableConfig) -> str:
    """基于详尽的文字（SLC: Subject, Lighting, Camera）生成该房间的超写实效果图。"""
    session_id = config.get("configurable", {}).get("session_id", "")
    user_id = config.get("configurable", {}).get("user_id", "")
    
    locked_prompt = _build_structure_locked_prompt(prompt)
    reference_image, reference_size = _load_latest_current_room_reference(session_id, user_id)
    # 有原图时优先用 2K 档位，模型会按输入图比例生成，通常比固定像素更稳。
    resolved_size = "2K" if reference_image else (reference_size or _derive_size_from_aspect(aspect_ratio))
    logger.info("Generating image with locked prompt (size=%s, has_reference=%s)", resolved_size, bool(reference_image))
    
    # 获取生成 URL
    image_url_or_b64 = await generate_image(
        locked_prompt,
        reference_image=reference_image,
        size=resolved_size,
    )
    if not image_url_or_b64:
        return "效果图生成失败：服务没有返回有效图片地址。"
        
    version = 1
    recent_image = latest_asset(session_id, user_id, "generated_render")
    if recent_image and isinstance(recent_image, dict) and recent_image.get("metadata", {}).get("asset_name") == asset_name:
        version = recent_image.get("version", 0) + 1
        
    artifact_filename = f"{asset_name}_v{version}.png"
    filepath = os.path.join(ARTIFACT_ROOT, artifact_filename)
    
    # 落地文件
    try:
        if image_url_or_b64.startswith("base64,"):
            import base64
            b64_data = image_url_or_b64.split(",", 1)[1]
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(b64_data))
        else:
            response = requests.get(image_url_or_b64, timeout=15)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
                
        # 存库
        save_asset(
            session_id=session_id,
            user_id=user_id,
            filename=artifact_filename,
            asset_type="generated_render",
            version=version,
            metadata={"asset_name": asset_name}
        )
        return f"✅ Renovation rendering generated successfully! Artifact saved as {asset_name} version {version} ({artifact_filename})."
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return f"效果图生成保存失败: {e}"


class EditInput(BaseModel):
    prompt: str = Field(description="Specific prompt containing what changes to make (e.g. 'Make the cabinets darker') combined with the original context.")
    artifact_filename: str = Field(default="", description="The specific filename to conceptually edit")

@tool(args_schema=EditInput)
async def edit_renovation_rendering_tool(prompt: str, artifact_filename: str, config: RunnableConfig) -> str:
    """由于主流通用 API（除特殊生图平台外）较难提供单纯的 '原图修改' 接口，此处通过将修改意图汇总给大模型，生成一个新 Prompt 再重新生成。"""
    
    # 借用 generate 生成新的
    # 真实企业中通常由专门风格化 LoRA 或 IN-PAINT 接口
    return await generate_renovation_rendering_tool.invoke({
        "prompt": f"(Re-rendered to update: {prompt})",
        "aspect_ratio": "16:9",
        "asset_name": artifact_filename.replace('.png', '') or "edited_render"
    }, config=config)


@tool
def list_renovation_renderings_tool(config: RunnableConfig) -> str:
    """List all available generated rendering artifacts in the current session."""
    session_id = config.get("configurable", {}).get("session_id", "")
    user_id = config.get("configurable", {}).get("user_id", "")
    
    state = session_state_snapshot(session_id, user_id)
    last_render = state.get("last_generated_rendering")
    
    if not last_render:
        return "No renderings have been created yet."
    return f"Latest stored rendering is: {last_render}"

# end
