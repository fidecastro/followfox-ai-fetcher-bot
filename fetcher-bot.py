import discord
from discord.ext import commands
import asyncio
import json
import requests
import io
import base64
from PIL import Image, PngImagePlugin

TOKEN = 'MTEwNTUyNDQwNDM2MTg4NzgxNA.G-qIPm.rCLWCBPFgwBSKVE-MtalGl-CT5syQYNCqbebXk'

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

SERVER_ID = 1105589864453394472  # Followfox AI Testbed
#SERVER_ID = 1095243502641762336  # Followfox.ai server

async def generate_images(input_text):
    
    import json
    import requests
    import io
    import base64
    from PIL import Image, PngImagePlugin

    url = "http://127.0.0.1:7860"

    payload = {
        "prompt": input_text,
        "steps": 20
    }
        
    for j in range(4):

        response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)

        r = response.json()
        
        for i in r['images']:
            image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))

            png_payload = {
                "image": "data:image/png;base64," + i
            }
            response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)

            pnginfo = PngImagePlugin.PngInfo()
            pnginfo.add_text("parameters", response2.json().get("info"))
            image.save(f'image{j+1}.png', pnginfo=pnginfo)
        
    return ["image1.png", "image2.png", "image3.png", "image4.png"]

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='create')
async def create(ctx, *, input_text: str):
    # Check if the command was executed in the desired server
    if ctx.guild.id == SERVER_ID:
        images = await generate_images(input_text)

        for image in images:
            with open(image, 'rb') as f:
                await ctx.send(file=discord.File(f))
    else:
        await ctx.send("This bot only works in the designated server.")

bot.run(TOKEN)
