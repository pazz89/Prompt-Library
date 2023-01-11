# -*- coding: utf-8 -*-
"""
Created on Thu Dec 15 17:48:56 2022

@author: Pazz
"""
# from PIL import Image, PngImagePlugin

import itertools
import json
import os
import os.path
import re
import shutil
import time
import math
from tkinter import *
from tkinter import font, messagebox, ttk
from tkinter.simpledialog import askstring

import yaml
from PIL import Image, ImageTk, ImageFont, ImageDraw, ImageOps
from yaml.loader import SafeLoader

from promptLibrary_preview import (DeleteRefToMissingImages, PreviewExlusivity,
                                   PreviewFiles, PreviewList,
                                   SetCachedPerviewFileDirty, SyncPreviewList,
                                   timer)


class CategoryList:
    firstVal = "-"
    def __init__(self, root, data, cat, onselect):
        self.root = root
        self.promptName = StringVar()
        self.disable = BooleanVar()
        self.noIgnore = BooleanVar()
        self.dat = data
        self.cat = cat
        self.cb_change = onselect
        self.weightVal = StringVar()
        self.weightVal.set('1.0')
        
        self.frame = ttk.Frame(root, padding=(5, 5, 5, 5))
        
        self.lbox = Listbox(self.frame, exportselection=False, height=2, width=60)
        scrl = ttk.Scrollbar(self.frame, orient=VERTICAL, command=self.lbox.yview)
        f = font.nametofont('TkTextFont')
        f.config(weight='bold')
        self.catTitle = ttk.Label(self.frame, text=self.cat,font=f)
        self.dis = ttk.Checkbutton(self.frame, text="Disable", variable=self.disable, onvalue=True, command=self.cb_disabled)
        self.always = ttk.Checkbutton(self.frame, text="Don't Ignore", variable=self.noIgnore, onvalue=True)
        self.lbox.configure(yscrollcommand=scrl.set)
        self.lbox.bind("<<ListboxSelect>>", lambda e: self.cb_change())
        self.lbox.bind("<Double-Button-1>", lambda e: self.cb_edit(self.lbox.get(self.lbox.curselection())))
        self.lbox.bind("<Button-3>", lambda e: self.cb_copy(self.lbox.get(self.lbox.curselection())))
        sep = ttk.Separator(self.frame, orient=HORIZONTAL)
        self.weight = ttk.Spinbox(self.frame, format="%.1f",increment=0.1,from_=0.0, to=10.0, textvariable=self.weightVal, width=5, command=self.cb_change)
        
        btnframe = ttk.Frame(self.frame)
        btnAdd = ttk.Button(btnframe, text='+', command=self.cb_add,width=1)
        btnDel = ttk.Button(btnframe, text='-',width=1)
        btnDel.bind("<Button-1>", lambda e: self.cb_delete(self.lbox.get(self.lbox.curselection())))
        
        self.lbox.insert(0,self.firstVal)
        for idx, name in enumerate(self.dat[self.cat]):
            self.lbox.insert(idx+1,name)  
            
        self.lbox.grid(column=0, row=1, columnspan=4, sticky=(N,S,E,W))
        scrl.grid(column=4, row=1, sticky=(N,S,E,W))
        
        self.catTitle.grid(column=0, row=0, pady=0, sticky=(N,S,W))
        self.dis.grid(column=2,row=0, sticky=(N,S,E))
        self.always.grid(column=3,row=0, sticky=(N,S,E))
        self.weight.grid(column=1,row=0, sticky=(N,S,E),padx=2)
        
        btnframe.grid(column=4,row=1,rowspan=2,sticky=(N,E,W))
        btnAdd.grid(column=0,row=0,sticky=(N,E,W))
        btnDel.grid(column=0,row=1,sticky=(N,E,W))
        sep.grid(column=0,row=2, columnspan=4, sticky=(N,S,E,W), pady=5)
        
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(1, weight=1)
        self.lbox.selection_set(0)
        
    def returnSelf(self):
        return self.cat, self.dat[self.cat]
    
    def returnSelPrompt(self):
        i = self.lbox.curselection()
        c = ''
        if len(i) > 0 and self.getDisabled() == False and i[0] > 0:
            c = self.lbox.get(i)
        return c
    
    def selectByName(self, name):
        names = self.lbox.get(0, END)
        idx = names.index(name)
        self.lbox.selection_clear(0, END)
        self.lbox.selection_set(idx)
        
    def dontIgnore(self):
        return self.noIgnore.get()
        
    def relist(self, data):
        self.dat = data
        self.lbox.delete(0, END)
        self.lbox.insert(0,self.firstVal)
        for idx, name in enumerate(self.dat[self.cat]):
            self.lbox.insert(idx+1,name)  
        self.cb_change()
        
    def cb_copy(self, prompt):
        promptVal = self.dat[self.cat][prompt]["Prompt"]
        negPromptVal = self.dat[self.cat][prompt]["NegPrompt"] if "NegPrompt" in self.dat[self.cat][prompt] else ''
        
        r = Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(promptVal if promptVal else negPromptVal)
        r.update()
        r.destroy()
            
    def cb_edit(self, prompt):
        if prompt == self.firstVal:
            return
        idx = self.lbox.curselection()
        promptVal = self.dat[self.cat][prompt]["Prompt"]
        negPromptVal = self.dat[self.cat][prompt]["NegPrompt"] if "NegPrompt" in self.dat[self.cat][prompt] else ''
        
        isValid, newPrompt, newPromptVal, newNegPromptVal = PromptEdit(self.root).show(prompt, promptVal, negPromptVal)
        if isValid:
            self.dat[self.cat][prompt]["Prompt"] = newPromptVal
            if newNegPromptVal:
                self.dat[self.cat][prompt]["NegPrompt"] = {}
                self.dat[self.cat][prompt]["NegPrompt"] = newNegPromptVal
                
            if "NegPrompt" in self.dat[self.cat][prompt]:
                self.dat[self.cat][prompt]["NegPrompt"] = newNegPromptVal
            
            
            self.dat[self.cat] = {newPrompt if k == prompt and newPrompt != prompt else k:v for k,v in self.dat[self.cat].items()}
            self.relist(self.dat)
            self.lbox.selection_set(idx)
            self.cb_change(edited=True)
    
    def cb_add(self):
        isValid, newPrompt, newPromptVal, newNegPromptVal =  PromptEdit(self.root).show('', '', '')
        if isValid:
            self.dat[self.cat][newPrompt] = {}
            self.dat[self.cat][newPrompt]["Prompt"] = newPromptVal
            if newNegPromptVal:
                self.dat[self.cat][newPrompt]["NegPrompt"] = {}
                self.dat[self.cat][newPrompt]["NegPrompt"] = newNegPromptVal
            self.cb_change(edited=True)
            self.relist(self.dat)
            # self.lbox.selection_set(len(self.dat[self.cat]))
    
    def cb_delete(self, prompt):
        answer = messagebox.askyesno(title='Confirmation',
                    message="Are you sure that you want to delete '{0}'?\n\n{1}".format(prompt, self.dat[self.cat][prompt]["Prompt"]))
        if answer:
            self.dat[self.cat].pop(prompt)
            self.relist(self.dat)
            self.cb_change(edited=True)
    
    
    def grid(self, **kwargs):
        self.frame.grid(kwargs)
        
    def cb_disabled(self):
        d = self.disable.get()
        s = DISABLED if d == True else NORMAL
        self.lbox.configure(state=s) #Add this command after selection
        self.cb_change()
        
    def getDisabled(self):
        return self.disable.get()
    
    def getName(self):
        return self.cat
    
    def getSelectedPromptDict(self):
        i = self.lbox.curselection()
        sel = {}
        if len(i) > 0 and self.getDisabled() == False and i[0] > 0:
            selPrompt = self.lbox.get(i)
            sel = {self.cat:selPrompt}
        
        return sel
    
    def getPromptCount(self):
        return len(self.dat[self.cat])
    
    def getPrompt(self):
        i = self.lbox.curselection()
        weight = self.weightVal.get()
        p = ''
        if len(i) > 0 and self.getDisabled() == False and i[0] > 0:
            p += '' if weight =='1.0' else '('
            sel = self.lbox.get(i)
            i = self.dat[self.cat][sel]
            if "Prompt" in i:
                p += self.dat[self.cat][sel]["Prompt"]
                p += ':{0})'.format(weight) if weight != '1.0' else ''
        return p
    
    def getNegativePrompt(self):
        i = self.lbox.curselection()
        p = ''
        if len(i) > 0 and self.getDisabled() == False and i[0] > 0:
            sel = self.lbox.get(i)
            i = self.dat[self.cat][sel]
            if "NegPrompt" in i:
                p = i["NegPrompt"]
        return p

    def getSettings(self):
        return ''
    
    def isUnspecified(self):
        i = self.lbox.curselection()
        if not i:
            return True
        return self.getDisabled() == False and i[0] == 0

