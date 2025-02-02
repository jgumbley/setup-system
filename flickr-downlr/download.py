import requests
from bs4 import BeautifulSoup
import random
import time
import os
import tempfile
import subprocess
import logging
import argparse
from PIL import Image
from io import BytesIO

def setup_logging(debug=False):
    """Configure logging based on debug flag"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

def is_landscape(image_data):
    """Check if image is landscape orientation"""
    try:
        img = Image.open(BytesIO(image_data))
        width, height = img.size
        aspect_ratio = width / height
        # Accept any landscape image with aspect ratio between 1.2 and 2.5
        is_suitable = width > height and 1.2 <= aspect_ratio <= 2.5
        logger.debug(f"Image dimensions: {width}x{height}, aspect ratio: {aspect_ratio:.2f}, suitable: {is_suitable}")
        return is_suitable
    except Exception as e:
        logger.error(f"Error checking image dimensions: {e}")
        return False

def show_image(image_data):
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp.write(image_data)
        tmp_path = tmp.name
        logger.debug(f"Saved temporary image to {tmp_path}")
    
    try:
        # Use kitty's icat to display the image
        subprocess.run(['kitty', '+kitten', 'icat', tmp_path], check=True)
        return tmp_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to display image: {e}")
        os.unlink(tmp_path)
        return None

def try_image_sizes(base_url):
    """Try different Flickr size suffixes in order of preference"""
    # Try different sizes in order of largest to smallest
    # o = original
    # 6k = 6144 on longest side
    # k = 2048 on longest side
    # h = 1600 on longest side
    # b = 1024 on longest side
    sizes = ['o', '6k', 'k', 'h', 'b']
    for size in sizes:
        url = base_url.replace('_w.', f'_{size}.')
        logger.debug(f"Trying size {size}: {url}")
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
    return None

def download_interactive(username, max_pages):
    logger.info(f"Starting interactive download for user: {username}")
    page_num = 1
    
    while True:
        try:
            # Use standard page URL format
            page_url = f"https://www.flickr.com/photos/{username}/page{page_num}"
            logger.info(f"Accessing page {page_num}/{max_pages}: {page_url}")
            
            response = requests.get(page_url)
            logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                logger.debug("Created BeautifulSoup object")
                
                # Find all img tags that might be photos
                images = []
                images.extend(soup.find_all('img', attrs={'height': '100%', 'loading': 'lazy'}))
                images.extend(soup.find_all('img', class_='photo-list-photo-view'))
                
                logger.info(f"Found {len(images)} images on page")
                
                if images:
                    # Take a random image from this page
                    img = random.choice(images)
                    logger.debug(f"Selected image tag: {img}")
                    src = img.get('src')
                    
                    if src:
                        # Add https: if the URL starts with //
                        if src.startswith('//'):
                            src = 'https:' + src
                        
                        # Try different image sizes
                        image_data = try_image_sizes(src)
                        if image_data and is_landscape(image_data):
                            # Show image and get temporary file path
                            tmp_path = show_image(image_data)
                            if tmp_path:
                                choice = input("Save this image? (y/n): ").lower()
                                
                                if choice == 'y':
                                    filename = src.split('/')[-1].replace('_w.', '_k.')
                                    with open(filename, 'wb') as f:
                                        f.write(image_data)
                                    logger.info(f"Successfully saved image as {filename}")
                                else:
                                    logger.info("Image skipped by user")
                                
                                # Clean up temporary file
                                os.unlink(tmp_path)
                                logger.debug(f"Cleaned up temporary file {tmp_path}")
                        else:
                            logger.debug("Image is not suitable (wrong aspect ratio or download failed)")
                else:
                    logger.warning("No images found on page")
                    
                # Move to next page
                page_num += 1
                if page_num > max_pages:  # Reset after max pages
                    page_num = 1
            else:
                logger.warning(f"Failed to access page: {response.status_code}")
                # If page fails, try next one
                page_num += 1
                if page_num > max_pages:
                    page_num = 1
            
            # Brief pause between requests
            time.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("\nUser interrupted the process. Stopping...")
            break
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}", exc_info=True)
            logger.info("Waiting 1 second before retrying...")
            time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download images from Flickr')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('-u', '--username', default='nasa', help='Flickr username (default: nasa)')
    parser.add_argument('-p', '--pages', type=int, default=50, help='Maximum number of pages to cycle through (default: 50)')
    args = parser.parse_args()
    
    # Setup logging based on debug flag
    logger = setup_logging(args.debug)
    
    logger.info("Starting Flickr downloader script")
    download_interactive(args.username, args.pages)