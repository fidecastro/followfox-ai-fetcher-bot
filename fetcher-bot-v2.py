##### Followfox AI Fetcher Bot - Version 2 - May 18 2023

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

TOKEN = os.getenv('DISCORD_BOT_TOKEN')  # Fetch token from environment variable
SERVER_ID = [1105589864453394472]  # Followfox AI Testbed

# These base prompts will be added to the input text to generate the images. The user will NOT see these prompts as additions to their input text.
base_negative_prompt = ", worst quality, deformed, low quality, bad"
base_positive_prompt = ", best quality, high quality, good"

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)


async def generate_images(session, base_url, payload, image_number):
    async with session.post(f'{base_url}/sdapi/v1/txt2img', json=payload) as response:
        r = await response.json()
        for i in r['images']:
            image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))
            png_payload = {
                "image": "data:image/png;base64," + i
            }
            async with session.post(f'{base_url}/sdapi/v1/png-info', json=png_payload) as response2:
                pnginfo_data = await response2.json()
                pnginfo = PngImagePlugin.PngInfo()
                pnginfo.add_text("parameters", pnginfo_data.get("info"))
                bio = io.BytesIO()  # we'll use BytesIO to hold the image in memory
                image.save(bio, 'PNG', pnginfo=pnginfo)
                bio.seek(0)  # reset file pointer to the beginning
            return discord.File(bio, filename=f'image{image_number+1}.png')  # directly return a Discord file object


async def fetch_images(input_text, input_negative_text):
    base_url = "http://127.0.0.1:7860"

    # Read the dictionary from the Payload JSON file
    with open('payload.json', 'r') as json_file:
        payload = json.load(json_file)
    
    payload["prompt"] = input_text  # Introduce to payload the input text
    payload["negative_prompt"] = input_negative_text  # Introduce to payload the input text
    
    async with aiohttp.ClientSession() as session:
        tasks = [generate_images(session, base_url, payload, j) for j in range(4)]
        return await asyncio.gather(*tasks)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')


@bot.slash_command(name="create", guild_ids=SERVER_ID, description="Create new images using FollowFox AI Vodka-V2", interaction_response_message="Creating images. Please wait...")
async def create(ctx, *, prompt: str, negative_prompt: str = ""):
    start_time = time.time()
    print(f"{start_time:.2f}: Fetcher received request. Sending to SD API...")
    await ctx.respond(f"Creating images for *'{prompt}' --neg '{negative_prompt}'*. Please wait...")
    images = await fetch_images(prompt+base_positive_prompt, negative_prompt+base_negative_prompt)    
    for image in images:    
        await ctx.send(f"*'{prompt}' --neg '{negative_prompt}', by {ctx.author.mention}:*", file=image)       
        timestamp = time.time()
        print(f"    {timestamp:.2f}: '{prompt}' --neg '{negative_prompt}', by @{ctx.author}.")
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"    Fetcher request completed in {elapsed_time:.2f} seconds.")


bot.run(TOKEN)