class SettingsList(CategoryList):
    def __init__(self, root, data, cat, onselect):
        super().__init__(root, data, cat, onselect)
        self.noIgnore.set(True)
        self.weight.grid_remove()
        self.catTitle.config(text = "Settings")

    def getSettings(self):
        i = self.lbox.curselection()
        p = ''
        if len(i) > 0 and self.getDisabled() == False and i[0] > 0:
            sel = self.lbox.get(i)
            i = self.dat[self.cat][sel]
            if "Setting" in i:
                p = i["Setting"]
        return p

    def cb_copy(self, prompt):
        setVal = self.dat[self.cat][prompt]["Setting"]
        
        r = Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(setVal)
        r.update()
        r.destroy()
            
    def cb_edit(self, setting):
        if setting == self.firstVal:
            return
        idx = self.lbox.curselection()
        setVal = self.dat[self.cat][setting]["Setting"]
        
        isValid, newSetting, newSettingtVal = SettingsEdit(self.root).show(setting, setVal)
        if isValid:
            self.dat[self.cat][setting]["Setting"] = newSettingtVal
             
            self.dat[self.cat] = {newSetting if k == setting and newSetting != setting else k:v for k,v in self.dat[self.cat].items()}
            self.relist(self.dat)
            self.lbox.selection_set(idx)
            self.cb_change(edited=True)
    
    def cb_add(self):
        isValid, newSetting, newSettingtVal = SettingsEdit(self.root).show('', '')
        
        if isValid:
            self.dat[self.cat][newSetting] = {}
            self.dat[self.cat][newSetting]["Setting"] = newSettingtVal
            self.cb_change(edited=True)
            self.relist(self.dat)
            # self.lbox.selection_set(len(self.dat[self.cat]))

            
    def cb_delete(self, prompt):
        answer = messagebox.askyesno(title='Confirmation',
                    message="Are you sure that you want to delete '{0}'?\n\n{1}".format(prompt, self.dat[self.cat][prompt]["Setting"]))
        if answer:
            self.dat[self.cat].pop(prompt)
            self.relist(self.dat)
            self.cb_change(edited=True)
    
class PromptEdit:
    def __init__(self, root):
        self.valid=False
        self.dlg = Toplevel(root)
        self.dlg.title("Edit Prompt")
        
        self.pName = StringVar()
        self.p = StringVar()
        self.np = StringVar()

        ttk.Label(self.dlg, text="Name:").grid(row=0, columnspan=2, sticky=(N,S,W))
        self.pNameVal = ttk.Entry(self.dlg, textvariable=self.pName)
        self.pNameVal.grid(row=1, columnspan=2, sticky=(N,S,E,W))
        
        ttk.Label(self.dlg, text="Prompt:").grid(row=2, columnspan=2, sticky=(N,S,W))
        self.pVal = ttk.Entry(self.dlg, textvariable=self.p)
        self.pVal.grid(row=3, columnspan=2, sticky=(N,S,E,W))
        
        ttk.Label(self.dlg, text="Neg.Prompt:").grid(row=4, columnspan=2, sticky=(N,S,W))
        self.npVal = ttk.Entry(self.dlg, textvariable=self.np)
        self.npVal.grid(row=5, columnspan=2, sticky=(N,S,E,W))
        
        
        ttk.Button(self.dlg, text="Confirm", command=self.confirm).grid(column=0,row=6)
        ttk.Button(self.dlg, text="Cancel", command=self.dismiss).grid(column=1,row=6)
        self.dlg.protocol("WM_DELETE_WINDOW", self.dismiss) # intercept close button
        
        self.dlg.grid_columnconfigure(0, weight=1)
        self.dlg.grid_columnconfigure(1, weight=1)

    def show(self, promptName, prompt, negPrompt):
        
        self.pNameVal.insert(0, promptName)
        self.pVal.insert(0, prompt)
        self.npVal.insert(0, negPrompt)
        
        self.dlg.wait_visibility() # can't grab until window appears, so we wait
        self.dlg.grab_set()        # ensure all input goes to our window
        self.dlg.wait_window()     # block until window is destroyed
        
        return (self.valid, self.pName.get(), self.p.get(), self.np.get())
        
    def dismiss(self):
        self.dlg.grab_release()
        self.dlg.destroy()
        
    def confirm(self):
        self.valid = True
        self.dismiss()


