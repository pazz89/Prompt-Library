import copy
import math
import os
import random
import sys
import traceback
import shlex
import json

import yaml
from yaml.loader import SafeLoader

import modules.scripts as scripts
import gradio as gr

from modules import sd_samplers
from modules import images
from modules.processing import Processed, process_images
from PIL import Image
from modules.shared import opts, cmd_opts, state
from modules.generation_parameters_copypaste import parse_generation_parameters
import modules.shared as shared
import modules.sd_samplers
import modules.sd_models

def process_string_tag(tag):
    return tag


def process_int_tag(tag):
    return int(tag)


def process_float_tag(tag):
    return float(tag)


def process_boolean_tag(tag):
    return True if (tag == "true") else False


prompt_tags = {
    "sd_model": None,
    "outpath_samples": process_string_tag,
    "outpath_grids": process_string_tag,
    "prompt_for_display": process_string_tag,
    "prompt": process_string_tag,
    "negative_prompt": process_string_tag,
    "styles": process_string_tag,
    "seed": process_int_tag,
    "subseed_strength": process_float_tag,
    "subseed": process_int_tag,
    "seed_resize_from_h": process_int_tag,
    "seed_resize_from_w": process_int_tag,
    "sampler_index": process_int_tag,
    "sampler_name": process_string_tag,
    "batch_size": process_int_tag,
    "n_iter": process_int_tag,
    "steps": process_int_tag,
    "cfg_scale": process_float_tag,
    "width": process_int_tag,
    "height": process_int_tag,
    "restore_faces": process_boolean_tag,
    "tiling": process_boolean_tag,
    "do_not_save_samples": process_boolean_tag,
    "do_not_save_grid": process_boolean_tag
}


def cmdargs(line):
    args = shlex.split(line)
    pos = 0
    res = {}

    while pos < len(args):
        arg = args[pos]

        assert arg.startswith("--"), f'must start with "--": {arg}'
        assert pos+1 < len(args), f'missing argument for command line option {arg}'

        tag = arg[2:]

        if tag == "prompt" or tag == "negative_prompt":
            pos += 1
            prompt = args[pos]
            pos += 1
            while pos < len(args) and not args[pos].startswith("--"):
                prompt += " "
                prompt += args[pos]
                pos += 1
            res[tag] = prompt
            continue


        func = prompt_tags.get(tag, None)
        assert func, f'unknown commandline option: {arg}'

        val = args[pos+1]
        if tag == "sampler_name":
            val = sd_samplers.samplers_map.get(val.lower(), None)

        res[tag] = func(val)

        pos += 2

    return res


def load_prompt_file(file):
    if file is None:
        lines = []
    else:
        lines = [x.strip() for x in file.decode('utf8', errors='ignore').split("\n")]

    return None, "\n".join(lines), gr.update(lines=7)
    
class SharedSettingsStackHelper(object):
    def __enter__(self):
        self.model = shared.sd_model
  
    def __exit__(self, exc_type, exc_value, tb):
        modules.sd_models.reload_model_weights(self.model)

