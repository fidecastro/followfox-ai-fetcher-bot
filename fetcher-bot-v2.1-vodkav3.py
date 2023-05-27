##### Followfox AI Fetcher Bot - Version 2.1 - May 26 2023

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
MAX_IMAGES = 4  # Maximum number of images to generate
base_url = "http://127.0.0.1:7860"

# These base prompts will be added to the input text to generate the images. The user will NOT see these prompts as additions to their input text.
base_negative_prompt = ", worst quality, deformed, low quality, bad"
base_positive_prompt = ", best quality, high quality, good"

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

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
    
    with open('payload-img2img.json', 'r') as json_file:
        payload_upscale = json.load(json_file)

    with open('payload-controlnet.json', 'r') as json_file:
        controlnet = json.load(json_file)
            
    controlnet["args"][0]["input_image"]=[png_payload["image"]]
    controlnet["args"][0]["control_mode"] = 2  # Choose "ControlNet is more important” option
    controlnet["args"][0]["module"]="tile_resample"
    controlnet["args"][0]["model"]="control_v11f1e_sd15_tile [a371b31b]"            
    payload_upscale["init_images"] = [png_payload["image"]]
    payload_upscale["prompt"] = payload["prompt"]
    payload_upscale["negative_prompt"] = payload["negative_prompt"]
    payload_upscale["resize_mode"]= 0 #3 = Just resize (latent upscale)
    payload_upscale["width"]=1024
    payload_upscale["height"]=1024
    payload_upscale["cfg_scale"]=max(payload["cfg_scale"]-0.5,1)
    payload_upscale["steps"]=150
    payload_upscale["denoising_strength"] = 0.25
    payload_upscale["alwayson_scripts"] = {"controlnet": controlnet}

    async with session.post(f'{base_url}/sdapi/v1/img2img', json=payload_upscale) as response3:
        r = await response3.json()
        j = r['images'][0]
        print(f"IMG2IMG image {j[-32:]} for TXT2IMG image {image_b64[-32:]}")
        image_upscale = Image.open(io.BytesIO(base64.b64decode(j)))
        png_payload_upscale = {
            "image": "data:image/png;base64," + j
        }
        async with session.post(f'{base_url}/sdapi/v1/png-info', json=png_payload_upscale) as response4:
            pnginfo_data = await response4.json()
            pnginfo = PngImagePlugin.PngInfo()
            pnginfo.add_text("parameters", pnginfo_data.get("info"))
            bio_upscale = io.BytesIO()  # we'll use BytesIO to hold the image in memory
            image_upscale.save(bio_upscale, 'PNG', pnginfo=pnginfo)
            bio_upscale.seek(0)  # reset file pointer to the beginning        
        return discord.File(bio_upscale, filename=f'image{image_number+1}.png')  # directly return a Discord file object
            

async def generate_images(session, base_url, payload, image_number):
    async with session.post(f'{base_url}/sdapi/v1/txt2img', json=payload) as response:
        r = await response.json()
        file_objects = []  # This list will store all the file objects that are generated
        for i in r['images']:
            print(f"TXT2IMG image {i[-32:]}")
            file_object = await process_image(session, base_url, i, payload, image_number)  
            file_objects.append(file_object)  # Add the generated file object to the list
        return file_objects  # Return the list of file objects


async def fetch_images(input_text, input_negative_text):

    # Read the dictionary from the Payload JSON file
    with open('payload-txt2img.json', 'r') as json_file:
        payload = json.load(json_file)

    payload["prompt"] = input_text  # Introduce to payload the input text
    payload["negative_prompt"] = input_negative_text  # Introduce to payload the input text
    
    async with aiohttp.ClientSession() as session:        
        async with session.get(f'{base_url}/sdapi/v1/options') as resp:
            opt_json = await resp.json()
            #opt_json['sd_model_checkpoint'] = "1_bloody_mary_v1.safetensors [ac7d34f7c9]"
            #opt_json['sd_model_checkpoint'] = "vodkaByFollowfoxAI_v10.safetensors [d1d133610b]"
            #opt_json['sd_model_checkpoint'] = "vodkaByFollowfoxAI_v20.safetensors [5e1d7de310]"
            opt_json['sd_model_checkpoint'] = "4_vodka_v3_100.ckpt [8dc24d7ba9]"
        tasks = [generate_images(session, base_url, payload, k) for k in range(MAX_IMAGES)]
        file_objects = await asyncio.gather(*tasks)  # This will be a list of lists
        return [item for sublist in file_objects for item in sublist]  # Flatten the list
    

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.slash_command(name="create-vodka-v3", guild_ids=SERVER_ID, description="Create upscaled images using FollowFox AI Vodka v3", interaction_response_message="Creating images. Please wait...")
async def create(ctx, *, prompt: str, negative_prompt: str = ""):
    start_time = time.time()
    print(f"{start_time:.2f}: Fetcher received request. Sending to SD API...")
    await ctx.respond(f"Serving images for *'{prompt}' --neg '{negative_prompt}'*. Please wait...")
    images = await fetch_images(prompt + base_positive_prompt, negative_prompt + base_negative_prompt)    
    files_dict = {f'file{i}': image for i, image in enumerate(images)}
    await ctx.send(f"*'{prompt}' --neg '{negative_prompt}', by {ctx.author.mention}:*", files=files_dict.values())       
    timestamp = time.time()
    print(f"    {timestamp:.2f}: '{prompt}' --neg '{negative_prompt}', by @{ctx.author}.")
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"    Fetcher request completed in {elapsed_time:.2f} seconds.")


bot.run(TOKEN)
