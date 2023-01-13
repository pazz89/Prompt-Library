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

import json

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

from modules.processing import StableDiffusionProcessing
from collections import namedtuple

Generation = namedtuple('Generation', ['Settings', 'Prompts'])

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

    def run(self, p:StableDiffusionProcessing, checkbox_same_seed, save_to_webui, libraryPath: str):  
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
            infotx = '\n' + f"Applying Setting {name}"
            print(infotx)
            print(''.ljust(len(infotx)-1, '-'))   
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

            if "Size-1" in setting:
                p.width = int(setting["Size-1"])
            if "Size-2" in setting:
                p.height = int(setting["Size-2"])

        promptList = libraryPath + "\promptList.txt"
        previewFile = libraryPath + "\previews.json"
        previewPath = libraryPath + "\_previews"
        
        assert os.path.isfile(promptList), f'missing list for preview generation'
        assert os.path.isfile(previewFile), f'missing preview file'
        with open(previewFile, 'r') as f:
            previewData = json.load(f)
        
        if save_to_webui:
            p.do_not_save_samples = False
            p.do_not_save_grid = False
        else:
            p.do_not_save_samples = True
            p.do_not_save_grid = True
        
        if save_to_webui == False:
            p.n_iter = 1


        data = []
        with open(promptList, 'r') as f:     
            lst = json.loads(f.read())
            for e in lst:
                data.append(Generation(**e))

        settings = []
        for s in data:
            if s.Settings:
                para = parse_generation_parameters(s.Settings["Setting"]+ ", Dummy1: well, Dummy2: lol")
                para["_settingName"] = s.Settings["SettingName"]
                settings.append(para)
        checkSettings(settings)

        job_count = 0
        totIteration = 0
        for job in data:
            job_count += len(job.Prompts)
            totIteration += math.ceil(job_count / p.batch_size)

        infotx = f"Will process {job_count} previews in {totIteration} jobs {p.n_iter} times, using {len(data)} settings. Total of {totIteration*p.n_iter} jobs"
        print('\n'+''.ljust(len(infotx), '-'))    
        print(infotx)
        print(''.ljust(len(infotx), '-'))   
        state.job_count = totIteration*p.n_iter

        if p.seed == -1:
            p.seed = int(random.randrange(4294967294))

        p.prompt = []
        p.negative_prompt = []
        imgs = []
        all_prompts = []
        infotexts = []
        all_seeds = []
        
        batch_count = math.ceil(job_count / p.batch_size)
        c_batch_size = p.batch_size
        
        startSeed = p.seed
        with SharedSettingsStackHelper():
            for n in range(p.n_iter):
                if state.interrupted or state.skipped:
                    break;
                for setIdx, generation in enumerate(data):
                    if state.interrupted or state.skipped:
                        break;
                    jobs = generation.Prompts
                    setting = generation.Settings
                    if setting:
                        para = parse_generation_parameters(setting["Setting"]+ ", Dummy1: well, Dummy2: lol")
                        para["_settingName"] = setting["SettingName"]
                        applySettings(para)
                    
                    p.batch_size = c_batch_size
                    processedPrompts = 0
                    toProcessPrompts = len(jobs)

                    if checkbox_same_seed:
                        seedInit = startSeed + n
                    else:
                        seedInit = startSeed + n * processedPrompts
                        
                    for i in range(0,toProcessPrompts,p.batch_size):
                        p.prompt = []
                        p.negative_prompt = []
                        p.seed = []
                        
                        batchStart = i
                        batchEnd = i+p.batch_size
                        batchEnd = batchEnd if batchEnd <= toProcessPrompts else toProcessPrompts
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
                        
                        infotx = f"\nPreview {batchStart} to {batchEnd} of {toProcessPrompts} of setting {setIdx+1} (Iteration #{n+1})"  
                        print('\n' + infotx)
                        print(''.ljust(len(infotx)-1, '-'))   
                        proc = process_images(p)
                        state.job = f"{state.job_no} out of {state.job_count}" 

                        processedPrompts += p.batch_size
                        
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
                                    if setting:
                                        previewData["_settings"][para["_settingName"]]['Files'].append(relFName)
                                    for ct in jobs[j]["cat"]:
                                        prmpt = jobs[j]["cat"][ct]
                                        previewData[ct][prmpt]['Files'].append(relFName)
                                
                                with open(previewFile, 'w') as f:
                                    json.dump(previewData, f, sort_keys=False)       
                                
                        else:
                            break;
                    
            infotx = f"Finished! Created {len(all_prompts)} images"  
            print('\n\n' + infotx)
            print(''.ljust(len(infotx), '-') + '\n')               
        return Processed(p, imgs, seedInit, "", all_prompts=all_prompts, infotexts=infotexts, all_seeds=all_seeds)
