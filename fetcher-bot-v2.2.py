##### Followfox AI Fetcher Bot - Version 2.2 - May 31 2023

import os
import discord
from discord.ext import commands
import asyncio
import aiohttp
from PIL import Image, PngImagePlugin
import base64
import io
import json
import time
from filelock import FileLock, Timeout

TOKEN = os.getenv('DISCORD_BOT_TOKEN_BM')  # Fetch token from environment variable
SERVER_ID = [1105589864453394472]  # Followfox AI Testbed
IMG_PER_BATCH = 1  # Number of images to generate per batch
TOTAL_BATCHES = 4  # Maximum number of batches to generate (Warning: IMG_PER_BATCH * TOTAL_BATCHES must be <= 10)
base_url = "http://127.0.0.1:7860"

MODEL_NAME = "1_bloody_mary_v1.safetensors [ac7d34f7c9]"
BOT_NAME = 'create'
BOT_DESCRIPTION = 'Create upscaled images using FollowFox AI Bloody Mary'

# Base Delay in seconds between tries
RETRY_DELAY_SECONDS = 5

# Filelock Retry settings
MAX_RETRIES = 100

# These base prompts will be added to the input text to generate the images. The user will NOT see these prompts as additions to their input text.
base_negative_prompt = ", worst quality, deformed, low quality, bad"
base_positive_prompt = ", best quality, high quality, good"

######## Code starts here
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

sem = asyncio.Semaphore(1)  # Create a semaphore that allows only one concurrent operation

async def process_image(session, base_url, image_b64, payload, image_number):
    image = Image.open(io.BytesIO(base64.b64decode(image_b64.split(",",1)[0])))
    png_payload = {
        "image": "data:image/png;base64," + image_b64
    }
    async with session.post(f'{base_url}/sdapi/v1/png-info', json=png_payload) as response2:
        pnginfo_data = await response2.json()
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("parameters", pnginfo_data.get("info"))
        bio = io.BytesIO()  # we'll use BytesIO to hold the image in memory
        image.save(bio, 'PNG', pnginfo=pnginfo)
        bio.seek(0)  # reset file pointer to the beginning
    timestamp = time.time()
    print(f'    {timestamp:.2f}: '+ MODEL_NAME + '- Avoiding Txt2Img processing...')
    return discord.File(bio, filename=f'image{image_number+1}.png')  # directly return a Discord file object
            

async def generate_images(session, base_url, payload, image_number):
    async with session.post(f'{base_url}/sdapi/v1/txt2img', json=payload) as response:
        r = await response.json()
        file_objects = []  # This list will store all the file objects that are generated
        for i in r['images']:
            timestamp = time.time()
            print(f'    {timestamp:.2f}: '+ MODEL_NAME + f'- TXT2IMG image {i[-32:]}')
            file_object = await process_image(session, base_url, i, payload, image_number)  
            file_objects.append(file_object)  # Add the generated file object to the list
        return file_objects  # Return the list of file objects


async def fetch_images(input_text, input_negative_text):
    with open('payload-txt2img.json', 'r') as json_file:
        payload = json.load(json_file)
        
    payload["prompt"] = input_text  # Introduce to payload the input text
    payload["negative_prompt"] = input_negative_text  # Introduce to payload the input text
    payload["batch_size"]=IMG_PER_BATCH

    async with aiohttp.ClientSession() as session:
        # Get the existing options
        async with session.get(f'{base_url}/sdapi/v1/options') as resp:
            opt_json = await resp.json()

        # Retry logic for updating the options
        for attempt in range(MAX_RETRIES):
            timestamp = time.time()
            print(f'    {timestamp:.2f}: '+ MODEL_NAME + f'- Waiting to check model...')            
            async with sem:  # Protect the operation with a semaphore
                try:
                    with FileLock("options.lock", timeout=1):  # Try to acquire the lock
                        # Update the options with the correct SD model
                        opt_json['sd_model_checkpoint'] = MODEL_NAME
                        
                        # Re-POST the entire options object
                        async with session.post(f'{base_url}/sdapi/v1/options', json=opt_json) as resp:
                            if resp.status != 200:
                                timestamp = time.time()
                                print(f'    {timestamp:.2f}: '+ MODEL_NAME + f'- Failed to update model: {resp.status}')
                            else:
                                timestamp = time.time()
                                print(f'    {timestamp:.2f}: '+ MODEL_NAME + '- Model updated successfully')
                                break  # If we successfully updated the options, break out of the retry loop
                except Timeout:
                    timestamp = time.time()
                    print(f'    {timestamp:.2f}: '+ MODEL_NAME + f'- Lock is in use. Retrying after {RETRY_DELAY_SECONDS} seconds...')
                    await asyncio.sleep(RETRY_DELAY_SECONDS)  # Wait before retrying
                else:
                    timestamp = time.time()
                    print(f'    {timestamp:.2f}: '+ MODEL_NAME + f'- Failed to update options after {MAX_RETRIES} attempts')
                    break  # If we've reached the max number of retries, give up

        tasks = [generate_images(session, base_url, payload, k) for k in range(TOTAL_BATCHES)]
        file_objects = await asyncio.gather(*tasks)  # This will be a list of lists
        return [item for sublist in file_objects for item in sublist]  # Flatten the list
    

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.slash_command(name=BOT_NAME, guild_ids=SERVER_ID, description=BOT_DESCRIPTION, interaction_response_message="Serving images. Please wait...")
async def create(ctx, *, prompt: str, negative_prompt: str = ""):
    start_time = time.time()
    print(f"{start_time:.2f}: Fetcher received request. Sending to SD API...")
    await ctx.respond(f"Serving images for *{prompt} --neg {negative_prompt}*. Please wait...")
    images = await fetch_images(prompt + base_positive_prompt, negative_prompt + base_negative_prompt)    
    files_dict = {f'file{i}': image for i, image in enumerate(images)}
    await ctx.send(f"*{prompt} --neg {negative_prompt}, by {ctx.author.mention}:*", files=files_dict.values())       
    timestamp = time.time()
    print(f"    {timestamp:.2f}: "+ MODEL_NAME + f"{prompt} --neg {negative_prompt}, by @{ctx.author}.")
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"    Fetcher request completed in {elapsed_time:.2f} seconds.")

bot.run(TOKEN)