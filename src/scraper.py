import os
import json
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto

# --- Configuration & Setup ---

# Load environment variables
load_dotenv()
API_ID = os.getenv('TG_API_ID')
API_HASH = os.getenv('TG_API_HASH')

# Ensure API keys are present
if not API_ID or not API_HASH:
    raise ValueError("Please set TG_API_ID and TG_API_HASH in your .env file.")

# Channels to scrape
CHANNELS = [
    'https://t.me/CheMed123',          
    'https://t.me/lobelia4cosmeticss',   
    'https://t.me/tikvahpharma',     
    
]

# Set up Logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename=f"logs/scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(console_handler)


# --- Helper Functions ---

def ensure_directories():
    """Ensure base data lake directories exist."""
    os.makedirs('data/raw/telegram_messages', exist_ok=True)
    os.makedirs('data/raw/images', exist_ok=True)

def save_json(data, date_str, channel_name):
    """Saves scraped data to partitioned JSON files."""
    dir_path = f'data/raw/telegram_messages/{date_str}'
    os.makedirs(dir_path, exist_ok=True)
    
    file_path = os.path.join(dir_path, f'{channel_name}.json')
    
    # If file exists, append to it; otherwise create new
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        existing_data.extend(data)
        data_to_save = existing_data
    else:
        data_to_save = data
        
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)


# --- Main Scraping Logic ---

async def scrape_channel(client, channel_name):
    """Scrapes a single channel for messages and media."""
    logging.info(f"Starting to scrape channel: {channel_name}")
    
    # Dictionary to hold messages grouped by date
    # Format: {'YYYY-MM-DD': [message1, message2, ...]}
    messages_by_date = {}
    
    try:
        # Iterate through messages in the channel (limit can be added to client.iter_messages)
        # e.g., client.iter_messages(channel_name, limit=100) for testing
        async for message in client.iter_messages(channel_name):
            if not message.date:
                continue
                
            date_str = message.date.strftime('%Y-%m-%d')
            
            # Extract required fields
            msg_data = {
                'message_id': message.id,
                'channel_name': channel_name,
                'message_date': message.date.isoformat(),
                'message_text': message.message or "",
                'views': message.views or 0,
                'forwards': message.forwards or 0,
                'has_media': False,
                'image_path': None
            }

            # Handle Media (Images)
            if message.media:
                msg_data['has_media'] = True
                
                # Check if the media is a photo
                if isinstance(message.media, MessageMediaPhoto):
                    image_dir = f"data/raw/images/{channel_name}"
                    os.makedirs(image_dir, exist_ok=True)
                    image_path = os.path.join(image_dir, f"{message.id}.jpg")
                    
                    # Download image if it doesn't already exist
                    if not os.path.exists(image_path):
                        await client.download_media(message, file=image_path)
                    
                    msg_data['image_path'] = image_path

            # Group messages by date for partitioning
            if date_str not in messages_by_date:
                messages_by_date[date_str] = []
            messages_by_date[date_str].append(msg_data)
            
        # Save partitioned data to Data Lake
        for date_str, msgs in messages_by_date.items():
            save_json(msgs, date_str, channel_name)
            
        logging.info(f"Successfully scraped {sum(len(v) for v in messages_by_date.values())} messages from {channel_name}")
        
    except Exception as e:
        logging.error(f"Error scraping channel {channel_name}: {e}")

async def main():
    """Main execution function."""
    ensure_directories()
    
    # Create the Telethon client
    # 'session_name' creates a local .session file to save your login state
    client = TelegramClient('medical_scraping_session', API_ID, API_HASH)
    
    await client.start()
    logging.info("Telegram Client Started.")
    
    for channel in CHANNELS:
        await scrape_channel(client, channel)
        
    logging.info("Scraping completed for all channels.")

if __name__ == '__main__':
    # Run the async main function
    asyncio.run(main())