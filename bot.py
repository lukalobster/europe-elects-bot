import os
import requests
from bs4 import BeautifulSoup
import re
import html
import time

# Configuration
SCRAPEDO_API_KEY = os.getenv("SCRAPEDO_API_KEY")
FACEBOOK_PAGE_URL = "https://www.facebook.com/EuropeElects"
POSTS_FILE = "posts.txt"
LAST_ID_FILE = "last_fb_post.txt"

def fetch_facebook_posts():
    print(f"🔍 Fetching Facebook page: {FACEBOOK_PAGE_URL} using Scrape.do...")
    try:
        # Scrape.do API endpoint
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

def run_bot():
    last_id = "0"
    if os.path.exists(LAST_ID_FILE):
        with open(LAST_ID_FILE, "r") as f:
            last_id = f.read().strip()
            
    all_fb_posts = fetch_facebook_posts()
    if not all_fb_posts:
        return
        
    # Process oldest first
    all_fb_posts.reverse()
    
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
        # Sync last_id if we found posts but none were new
        if all_fb_posts:
            latest_id = all_fb_posts[-1]["id"]
            if latest_id != last_id:
                with open(LAST_ID_FILE, "w") as f:
                    f.write(latest_id)
                print(f"Synced last_fb_post.txt to latest ID: {latest_id}")
        return
        
    print(f"🚀 Found {len(new_posts)} NEW posts!")
    
    with open(POSTS_FILE, "a", encoding="utf-8") as f:
        for post in new_posts:
            f.write(f"--- POST ID: {post['id']} ---\n")
            f.write(f"TEXT: {post['text']}\n")
            f.write(f"IMAGES: {', '.join(post['images'])}\n")
            f.write("-" * 20 + "\n\n")
            
            # Update last_id
            with open(LAST_ID_FILE, "w") as f_id:
                f_id.write(post["id"])
            print(f"✅ Saved post ID: {post['id']} to {POSTS_FILE}")

if __name__ == '__main__':
    run_bot()
