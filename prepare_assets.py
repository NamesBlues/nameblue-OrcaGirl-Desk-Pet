"""把项目根目录里的素材整理成桌宠直接可用的 PNG，输出到 assets/。

做两件事：
  1. 裁掉四周多余留白（原图 1840x1840，角色实际只占约 36%）。
  2. 缩放到合理分辨率（桌宠最大也就显示到 300px 左右，1024 足够清晰）。

关于透明背景：
  素材本身已经是带 alpha 的 PNG，直接沿用。
  如果以后放进来的图是白底不透明的，会自动走「抠白底」流程：从四边向内洪水填充，
  只把与外界连通的白色判为背景，所以水手帽、袜子这类被描边包围的白色不会被误伤。

用法：
    python tools/prepare_assets.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets"

# 输出分辨率上限
MAX_SIZE = 1024
# 抠白底时，三个通道都 >= 这个值才算「白」
WHITE_MIN = 240

JOBS = [
    ("orca girl.png", OUT_DIR / "orca_girl.png"),
    ("orca.png", OUT_DIR / "orca.png"),
    ("气泡1.png", OUT_DIR / "bubbles" / "bubble_1.png"),
    ("气泡2.png", OUT_DIR / "bubbles" / "bubble_2.png"),
    ("气泡3.png", OUT_DIR / "bubbles" / "bubble_3.png"),
    ("气泡4.png", OUT_DIR / "bubbles" / "bubble_4.png"),
]


def has_usable_alpha(img: Image.Image) -> bool:
    """判断这张图是不是已经有真正的透明背景（而不是全不透明的摆设 alpha）。"""
    if img.mode not in ("RGBA", "LA", "P"):
        return False
    alpha = np.asarray(img.convert("RGBA"))[..., 3]
    return bool((alpha == 0).mean() > 0.01)


def background_mask(rgb: np.ndarray) -> np.ndarray:
    """从四边向内洪水填充，返回 True 表示该像素是与外界连通的白色背景。"""
    h, w, _ = rgb.shape
    white = (rgb >= WHITE_MIN).all(axis=2)

    reached = np.zeros((h, w), dtype=bool)
    reached[0, :] = white[0, :]
    reached[-1, :] = white[-1, :]
    reached[:, 0] |= white[:, 0]
    reached[:, -1] |= white[:, -1]

    rounds = 0
    while True:
        rounds += 1
        grow = reached.copy()
        grow[1:, :] |= reached[:-1, :]
        grow[:-1, :] |= reached[1:, :]
        grow[:, 1:] |= reached[:, :-1]
        grow[:, :-1] |= reached[:, 1:]
        grow &= white
        if grow.sum() == reached.sum():
            break
        reached = grow

    print(f"    抠白底：蔓延 {rounds} 轮，判为背景 {reached.mean() * 100:.1f}%")
    return reached


def remove_white_background(img: Image.Image) -> Image.Image:
    """白底图 -> 透明图。顺带按 alpha 反解颜色，避免缩放后边缘发白雾。"""
    rgb = np.asarray(img.convert("RGB")).astype(np.float32)
    bg = background_mask(rgb.astype(np.uint8))
    alpha = np.where(bg, 0, 255).astype(np.uint8)

    a = alpha.astype(np.float32) / 255.0
    a3 = np.clip(a, 1e-4, 1.0)[..., None]
    # 原始像素 = 角色色 * a + 白色 * (1 - a)，反解出角色色
    straight = np.clip((rgb - (1.0 - a3) * 255.0) / a3, 0.0, 255.0)
    straight = np.where((a > 0.0)[..., None], straight, 0.0)

    return Image.fromarray(np.dstack([straight.astype(np.uint8), alpha]))


def crop_and_resize(img: Image.Image) -> Image.Image:
    alpha = np.asarray(img)[..., 3]
    ys, xs = np.nonzero(alpha > 0)
    if len(xs) == 0:
        return img
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    img = img.crop(box)
    if max(img.size) > MAX_SIZE:
        ratio = MAX_SIZE / max(img.size)
        img = img.resize(
            (max(1, round(img.width * ratio)), max(1, round(img.height * ratio))),
            Image.LANCZOS,
        )
    return img


def process(src: Path, dst: Path) -> Path:
    print(f"  {src.name} -> {dst.relative_to(ROOT)}")
    img = Image.open(src)
    print(f"    原图 {img.width}x{img.height} ({img.mode})")

    if has_usable_alpha(img):
        img = img.convert("RGBA")
        print("    已有透明通道，直接沿用")
    else:
        print("    白底不透明，执行抠图")
        img = remove_white_background(img)

    img = crop_and_resize(img)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, optimize=True)
    print(f"    输出 {img.width}x{img.height}")
    return dst


def write_preview(paths: list[Path]) -> None:
    """把结果贴在洋红底上生成预览图，方便肉眼确认边缘是否干净。"""
    cell, pad, cols = 380, 16, 3
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (cell + pad) + pad, rows * (cell + pad) + pad), (255, 0, 255))
    for i, p in enumerate(paths):
        img = Image.open(p).convert("RGBA")
        img.thumbnail((cell, cell), Image.LANCZOS)
        cx = pad + (i % cols) * (cell + pad) + (cell - img.width) // 2
        cy = pad + (i // cols) * (cell + pad) + (cell - img.height) // 2
        sheet.paste(img, (cx, cy), img)
    out = ROOT / "tools" / "preview.png"
    sheet.save(out)
    print(f"\n预览图（洋红底）：{out}")


def main() -> int:
    started = time.time()
    print(f"素材目录：{ROOT}\n")
    done: list[Path] = []
    for name, dst in JOBS:
        src = ROOT / name
        if not src.exists():
            print(f"  !! 找不到 {name}，跳过")
            continue
        done.append(process(src, dst))
    if done:
        write_preview(done)
    print(f"\n完成，用时 {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