class SettingsEdit:
    def __init__(self, root):
        self.valid=False
        self.dlg = Toplevel(root)
        self.dlg.title("Edit Settings")
        
        self.sName = StringVar()
        self.s = StringVar()

        ttk.Label(self.dlg, text="Name:").grid(row=0, columnspan=2, sticky=(N,S,W))
        self.sNameVal = ttk.Entry(self.dlg, textvariable=self.sName)
        self.sNameVal.grid(row=1, columnspan=2, sticky=(N,S,E,W))
        
        ttk.Label(self.dlg, text="Settings:").grid(row=2, columnspan=2, sticky=(N,S,W))
        self.settings = ttk.Entry(self.dlg, textvariable=self.s)
        self.settings.grid(row=3, columnspan=2, sticky=(N,S,E,W))        
        
        ttk.Button(self.dlg, text="Confirm", command=self.confirm).grid(column=0,row=6)
        ttk.Button(self.dlg, text="Cancel", command=self.dismiss).grid(column=1,row=6)
        self.dlg.protocol("WM_DELETE_WINDOW", self.dismiss) # intercept close button
        
        self.dlg.grid_columnconfigure(0, weight=1)
        self.dlg.grid_columnconfigure(1, weight=1)

    def show(self, settingsName, settings):
        
        self.sNameVal.insert(0, settingsName)
        self.settings.insert(0, settings)
        
        self.dlg.wait_visibility() # can't grab until window appears, so we wait
        self.dlg.grab_set()        # ensure all input goes to our window
        self.dlg.wait_window()     # block until window is destroyed
        
        return (self.valid, self.sName.get(), self.s.get())
        
    def dismiss(self):
        self.dlg.grab_release()
        self.dlg.destroy()
        
    def confirm(self):
        self.valid = True
        self.dismiss()
        

class PromptPreview:
    def __init__(self, root, cb_copyWith):
        self.copyCB = cb_copyWith
        self.acpy = BooleanVar()
        self.frame = ttk.Frame(root, padding=(5, 5, 5, 5))
        self.promptText = Text(self.frame, width=40, height=10,wrap = "word")    
        scrl = ttk.Scrollbar(self.frame, orient=VERTICAL, command=self.promptText.yview)
        f = font.nametofont('TkTextFont')
        f.config(weight='bold')
        lbl = ttk.Label(self.frame, text="Prompt", font=f)
        self.promptText.configure(yscrollcommand=scrl.set)
        self.cpyBtn = ttk.Button(self.frame, text='Copy', command=self.copy)
        self.cpyWBtn = ttk.Button(self.frame, text='Copy with Preview Parameters', command=self.copyWith)
        self.autoCpy = ttk.Checkbutton(self.frame, text="Auto Copy", variable=self.acpy, onvalue=True)
        
        lbl.grid(column=0, row=0, pady=0, sticky=(N,S,W))
        self.promptText.grid(column=0, row=1, sticky=(N,S,E,W), columnspan=3)
        scrl.grid(column=3, row=1, sticky=(N,S,E,W))
        self.cpyBtn.grid(column=0,row=2, sticky=(N,S,E,W), pady=5)
        self.cpyWBtn.grid(column=1,row=2, sticky=(N,S,E,W), pady=5)
        self.autoCpy.grid(column=2,row=2, sticky=(N,S,E,W), pady=5, columnspan=2)
        
        self.frame.grid_columnconfigure(0, weight=2)
        self.frame.grid_columnconfigure(1, weight=1)
        self.frame.grid_rowconfigure(1, weight=1)
        
        self.promptText.tag_configure('marked', background='light grey')
        self.promptText.tag_configure('negPrompt', foreground='red')
        
    def setText(self, text):
        self.promptText.delete("1.0","end")
        self.promptText.insert(END, text)
        ac = self.acpy.get()
        
        if ac == True:
            self.copy()
            
    def markText(self, searchText):
        countVar = StringVar()
        index = self.promptText.search(searchText, '1.0',  stopindex=END, count=countVar)
        if index != '':
            self.promptText.tag_add('marked', index,  "%s + %sc" % (index, countVar.get()))
        
    def markNegPrompt(self):
        index = self.promptText.search('Negative prompt:', '1.0', END)
        if index != '':
            self.promptText.tag_add('negPrompt', index, END)
            
    def tag_add(self, **kwargs):
        self.promptText.tag_add(kwargs)

    def grid(self, **kwargs):
        self.frame.grid(kwargs)
        
    def copy(self):        
        s = self.promptText.get("1.0",END)
        r = Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(s)
        r.update()
        r.destroy()
        
    def copyWith(self):        
        s = self.promptText.get("1.0",END)
        self.copyCB(s)
        
    def setFocus(self):
        # self.cpyBtn.focus_set()
        pass
    
    def getPrompt(self):
        return self.promptText.get("1.0",END)
        
