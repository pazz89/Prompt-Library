# Prompt-Library
 A simple Python UI to manage your favourite prompts for prompt based image generation

## How to use
This application allows to combine prompts from different categories (like 'Subject' , 'Details') to one prompt. It is mainly targeted to be used with https://github.com/AUTOMATIC1111/stable-diffusion-webui but I guess it can be used for any other project aswell. Different Sets can be created if for example you want to separte your SD1.5 and SD2.0 prompts. This can be done by creating subfolders. Each subfolder needs a 'config.yaml' file which contains the prompts and their display names etc. The structure of this config file is fairly simple and can be seen in the template file.
Here is a screenshot of the application:
![Alt text](doc/PromptLibraryInterface.png "Interface of Prompt-Library")

The option 'Auto Copy' allows to copy the current prompt to the clipboard on every selection change

## Future plans
If time allows, I have plans to add:
* Prompt Editor to create and delete prompts from the interface instead manually editing the config.yaml
* Preview function to display a preview of the currently selected prompt (exponential amount of images necessary though)
* Rewrite for gradio to integrate as extension to https://github.com/AUTOMATIC1111/stable-diffusion-webui

## Installation
* Make sure Python is installed on your Computer
* Download the files
* Install the required Modules `$ pip install -r requirements.txt`
* Run promptLibrary.py `python promptLibrary.py`