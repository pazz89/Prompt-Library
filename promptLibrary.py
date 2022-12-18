# -*- coding: utf-8 -*-
"""
Created on Thu Dec 15 17:48:56 2022

@author: Pazz
"""
# from PIL import Image, PngImagePlugin

import time

from tkinter import *
from tkinter import ttk
from tkinter import font

import yaml
from yaml.loader import SafeLoader
import itertools

import os
import os.path

class CategoryList:
    def __init__(self, root, data, cat, onselect):
        self.promptName = StringVar()
        self.disable = BooleanVar()
        self.dat = data
        self.cat = cat
        self.changeCB = onselect
        self.weightVal = StringVar()
        self.weightVal.set('1.0')
        
        self.frame = ttk.Frame(root, padding=(5, 5, 5, 5))
        
        self.lbox = Listbox(self.frame, exportselection=False, height=2, width=30)
        scrl = ttk.Scrollbar(self.frame, orient=VERTICAL, command=self.lbox.yview)
        f = font.nametofont('TkTextFont')
        f.config(weight='bold')
        lbl = ttk.Label(self.frame, text=cat,font=f)
        self.dis = ttk.Checkbutton(self.frame, text="Disable", variable=self.disable, onvalue=True, command=self.cb_disabled)
        self.lbox.configure(yscrollcommand=scrl.set)
        self.lbox.bind("<<ListboxSelect>>", lambda e: self.changeCB())
        sep = ttk.Separator(self.frame, orient=HORIZONTAL)
        weight = ttk.Spinbox(self.frame, format="%.1f",increment=0.1,from_=0.0, to=10.0, textvariable=self.weightVal, width=5, command=self.changeCB)
        
        self.lbox.insert(0,"-")
        for idx, name in enumerate(self.dat[self.cat]):
            self.lbox.insert(idx+1,name)  
            
        self.lbox.grid(column=0, row=1, columnspan=3, sticky=(N,S,E,W))
        scrl.grid(column=3, row=1, sticky=(N,S,E,W))
        
        lbl.grid(column=0, row=0, pady=0, sticky=(N,S,W))
        self.dis.grid(column=2,row=0, sticky=(N,S,E))
        weight.grid(column=1,row=0, sticky=(N,S,E),padx=2)
        sep.grid(column=0,row=2, columnspan=3, sticky=(N,S,E,W), pady=5)
        
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(1, weight=1)
        
    def relist(self, data):
        self.dat = data
        self.lbox.delete(0, END)
        self.lbox.insert(0,"-")
        for idx, name in enumerate(self.dat[self.cat]):
            self.lbox.insert(idx+1,name)  
    
    def grid(self, **kwargs):
        self.frame.grid(kwargs)
        
    def cb_disabled(self):
        d = self.disable.get()
        s = DISABLED if d == True else NORMAL
        self.lbox.configure(state=s) #Add this command after selection
        self.changeCB()
        
    def getDisabled(self):
        return self.disable.get()
    
    def getName(self):
        return self.cat
    
    def getPromptCount(self):
        return len(self.dat[self.cat])
    
    def getPrompt(self):
        i = self.lbox.curselection()
        weight = self.weightVal.get()
        p = ''
        if len(i) > 0 and self.getDisabled() == False and i[0] > 0:
            p += '' if weight =='1.0' else '('
            sel = self.lbox.get(i)
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
        

class PromptPreview:
    def __init__(self, root):
        self.acpy = BooleanVar()
        self.frame = ttk.Frame(root, padding=(5, 5, 5, 5))
        self.promptText = Text(self.frame, width=40, height=10,wrap = "word")    
        scrl = ttk.Scrollbar(self.frame, orient=VERTICAL, command=self.promptText.yview)
        f = font.nametofont('TkTextFont')
        f.config(weight='bold')
        lbl = ttk.Label(self.frame, text="Prompt", font=f)
        self.promptText.configure(yscrollcommand=scrl.set)
        self.cpyBtn = ttk.Button(self.frame, text='Copy', command=self.copy)
        self.autoCpy = ttk.Checkbutton(self.frame, text="Auto Copy", variable=self.acpy, onvalue=True)
        
        lbl.grid(column=0, row=0, pady=0, sticky=(N,S,W))
        self.promptText.grid(column=0, row=1, sticky=(N,S,E,W), columnspan=3)
        scrl.grid(column=3, row=1, sticky=(N,S,E,W))
        self.cpyBtn.grid(column=0,row=2, sticky=(N,S,E,W), pady=5)
        self.autoCpy.grid(column=2,row=2, sticky=(N,S,E,W), pady=5, columnspan=2)
        
        self.frame.grid_columnconfigure(0, weight=1)
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
        
    def setFocus(self):
        self.cpyBtn.focus_set()
                

class Set:
    def __init__(self, root, path):    
        
        name = path.replace('.', '').replace('\\','')
        filename = path + '\config.yaml'
        frame = ttk.Frame(root)
        root.add(frame, text=name)
        
        with open(filename) as f:
            struct = yaml.load(f, Loader=SafeLoader)
            
        self.catList = []
        for idx, cat in enumerate(struct):
            c = CategoryList(frame, struct, cat, self.listboxSelectionChanged)
            c.grid(column=0, row=idx, sticky=(N,W,E,S))
            frame.grid_rowconfigure(idx,weight=c.getPromptCount())
            self.catList.append(c)
        
        self.pPreview = PromptPreview(frame)
        self.pPreview.grid(column=2, row=0, rowspan=3, sticky=(N,W,E,S))
        
        ttk.Separator(frame, orient=VERTICAL).grid(column=1, row=0, rowspan=len(struct), sticky=(N,W,E,S))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(2, weight=1)    
        
    def listboxSelectionChanged(self):
        pp = ''
        np = ''
        for c in self.catList:
            p = c.getPrompt()
            n = c.getNegativePrompt()
            pp += p + "," if p else ''
            np += n + "," if n else ''
            
        pp = pp.removesuffix(",")
        np = np.removesuffix(",")
        pp += '\nNegative prompt: '+np if np else ''
        
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
                
def main():
    root = Tk()
    root.title("Prompt Library")
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)
    n = ttk.Notebook(root)
    n.grid(sticky=(N,W,E,S))

    setNames = [x[0] for x in os.walk('.')]
    del setNames[0]

    for s in setNames:
        filename = s + '\config.yaml'
        if os.path.isfile(filename):
            Set(n,s)
        else:
            continue
        
        
    root.mainloop()

if __name__ == "__main__":
    main()
        
