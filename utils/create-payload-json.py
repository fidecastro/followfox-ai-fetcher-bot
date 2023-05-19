import json

payload = {
    "enable_hr": True,
    "denoising_strength": 0.7,
    "firstphase_width": 0,
    "firstphase_height": 0,
    "hr_scale": 2.5,
    "hr_upscaler": "Latent",
    "hr_second_pass_steps": 0,
    "hr_resize_x": 0,
    "hr_resize_y": 0,
    "prompt": "",  # Prompt would be dynamically inserted later
    "styles": [],
    "seed": -1,
    "subseed": -1,
    "subseed_strength": 0,
    "seed_resize_from_h": -1,
    "seed_resize_from_w": -1,
    "sampler_name": "",
    "batch_size": 1,
    "n_iter": 1,
    "steps": 30,
    "cfg_scale": 7,
    "width": 512,
    "height": 512,
    "restore_faces": True,
    "tiling": False,
    "do_not_save_samples": False,
    "do_not_save_grid": False,
    "negative_prompt": "",
    "eta": 0,
    "s_min_uncond": 0,
    "s_churn": 0,
    "s_tmax": 0,
    "s_tmin": 0,
    "s_noise": 1,
    "override_settings": {},
    "override_settings_restore_afterwards": False,
    "script_args": [],
    "sampler_index": "Euler a",
    "script_name": "",
    "send_images": True,
    "save_images": True,
    "alwayson_scripts": []
}

# Write the dictionary to a JSON file
with open('payload.json', 'w') as json_file:
    json.dump(payload, json_file, indent=4)
