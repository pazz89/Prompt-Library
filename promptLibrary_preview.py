# -*- coding: utf-8 -*-
"""
Created on Fri Dec 23 14:44:14 2022

@author: klip
"""
import itertools
import yaml
from yaml.loader import SafeLoader
import json

import os
import os.path

import functools
import time
from pathlib import Path
from collections import namedtuple
from functools import partial

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

Generation = namedtuple("Generation", ["Settings", "Prompts"])

previewFileCache = {}
previewFileCacheDirty = {}
previewFileCacheModTime = {}


def timer(func):
    """Print the runtime of the decorated function"""

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()  # 1
        value = func(*args, **kwargs)
        end_time = time.perf_counter()  # 2
        run_time = end_time - start_time  # 3
        # print(f"Finished {func.__name__!r} in {run_time:.4f} secs")
        return value

    return wrapper_timer


@timer
def SyncPreviewList(promptData, path):
    filename = path + "\previews.json"
    try:
        SetCachedPerviewFileDirty(path)
        previewData = GetCachedPreviewFile(path)
        # complement preview list with new prompts
        for cat in promptData:
            if cat not in previewData:
                previewData[cat] = {}
                for prompt in promptData[cat]:
                    previewData[cat][prompt] = {}
                    previewData[cat][prompt]["Files"] = []
                    SetCachedPerviewFileDirty(path)
            else:
                for prompt in promptData[cat]:
                    if prompt not in previewData[cat]:
                        previewData[cat][prompt] = {}
                        previewData[cat][prompt]["Files"] = []
                        SetCachedPerviewFileDirty(path)

    except:
        # create new preview list from prompts
        previewData = {}
        for cat in promptData:
            previewData[cat] = {}
            for prompt in promptData[cat]:
                previewData[cat][prompt] = {}
                previewData[cat][prompt]["Files"] = []
                SetCachedPerviewFileDirty(path)

    # check for legacy prompts in the preview list
    unlistedPreviewCandidates = []
    for cat in list(previewData):
        if cat not in promptData:
            for prompt in list(previewData[cat]):
                unlistedPreviewCandidates += previewData[cat][prompt]["Files"]
            previewData.pop(cat)
            SetCachedPerviewFileDirty(path)
        else:
            for prompt in list(previewData[cat]):
                if prompt not in promptData[cat]:
                    unlistedPreviewCandidates += previewData[cat][prompt]["Files"]
                    previewData[cat].pop(prompt)
                    SetCachedPerviewFileDirty(path)

    # verify if legacy prompts had previews attached which are not needed anymore
    VerifyPreviewListing(unlistedPreviewCandidates, previewData, path)

    with open(filename, "w") as f:
        json.dump(previewData, f, sort_keys=False)

    DeleteRefToMissingImages(path)

    previewData = GetCachedPreviewFile(path)


@timer
def DeleteRefToMissingImages(path):
    filename = path + "\previews.json"
    picsPath = path + "\_previews\\"
    try:
        with open(filename) as f:
            previewData = json.load(f)
            for cat in previewData:
                for prompt in previewData[cat]:
                    for f in list(previewData[cat][prompt]["Files"]):
                        if os.path.isfile(picsPath + f) == False:
                            previewData[cat][prompt]["Files"].remove(f)
                            SetCachedPerviewFileDirty(path)

        with open(filename, "w") as f:
            json.dump(previewData, f, sort_keys=False)

    except:
        pass


def GetCachedPreviewFile(path, load=False):
    global previewFileCache
    global previewFileCacheDirty

    loadToCache = load
    CheckPreviewModification(path)

    if path in previewFileCacheDirty:
        if previewFileCacheDirty[path]:
            loadToCache = True
    else:
        loadToCache = True

    if loadToCache:
        print("load preview file to cache")
        filename = path + "\previews.json"
        if not Path(filename).exists():
            fyaml = Path(path) / "previews.yaml"
            if fyaml.exists():
                with open(fyaml) as f:
                    data = yaml.load(f, Loader=SafeLoader)
                    with open(filename, "w") as f2:
                        json.dump(data, f2, sort_keys=False)

        with open(filename) as f:
            previewFileCache[path] = json.load(f)
        previewFileCacheDirty[path] = False

    return previewFileCache[path]


