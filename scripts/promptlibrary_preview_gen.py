import copy
import math
import os
import random
import sys
import traceback
import shlex

import modules.scripts as scripts
import gradio as gr

from modules import sd_samplers
from modules import images
from modules.processing import Processed, process_images
from PIL import Image
from modules.shared import opts, cmd_opts, state


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


class Script(scripts.Script):
    def title(self):
        return "Generate Previews for the Prompt Library"

    def ui(self, is_img2img):
        checkbox_same_seed = gr.Checkbox(label="Use same seed for all previews", value=False)

        prompt_txt = gr.Textbox(label="List of prompt inputs", lines=1)
        file = gr.File(label="Upload prompt inputs", type='bytes')

        file.change(fn=load_prompt_file, inputs=[file], outputs=[file, prompt_txt, prompt_txt])

        # We start at one line. When the text changes, we jump to seven lines, or two lines if no \n.
        # We don't shrink back to 1, because that causes the control to ignore [enter], and it may
        # be unclear to the user that shift-enter is needed.
        prompt_txt.change(lambda tb: gr.update(lines=7) if ("\n" in tb) else gr.update(lines=2), inputs=[prompt_txt], outputs=[prompt_txt])
        return [checkbox_same_seed, prompt_txt]

    def run(self, p, checkbox_same_seed, prompt_txt: str):
        lines = [x.strip() for x in prompt_txt.splitlines()]
        lines = [x for x in lines if len(x) > 0]

        p.do_not_save_samples = True
        p.do_not_save_grid = True
        p.n_iter = 1

        job_count = 0
        jobs = []

        for line in lines:
            if "--" in line:
                try:
                    args = cmdargs(line)
                except Exception:
                    print(f"Error parsing line {line} as commandline:", file=sys.stderr)
                    print(traceback.format_exc(), file=sys.stderr)
                    args = {"prompt": line}
            else:
                args = {"prompt": line}

            n_iter = args.get("n_iter", 1)
            if n_iter != 1:
                job_count += n_iter
            else:
                job_count += 1

            jobs.append(args)
        totIteration = math.ceil(job_count / p.batch_size)
        print(f"Will process {len(lines)} previews in {totIteration} jobs.")
        if p.seed == -1:
            p.seed = int(random.randrange(4294967294))

        p.prompt = []
        p.negative_prompt = []
        imgs = []
        all_prompts = []
        infotexts = []
        
        batch_count = math.floor(job_count / p.batch_size)
        batch_reamin = job_count - (batch_count * p.batch_size)
        state.job_count = batch_count+1
        
        seedInit = p.seed
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
            print(f"\nPreview {batchStart} to {batchEnd} of {job_count}")    
            state.job = f"{state.job_no + 1} out of {state.job_count}" 
            proc = process_images(p)
            
            if len(proc.images) > 0 and state.interrupted == False and state.skipped == False:
                imgs.append(images.image_grid(proc.images))
                all_prompts += proc.all_prompts
                infotexts += proc.infotexts
                basename = "plib_"
                for i in range(len(proc.images)):
                    print(images.save_image(proc.images[i], p.outpath_samples + "\\promptLibrary", basename,
                    p.seed[i], p.prompt[i], opts.samples_format, info= proc.info, p=p))
            else:
                break;
        return Processed(p, imgs, p.seed, "", all_prompts=all_prompts, infotexts=infotexts)