class ImagePreview:
    imgIdx = 0
    def __init__(self, root, cb_del, cb_sel):
        self.frame = ttk.Frame(root, padding=(5, 5, 5, 5))
        self.canvas = Label(self.frame, anchor=CENTER, borderwidth=0)
        self.canvas.grid(row = 1,sticky=(N,S,E,W),columnspan=3)
        self.on_delete = cb_del
        self.on_select = cb_sel
        
        f = font.nametofont('TkTextFont')
        f.config(weight='bold')
        self.lbl = ttk.Label(self.frame, text="Visual Reference", font=f)
        self.lbl.grid(row=0,sticky=(N,S,E,W),columnspan=3)
        
        self.canvas.bind("<Button-1>", self.NextImage)
        self.canvas.bind("<Button-4>", self.NextImage)
        self.canvas.bind("<Button-2>", self.PreviousImage)
        self.canvas.bind("<Button-3>", self.PreviousImage)
        self.canvas.bind("<Button-5>", self.PreviousImage)
        self.canvas.bind("<MouseWheel>", self.ScrollImage)

        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.hasImage = False
        
        self.iInfo = Text(self.frame,height=5,wrap = "word")    
        self.iInfo.grid(row=2, sticky=(N,S,E,W))
        self.iInfo.config(state=DISABLED)
        scrl = ttk.Scrollbar(self.frame, orient=VERTICAL, command=self.iInfo.yview)
        self.iInfo.configure(yscrollcommand=scrl.set)
        scrl.grid(column=1, row=2, sticky=(N,S,E,W))
        
        btnFrame = ttk.Frame(self.frame, padding=(5, 5, 5, 5))
        btnFrame.grid(column=2,row=2, sticky=(N,E,W))
        self.delBtn = ttk.Button(btnFrame, text='Delete', command=self.DeleteImage)
        self.delBtn.grid(row=0, sticky=(N,E,W))
        self.delBtn.config(state=DISABLED)
        
        self.selBtn = ttk.Button(btnFrame, text='Select', command=self.SelectImagePrompts)
        self.selBtn.grid(row=1, sticky=(N,E,W))
        self.selBtn.config(state=DISABLED)
        
        self.cpyBtn = ttk.Button(btnFrame, text='Copy', command=self.CopyImageSettings)
        self.cpyBtn.grid(row=2, sticky=(N,E,W))
        self.cpyBtn.config(state=DISABLED)
        
        self.noCpy = BooleanVar()
        self.noCpyCkp = ttk.Checkbutton(btnFrame, text="Copy Model/Batch", variable=self.noCpy, onvalue=True)
        self.noCpyCkp.grid(row=3, sticky=(N,E,W)) 
        self.noCpy.set(False)
        
           
                
        
    def _getSize(self, fw, fh, iw, ih):
        if fw >= iw and fh >= ih:
            return iw, ih
        
        if fw >= iw and fh < ih:
            return int(iw * fh/ih), fh
        
        if fw < iw and fh >= ih:
            return fw, int(ih*fw/iw)
        
        if fw < iw and fh < ih:
            dw = fw/iw
            dh = fh/ih
            
            w = iw * dw if dw < dh else iw * dh
            h = ih * dw if dw < dh else ih * dh
            
            return int(w), int(h)
        
    def ScrollImage(self, event):
        if event.delta < 0:
            self.NextImage(event)
        else:
            self.PreviousImage(event)
        
    def NextImage(self, event):
        if self.hasImage == False:
            return
        self.imgIdx = self.imgIdx + 1 if self.imgIdx + 1 <= len(self.images) else 1
        self.SetImage(self.imgPath + self.images[self.imgIdx-1][1])
        self.UpdateVisRefLabel()
    
    def PreviousImage(self, event):
        if self.hasImage == False:
            return
        self.imgIdx = self.imgIdx - 1 if self.imgIdx - 1 > 0 else len(self.images)
        self.SetImage(self.imgPath + self.images[self.imgIdx-1][1])
        self.UpdateVisRefLabel()
        
    def SetPreviewIndex(self, index):
        if self.hasImage == False:
            return
        self.imgIdx = index if index <= len(self.images) and index > 0 else 1
        self.SetImage(self.imgPath + self.images[self.imgIdx-1][1])
        self.UpdateVisRefLabel()
        
        
    
    def SetImageSet(self, path, images):
        self.delBtn.config(state=NORMAL)
        self.cpyBtn.config(state=NORMAL)
        self.selBtn.config(state=NORMAL)
        self.imgPath = path
        self.images = images
        self.imgIdx = 1
        self.UpdateVisRefLabel()
        self.SetImage(self.imgPath + self.images[0][1])
    
    def UpdateVisRefLabel(self):
        addStyles = ''
        addStylesCount = self.images[self.imgIdx-1][0]
        if addStylesCount > 0:
            addStyles = '('
            for style in self.images[self.imgIdx-1][2]:
                for k in style:
                    addStyles += f'{k}/{style[k]}, '
            addStyles = addStyles.removesuffix(", ")
            addStyles += ')'
            
        self.lbl.config(text=f"Visual Reference - {self.imgIdx}/{len(self.images)} - Additional Prompts: {addStylesCount} {addStyles}")
    
    def DeleteImage(self):    
        file = self.imgPath + self.images[self.imgIdx-1][1]
        os.remove(file)
        self.on_delete(self.imgIdx-1)
        
    def SelectImagePrompts(self):    
        styles = self.images[self.imgIdx-1][2]
        self.on_select(styles)
        
    def CopyImageSettings(self):
        file = self.imgPath + self.images[self.imgIdx-1][1]
        imgOrig = Image.open(file)
        
        cpyModel = self.noCpy.get()
        
        info = imgOrig.info
        if 'parameters' in info:   
            s = info['parameters']
            if not cpyModel:
                s = re.sub("Model hash: [a-zA-Z0-9]*[\s,]*|Batch size: [a-zA-Z0-9]*[\s,]*|Batch pos: [a-zA-Z0-9]*[\s,]*", '', s)
            
            r = Tk()
            r.withdraw()
            r.clipboard_clear()
            r.clipboard_append(s)
            r.update()
            r.destroy()
        
        
    def SetImage(self, fImg):
        if isinstance(fImg, str):
            self.imgOrig = Image.open(fImg)
        else:
            self.imgOrig = fImg

        
        self.iInfo.config(state=NORMAL)
        info = self.imgOrig.info
        if 'parameters' in info:
            self.iInfo.delete("1.0","end")
            lines = [x.strip() for x in info['parameters'].splitlines()]
            for l in range(0,len(lines)-1):
                self.iInfo.insert(END, lines[l] + "\n")
            self.iInfo.insert("1.0", lines[-1] + "\n\n")
        else:
            self.iInfo.delete("1.0","end")
        self.iInfo.config(state=DISABLED)
        
        w, h = self._getSize(self.canvas.winfo_width(), self.canvas.winfo_height(), self.imgOrig.width, self.imgOrig.height)
        self.img = ImageTk.PhotoImage(self.imgOrig.resize((w, h)))
        
        self.canvas.configure(image=self.img)
        # self.canvas.create_image(0, 0, anchor=NW, image=self.img) 
        self.hasImage = True
        
    def GetParameters(self):
        if self.hasImage == False:
            return ''
        try:
            file = self.imgPath + self.images[self.imgIdx-1][1]
            imgOrig = Image.open(file)
            
            info = imgOrig.info
            if 'parameters' in info:
                lines = [x.strip() for x in info['parameters'].splitlines()]
                return lines[-1]
            else:
                return ''
        except:
            return ''
        
    def ClearImage(self):
        self.delBtn.config(state=DISABLED)
        self.cpyBtn.config(state=DISABLED)
        self.selBtn.config(state=DISABLED)
        self.hasImage = False
        self.canvas.configure(image='')
        self.iInfo.config(state=NORMAL)
        self.iInfo.delete("1.0","end")
        self.iInfo.config(state=DISABLED)
        self.lbl.config(text=f"Visual Reference")
        

    def grid(self, **kwargs):
        self.frame.grid(kwargs)

    def grid_remove(self):
        self.frame.grid_remove()
    
