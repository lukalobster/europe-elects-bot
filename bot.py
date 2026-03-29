import os
import requests
from bs4 import BeautifulSoup
from mastodon import Mastodon
import re
import html
import time
import io

# Configuration
MASTODON_ACCESS_TOKEN = os.getenv("MASTODON_ACCESS_TOKEN")
SCRAPEDO_API_KEY = os.getenv("SCRAPEDO_API_KEY")
FACEBOOK_PAGE_URL = "https://www.facebook.com/EuropeElects"

# Initialize Mastodon API
try:
    mastodon = Mastodon(
        access_token=MASTODON_ACCESS_TOKEN,
        api_base_url="https://mastodon.social"
    )
    print("✅ Mastodon connection initialized.")
except Exception as e:
    print(f"❌ Failed to initialize Mastodon: {e}")
    exit(1)

def fetch_facebook_posts():
    print(f"🔍 Fetching Facebook page: {FACEBOOK_PAGE_URL} using Scrape.do...")
    try:
        # CORRECT Scrape.do API endpoint
        scrapedo_url = f"http://api.scrape.do?url={FACEBOOK_PAGE_URL}&token={SCRAPEDO_API_KEY}&render=true"
        
        response = requests.get(scrapedo_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        posts_data = []
        
        # Find post articles
        potential_posts = soup.find_all("div", {"role": "article"}) 
        if not potential_posts:
            potential_posts = soup.find_all("div", class_=lambda x: x and ("userContent" in x or "story_body_container" in x))

        for post_element in potential_posts:
            text_content = []
            image_urls = []
            
            # Extract text
            for p in post_element.find_all(["p", "span"], class_=lambda x: x and ("text_exposed_root" in x or "userContent" in x or "story_body_container" in x or "x1iorvi4" in x)):
                text_content.append(p.get_text(separator=" ", strip=True))
            
            # Extract images
            for img in post_element.find_all("img"):
                if "src" in img.attrs and not img["src"].startswith("data:") and "scontent" in img["src"]:
                    image_urls.append(img["src"])
            
            full_text = "\n\n".join(filter(None, text_content))
            if full_text or image_urls:
                # Create a unique ID based on content
                post_id = str(hash(full_text + "".join(image_urls)))
                posts_data.append({
                    "id": post_id,
                    "text": full_text,
                    "images": list(set(image_urls))
                })
        
        print(f"✅ Found {len(posts_data)} potential posts.")
        return posts_data

    except Exception as e:
        print(f"❌ Error fetching or parsing Facebook: {e}")
    return []

def download_image(url):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        return io.BytesIO(response.content)
    except Exception as e:
        print(f"❌ Error downloading image: {e}")
    return None

def run_bot():
    last_id_file = "last_fb_post.txt"
    last_id = "0"
    if os.path.exists(last_id_file):
        with open(last_id_file, "r") as f:
            last_id = f.read().strip()

    all_fb_posts = fetch_facebook_posts()
    if not all_fb_posts:
        return

    all_fb_posts.reverse() # Process oldest first
    
    new_posts = []
    found_last = False
    for post in all_fb_posts:
        if post["id"] == last_id:
            found_last = True
            continue
        if found_last or last_id == "0":
            new_posts.append(post)

    if not new_posts:
        print("idling... No NEW posts found.")
        if all_fb_posts:
            latest_id = all_fb_posts[-1]["id"]
            if latest_id != last_id:
                with open(last_id_file, "w") as f:
                    f.write(latest_id)
                print(f"Synced last_fb_post.txt to latest ID: {latest_id}")
        return

    print(f"🚀 Found {len(new_posts)} NEW posts!")
    for post in new_posts:
        media_ids = []
        for img_url in post["images"][:4]:
            image_data = download_image(img_url)
            if image_data:
                try:
                    media = mastodon.media_post(image_data, mime_type="image/jpeg")
                    media_ids.append(media["id"])
                except Exception as e:
                    print(f"❌ Media upload error: {e}")
            
        try:
            # Clean up text
            clean_text = html.unescape(post["text"])
            mastodon.status_post(clean_text[:500], media_ids=media_ids)
            print(f"✅ Posted ID: {post['id']}")
            with open(last_id_file, "w") as f:
                f.write(post["id"])
        except Exception as e:
            print(f"❌ Posting error: {e}")
        time.sleep(5)

if __name__ == \"__main__\":
    run_bot()
