# -*- coding: utf-8 -*-
"""
Created on Fri Dec 23 14:44:14 2022

@author: klip
"""
import itertools
import yaml
from yaml.loader import SafeLoader

import os
import os.path

def SyncPreviewList(promptData, path):
    
    filename = path + '\previews.yaml'
    try:
        with open(filename) as f:
            previewData = yaml.load(f, Loader=SafeLoader)
        
        # complement preview list with new prompts
        for cat in promptData:
            if cat not in previewData:
                previewData[cat] = {}
                for prompt in promptData[cat]:
                    previewData[cat][prompt] = {}
                    previewData[cat][prompt]["Files"] = []
            else:
                for prompt in promptData[cat]:
                    if prompt not in previewData[cat]:
                        previewData[cat][prompt] = {}
                        previewData[cat][prompt]["Files"] = []
                        
    except:
        # create new preview list from prompts
        previewData = {}
        for cat in promptData:
            previewData[cat] = {}
            for prompt in promptData[cat]:
                previewData[cat][prompt] = {}
                previewData[cat][prompt]["Files"] = []
    
    # check for legacy prompts in the preview list             
    unlistedPreviewCandidates = []
    for cat in list(previewData):
        if cat not in promptData:
            for prompt in list(previewData[cat]):
                unlistedPreviewCandidates.append(previewData[cat][prompt]["Files"])
            previewData.pop(cat)
        else:
            for prompt in list(previewData[cat]):
                if prompt not in promptData[cat]:
                    unlistedPreviewCandidates.append(previewData[cat][prompt]["Files"])
                    previewData[cat].pop(prompt)
                    
    # verify if legacy prompts had previews attached which are not needed anymore                
    VerifyPreviewListing(unlistedPreviewCandidates, previewData, path)     
               
    with open(filename, 'w') as f:
        yaml.dump(previewData, f, sort_keys=False)                 
            
def VerifyPreviewListing(unlistedPreviewCandidates, previewData, path):
    
    for img in unlistedPreviewCandidates:
        for cat in previewData:
            for prompt in previewData[cat]:
                for f in previewData[cat][prompt]["Files"]:
                    if img == f:
                        unlistedPreviewCandidates.remove(img)
                        
    picsPath = path + '\_previews'
    archivePath = picsPath + '\_archive'
    try:
        os.mkdir(archivePath)
    except:
        pass
             
    for img in unlistedPreviewCandidates:
        os.replace('{}\{}'.format(picsPath, img), '{}\{}'.format(archivePath, img))
                 
                 
    

def MissingPreviewList(promptData, path):
    
    filename = path + '\previews.yaml'
    with open(filename) as f:
        previewData = yaml.load(f, Loader=SafeLoader)
    
    promptList = []
    combinations = 0
    # Loop through every possible category combination count (i.e. 3 Categories = 1-3)
    for i in range(1, len(promptData)+1): 
        
        # Loop through List of every possible category combination with the given combination count
        for catList in itertools.combinations(promptData, i):
            # for the given Category combination, create a list of all possible Prompt combinations
            print("-----")
            lst = [list(promptData[catList[0]])] # List of all prompts from 1st category as init value
            print("\t", catList[0])
            
            # Append the prompts from the other categories
            for j in range(1,i):
                print("\t", catList[j])
                lst2 = list(promptData[catList[j]])
                lst.append(lst2)
            
            # calculate Cartesian product to get all prompt combinations 
            promptNames = list(itertools.product(*lst))
            combinations += len(promptNames) #calculate total combination count

            #check if a picture of the prompt combination already exists
            for p in promptNames:
                commonFiles = set(previewData[catList[0]][p[0]]["Files"]) # init with files of the 1st prompt
                prm = promptData[catList[0]][p[0]]["Prompt"]
                prompt = prm + ", " if prm else ''  # init prompt to create the picture
                if "NegPrompt" in promptData[catList[0]][p[0]]:
                    nprm= promptData[catList[0]][p[0]]["NegPrompt"]
                else:
                    nprm = ''
                nprompt = nprm + ", " if nprm else ''  # init prompt to create the picture
                for l in range(1,len(catList)):
                    #check if there is the same file for every prompt in this combination
                    commonFiles = set(commonFiles & set(previewData[catList[l]][p[l]]["Files"])) 
                    prm = promptData[catList[l]][p[l]]["Prompt"]
                    prompt += prm + ", " if prm else ''
                    if "NegPrompt" in promptData[catList[l]][p[l]]:
                        nprm= promptData[catList[l]][p[l]]["NegPrompt"]
                    else:
                        nprm = ''    
                    nprompt += nprm + ", " if nprm else ''  # init prompt to create the picture
                        
                prompt = prompt.removesuffix(", ")
                nprompt = nprompt.removesuffix(", ")
                
                # create list for which prompts this picture will be generated if not already available
                target = '('
                for l in range(0,len(catList)):
                    target += "{" + catList[l] + ","+p[l] +"}, "
                target = target.removesuffix(", ")
                target += ')'
                
                trgt = {}
                for l in range(0,len(catList)):
                    trgt[catList[l]] = p[l]
                    
                finalPrompt = f"--prompt '{prompt}' --negative_prompt '{nprompt}'"
                
                if len(commonFiles) == 0:
                    promptList.append((trgt, finalPrompt))
                    # print(target,",","Prompt:",prompt)
                # else:
                #     print(target,",","CommonFiles:", commonFiles)
                
    
    return promptList