class GridPreview:
    imgIdx = 0
    def __init__(self, root, catList, path, cb_commonFiles):
        self.frame = ttk.Frame(root, padding=(5, 5, 5, 5))
        self.canvas = Label(self.frame, anchor=CENTER, borderwidth=0)
        self.canvas.grid(row = 1,sticky=(N,S,E,W),columnspan=3)
        self.commonFiles = cb_commonFiles
        self.catList = catList
        self.path = path
        
        f = font.nametofont('TkTextFont')
        f.config(weight='bold')
        self.lbl = ttk.Label(self.frame, text="Visual Reference", font=f)
        self.lbl.grid(row=0,sticky=(N,S,E,W),columnspan=3)
        
        self.canvas.bind("<Button-1>", self.NextImage)
        self.canvas.bind("<Button-4>", self.NextImage)
        self.canvas.bind("<Button-2>", self.PreviousImage)
        self.canvas.bind("<Button-3>", self.PreviousImage)
        self.canvas.bind("<Button-5>", self.PreviousImage)
        self.canvas.bind("<MouseWheel>", self.ScrollImage)

        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.hasImage = False              

    def grid(self, **kwargs):
        self.frame.grid(kwargs)

    def grid_remove(self):
        self.frame.grid_remove()

    def ScrollImage(self, event):
        if event.delta < 0:
            self.NextImage(event)
        else:
            self.PreviousImage(event)
        
    def NextImage(self, event):
        if self.hasImage == False:
            return
        self.imgIdx = self.imgIdx + 1 if self.imgIdx + 1 <= len(self.combo) else 1
        self.SetImage(self.combo[self.imgIdx-1])
        self.UpdateVisRefLabel()
    
    def PreviousImage(self, event):
        if self.hasImage == False:
            return
        self.imgIdx = self.imgIdx - 1 if self.imgIdx - 1 > 0 else len(self.combo)
        self.SetImage(self.combo[self.imgIdx-1])
        self.UpdateVisRefLabel()

    def ClearImage(self):
        self.hasImage = False
        self.canvas.configure(image='')
        self.lbl.config(text=f"Visual Reference")

    def UpdateVisRefLabel(self):      
        self.lbl.config(text=f"Visual Reference - {self.imgIdx}/{len(self.combo)} - {self.xlabel}/{self.ylabel}")

    def _getSize(self, fw, fh, iw, ih):
        if fw >= iw and fh >= ih:
            return iw, ih
        
        if fw >= iw and fh < ih:
            return int(iw * fh/ih), fh
        
        if fw < iw and fh >= ih:
            return fw, int(ih*fw/iw)
        
        if fw < iw and fh < ih:
            dw = fw/iw
            dh = fh/ih
            
            w = iw * dw if dw < dh else iw * dh
            h = ih * dw if dw < dh else ih * dh
            
            return int(w), int(h)
            
    def SetImage(self, combo):
        xLabel = combo[0]
        yLabel = combo[1]
        fImg, flipped = self.gridPreview(self.selection, xLabel, yLabel)

        self.imgOrig = fImg
        
        w, h = self._getSize(self.canvas.winfo_width(), self.canvas.winfo_height(), self.imgOrig.width, self.imgOrig.height)
        # self.img = ImageTk.PhotoImage(self.imgOrig.resize((w, h)))
        self.img = ImageTk.PhotoImage(self.imgOrig)
        
        self.canvas.configure(image=self.img)
        self.hasImage = True
        if flipped:
            self.xlabel = yLabel
            self.ylabel = xLabel
        else:
            self.xlabel = xLabel
            self.ylabel = yLabel
        self.UpdateVisRefLabel()

    def previewFromSelection(self, selection:dict, combo):
        
        self.images = []
        self.combo = combo
        self.selection = selection
        
        self.imgIdx = 1
        if len(self.combo) > 0:
            self.SetImage(self.combo[0])
            self.UpdateVisRefLabel()
        else:
            self.ClearImage()


    def gridPreview(self, selection:dict, cat1='', cat2=''):
        sel = selection.copy()
        flipped = False
        cat1Keys = []
        cat2Keys = []
        for c in self.catList :
            if c.getName() in [cat1]:
                cat1Keys += list(c.returnSelf()[1].keys())
            if c.getName() in [cat2]:
                cat2Keys += list(c.returnSelf()[1].keys())
        
        xy = []
        xyImg = []
        wMax = 0
        hMax = 0
        for c1 in cat1Keys:
            sel.pop(cat1, None)
            sel.pop(cat2, None)
            sel[cat1] = c1
            x = []
            xImg = []
            for c2 in cat2Keys:
                sel[cat2] = c2
                cfl = self.commonFiles(sel)
                cf = cfl[0] if cfl else []
                if cf:
                    img = Image.open(self.path + '\_previews\\' + cf[1])
                    wMax = max(wMax, img.width)
                    hMax = max(hMax, img.height)
                    x.append(cf)
                    xImg.append(img)
                else:
                    img = Image.new('RGBA', (wMax, hMax), color=(0,0,0,0))
                    x.append((0,'',dict()))
                    xImg.append(img)
            xy.append(x)
            xyImg.append(xImg)

        textsize = 12
        textsize_s = 10
        padding = (textsize+5,textsize+5)
        fnt = ImageFont.truetype("arial.ttf", textsize)
        fnt_s = ImageFont.truetype("arial.ttf", int(textsize_s))
        w, h = wMax, hMax
        if w == 0 or h == 0:
            imgSize = (self.canvas.winfo_width(), self.canvas.winfo_height())
            grid = Image.new('RGBA',imgSize, color=(0,0,0,0))
            d = ImageDraw.Draw(grid)
            txt = 'No Images Found!'
            d.text((10,10), txt, 'red', fnt)
            return grid, False


        imgSize = (len(xy)* w, len(xy[0]) * h)
        if len(xy[0]) * h > len(xy) * h:
            flipped = True
            # Transpose Matrices
            xy = [list(x) for x in zip(*xy)]
            xyImg = [list(x) for x in zip(*xyImg)]
            tmp = cat1Keys
            cat1Keys = cat2Keys
            cat2Keys = tmp
            
        imgSize = (len(xy)* w, len(xy[0]) * h)


        
        wf, hf = self._getSize(self.canvas.winfo_width() - padding[0], self.canvas.winfo_height() - padding[1],imgSize[0], imgSize[1])
        ws = wf/imgSize[0]
        hs = hf/imgSize[1]
        scale = (ws, hs)
        imgSize = (wf, hf)
        w = math.floor(w * scale[0])
        h = math.floor(h * scale[1])

        gridSize =  tuple(map(lambda i, j: i + j, imgSize, padding))
        grid = Image.new('RGBA', gridSize, color=(0,0,0,0))

        for ix, x in enumerate(xy):
            for iy, y in enumerate(x):
                img = xyImg[ix][iy]
                size = (math.floor(img.width*ws), math.floor(img.height*hs))
                img = img.resize(size)
                if y[0] > 0:
                    imgExclBase = Image.new('RGBA', (textsize_s*2,textsize_s*2), color=(255,255,255,0))
                    imgExcl = ImageDraw.Draw(imgExclBase)
                    imgExcl.polygon([(0,0),(0,textsize_s*2),(textsize_s*2,0)],fill=(255,255,255,150))
                    imgExcl.text((0, 0), f'+{y[0]}', 'red', fnt_s)
                    img.paste(imgExclBase, (0,0), imgExclBase)
                grid.paste(img, box=(padding[0] + ix*w, padding[1] + iy*h))

        d = ImageDraw.Draw(grid)
        for ix, x in enumerate(cat1Keys):
            d.text((padding[0] + ix * w, 0),x, 'black', fnt)

        for iy, y in enumerate(cat2Keys):
            txt=Image.new('RGBA', (h,padding[1]),color=(0,0,0,0))
            dtxt = ImageDraw.Draw(txt)
            dtxt.text( (0, 0), y, 'black', fnt)
            dtxt=txt.rotate(90,  expand=1)
            grid.paste(dtxt, box=(0, padding[1] + iy * h))

        return grid, flipped