def CheckPreviewModification(path):
    global previewFileCacheDirty
    global previewFileCacheModTime
    prevPath = path + "\\_previews\\"

    subDir = [x for x in os.listdir(prevPath) if os.path.isdir(prevPath + x)]

    totModTime = 0
    for s in subDir:
        totModTime += os.path.getmtime(prevPath)
        totModTime += os.path.getmtime(prevPath + s)

    if path in previewFileCacheModTime:
        if totModTime > previewFileCacheModTime[path]:
            SetCachedPerviewFileDirty(path)
            previewFileCacheModTime[path] = totModTime

    else:
        SetCachedPerviewFileDirty(path)
        previewFileCacheModTime[path] = totModTime


def SetCachedPerviewFileDirty(path):
    global previewFileCacheDirty
    previewFileCacheDirty[path] = True


@timer
def VerifyPreviewListing(unlistedPreviewCandidates, previewData, path):

    # for img in unlistedPreviewCandidates:
    #     for cat in previewData:
    #         for prompt in previewData[cat]:
    #             for f in previewData[cat][prompt]["Files"]:
    #                 if img == f:
    #                     unlistedPreviewCandidates.remove(img)

    picsPath = path + "\_previews"
    archivePath = picsPath + "\_archive"
    try:
        os.mkdir(picsPath)
        os.mkdir(archivePath)
    except:
        pass

    for img in unlistedPreviewCandidates:
        try:
            os.replace(
                "{}\{}".format(picsPath, img),
                "{}\{}".format(archivePath, img.replace("\\", "_")),
            )
        except:
            pass


@timer
def PreviewFiles(promptData, path):
    previewData = GetCachedPreviewFile(path)
    commonFiles = set()
    for c in promptData:
        if not commonFiles:
            commonFiles = set(previewData[c][promptData[c]]["Files"])
        else:
            commonFiles = set(commonFiles & set(previewData[c][promptData[c]]["Files"]))
        if not commonFiles:
            return []
    return list(commonFiles)


@timer
def PreviewExlusivity(promptData, path, files):
    previewData = GetCachedPreviewFile(path)

    return PreviewExlusivityCore(promptData, previewData, files)


@timer
def PreviewExlusivityCore(promptData, previewData, files):
    exCount = [0] * len(files)
    exStyles = [[] for _ in range(len(files))]
    for c in previewData:
        if c in promptData:
            continue
        for p in previewData[c]:
            for idx, f in enumerate(files):
                if f in previewData[c][p]["Files"]:
                    exCount[idx] += 1
                    exStyles[idx].append({c: p})

    return exCount, exStyles


@timer
def PreviewList(promptData, path, missingOnly, fileList=False):

    previewData = GetCachedPreviewFile(path)

    # create a list of categories which shouldn't be skipped because only one prompt was selected to create images for
    dontSkipList = []
    settingsData = []
    if "_settings" in promptData:
        if "dontIgnore" in promptData["_settings"]:
            promptData["_settings"].pop("dontIgnore")
        for s in promptData["_settings"]:
            d = promptData["_settings"][s]
            if "dontIgnore" in d:
                d.pop("dontIgnore")
            d["SettingName"] = s
            settingsData.append(d)
        promptData.pop("_settings")

    for c in promptData:
        if c == "_settings":
            if promptData[c]:
                dontSkipList.append(c)
        if "dontIgnore" in promptData[c]:
            dontSkipList.append(c)
            promptData[c].pop("dontIgnore")  # remove to don't mess up prompts
        if len(promptData[c]) == 1:
            for p in promptData[c]:
                if "dontIgnore" in promptData[c][p]:
                    dontSkipList.append(c)
                    promptData[c][p].pop(
                        "dontIgnore"
                    )  # remove to don't mess up prompts

    if not settingsData:
        settingsData.append({})

    generationList = []

    for setting in settingsData:
        promptData["_settings"] = {}
        if setting:
            promptData["_settings"][setting["SettingName"]] = setting["Setting"]

        promptList = []

        # Loop through every possible category combination count (i.e. 3 Categories = 1-3)
        _PreviewListInnerFixed = partial(
            _PreviewListInner,
            promptData,
            previewData,
            missingOnly,
            dontSkipList,
            setting,
        )
        combCountList = list(range(1, len(promptData) + 1))
        with ProcessPoolExecutor() as Executor:
            result = Executor.map(_PreviewListInnerFixed, combCountList)
            for d in result:
                if d:
                    promptList += d

        # for i in range(1, len(promptData)+1):
        #     promptList += _PreviewListInnerFixed(i)

        # promptList_noDuplicates = []
        # [promptList_noDuplicates.append(x) for x in promptList if x not in promptList_noDuplicates]
        if len(promptList) > 0:
            gen = Generation(Settings=setting, Prompts=promptList)
            generationList.append(gen)

    return generationList


