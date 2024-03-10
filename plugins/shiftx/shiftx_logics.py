# shiftx_logics.py
import os
import logging
import cairosvg
import subprocess
from PIL import Image
from pathlib import Path
from pdf2docx import Converter
from modules.configurator import get_env_var_from_db

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

SHIFTX_MP3_TO_AAC_BITRATE = get_env_var_from_db('SHIFTX_MP3_TO_AAC_BITRATE') or '192k'
SHIFTX_AAC_TO_MP3_BITRATE = get_env_var_from_db('SHIFTX_AAC_TO_MP3_BITRATE') or '192k'
SHIFTX_OGG_TO_MP3_QUALITY = get_env_var_from_db('SHIFTX_OGG_TO_MP3_QUALITY') or '4'
SHIFTX_MP3_TO_OGG_QUALITY = get_env_var_from_db('SHIFTX_MP3_TO_OGG_QUALITY') or '4'

# Create ShiftX_Temp directory if it doesn't exist
temp_dir = Path(__file__).parent / "ShiftX_Temp"
temp_dir.mkdir(exist_ok=True)

def pdf_to_word(pdf_file_path, word_file_path):
    cv = Converter(pdf_file_path)
    cv.convert(word_file_path)
    cv.close()
    logger.info(f"Converted {pdf_file_path} to {word_file_path}")

def jpeg_to_png(jpeg_file_path, png_file_path):
    image = Image.open(jpeg_file_path)
    image.save(png_file_path)
    logger.info(f"Converted {jpeg_file_path} to {png_file_path}")

def png_to_jpeg(png_file_path, jpeg_file_path):
    image = Image.open(png_file_path)
    rgb_im = image.convert('RGB')  
    rgb_im.save(jpeg_file_path, quality=95)  
    logger.info(f"Converted {png_file_path} to {jpeg_file_path}")

def svg_to_png(svg_file_path, png_file_path):
    cairosvg.svg2png(url=svg_file_path, write_to=png_file_path)
    logger.info(f"Converted {svg_file_path} to {png_file_path}")

def svg_to_jpeg(svg_file_path, jpeg_file_path):
    cairosvg.svg2png(url=svg_file_path, write_to=jpeg_file_path)
    logger.info(f"Converted {svg_file_path} to {jpeg_file_path}")

def tiff_to_png(tiff_file_path, png_file_path):
    image = Image.open(tiff_file_path)
    image.save(png_file_path, "PNG")
    logger.info(f"Converted {tiff_file_path} to {png_file_path}")

def tiff_to_jpeg(tiff_file_path, jpeg_file_path):
    image = Image.open(tiff_file_path)
    rgb_image = image.convert('RGB')
    rgb_image.save(jpeg_file_path, "JPEG", quality=90)
    logger.info(f"Converted {tiff_file_path} to {jpeg_file_path}")

def webp_to_png(webp_file_path, png_file_path):
    image = Image.open(webp_file_path)
    image.save(png_file_path, "PNG")
    logger.info(f"Converted {webp_file_path} to {png_file_path}")

def webp_to_jpeg(webp_file_path, jpeg_file_path):
    image = Image.open(webp_file_path)
    rgb_image = image.convert('RGB')
    rgb_image.save(jpeg_file_path, "JPEG", quality=90)
    logger.info(f"Converted {webp_file_path} to {jpeg_file_path}")

def png_to_tiff(png_file_path, tiff_file_path):
    image = Image.open(png_file_path)
    image.save(tiff_file_path, "TIFF")
    logger.info(f"Converted {png_file_path} to {tiff_file_path}")

def jpeg_to_tiff(jpeg_file_path, tiff_file_path):
    image = Image.open(jpeg_file_path)
    image.save(tiff_file_path, "TIFF")
    logger.info(f"Converted {jpeg_file_path} to {tiff_file_path}")

def png_to_webp(png_file_path, webp_file_path):
    image = Image.open(png_file_path)
    image.save(webp_file_path, "WEBP")
    logger.info(f"Converted {png_file_path} to {webp_file_path}")

def jpeg_to_webp(jpeg_file_path, webp_file_path):
    image = Image.open(jpeg_file_path)
    image.save(webp_file_path, "WEBP")
    logger.info(f"Converted {jpeg_file_path} to {webp_file_path}")

def pdf_to_txt(pdf_file_path, txt_file_path):
    from pdfminer.high_level import extract_text
    text = extract_text(pdf_file_path)
    with open(txt_file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    logger.info(f"Converted {pdf_file_path} to {txt_file_path}")

def txt_to_pdf(txt_file_path, pdf_file_path):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size = 12)
    with open(txt_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            pdf.cell(200, 10, txt=line, ln=True)
    pdf.output(pdf_file_path)
    logger.info(f"Converted {txt_file_path} to {pdf_file_path}")

def mp3_to_aac(mp3_file_path, aac_file_path):
    cmd = ['ffmpeg', '-i', mp3_file_path, '-c:a', 'aac', '-b:a', SHIFTX_MP3_TO_AAC_BITRATE, aac_file_path]
    subprocess.run(cmd, check=True)
    logger.info(f"Converted {mp3_file_path} to {aac_file_path}")

def aac_to_mp3(aac_file_path, mp3_file_path):
    cmd = ['ffmpeg', '-i', aac_file_path, '-c:a', 'libmp3lame', '-b:a', SHIFTX_AAC_TO_MP3_BITRATE, mp3_file_path]
    subprocess.run(cmd, check=True)
    logger.info(f"Converted {aac_file_path} to {mp3_file_path}")

def mp3_to_ogg(mp3_file_path, ogg_file_path):
    cmd = ['ffmpeg', '-i', mp3_file_path, '-c:a', 'libvorbis', '-q:a', SHIFTX_MP3_TO_OGG_QUALITY, ogg_file_path]
    subprocess.run(cmd, check=True)
    logger.info(f"Converted {mp3_file_path} to {ogg_file_path}")

def ogg_to_mp3(ogg_file_path, mp3_file_path):
    cmd = ['ffmpeg', '-i', ogg_file_path, '-c:a', 'libmp3lame', '-q:a', SHIFTX_OGG_TO_MP3_QUALITY, mp3_file_path]
    subprocess.run(cmd, check=True)
    logger.info(f"Converted {ogg_file_path} to {mp3_file_path}")

def is_correct_file_type(file_path, expected_ext):
    return file_path.lower().endswith(expected_ext)

def cleanup_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"Deleted {file_path}")