class Set:
    dirty = False
    gridView = False
    def __init__(self, root, name):    
        self.path = name
        self.filename = self.path + '\config.yaml'
        self.Previewfilename = self.path + '\previews.yaml'
        self.frame = ttk.Frame(root)
        root.add(self.frame, text=self.path)
        DeleteRefToMissingImages(self.path)
        with open(self.filename) as f:
            struct = yaml.load(f, Loader=SafeLoader)
            
        self.catList = []
        for idx, cat in enumerate(struct):
            if cat == "_settings":
                continue
            c = CategoryList(self.frame, struct, cat, self.listboxSelectionChanged)
            c.grid(column=0, row=idx, sticky=(N,W,E,S))
            self.frame.grid_rowconfigure(idx,weight=c.getPromptCount())
            self.catList.append(c)
            
        if "_settings" not in struct:
            struct["_settings"] = {}
            with open(self.filename, 'w') as f:
                yaml.dump(struct, f, sort_keys=False)

        cs = SettingsList(self.frame, struct, "_settings", self.listboxSelectionChanged)
        idx = len(struct)
        cs.grid(column=0, row=idx,sticky=(N,W,E,S))
        self.frame.grid_rowconfigure(idx,weight=cs.getPromptCount())
        self.catList.append(cs)
        
        ppFrame = ttk.Frame(self.frame)
        ppFrame.grid(column=2, row = 0, rowspan=idx+2, sticky=(N,W,E,S))
        self.pPreview = PromptPreview(ppFrame, self.copyWithPreviewPara)
        self.pPreview.grid(column=0, row=0, sticky=(N,W,E,S))
       
        self.iPreview = ImagePreview(ppFrame, self.cb_imageDeleted, self.cb_imageSelectPrompts)
        self.gPreview = GridPreview(ppFrame, self.catList, self.path, self.getPreviewFilesFromSelection)

        if not self.gridView:
            self.iPreview.grid(column=0, row=1, sticky=(N,W,E,S))
        else:
            self.gPreview.grid(column=0, row=1, sticky=(N,W,E,S))


        ppFrame.grid_columnconfigure(0, weight=1)
        ppFrame.grid_rowconfigure(1, weight=1)
                
        ttk.Separator(self.frame, orient=VERTICAL).grid(column=1, row=0, rowspan=len(struct)+2, sticky=(N,W,E,S))
        
        btnFrame = ttk.Frame(self.frame)
        btnFrame.grid(column=0, row=idx+1)

        self.saveBtn = ttk.Button(btnFrame, text='Save', command=self.cb_save)
        self.saveBtn.config(state=DISABLED)
        # self.saveBtn.grid(column=0)
        
        self.resetBtn = ttk.Button(btnFrame, text='Reset Selection', command=self.cb_reset)
        self.resetBtn.grid(column=0, row=0)

        self.gridBtn = ttk.Button(btnFrame, text='Toggle Grid View', command=self.cb_toggleGridView)
        self.gridBtn.grid(column=1, row=0)
        
        # frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(2, weight=1)  
        
        SyncPreviewList(struct, self.path)

    def cb_toggleGridView(self):
        if self.gridView:
            self.gridView = False
            self.gPreview.grid_remove()
            self.iPreview.grid(column=0, row=1, sticky=(N,W,E,S))
        else:
            self.gridView = True
            self.iPreview.grid_remove()
            self.gPreview.grid(column=0, row=1, sticky=(N,W,E,S))

        self.frame.update()
        self.listboxSelectionChanged()

    def copyWithPreviewPara(self, prompt):
        para = self.iPreview.GetParameters()
        clip = prompt + para
        
        r = Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(clip)
        r.update()
        r.destroy()
        
    def cb_dirty(self):
        self.dirty = True
        self.saveBtn.config(state=NORMAL)
        self.cb_save()
        
    def cb_save(self):
        saveDict = {}
        for idx, cat in enumerate(self.catList):
            c, d = cat.returnSelf()
            saveDict[c] = d
        
        with open(self.filename, 'w') as f:
            yaml.dump(saveDict, f, sort_keys=False)
            self.dirty = False
            self.saveBtn.config(state=DISABLED)
            for idx, cat in enumerate(self.catList):
                cat.dirty = False
                
        SyncPreviewList(saveDict, self.path)
        try:
            os.remove(self.path + "\promptList.txt")
        except:
            pass
        
    def cb_imageDeleted(self, selectPreview):
        data = {}
        for idx, cat in enumerate(self.catList):
            c, d = cat.returnSelf()
            data[c] = d
        SyncPreviewList(data, self.path)
        self.listboxSelectionChanged()
        print(selectPreview)
        self.iPreview.SetPreviewIndex(selectPreview)
    
    def cb_imageSelectPrompts(self, selection):
        for sel in selection:
            for c in sel:
                for cat in self.catList:
                    if c == cat.getName():
                        cat.selectByName(sel[c])
        self.listboxSelectionChanged()
        
    def cb_reset(self):
        for cat in self.catList:
            cat.selectByName(cat.firstVal)
        self.listboxSelectionChanged()
        
                
    @timer   
    def listboxSelectionChanged(self, edited = False):
        if edited:
            self.cb_dirty()
            
        pp = ''
        np = ''
        sp = ''
        selDict = {}
        for c in self.catList:
            selDict.update(c.getSelectedPromptDict())
            p = c.getPrompt()
            n = c.getNegativePrompt()
            s = c.getSettings()
            pp += p + ", " if p else ''
            np += n + ", " if n else ''
            sp = s if s else ''
        pp = pp.removesuffix(", ")
        np = np.removesuffix(", ")
        pp += '\nNegative prompt: '+np if np else ''
        pp += '\n' + sp if sp else ''
        
        self.pPreview.setText(pp)
        self.pPreview.setFocus()
        
        mark = False
        for c in self.catList:
            text = c.getPrompt()
            if text == '':
                continue
            if mark:
                self.pPreview.markText(text)
                mark = False
            else:
                mark = True
        
        self.pPreview.markNegPrompt()

        if self.gridView:
            notSetCat = []
            for c in self.catList:
                if c.isUnspecified():
                    notSetCat.append(c.getName())
            gridCombo = list(itertools.combinations(notSetCat, 2))
            self.gPreview.previewFromSelection(selDict, gridCombo)
        else:
            self.previewFromSelection(selDict)
        

    def previewFromSelection(self, selection):
        # Get Preview Files
        commonFiles = self.getPreviewFilesFromSelection(selection)
        
        # print(f'Found {len(commonFiles)} Files with exclusivities: {[x[0] for x in commonFiles]}')
        if len(commonFiles) > 0:
            self.iPreview.SetImageSet(self.path + '\_previews\\', commonFiles)
        else:
            self.iPreview.ClearImage()
    
    
    def getPreviewFilesFromSelection(self, selection):
        # Get Preview Files
        commonFiles = PreviewFiles(selection, self.path)
        
        # Sorty by Exclusivity
        commonFilesExcl, addStyles = PreviewExlusivity(selection, self.path, commonFiles)
        
        # commonFiles = [x for _,x in sorted(zip(commonFilesExcl,commonFiles))]
        commonFiles = sorted(zip(commonFilesExcl,commonFiles,addStyles))

        return commonFiles


    def createPreviewList(self, missing):
        allData = {}
        for idx, cat in enumerate(self.catList):
            c, d = cat.returnSelf()
            allData[c] = d
            
        previewData = {}
        for cat in self.catList:
            if cat.getDisabled() == False:
                if cat.isUnspecified():
                    c, d = cat.returnSelf()
                    previewData[c] = d
                    if cat.dontIgnore():
                        previewData[c]['dontIgnore'] = True
                else:
                    c, d = cat.returnSelf()
                    p = cat.returnSelPrompt()
                    previewData[c] = {}
                    previewData[c][p] = d[p]
                    previewData[c][p]['dontIgnore'] = True
                    
        SyncPreviewList(allData, self.path)
        promptList = PreviewList(previewData, self.path, missing)
        # print(promptList)
        with open(self.path + "\promptList.txt", 'w') as f:
            j = json.dumps([gen._asdict() for gen in promptList])
            f.write(j)

        pl = 0
        for s in promptList:
            pl  += len(s.Prompts)  
        sl = len(promptList)
        
        if not promptList or not promptList[0].Settings:
            messagebox.showinfo("Prompt File created", f"Prompt File for {pl} previews created!")
        else:
            messagebox.showinfo("Prompt File created", f"Prompt File for {pl} previews created using {sl} setting(s)!")

