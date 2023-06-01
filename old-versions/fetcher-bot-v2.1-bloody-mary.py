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
from filelock import FileLock, Timeout

TOKEN = os.getenv('DISCORD_BOT_TOKEN_BM')  # Fetch token from environment variable
SERVER_ID = [1105589864453394472]  # Followfox AI Testbed
IMG_PER_BATCH = 1  # Number of images to generate per batch
TOTAL_BATCHES = 4  # Maximum number of batches to generate (Warning: IMG_PER_BATCH * TOTAL_BATCHES must be <= 10)
base_url = "http://127.0.0.1:7860"
img2img_switch = False # Set to True to enable Img2Img generation
img2img_upscaling = False # if set to True AND img2img_swith is also True, will bypass Img2img+Controlnet and will just do Ultra Upscaling

#MODEL_NAME = "vodkaByFollowfoxAI_v10.safetensors [d1d133610b]"
#MODEL_NAME = "vodkaByFollowfoxAI_v20.safetensors [5e1d7de310]"
#MODEL_NAME = "4_vodka_v3_100.ckpt [8dc24d7ba9]"
MODEL_NAME = "1_bloody_mary_v1.safetensors [ac7d34f7c9]"

#BOT_NAME = 'create-vodka-v3'
#BOT_NAME = 'create-bloodymary'
BOT_NAME = 'create'

#BOT_DESCRIPTION = 'Create upscaled images using FollowFox AI Vodka V3'
BOT_DESCRIPTION = 'Create upscaled images using FollowFox AI Bloody Mary'

# Filelock Retry settings
RETRY_DELAY_SECONDS = 5
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
    if img2img_switch == False: 
        timestamp = time.time()
        print(f'    {timestamp:.2f}: '+ MODEL_NAME + '- Avoiding Txt2Img processing...')
        return discord.File(bio, filename=f'image{image_number+1}.png')  # directly return a Discord file object
    else: 
        timestamp = time.time()
        print(f'    {timestamp:.2f}: '+ MODEL_NAME + '- Processing image with Img2Img...')
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
        if img2img_upscaling == True:
            payload_upscale["script_name"] = "Ultimate SD upscale"  # Introduce to payload the script name
            payload_upscale["script_args"] = [info:="", tile_width:=640, tile_height:=640, mask_blur:=8, padding:=32, seams_fix_width:=0, seams_fix_denoise:=0, seams_fix_padding:=0, upscaler_index:=3, save_upscaled_image:=True, redraw_mode:=2, save_seams_fix_image:=False, seams_fix_mask_blur:=0, seams_fix_type:=0, target_size_type:="From img2img2 settings", custom_width:=0, custom_height:=0, custom_scale:=1] # Introduce to payload the script arguments
        payload_upscale["alwayson_scripts"] = {"controlnet": controlnet}

        async with session.post(f'{base_url}/sdapi/v1/img2img', json=payload_upscale) as response3:
            r = await response3.json()
            j = r['images'][0]
            timestamp = time.time()            
            print(f'    {timestamp:.2f}: '+ MODEL_NAME + '- IMG2IMG image {j[-32:]} for TXT2IMG image {image_b64[-32:]}')
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