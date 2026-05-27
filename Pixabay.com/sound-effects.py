import os
import sys
import re
import random
import time
import urllib.parse
import traceback
from curl_cffi import requests

def build_audio_automation():
    # 1. Ask for user input
    query = input("Enter your Pixabay sound effects search query (e.g., whoosh): ").strip()
    if not query:
        print("[-] Error: Query cannot be empty.")
        return

    # Format the query properly for the URL
    encoded_query = urllib.parse.quote(query)
    
    # Construct the exact URL with the duration filter applied
    search_url = f"https://pixabay.com/sound-effects/search/{encoded_query}/?duration=0-30"

    # Define the Android mobile download path
    save_dir = "/storage/emulated/0/Download"
    
    if not os.path.exists(save_dir):
        print(f"[-] The directory {save_dir} does not exist. Ensure storage permissions are granted.")
        return

    # Initialize curl_cffi Session to bypass Cloudflare
    print(f"[*] Initializing curl_cffi Session (impersonating Chrome)...")
    session = requests.Session(impersonate="chrome")
    
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        # 2. Fetch the main sound effects search page
        print(f"\n[*] Sending HTTP GET request to {search_url} ...")
        response = session.get(search_url, headers=headers, timeout=30)
        html_content = response.text

        if "Just a moment..." in html_content or "cf-challenge-running" in html_content:
            print("\n[!] ALERT: Cloudflare Turnstile BLOCKED the search page request. Exiting.")
            return
            
        print(f"[+] SUCCESS! Cloudflare bypassed cleanly on search page (Status {response.status_code}).")

        # 3. Extract audio links while maintaining exact top-to-bottom ranking order
        link_pattern = r'href="(/sound-effects/[a-zA-Z0-9-]+-\d+/)"'
        raw_links = re.findall(link_pattern, html_content)
        
        # Remove duplicates but keep the exact ranking order from the source HTML
        ordered_links = []
        for link in raw_links:
            if link not in ordered_links:
                ordered_links.append(link)
        
        if not ordered_links:
            print("[-] No sound effect links found on the first page. Try a different query.")
            return
            
        # 4. Slice strictly the TOP 10 links
        top_10_links = ordered_links[:10]
        print(f"[+] Found {len(ordered_links)} unique audio links.")
        print(f"[*] Proceeding to download the Top {len(top_10_links)} ranked results.\n")
        print("="*50)

        # 5. Visit each link and download the mp3
        for i, relative_link in enumerate(top_10_links, 1):
            audio_page_url = f"https://pixabay.com{relative_link}"
            print(f"\n[*] [{i}/{len(top_10_links)}] Visiting: {audio_page_url}")
            
            page_res = session.get(audio_page_url, headers=headers, timeout=30)
            
            if "cf-challenge-running" in page_res.text:
                print(f"[-] Blocked by Cloudflare on {audio_page_url}. Skipping.")
                continue
            
            # Find the actual .mp3 link in the page source
            mp3_pattern = r'https://cdn\.pixabay\.com/(?:download/)?audio/[a-zA-Z0-9/_-]+\.mp3'
            mp3_links = re.findall(mp3_pattern, page_res.text)
            
            # Fallback regex in case the audio CDN structure changes slightly
            if not mp3_links:
                fallback_pattern = r'https://[a-zA-Z0-9./_-]+\.mp3'
                mp3_links = re.findall(fallback_pattern, page_res.text)

            if not mp3_links:
                print("[-] No direct .mp3 links found on this page. Skipping.")
                continue
            
            # Take the first mp3 embedded found on the page
            chosen_mp3 = mp3_links[0]
            print(f"[+] Found MP3: {chosen_mp3}")
            
            # Extract unique ID for filename
            # Example: /sound-effects/dramatic-whoosh-12345/ -> 12345
            audio_id = relative_link.strip('/').split('-')[-1]
            filename = f"{query.replace(' ', '_')}_{audio_id}.mp3"
            save_path = os.path.join(save_dir, filename)
            
            print(f"[*] Downloading file to {save_path} ...")
            
            aud_res = session.get(chosen_mp3, headers=headers, timeout=60)
            
            with open(save_path, "wb") as f:
                f.write(aud_res.content)
                
            print(f"[+] Audio Download Complete: {filename}")
            
            # Small random delay to act human and keep Cloudflare happy
            time.sleep(random.uniform(1.5, 3.5))

        print("\n" + "="*50)
        print(f"[+] Automation finished! Top 10 audio files have been saved to {save_dir}.")

    except Exception as e:
        print("\n" + "="*50)
        print("CRITICAL FAILURE DETECTED")
        print("="*50)
        print(f"[*] Error Type: {type(e).__name__}")
        print(f"[*] Error Details: {e}")
        traceback.print_exc(file=sys.stdout)
        print("="*50)

if __name__ == "__main__":
    build_audio_automation()