class SetEdit:
    isValidEdit = False
    def __init__(self, root, name):  
        
        self.tl= Toplevel(root)
        self.tl.title("Edit Set")
        self.tl.grid_columnconfigure(0, weight=1)
        self.tl.grid_rowconfigure(0, weight=1)  
        
        self.frame = ttk.Frame(self.tl, padding=(5, 5, 5, 5))
        self.frame.grid(sticky=(N,S,E,W))
        self.frame.grid_columnconfigure(1, weight=1)  
        self.frame.grid_rowconfigure(1, weight=1)  
        
        if name != '':
            self.path = name
            self.filename = self.path + '\config.yaml'
            
            with open(self.filename) as f:
                self.struct = yaml.load(f, Loader=SafeLoader)
        else:
            self.struct = {}
            self.path = ''
                
        self.setName = StringVar()

        ttk.Label(self.frame, text="Set Name:").grid(row=0, column=0, sticky=(N,S,W))
        self.setNameVal = ttk.Entry(self.frame, textvariable=self.setName)
        self.setNameVal.grid(row=0, column=1, sticky=(N,S,E,W))
        self.setNameVal.insert(0, name)
        
        self.setContent = ttk.Treeview(self.frame)
        self.setContent.grid(row=1,columnspan=2, sticky=(N,S,E,W))
                
        self.setContent['columns']= ('id', 'index')
        self.setContent.column("#0", width=0,  stretch=NO)
        self.setContent.column("id",anchor=W, width=80)
        self.setContent.column("index",anchor=CENTER, width=70, stretch=NO)
        
        self.setContent.heading("#0",text="",anchor=CENTER)
        self.setContent.heading("id",text="Name",anchor=CENTER)
        self.setContent.heading("index",text="Index",anchor=CENTER)
        
        self.setContent.bind('<Double-1>', self.contentSelected)  
        
        
        inputFrame = ttk.Frame(self.frame, padding=(5, 5, 5, 5))
        inputFrame.grid(row=2, columnspan=2, sticky=(N,S,E,W))
        inputFrame.grid_columnconfigure(0, weight=1)  
        
        cName = Label(inputFrame,text="Name")
        cName.grid(row=0,column=0, sticky=(N,S,E,W))

        cIndex= Label(inputFrame,text="Index",width=1)
        cIndex.grid(row=0,column=1, sticky=(N,S,E,W))

        self.cNameEntry = Entry(inputFrame)
        self.cNameEntry.grid(row=1,column=0, sticky=(N,S,E,W))

        self.cIndexEntry = Entry(inputFrame)
        self.cIndexEntry.grid(row=1,column=1, sticky=(N,S,E,W))

        
        
        btnFrame = ttk.Frame(self.frame, padding=(5, 5, 5, 5))
        btnFrame.grid(row = 3, columnspan=2,sticky=(S,E,W))
        btnFrame.grid_columnconfigure(0, weight=1)
        btnFrame.grid_columnconfigure(1, weight=1)
        btnFrame.grid_columnconfigure(2, weight=1)
        
        self.insertBtn = ttk.Button(btnFrame, text='Insert', command=self.cb_insert)
        self.insertBtn.grid(row=0,column=0)
        
        self.updateBtn = ttk.Button(btnFrame, text='Update Selected', command=self.cb_update)
        self.updateBtn.grid(row=0,column=1)
        
        self.removeBtn = ttk.Button(btnFrame, text='Remove Selected', command=self.cb_remove)
        self.removeBtn.grid(row=0,column=2)
        
        self.saveBtn = ttk.Button(btnFrame, text='Save', command=self.cb_save)
        self.saveBtn.grid(row=0,column=3)
        
        self.updateList()
        
    def contentSelected(self, event):
        self.cNameEntry.delete(0,END)
        self.cIndexEntry.delete(0,END)
        
        sel = self.setContent.item(self.setContent.focus())
        curName = sel['values'][0]
        curIndex = sel['values'][1]
        
        self.cNameEntry.insert(0,curName)
        self.cIndexEntry.insert(0,curIndex)        
        
        
        
    def show(self):
        self.tl.wait_visibility() # can't grab until window appears, so we wait
        self.tl.grab_set()        # ensure all input goes to our window
        self.tl.wait_window()     # block until window is destroyed
        return self.isValidEdit
        
    def updateList(self):        
        self.cNameEntry.delete(0,END)
        self.cIndexEntry.delete(0,END)
        
        self.setContent.delete(*self.setContent.get_children())
        
        for idx, cat in enumerate(self.struct):
            self.setContent.insert(parent='',index='end',iid = idx,text='',values=(cat,idx))
    
    def reorder(self):
        idx = self.cIndexEntry.get()
        catName = self.cNameEntry.get()
        
        if idx == '':
            return
        
        keyList = list(self.struct.keys())
        keyList.remove(catName)
        
        keyList.insert(int(idx), catName)        
        self.struct = {k: self.struct[k] for k in keyList}
        
        
    def cb_insert(self):
        catName = self.cNameEntry.get()
        if catName == '':
            return
        
        if catName in self.struct:
            messagebox.showerror("Item already exists", "Can't add an item that already exists", parent=self.tl)
            return
        else:
            self.struct[catName] = {}
        
        self.reorder()
        self.updateList()
        
    def cb_update(self):
        catName = self.cNameEntry.get()
        if catName == '':
            return
        if self.setContent.focus() == '':
            messagebox.showerror("No item selected", "You have to select an Item before you can update", parent=self.tl)
            return
        
        sel = self.setContent.item(self.setContent.focus())
        curItem = sel['values'][0]
        
        if catName in self.struct and catName != curItem:
            messagebox.showerror("Item already exists", "Can't rename an item to an already existing item", parent=self.tl)
        else:
            self.struct = {catName if k == curItem else k:v for k,v in self.struct.items()}
        
        self.reorder()       
        self.updateList()
    
    def cb_remove(self):
        if self.setContent.focus() == '':
            messagebox.showerror("No item selected", "You have to select an Item you want to remove", parent=self.tl)
            return
        
        sel = self.setContent.item(self.setContent.focus())
        curItem = sel['values'][0]
        self.struct.pop(curItem)
           
        self.updateList()
    
    def cb_save(self):
        
        if self.path == '':
            self.path = self.setName.get()
            if os.path.exists(self.path):
                messagebox.showerror("Save Error", "A set with this name already exists!", parent=self.tl)
                return
            
            try:
                os.mkdir(self.path)
            except:
                messagebox.showerror("Save Error", "Failed to create folder!", parent=self.tl)
                return
            
            self.filename = self.path + '\config.yaml'
            
        
        with open(self.filename, 'w') as f:
            yaml.dump(self.struct, f, sort_keys=False)
                        
        if self.path != self.setName.get():
            try:
                os.rename(self.path, self.setName.get())
                self.path = self.setName.get()
            except:
                messagebox.showerror("Save Error", "Failed to rename set!", parent=self.tl)
                return
            
        SyncPreviewList(self.struct, self.path)
        try:
            os.remove(self.path + "\promptList.txt")
        except:
            pass
                
        self.isValidEdit = True    
        self.tl.grab_release()
        self.tl.destroy()
          
