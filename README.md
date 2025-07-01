# ColorMatchTool
A Python GUI script that automatically matches the average color between reference and target images.

# What It Does
The Color Match Tool analyzes the average RGB color of reference images and applies that color tone to corresponding target images. 

# How It Works
The Color Matching Algorithm

Color Analysis: Calculates the average RGB values of each reference image

Mask Processing: Optionally excludes pixels matching a specific color (useful for irrelevant areas of the reference image, i.e. empty black parts of videogame textures)

Color Shifting: Applies the difference between reference and target averages to every each individual pixel, preserving all details. It's not applying a tint to the target image, but changes the color of every pixel individually.

Output Generation: Saves processed target images with _AVGCOLOR suffix

![image](https://github.com/user-attachments/assets/88b0852c-7fa6-432b-ab85-32c39d7d72ab)

![image](https://github.com/user-attachments/assets/5257bbe3-5fbf-43ce-9da4-c6870ac6539e)