class Script(scripts.Script):
    def title(self):
        return "Generate Previews for the Prompt Library"

    def ui(self, is_img2img):
        checkbox_same_seed = gr.Checkbox(label="Use same seed for all previews", value=False)
        save_to_webui = gr.Checkbox(label="Save to web ui instead of prompt library", value=False)

        libraryPath = gr.Textbox(label="Prompt Library Directory",
                                 placeholder="Absolute Path to the Sub-Directory of the Prompt Library")

        return [checkbox_same_seed, save_to_webui, libraryPath]

    def run(self, p, checkbox_same_seed, save_to_webui, libraryPath: str):  
        startSeed = 0
        def checkSettings(settings):
            for s in settings:
                if "Model" in s:
                    ckp = s["Model"]
                    info = modules.sd_models.get_closet_checkpoint_match(ckp)
                    if info is None:
                        raise RuntimeError(f"Unknown checkpoint: {ckp}. Make sure you use model name without folder prefix")
                
                if "Sampler" in s:
                    smpl = s["Sampler"]
                    sampler_name = sd_samplers.samplers_map.get(smpl.lower(), None)
                    if sampler_name is None:
                        raise RuntimeError(f"Unknown sampler: {smpl}")

        def applySettings(setting):
            if not setting:
                print('\n' + f"No Setting to apply")
                return

            name = setting["_settingName"]
            print('\n' + f"Applying Setting {name}")
            if "Model" in setting:
                ckp = setting["Model"]
                info = modules.sd_models.get_closet_checkpoint_match(ckp)
                if info is None:
                    raise RuntimeError(f"Unknown checkpoint: {ckp}. Make sure you use model name without folder prefix")
                modules.sd_models.reload_model_weights(shared.sd_model, info)
                p.sd_model = shared.sd_model
            
            if "Sampler" in setting:
                smpl = setting["Sampler"]
                sampler_name = sd_samplers.samplers_map.get(smpl.lower(), None)
                if sampler_name is None:
                    raise RuntimeError(f"Unknown sampler: {smpl}")

                p.sampler_name = sampler_name

            if "CFG scale" in setting:
                cfg = setting["CFG scale"]
                p.cfg_scale = float(cfg)
                
            if "Steps" in setting:
                stp = setting["Steps"]
                p.steps = int(stp)

            if "Seed" in setting:
                sed = setting["Seed"]
                nonlocal startSeed
                startSeed = int(sed)

        promptList = libraryPath + "\promptList.txt"
        previewFile = libraryPath + "\previews.yaml"
        previewPath = libraryPath + "\_previews"
        
        assert os.path.isfile(promptList), f'missing list for preview generation'
        assert os.path.isfile(previewFile), f'missing preview file'
        
        with open(promptList, 'r') as f:     
            s = f.read()
            data = json.loads(s)
            jobs = data["Prompts"]
            _settings = data["Settings"]

        settings = []
        for s in _settings:
            para = parse_generation_parameters(s["Setting"]+ ", Dummy1: well, Dummy2: lol")
            para["_settingName"] = s["SettingName"]
            settings.append(para)
        
        if settings:
            setLen = len(settings)
        else:
            settings.append({})
            setLen = 1

        with open(previewFile, 'r') as f:
            previewData = yaml.load(f, Loader=SafeLoader)
        
        if save_to_webui:
            p.do_not_save_samples = False
            p.do_not_save_grid = False
        else:
            p.do_not_save_samples = True
            p.do_not_save_grid = True
        
        if save_to_webui == False:
            p.n_iter = 1

        job_count = len(jobs)       
        tot_job_count = job_count * setLen    
            
        totIteration = math.ceil(job_count / p.batch_size)
        print(f"Will process {job_count} previews in {totIteration} jobs {p.n_iter} times, each with {setLen} settings. Total of {totIteration*p.n_iter*setLen} jobs")
        if p.seed == -1:
            p.seed = int(random.randrange(4294967294))

        p.prompt = []
        p.negative_prompt = []
        imgs = []
        all_prompts = []
        infotexts = []
        all_seeds = []
        
        batch_count = math.ceil(job_count / p.batch_size)
        
        checkSettings(settings)
        startSeed = p.seed
        with SharedSettingsStackHelper():
            for n in range(p.n_iter):
                for setIdx, set in enumerate(settings):
                    applySettings(set)
                    state.job_count = (batch_count)*p.n_iter*setLen

                    if checkbox_same_seed:
                        seedInit = startSeed + n
                    else:
                        seedInit = startSeed + n * job_count
                        
                    for i in range(0,job_count,p.batch_size):
                        p.prompt = []
                        p.negative_prompt = []
                        p.seed = []
                        
                        batchStart = i
                        batchEnd = i+p.batch_size
                        batchEnd = batchEnd if batchEnd <= job_count else job_count
                        p.batch_size = 0
                        
                        for j in range(batchStart, batchEnd):
                            p.prompt.append(jobs[j]["prompt"])
                            if "negative_prompt" in jobs[j]:
                                p.negative_prompt.append(jobs[j]["negative_prompt"])
                            else:
                                p.negative_prompt.append('')
                                
                            if checkbox_same_seed:
                                p.seed.append(seedInit)
                            else:
                                p.seed.append(seedInit + j)
                            p.batch_size +=1  
                            
                        print(f"\nPreview {batchStart} to {batchEnd} of {job_count} of setting {setIdx+1} (Iteration #{n+1})")    
                        state.job = f"{state.job_no + 1} out of {state.job_count}" 
                        
                        proc = process_images(p)
                        
                        if len(proc.images) > 0 and state.interrupted == False and state.skipped == False:
                            
                            if save_to_webui:
                                imgs += proc.images
                            else:
                                imgs.append(images.image_grid(proc.images))
                                
                            all_prompts += proc.all_prompts
                            infotexts += proc.infotexts
                            all_seeds += p.seed
                            if save_to_webui == False:
                                basename = "plib_"
                                assert len(proc.images) == batchEnd-batchStart, f'failure on image generation'
                                for i, j in zip(range(len(proc.images)),range(batchStart, batchEnd)):
                                    ifName,_ = images.save_image(proc.images[i], previewPath, basename, p.seed[i], p.prompt[i], opts.samples_format, info=proc.infotexts[i], p=p)
                                    
                                    relFName = ifName.replace(previewPath, '')
                                    previewData["_settings"][set["_settingName"]]['Files'].append(relFName)
                                    for ct in jobs[j]["cat"]:
                                        prmpt = jobs[j]["cat"][ct]
                                        previewData[ct][prmpt]['Files'].append(relFName)
                                
                                with open(previewFile, 'w') as f:
                                    yaml.dump(previewData, f, sort_keys=False)       
                                
                        else:
                            break;
                    
                    
        return Processed(p, imgs, seedInit, "", all_prompts=all_prompts, infotexts=infotexts, all_seeds=all_seeds)