def _PreviewListInner(
    promptData, previewData, missingOnly, dontSkipList, setting, combCount
):

    promptList = []
    catIterations = list(itertools.combinations(promptData, combCount))

    # Remove unwanted combinations
    for catList in catIterations.copy():
        for c in dontSkipList + ["_settings"] if setting else dontSkipList:
            if c not in catList:
                catIterations.remove(catList)
                break

    # Loop through List of every possible category combination with the given combination count
    _PreviewListInnerInerFixed = partial(
        _PreviewListInnerInner, promptData, previewData, missingOnly
    )

    for catList in catIterations:
        d = _PreviewListInnerInerFixed(catList)
        if d:
            promptList += d

    # with ThreadPoolExecutor() as Executor:
    #     result = Executor.map(_PreviewListInnerInerFixed, catIterations)
    #     for d in result:
    #         if d:
    #             promptList += d
    return promptList


def _PreviewListInnerInner(promptData, previewData, missingOnly, catList):
    promptList = []
    # print("-----")
    lst = [
        list(promptData[catList[0]])
    ]  # List of all prompts from 1st category as init value
    # print("\t", catList[0])

    # Append the prompts from the other categories
    for j in range(1, len(catList)):
        # print("\t", catList[j])
        lst2 = list(promptData[catList[j]])
        lst.append(lst2)

    # calculate Cartesian product to get all prompt combinations
    promptNames = list(itertools.product(*lst))

    # check if a picture of the prompt combination already exists
    for p in promptNames:
        commonFiles = set(
            previewData[catList[0]][p[0]]["Files"]
        )  # init with files of the 1st prompt

        if "Prompt" in promptData[catList[0]][p[0]]:
            prm = promptData[catList[0]][p[0]]["Prompt"]
        else:
            prm = ""
        prompt = prm + ", " if prm else ""  # init prompt to create the picture

        if "NegPrompt" in promptData[catList[0]][p[0]]:
            nprm = promptData[catList[0]][p[0]]["NegPrompt"]
        else:
            nprm = ""
        nprompt = nprm + ", " if nprm else ""  # init prompt to create the picture

        for l in range(1, len(catList)):
            # check if there is the same file for every prompt in this combination
            commonFiles = set(commonFiles & set(previewData[catList[l]][p[l]]["Files"]))

            if "Prompt" in promptData[catList[l]][p[l]]:
                prm = promptData[catList[l]][p[l]]["Prompt"]
            else:
                prm = ""
            prompt += prm + ", " if prm else ""
            if "NegPrompt" in promptData[catList[l]][p[l]]:
                nprm = promptData[catList[l]][p[l]]["NegPrompt"]
            else:
                nprm = ""
            nprompt += nprm + ", " if nprm else ""  # init prompt to create the picture

        prompt = prompt.removesuffix(", ")
        nprompt = nprompt.removesuffix(", ")

        # create list for which prompts this picture will be generated if not already available

        trgt = {}
        trgt["cat"] = {}
        for l in range(0, len(catList)):
            trgt["cat"][catList[l]] = p[l]
        trgt["cat"].pop("_settings", None)

        # finalPrompt = f"--prompt '{prompt}' --negative_prompt '{nprompt}'"
        finalPrompt = {}
        finalPrompt["prompt"] = prompt
        finalPrompt["negative_prompt"] = nprompt

        try:
            exclusivity = min(
                PreviewExlusivityCore(catList, previewData, commonFiles)[0]
            )
        except:
            exclusivity = -1
        trgt.update(finalPrompt)
        if len(commonFiles) == 0 or missingOnly == False or exclusivity != 0:
            promptList.append(trgt)

    return promptList
