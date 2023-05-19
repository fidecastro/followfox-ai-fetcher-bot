# followfox-ai-fetcher-bot
Fetcher bot by FollowFox AI. Discord bot to generate images using Auto1111's API.

To install:
1. git clone this repo
2. pip install -r requirements.txt

To run:
1- launch automatic1111 like this:  python launch.py --api
2- in another terminal: python fetcher-bot-v2.py

-----------------

**Version details:**

**Fetcher-bot-v2 - May 18 2023**
- Redesigned code so that it works completely asynchronously (2 functions, fecht_images and generate_images, using )
- Redesigned code so that images are stored on memory
- Changed discord token to be passed as an environmental variable and not within code (for security reasons)
- Switched from discord.py (deprecated library) to py-cord (continuously maintained) and used Slash Command interface
- Created payload.json file to send any and all API parameters
- Added negative prompting as optional parameter
- Added base_negative_prompt and base_positive_prompt as additions to final generation
- Created a minimal terminal print log to help debugging


**Fetcher-bot-v1 - May 09 2023**
- 4 images generated upon /create request by Auto1111 api
- Images created and saved as png files, then attached to discord msg
- Request for generation sent via POST
- Bug: was not sending CFG correct (was stuck at 7)
- Bug: could not work asynchronously