def main():
    global sets
    def on_closing():
        
        dirtySets = False
        for s in sets:
            if sets[s].dirty:
                dirtySets = True
        
        if dirtySets:
            if messagebox.askokcancel("There are unsafed changes", "Discard Changes?"):
                root.destroy()
        else:
            root.destroy()
            
    def on_edit():
        pset = n.tab(n.select(), "text")
        global sets
        if sets[pset].dirty:
            messagebox.showerror("There are unsafed changes", "Changes have to be saved before a set can be edited")
        else:
            hasChanges = SetEdit(root, pset).show()
            if hasChanges:
                sets = addSets(n,0)
    
    def on_new():
        global sets
        hasChanges = SetEdit(root, '').show()
        if hasChanges:
            sets = addSets(n,0)

    def on_copy():
        global sets
        pset = n.tab(n.select(), "text")
        newSet = askstring(f"Copy Set", f"Input Name for copy of {pset}", parent=root)
        if newSet:
            if os.path.exists(newSet):
                messagebox.showerror("Save Error", "A set with this name already exists!", parent=root)
                return
            try:
                os.mkdir(newSet)
                os.mkdir(newSet + "\\_previews")
            except:
                messagebox.showerror("Save Error", "Failed to create folder!", parent=root)
                return

            oldFile = pset + '\config.yaml'
            newFile = newSet + '\config.yaml'
            shutil.copyfile(oldFile, newFile)
            sets = addSets(n,0)

            
    def on_copyPath():
        global sets
        pset = n.tab(n.select(), "text")
        path = os.getcwd() + "\\" + pset

        r = Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(path)
        r.update()
        r.destroy()
            
    def on_createPreviewListMissing():
        on_createPreviewList(True)
        
    def on_createPreviewListAll():
        on_createPreviewList(False)
        
            
    def on_createPreviewList(missing):
        pset = n.tab(n.select(), "text")
        if sets[pset].dirty:
            messagebox.showerror("There are unsafed changes", "Changes have to be saved before list is generated")
            return
        
        sets[pset].createPreviewList(missing)
        
        
    
    def addSets(nb, selectIndex = 0):
        
        for pset in nb.tabs():
            nb.forget(pset)
                    
        setNames = [x[0] for x in os.walk('.')]
        del setNames[0]
        setNames = [x for x in os.listdir('.') if os.path.isdir(x)]
        st = {}
        for s in setNames:
            filename = s + '\config.yaml'
            if os.path.isfile(filename):
                name = s.replace('.', '').replace('\\','')
                st[name] = (Set(nb,name))
            else:
                continue
            
        nb.select(selectIndex)
        return st
        
            
    root = Tk()
    root.title("Prompt Library")
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)
    root.protocol("WM_DELETE_WINDOW", on_closing)   
    
    n = ttk.Notebook(root)
    n.grid(sticky=(N,W,E,S))
    sets = addSets(n, 0)
    
    menubar = Menu(root)
    filemenu = Menu(menubar, tearoff=0)
    previewmenu = Menu(menubar, tearoff=0)
    filemenu.add_command(label="New", command=on_new)
    filemenu.add_command(label="Edit", command=on_edit)
    filemenu.add_command(label="Copy", command=on_copy)
    previewmenu.add_command(label="Create list of missing previews (from selection)", command=on_createPreviewListMissing)
    previewmenu.add_command(label="Create list of all previews (from selection)", command=on_createPreviewListAll)
    previewmenu.add_separator()
    previewmenu.add_command(label="Copy Path to Clipboard", command=on_copyPath)
    menubar.add_cascade(label="Sets", menu=filemenu)
    menubar.add_cascade(label="Preview", menu=previewmenu)
    root.config(menu=menubar)
    
                
    root.mainloop()

if __name__ == "__main__":
    main()
        
